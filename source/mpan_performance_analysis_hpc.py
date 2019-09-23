"""
A script which processes the Electralink PV out-turn data and
performs nearest neighbour yield analysis to filter out
systems which are faulty or have corrupted metadata.

- First Authored 2018-05-08
- Owen Huxley <othuxley1@sheffield.ac.uk>
"""
try:
    from ConfigParser import SafeConfigParser
except ImportError:
    from configparser import SafeConfigParser
import pytz
import time as TIME
import numpy as np
import pandas as pd
from datetime import date, datetime, timedelta
from csv import reader
import os
import sys
import _pickle as pickle

from dbconnector import DBConnector

from generic_tools import GenericException

def main():
    PA_instance = PerformanceAnalyser()

    PA_instance.download_EL_meta()
    PA_instance.download_passiv_meta()
    PA_instance.download_EL_data()

    import pdb; pdb.set_trace()

    return()

class PerformanceAnalyser:
    def __init__(self, quiet=False):
        self.quiet = quiet
        self.config = self.load_config("C:/Users/owenh/Documents/PhD/Gitkraken/sensitivity_analysis/"
                                       "MPAN_performance_analysis/Config/config.ini")
        self.timer = 0
        self.neighbour_data = {}
        self.local = pytz.timezone("Europe/London")
        self.day = "2017-01-01" # how do I pass this from the iceberg job script
        self.EL_data = None
        self.EL_meta = None
        self.passiv_meta = None

    @staticmethod
    def load_config(file=None):
        """
        A function to load the config file.

        Parameters
        ----------
        `file` : str
            The path of the config file.
        Returns
        -------
        `config` : dict
            A dictionary containing the config parameters.

        """
        try:
            parser = SafeConfigParser()
            config = {}
            parser.read(file)
            config["config_location"] = file
            config["mysql_options_readwrite_electralink"] = parser.get("other", "mysql_options_readwrite_electralink")
            config["mysql_options_othuxley1_electralink"] = parser.get("other", "mysql_options_othuxley1_electralink")
            config["mysql_options_readwrite_pvstream"] = parser.get("other", "mysql_options_readwrite_pvstream")
            config["error_logfile"] = parser.get("other", "error_logfile")
            config["EL_readings_table"] = parser.get("other", "EL_readings_table")
            config["EL_meta_table"] = parser.get("other", "EL_meta_table")
            config["passiv_meta_view"] = parser.get("other", "passiv_meta_view")
            config["passiv_data"] = parser.get("other", "passiv_data")
            return config
        except Exception as err:
            raise GenericException(msg_id="PVLive.load_config", msg="Error loading config, "
                                   "please check that the config file (%s) exists and lists all of "
                                   "the required values." % file_location, filename=ERROR_LOGFILE,
                                   err=err)
            return

    def download_EL_data(self):
        today = self.day
        today = to_unixtime(datetime.strptime(today, "%Y-%m-%d"), timezone_="UTC")
        tomorrow = today + ( 24 * 60 * 60)
        readings_table = self.config["EL_readings_table"]
        with DBConnector(mysql_defaults=self.config["mysql_options_readwrite_electralink"],
                         session_tz="UTC") as dbc:
            sql_template = ("SELECT `MPAN`, UNIX_TIMESTAMP(`utc_timestamp`), `period_meter_consumption` FROM {} WHERE UNIX_TIMESTAMP(`utc_timestamp`)"
                             "BETWEEN '{}' and '{}';")
            sql_template = sql_template.format(readings_table, today, tomorrow)
            data = dbc.query(sql_template)
            # import pdb; pdb.set_trace()
            self.EL_data = np.asarray(data)
        return data

    def download_EL_meta(self):
        meta_table = self.config["EL_meta_table"]
        with DBConnector(mysql_defaults=self.config["mysql_options_readwrite_electralink"],
                         session_tz="UTC") as dbc:
            sql_template = ("SELECT `MPAN`, `max_capacity`, `latitude`, `longitude` FROM {};")
            sql_template = sql_template.format(meta_table)
            data = dbc.query(sql_template)
            self.EL_meta = np.asarray(data)
        return data

    def download_passiv_meta(self):
        meta_table = self.config["passiv_meta_view"]
        with DBConnector(mysql_defaults=self.config["mysql_options_readwrite_pvstream"],
                         session_tz="UTC") as dbc:
            sql_template = ("SELECT `ss_id`, `latitude`, `longitude`, `orientation`, `tilt`,"
                            "`kWp`, `area`, UNIX_TIMESTAMP(`operational_at`) FROM {};")
            sql_template = sql_template.format(meta_table)
            data = dbc.query(sql_template)
            self.passiv_meta = np.asarray(data)
        return data

    def mpan_performance(self, mpan):
        """
        A function to calculate the
        """
        this_mpan_data = self.data[data[:, 0] == mpan, :]
        other_mpan_data = self.data[data[:, 0] != mpan, :]
        unixtimes = np.unique(this_mpan_data[:, 1])
        results = []
        tot = len(unixtimes)
        i = 0
        with open(self.results_file, 'a') as out:
            for unixtime in unixtimes:
                this_mpan_this_hh = this_mpan_data[this_mpan_data[:, 1] == unixtime, :]
                this_mpan_this_hh = this_mpan_hh[:, -1].squeeze()
                other_mpans_this_hh = other_mpan_data[other_mpan_data[:, 2] == unixtime, -1]
                measurement_qty_id = this_mpan_this_hh[0,1]
                ACTUAL_ESTIMATED_INDICATOR = this_mpan_this_hh[0,3]
                if mpan not in self.neighbour_data:
                    neighbour_meta = get_neighbour_data(mpan)
                neighbour_data = other_mpans_this_hh[np.in1d(other_mpans_this_hh[:, 0], neigbour_meta[:, 0])] # what is this line doing?
                neighbour_yields = neighbour_data[:, -1] / neighbour_data[:, 2]
                median_yield = np.median(neighbour_yields)
                std_dev = np.std(neighbour_yields)
                this_yield = this_mpan_this_hh[-1] / this_mpan_this_hh[2]
                low_limit = median_yield - 3 * std_dev
                hi_limit = median_yield + 3 * std_dev
                # change these codes with words - pass fail etc
                if low_limit < this_yield < hi_limit:
                    code = 1 # Pass
                elif this_yield <= low_limit:
                    code = 0 # Fail low
                elif this_yield >= hi_limit:
                    code = 2 # Fail high
                else:
                    code = 4 # No data ??

                out.write("{},{},{},{},{},{}".format(int(mpan), measurement_qty_id,  int(unixtime), ACTUAL_ESTIMATED_INDICATOR,
                          this_mpan_this_hh, this_yield, median_yield, std_dev, code))
                # self.results_file.write("{},{},{},{},{},{}\n".format(*result))
                i+=1

        return results

    def mpan_passiv_neighbour(self):
        passiv_meta = self.passiv_meta
        mpan_meta = self.EL_meta[]


    def get_neighbour_data(self, mpan, ):

        meta = self.metadata
        this_location = meta[meta[:, 0] == mpan, 2:4].squeeze()
        other_locations = meta[meta[:, 0] != mpan, 2:4]
        km2lat = lambda x: degrees(x / 6371.0) # convert desired km buffer to geodesic equivalent
        limit = km2lat(50)
        lat_min = this_location[0] - limit
        lat_max = this_location[0] + limit
        lon_min = this_location[1] - limit
        lon_max = this_location[1] + limit
        # import pdb; pdb.set_trace()
        good_meta_indices = (meta[:, 2] >= lat_min) & (meta[:, 2] <= lat_max) & (meta[:, 3] >= lon_min) & (meta[:, 3] <= lon_max) & (meta[:, 0] != mpan)
        neigbour_meta = meta[good_meta_indices, :]
        #neighbour_data = data[np.in1d(data[:, 0], neigbour_meta[:, 0])]
        self.neighbour_data[mpan] = neighbour_meta
        return(neighbour_meta)

    def myprint(self, msg, time_section=None):
        """Use this function to print updates unless class attribute quiet is set to True."""
        if not self.quiet:
            if time_section == "stop":
                msg += " ({:.2f} seconds)".format(TIME.time() - self.timer)
            print(msg)
            if time_section == "start":
                self.timer = TIME.time()

