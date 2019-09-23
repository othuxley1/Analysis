"""
A script to derive a national PV site list.

- First Authored 2018-11-22
- Owen Huxley <othuxley1@sheffield.ac.uk
"""

import pandas as pd
import numpy as np
import time as TIME
from datetime import datetime
import picklecache
import os
import re
import io
import codecs
import pickle
import sys
from configparser import ConfigParser

def main():
    SLDerivation = SiteListDerivation()

def cached(cachefile):
    """
    A function that creates a decorator which will use "cachefile" for caching the results of the decorated function "fn".
    """
    def decorator(fn):  # define a decorator for a function "fn"
        def wrapped(*args, **kwargs):   # define a wrapper that will finally call "fn" with all arguments
            # if cache exists -> load it and return its content
            if os.path.exists(cachefile):
                with open(cachefile, 'rb') as cachehandle:
                    print("using cached result from '%s'" % cachefile)
                    return pickle.load(cachehandle)

            # execute the function with all arguments passed
            res = fn(*args, **kwargs)

            # write to cache file
            with open(cachefile, 'wb') as cachehandle:
                print("saving result to cache '%s'" % cachefile)
                pickle.dump(res, cachehandle)

            return res

        return wrapped

    return decorator   # return this "customized" decorator that uses "cachefile"

