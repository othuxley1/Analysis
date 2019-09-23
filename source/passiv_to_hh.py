"""
A script to munge the passiv 2 minutely data into half hourly data and upload it to the database.

- Owen Huxley <othuxley1@sheffield.ac.uk>
- First Authoured 2018-09-14
"""
try:
    from ConfigParser import SafeConfigParser
except ImportError:
    from configparser import SafeConfigParser
from datetime import datetime, timedelta
import time as TIME
import argparse
import numpy as np
import pytz
import pandas as pd
import ephem
import pytz


from dbconnector import DBConnector

from generic_tools import to_unixtime


def main():
    """
    The main function that runs the script.
    """

    munging_instance = MungingPassiv2min()
    munging_instance.myprint("Getting start and end date from database...", time_section="start")
    munging_instance.get_ss_ids()
    munging_instance.myprint("--> Finished", time_section="start")
    munging_instance.get_passiv_data()

class MungingPassiv2min:
    """ A class to resample the 5 minutley passiv intraday data into half hourly data."""
    def __init__(self, options=None):
        self.quiet = "quiet"
        self.update = False
        self.timer = 0
        self.config = self.load_config("C:/Users/owenh/Documents/PhD/Gitkraken/sensitivity_analysis"
                                       "/intraday/Config/config.ini")
        self.ss_ids = None
        self.frequency_change_date = "2017-01-17 14:00:00"
        self.horizon = -6
        if options is None:
            self.options = self.parse_options()
        else:
            self.options = dotdict(options)

    def parse_options(self):
        parser = argparse.ArgumentParser(description=("This is a command line interface (CLI) for the "
                                                  "passiv_to_hh script."),
                                         epilog="Owen Huxley 2018-10-10")
        parser.add_argument("-s", "--start", metavar="\"<yyyy-mm-dd HH:MM>\"", dest="start",
                            action="store", type=str, required=False, default=None,
                            help="Specify the start date in 'yyyy-mm-dd HH:MM' format (inclusive).")
        parser.add_argument("-e", "--end", metavar="\"<yyyy-mm-dd HH:MM>\"", dest="end",
                            action="store", type=str, required=False, default=None,
                            help="Specify the end date in 'yyyy-mm-dd HH:MM' format (inclusive).")
        parser.add_argument("-tz", "--time-zone", dest="tz_string", action="store", required=False,
                            metavar="\"<Olson timezone string>\"", type=str, default="UTC",
                            help="Specify the time zone used for the -s / --start and -e / --end "
                                 "options. Default is 'Europe/London' i.e. the local timezone in "
                                 "Sheffield.")
        parser.add_argument("-f5", "--frequency_5min", dest="freq5", action="store_true", required=False,
                            help="Specify that the data has 5 minute frequency, default is 2 minute.")
        options = parser.parse_args()
        def handle_options(options):
            """Collect options from the command line"""
            options.time_zone = pytz.timezone(options.tz_string)
            if options.start is not None and options.end is not None:
                try:
                    options.start = options.time_zone.localize(
                        datetime.strptime(options.start, "%Y-%m-%d %H:%M")
                    )
                    options.end = options.time_zone.localize(
                        datetime.strptime(options.end, "%Y-%m-%d %H:%M")
                    )
                except:
                    raise Exception("OptionsError: Failed to parse start and end datetime, make sure "
                                    "you use 'yyyy-mm-dd HH:MM' format.")
            else:
                raise Exception("OptionsError: You need to provide "
                                "BOTH the -s/--start AND -e/--end parameters.")
            return options
        return handle_options(options)

    def download_start_date(self):
        with DBConnector(mysql_defaults=self.config["mysql_options_readwrite_pvstream"],
                         session_tz="UTC") as dbc:
            sql = ("SELECT UNIX_TIMESTAMP(`date`) FROM `{}` ORDER BY `date` desc LIMIT 1")
            sql = sql.format(self.config["reading30compact_intraday"])
            start_date = dbc.query(sql)[0][0]
        return start_date

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
            config["mysql_options_readwrite_pvstream"] = parser\
                                                         .get("other",
                                                              "mysql_options_readwrite_pvstream")
            config["mysql_options_othuxley1_pvstream"] = parser\
                                                         .get("other",
                                                              "mysql_options_othuxley1_pvstream")
            config["error_logfile"] = parser.get("other", "error_logfile")
            config["reading30compact_intraday"] = parser.get("other", "reading30compact_intraday")
            config["passiv_table"] = parser.get("other", "passiv_data")
            config["passiv_meta"] = parser.get("other", "passiv_site_data")
            return config
        except:
            print("Error loading config, please check that config file exists and lists all of the"
                  " required values.")
            raise

    def get_ss_ids(self):
        """
        A function to download all ss_ids in the intraday passiv data.
        """
        with DBConnector(mysql_defaults=self.config["mysql_options_readwrite_pvstream"],
                         session_tz="UTC") as dbc:
            sql = ("SELECT `ss_id` FROM `{}` GROUP BY `ss_id`")
            sql = sql.format(self.config["passiv_table"])
            ss_ids = dbc.query(sql)
            ss_ids = [x[0] for x in ss_ids]
            self.ss_ids = ss_ids


    def get_passiv_data(self):
        """
        This function carries out the data munging. It works on one ss_id at a time.
        Returns
        -------
        `upload_array` : numpy array
            An array of half hourly data to be uploaded to the database. With Nulls for any data
            missing between the hours of sunrise and sunset, 0 for overnight readings, and measured
            readings everywhere else.
        --------
        """
        if self.options.freq5:
            minimum = 6
        else:
            minimum = 15
        ss_id_dict = {}
        for ss_id in self.ss_ids:
            if ss_id in ss_id_dict:
                print("Duplicate ss_id {}!".format(ss_id))
            else:
                print("Working with ss_id: {}".format(ss_id))
                data = self.download_ss_id_data(ss_id)
                if data.size != 0:
                    # import pdb; pdb.set_trace()
                    data_frame = pd.DataFrame(data[:, 1:], columns=["timestamps", "readings"])\
                                      .set_index("timestamps")
                    data_frame.index = pd.to_datetime(data_frame.index, unit="s", utc=True) # converting timestamp
                                                                                  # to pandas
                                                                                  # DatetimeIndex object
                    upload_data = self.resample_and_sum(data_frame, minimum, ss_id) # correct timestamp
                    if upload_data.size != 0:
                        lat, lon = self.download_ss_id_meta(ss_id)
                        # import pdb; pdb.set_trace()
                        new_index = pd.DatetimeIndex(start=self.options.start.replace(hour=0, minute=30,
                                                                                      second=0),
                                                     freq="30T", end=self.options.end.date() + timedelta(days=1),
                                                     tz=pytz.utc, closed=None)
                        # import pdb; pdb.set_trace()
                        upload_data = upload_data.reindex(new_index, fill_value=None)
                        daylight_times = self.generation_times(lat, lon, self.horizon, upload_data)
                        upload_data[(daylight_times["Rising"] > upload_data.index)     # setting hh's with
                                    | (upload_data.index > daylight_times["Setting"])  # insufficient
                                    & (upload_data["readings"] is None)] = 0           # readings to None
                        # import pdb; pdb.set_trace()
                        upload_data.index = pd.MultiIndex.from_arrays([upload_data.index.date,
                                                                       upload_data.index.time],
                                                                      names=['Date', 'Time'])
                        days = upload_data.values.shape[0] // 48
                        upload_values = upload_data.values.reshape(days, 48)
                        import pdb; pdb.set_trace()
                        upload_timestamps = np.unique(upload_data.index
                                                      .get_level_values(level=0))\
                                            .astype(np.int64) // 10**9           # astype(np.int64)
                                                                                 # returns time in
                                                                                 # nanoseconds
                        upload_array = np.column_stack((upload_timestamps[:-1],
                                                        np.full(upload_timestamps[:-1].shape,
                                                                ss_id),
                                                        upload_values))
                        self.upload_reading30compact(upload_array)
                    else:
                        upload_array = upload_data.values
                else:
                    upload_array = data
        return upload_array

    @staticmethod
    def generation_times(latitude, longitude, horizon, data_frame):
        """
        This function calculates the sunrise and sunset times for all dates in the DatetimeIndex
         object associated with the DataFrame data_frame at the location specified by the latitude
         and longitude.

        Parameters
        ----------
        `latitude` : int
            The latitude in degrees.
        `longitude` : int
            The longitude in degrees.
        `horizon` : int
            The altitude of the upper limb of a body at the moment you consider it to be rising and
             setting.
        `data_frame` : object
            The DataFrame with the index of dates for which you would like to calculate the
            sunrise and sunset times.
        Returns
        -------
        `daylight_data_frame` : object
            A DataFrame with the same DatetimeIndex as the original DataFrame object and two
            associated Series "sunrise" and "sunset".

        See Also
        --------
        `pyephem` : http://rhodesmill.org/pyephem/quick.html
        """
        PV_system = ephem.Observer()
        PV_system.lat = np.radians(latitude)
        PV_system.long = np.radians(longitude)
        PV_system.horizon = np.radians(horizon)
        rising_setting = []
        dates = data_frame.index.date
        for dt in dates:
            PV_system.date = dt
            sun = ephem.Sun(PV_system)
            rising = PV_system.next_rising(sun)
            setting = PV_system.next_setting(sun)
            rising_setting.append([rising.datetime(), setting.datetime()])
        rising_setting = np.array(rising_setting)
        daylight_data_frame = pd.DataFrame(data=rising_setting, index=data_frame.index,
                                           columns=["Rising", "Setting"])
        return daylight_data_frame

    def download_ss_id_meta(self, ss_id):
        """
        A function to download the metadata for a given ss_id.

        Parameters
        ----------
        `ss_id` : int
            Unique identifier for pv system.
        Returns
        -------
        `data[0]` : tuple
            A tuple containing the latitude and longitude for the ss_id passed.

        """
        with DBConnector(mysql_defaults=self.config["mysql_options_readwrite_pvstream"],
                         session_tz="UTC") as dbc:
            sql_template = ("SELECT `latitude`, `longitude` FROM {} where `ss_id` = {}")
            sql = sql_template.format(self.config["passiv_meta"], ss_id)
            data = dbc.query(sql)
        return data[0]

    def resample_and_sum(self, data, minimum, ss_id):
        """
        A function which resamples the data from or 5 minutely to half hourly. The resampled data
        is None if there are missing values for a given half hour.

        Parameters
        ----------
        `data` : object
            Pandas DataFrame with a DatetimeIndex.
        `freq` : str
            A string to specify whether the frequency of the input data is 2 or 5 minutley.
        Returns
        -------
        `upload_data` : object
            DataFrame object with a new half hourly index. Where there wasn't a complete half hour
             of readings the half hour reading was set to zero.

        Notes
        -----
        This function should be rewritten so that the minimum variable is calculated from
        a frequency passed as a function parameter. As opposed to being hard coded.
        """
        if  data.empty:
            return data
        resample = data.resample("30T", closed="left", label="right")
        sum30 = resample.mean()
        sum30 = sum30 * 0.5
        sum30[sum30 < 0] = None # converting negative readings to zero
        size30 = resample.size()
        # mask = (size30 == minimum). values or 
        good_data = sum30[(size30 == minimum).values]
        return good_data

    def download_ss_id_data(self, ss_id):
        """
        A function to download the data for a given ss_id.

        Parameters
        ----------
        `ss_id` : int
            Unique identifier for pv system.
        Returns
        -------
        `np.array(data)` : numpy array
            An array containing all the data for the ss_id passed with columns;
             (ss_id, timestamp, readings).
        """
        # import pdb; pdb.set_trace()
        with DBConnector(mysql_defaults=self.config["mysql_options_readwrite_pvstream"],
                         session_tz="UTC") as dbc:
            sql_template = ("SELECT `ss_id`, UNIX_TIMESTAMP(`timestamp`), `data` FROM {} WHERE"
                            " `timestamp` BETWEEN '{}' and '{}' and `ss_id` = {};")
            # print(sql_template)
            sql = sql_template.format(self.config["passiv_table"],
                                      datetime.strftime(self.options.start, "%Y-%m-%d %H:%M"),
                                      datetime.strftime(self.options.end, "%Y-%m-%d %H:%M"), ss_id)
            # print(sql)
            # import pdb; pdb.set_trace()

            data = dbc.query(sql)
        return np.array(data)

    def myprint(self, msg, time_section=None):
        """
        Use this function to print updates unless class attribute quiet is set to True.

        Parameters
        ----------
        `msg` : str
            The message to be printed.
        `time_section`: str
            A command to specify whether timing should "start" or "stop".
        """
        if not self.quiet:
            if time_section == "stop":
                msg += " ({:.2f} seconds)".format(TIME.time() - self.timer)
            print(msg)
            if time_section == "start":
                self.timer = TIME.time()

    def prepare_db(self):
        """
        Truncates the database table.
        """
        with DBConnector(mysql_defaults=self.config["mysql_options_admin_pvstream"],
                         session_tz="UTC") as dbc:
            sql_template = ("TRUNCATE TABLE `{}`;".format(self.config["reading30compact_intraday"]))
            dbc.iud_query(sql_template)

    def upload_reading30compact(self, data):
        """
        A function to upload the results to the reading30compact table in the database.

        Parameters
        ----------
        `data` : numpy array
            The array of data to upload. It needs to be in the same format as the reading30compact
             table in the database.

        """
        data = data.tolist()
        data = [[None if np.isnan(x) else x for x in line] for line in data]
        with DBConnector(mysql_defaults=self.config["mysql_options_readwrite_pvstream"],
                         session_tz="UTC") as dbc:
            sql_template = ("INSERT INTO `{}` (`date`, `ss_id`, `t1`, `t2`, `t3`, `t4`, `t5`, `t6`,"
                            " `t7`, `t8`, `t9`, `t10`, `t11`, `t12`, `t13`, `t14`, `t15`,"
                            " `t16`, `t17`, `t18`, `t19`, `t20`, `t21`, `t22`, `t23`, `t24`,"
                            " `t25`, `t26`, `t27`, `t28`, `t29`, `t30`, `t31`, `t32`, `t33`,"
                            " `t34`, `t35`, `t36`, `t37`, `t38`, `t39`, `t40`, `t41`, `t42`,"
                            " `t43`, `t44`, `t45`, `t46`, `t47`, `t48`) values"
                            " (FROM_UNIXTIME(%s), %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,"
                            " %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,"
                            " %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,"
                            " %s, %s, %s) "
                            "ON DUPLICATE KEY UPDATE "
                            "`t1`=VALUES(`t1`)",
                            "`t2`=VALUES(`t2`)",
                            "`t3`=VALUES(`t3`)",
                            "`t4`=VALUES(`t4`)",
                            "`t5`=VALUES(`t5`)",
                            "`t6`=VALUES(`t6`)",
                            "`t7`=VALUES(`t7`)",
                            "`t8`=VALUES(`t8`)",
                            "`t9`=VALUES(`t9`)",
                            "`t10`=VALUES(`t10`)",
                            "`t11`=VALUES(`t11`)",
                            "`t12`=VALUES(`t12`)",
                            "`t13`=VALUES(`t13`)",
                            "`t14`=VALUES(`t14`)",
                            "`t15`=VALUES(`t15`)",
                            "`t16`=VALUES(`t16`)",
                            "`t17`=VALUES(`t17`)",
                            "`t18`=VALUES(`t18`)",
                            "`t19`=VALUES(`t19`)",
                            "`t20`=VALUES(`t20`)",
                            "`t21`=VALUES(`t21`)",
                            "`t22`=VALUES(`t22`)",
                            "`t23`=VALUES(`t23`)",
                            "`t24`=VALUES(`t24`)",
                            "`t25`=VALUES(`t25`)",
                            "`t26`=VALUES(`t26`)",
                            "`t27`=VALUES(`t27`)",
                            "`t28`=VALUES(`t28`)",
                            "`t29`=VALUES(`t29`)",
                            "`t30`=VALUES(`t30`)",
                            "`t31`=VALUES(`t31`)",
                            "`t32`=VALUES(`t32`)",
                            "`t33`=VALUES(`t33`)",
                            "`t34`=VALUES(`t34`)",
                            "`t35`=VALUES(`t35`)",
                            "`t36`=VALUES(`t36`)",
                            "`t37`=VALUES(`t37`)",
                            "`t38`=VALUES(`t38`)",
                            "`t39`=VALUES(`t39`)",
                            "`t40`=VALUES(`t40`)",
                            "`t41`=VALUES(`t41`)",
                            "`t42`=VALUES(`t42`)",
                            "`t43`=VALUES(`t43`)",
                            "`t44`=VALUES(`t44`)",
                            "`t45`=VALUES(`t45`)",
                            "`t46`=VALUES(`t46`)",
                            "`t47`=VALUES(`t47`)",
                            "`t48`=VALUES(`t48`);")
            sql = sql_template[0].format(self.config["reading30compact_intraday"])
            dbc.iud_query(sql, data)
            print("uploaded data for ss_id: {}\n".format(data[0][1]))

def from_unixtime(unixtime_, timezone_="UTC"):
    """
    Convert a unixtime int, *unixtime_*, into python datetime object

    Parameters
    ----------
    `unixtime_` : int
        Unixtime i.e. seconds since epoch
    `timezone_` : string
        The timezone of the output date from Olson timezone database. Defaults to utc.
    Returns
    -------
    datetime.datetime
        Python datetime object (timezone aware)
    Notes
    -----
    unixtime == seconds since epoch (Jan 01 1970 00:00:00 UTC)\n
    pytz http://pythonhosted.org/pytz/\n
    Unit test: UKPVLiveTestCase.test_to_unixtime
    """
    return datetime.fromtimestamp(unixtime_, tz=pytz.timezone(timezone_))

if __name__ == "__main__":
    main()