def to_unixtime(datetime_, timezone_=None):
    """
    Convert a python datetime object, *datetime_*, into unixtime int

    Parameters
    ----------
    `datetime_` : datetime.datetime
        Datetime to be converted
    `timezone_` : string
        The timezone of the input date from Olson timezone database. If *datetime_* is timezone
        aware then this can be ignored.
    Returns
    -------
    float
        Unixtime i.e. seconds since epoch
    Notes
    -----
    unixtime == seconds since epoch (Jan 01 1970 00:00:00 UTC)\n
    See Also
    --------
    `Python module pytz docs <http://pythonhosted.org/pytz/>`_,
    :func:`UKPVLiveTestCase.test_to_unixtime`
    """
    if timezone_ is None and datetime_.tzinfo is None:
        raise GenericException(msg_id="generic_tools.to_unixtime", msg=("EITHER datetime_ must "
                                                                        "contain tzinfo OR "
                                                                        "timezone_must be passed."))
    if timezone_ is not None and datetime_.tzinfo is None:
        utc_datetime = pytz.timezone(timezone_).localize(datetime_).astimezone(pytz.utc)
    else:
        utc_datetime = datetime_.astimezone(pytz.utc)
    unixtime = int((utc_datetime - datetime(1970, 1, 1, 0, 0, 0, 0, pytz.utc)).total_seconds())
    return unixtime

if __name__ == "__main__":
    main()