class SiteListDerivation:
    """A class to derive the national PV sitelist from the raw data files."""

    def __init__(self, options=None):
        self.quiet = False
        self.FIT_file = r"C:/Users/owenh/Google Drive/PhD/Analysis_Owen/Capacity Mismatch Paper/"\
                         "raw/FIT/feed_in_tariff_installation_report_-_30_sept_2018_complete.csv"
        self.RO_file = r"C:/Users/owenh/Google Drive/PhD/Analysis_Owen/Capacity Mismatch Paper/"\
                        "raw/RO/RO - AccreditedStationsExternalPublic.csv"
        self.REPD_file = r"C:/Users/owenh/Google Drive/PhD/Analysis_Owen/Capacity Mismatch Paper/"\
                          "raw/REPD/repd-database-sep-2018.csv"
        self.SM_file = r"C:/Users/owenh/Google Drive/PhD/Analysis_Owen/Capacity Mismatch Paper/"\
                        "raw/SM/SM_report_4_20181122.csv"
        self.EL_file = r"C:/Users/owenh/Google Drive/PhD/Analysis_Owen/Capacity Mismatch Paper/"\
                        "raw/EL/Solar_Sheffield_Site_Data.csv"
        self.config_file = "Config/PV_site_list_derivation.ini"
        self.config = self.load_config(self.config_file)
        self.data = None
        self.run()

    def run(self):
        """The main function that executes all the class methods."""

        # loading FIT
        # ========================================================================
        self.myprint("Loading the FIT data and sorting by installed capacity....",
                     time_section="start")
        FIT_data = self.load_FIT()
        self.myprint("    --> Finished.", time_section="stop")

        # loading REPD
        # =========================================================================
        self.myprint("Loading the REPD data and sorting by installed capacity....",
                     time_section="start")
        REPD_data = self.load_REPD()
        self.myprint("    --> Finished.", time_section="stop")

        # loading SM
        # =========================================================================
        self.myprint("Loading the SM data and sorting by installed capacity....",
                     time_section="start")
        SM_data = self.load_SM()
        self.myprint("    --> Finished.", time_section="stop")

        # loading EL
        # =========================================================================
        self.myprint("Loading the EL data and sorting by installed capacity....",
                     time_section="start")
        EL_data = self.load_EL()
        self.myprint("    --> Finished.", time_section="stop")

        # loading RO
        # =========================================================================
        self.myprint("Loading the RO data and sorting by installed capacity....",
                     time_section="start")
        RO_data = self.load_RO()
        self.myprint("    --> Finished.", time_section="stop")

        self.data = {"FIT_data" : FIT_data, "REPD_data" : REPD_data, "SM_data" : SM_data,
                     "EL_data" : EL_data, "RO_data" : RO_data}
        # ========================================================================
        self.derivation()
        import pdb; pdb.set_trace()

    def derivation(self, sm_cut_off=5):
        """
        Here the national sitelist is derived.

        Parameters
        ----------
        `sm_cot_off` : float
            The cut off in MW to use for selecting non-fit data from Solar Media
            in deriving the site-list.
        Returns
        -------
        `parameter` : type
            Description
        Notes
        -----

        See Also
        --------
        """
        repd_geq_cutoff =  self.data["REPD_data"].loc[self.data["REPD_data"]["Capacity"]
                                                      >= sm_cut_off].copy()
        sm_leq_cutoff = self.data["SM_data"].loc[self.data["SM_data"]["Capacity"] < sm_cut_off
                                  & ~self.data["SM_data"]["Funding"].isin(["FIT"])].copy()
        fit_leq_5 = self.data["FIT_data"].loc[self.data["FIT_data"]["Capacity"]
                                                         < sm_cut_off].copy()
        frames = (repd_geq_cutoff, sm_leq_cutoff, fit_leq_5)
        site_list = pd.concat(frames)
        # import pdb; pdb.set_trace()
    
    @staticmethod
    def load_config(file=""):
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
            parser = ConfigParser()
            config = {}
            parser.read(file)
            config["config_location"] = file
            config["mysql_options_readwrite_capacity_analysis"] = parser\
                                                         .get("mysql_files",
                                                              "mysql_options_ssfdb2_readwrite_capacity_analysis")
            config["error_logfile"] = parser.get("other", "error_logfile")
            config["soalarsite_table"] = parser.get("mysql_tables", "solarsite_table")
            return config
        except:
            print("Error loading config, please check that config file exists and lists all of the"
                  " required values.")
            raise

    @cached("../data/site_list/fit_datframe.pickle")
    def load_FIT(self):
        with open(self.FIT_file, 'r') as fid:
            data = []
            fit_not_pv = 0
            next(fid)
            i = 1
            j = 0
            print_progress(j, 900000)
            for line in fid:
                i += 1
                # line = re.sub(r'"[^"]*"', lambda m: m.group(0).replace(",", ";"), line)
                row = line.strip().split(",")
                # if len(row) == 1:
                #     continue
                if len(row) != 19:
                    raise Exception("Parsed the wrong number of columns on line {} of the EL file "
                                    "('{}').".format(i, self.FIT_file))
                elif row[2] == "Photovoltaic":
                    j += 1
                    if 100000 % j:
                        print_progress(j, 900000)
                    # postcode = row[1] # if row[1]!="" else np.nan
                    capacity = float(row[3]) / 1000. if self.isNumber(row[3]) else np.nan
                    declared_net_capacity = float(row[4]) / 1000. if self.isNumber(row[4]) else np.nan
                    commission_date = datetime.strptime(row[6], "%d-%m-%Y %H:%M:%S").date() if row[6] != "" else np.nan
                    # lat
                    # lon
                    this_data = [row[0], row[1], capacity, declared_net_capacity, commission_date, row[8]]
                    # if this_data not in data:
                    data.append(this_data)
                else:
                    fit_not_pv += 1
            print_progress(900000, 900000)

        df = pd.DataFrame(np.array(data), columns=["Extension", "Postcode", "Capacity", "DN Capacity", "Install Date", "Export Status"])
        df.sort_values(by="Capacity", inplace=True, ascending=False)
        df["Source"] = "FIT"
        return df


    def load_REPD(self):
        """
        Loads REPD csv file
        """
        # ID, capacity, postcode, install_date
        with io.open(self.REPD_file, "rt", newline="") as fid:
            data = []
            next(fid)
            content = fid.read()
            content = re.sub(r'"[^"]*"', lambda m: m.group(0).replace("\r", " ").replace("\n", " "),
                             content)
            i = 1
            for line in content.split("\r\n"):
                i += 1
                line = re.sub(r'"[^"]*"', lambda m: m.group(0).replace(",", ";"), line)
                row = line.strip().split(",")
                if len(row) == 1:
                    continue
                if len(row) != 45:
                    raise Exception("Parsed the wrong number of columns on line {} of the REPD file "
                                    "('{}').".format(i, filename))
                test = (row[5] == "Solar Photovoltaics") and  (row[15] == "Operational")
                if test:
                    instal_date = datetime.strptime(row[44], "%Y-%m-%d").date() if row[44] != "" else np.nan
                    capacity = float(row[6]) if self.isNumber(row[6]) else np.nan
                    fit = self.isNumber(row[9])
                    data.append([row[1], capacity, row[21], row[22], row[23], instal_date])
                else:
                    continue
        df = pd.DataFrame(np.array(data), columns=["ID", "Capacity", "Postcode", "Eastings",
                                                     "Northings", "Install Date"])
        df.sort_values(by="Capacity", inplace=True, ascending=False)
        df["Source"] = "REPD"
        return df

    def load_RO(self):
        """
        Loads RO csv file
        """
        # ID, capacity, postcode, install_date
        data = []
        with io.open(self.RO_file, "rt", newline="\r\n") as fid:
            next(fid)
            i = 1
            for line in fid:
                i += 1
                # import pdb; pdb.set_trace()
                line = re.sub(r'"[^"]*"', lambda m: m.group(0).replace(",", ";"), line)
                row = line.strip().split(",")
                if len(row) == 1:
                    continue
                if len(row) != 14:
                    raise Exception("Parsed the wrong number of columns on line {} of the RO file "
                                    "('{}').".format(i, self.RO_file))
                postcode = re.findall("[A-Z][A-Z]?[0-9][0-9]? *[0-9][A-Z][A-Z]", row[-1])
                postcode = postcode[0] if len(postcode) > 0 else ""
                install_date = datetime.strptime(row[9], "%d/%m/%Y").date() if row[9] != "" else np.nan
                capacity = float(row[4]) / 1000. if self.isNumber(row[4]) else np.nan
                data.append([row[0], capacity, postcode, install_date])
        df = pd.DataFrame(np.array(data), columns=["ID", "Capacity", "Postcode", "Install Date"])
        df.sort_values(by="Capacity", inplace=True, ascending=False)
        df["Source"] = "RO"
        return df

    def load_SM(self):
        """
        Loads solar media csv file

        Notes
        -----
        The Solar Media file should be saved as a csv
        with only the following columns:
        Solar Media Ref #, Site Name, Final Capacity MWp-dc, Postal Address, Postcode, Postal Town,
        County, District, Region, Country, Eastings, Northings, Day-Month-Year, Completion Month,
        Completion Quarter, Completion Calendar Year, Original Funding Route,  Final Funding Route.

        Be careful when data is deleted using excel. The column must be right-clicked and deleted
        otherwise excel will leave empty strings inplace of deleted data.

        ID, capacity, postcode, install_date
        """
        data = []
        with io.open(self.SM_file, "rt", newline="") as fid:
            # skipping header line
            next(fid)
            # reading file as one long string
            content = fid.read()
            i = 1
            for line in content.split("\r\n"):
                i += 1
                line = re.sub(r'"[^"]*"', lambda m: m.group(0).replace(",", ";"), line)
                row = line.strip().split(",")
                if len(row) == 1:
                    continue
                if len(row) != 18:
                    raise Exception("Parsed the wrong number of columns on line {} of the SM file "
                                    "('{}').".format(i, filename))
                install_date = datetime.strptime(row[12], "%d-%m-%Y").date() if row[12] != "" else np.nan
                capacity = float(row[2]) if self.isNumber(row[2]) else np.nan
                data.append([row[0], capacity, row[4], row[10], row[11], install_date, row[-1]])
        df = pd.DataFrame(np.array(data), columns=["ID", "Capacity", "Postcode", "Eastings", "Northings",
                                                   "Install Date", "Funding"])
        df.sort_values(by="Capacity", inplace=True, ascending=False)
        df["Source"] = "SM"
        return df

    def load_EL(self):
        """
        Loads Electralink csv file
        ID, capacity, postcode, install_date
        """
        data = []
        with io.open(self.EL_file, "rt", newline="\r\n") as fid:
            next(fid)
            i = 1
            for line in fid:
                i += 1
                line = re.sub(r'"[^"]*"', lambda m: m.group(0).replace(",", ";"), line)
                row = line.strip().split(",")
                if len(row) == 1:
                    print("row of length 1")
                    continue
                if len(row) != 14:
                    raise Exception("Parsed the wrong number of columns on line {} of the EL file "
                                    "('{}').".format(i, filename))
                postcode = row[4] if row[4]!="" else np.nan
                capacity = float(row[6]) / 1000. if self.isNumber(row[6]) else np.nan
                earliest_gen_date = datetime.strptime(row[7], "%Y-%m-%d").date() if row[7] != "" else np.nan
                ro_repd_gen_date = datetime.strptime(row[8], "%Y-%m-%d").date() if row[8] != "" else np.nan
                lat = float(row[9]) / 1000. if self.isNumber(row[9]) else np.nan
                lon = float(row[10]) / 1000. if self.isNumber(row[10]) else np.nan
                this_data = [row[0].strip(), capacity, postcode, earliest_gen_date,
                             ro_repd_gen_date, lat, lon]
                if this_data not in data:
                    data.append(this_data)
        df = pd.DataFrame(np.array(data), columns=["ID", "Capacity", "Postcode",
                                                   "Earliest Gen Date", "RO/REPD Start Date",
                                                   "Lat", "Lon"])
        df.sort_values(by="Capacity", inplace=True, ascending=False)
        df["Source"] = "EL"
        return df

    # def upload_SL_to_db(self):


    @staticmethod
    def isNumber(x):
        """
        number check
        """
        try:
            float(x)
            return True
        except ValueError:
            return False

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

def print_progress(iteration, total, prefix='', suffix='', decimals=2, bar_length=100):
    """
    Call in a loop to create terminal progress bar.

    Parameters
    ----------
    `iteration` : int
        current iteration (required)
    `total` : int
        total iterations (required)
    `prefix` : string
        prefix string (optional)
    `suffix` : string
        suffix string (optional)
    `decimals` : int
        number of decimals in percent complete (optional)
    `bar_length` : int
        character length of bar (optional)
    Notes
    -----
    Taken from `Stack Overflow <http://stackoverflow.com/a/34325723>`_.
    """
    filled_length = int(round(bar_length * iteration / float(total)))
    percents = round(100.00 * (iteration / float(total)), decimals)
    progress_bar = '#' * filled_length + '-' * (bar_length - filled_length)
    sys.stdout.write('\r%s |%s| %s%s %s' % (prefix, progress_bar, percents, '%', suffix))
    sys.stdout.flush()
    if iteration == total:
        sys.stdout.write('\n')
        sys.stdout.flush()

if __name__ == "__main__":
    main()