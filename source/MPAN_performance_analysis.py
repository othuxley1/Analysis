"""
A script which processes the Electralink PV out-turn data and
performs nearest neighbour yield analysis to filter out
systems which are faulty or have corrupted metadata.

- First Authored 2018-05-08
- Owen Huxley <othuxley1@sheffield.ac.uk>
"""

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

def main():
    ##### CONFIG #####
    ##################
    performance_analysis = PerformanceAnalyser()
    performance_analysis.myprint("Starting analysis...", time_section="start")
    print("Reading metadata from {}...".format(performance_analysis.meta_file))
    meta = performance_analysis.load_meta()
    print("Reading data from {}...".format(performance_analysis.data_file))
    data  = performance_analysis.load_data()
    print("Analysing performance...")
    import pdb; pdb.set_trace()
    used_mpans = []
    mpans = np.unique(data[:, 0])
    num_mpans = len(mpans)
    i = 0
    for mpan in mpans:
        i += 1
        if 1%100:
            print_progress(i, num_mpans)
        if np.in1d(mpan, meta[:, 0]):
            performance_analysis.mpan_performance(mpan)
            used_mpans.append(mpan)
            data = data[~np.in1d(data[:,0], used_mpans)]
        else:
            print("        No metadata for this system!! :(")
            used_mpans.append(mpan)
            data = data[~np.in1d(data[:,0], used_mpans)]
    performance_analysis.myprint("Analysis finished.", time_section="stop")
    # results_to_file(self.results_file, results)
    return()

class PerformanceAnalyser:
    def __init__(self, quiet=False):
        self.quiet = quiet
        self.timer = 0
        self.meta_file = r"C:/Users/owenh/Google Drive/PhD/SheffieldSolar/ss_work/analysis"\
                          "/Owen/Electralink/raw_data/Solar_Sheffield_Site_Data.csv"
        self.data_file = r"C:/Users/owenh/Google Drive/PhD/SheffieldSolar/ss_work/analysis"\
                          "/Owen/Electralink/raw_data/Solar_Sheffield_Output_test.psv"
        self.results_file = r"C:/Users/owenh/Google Drive/PhD/SheffieldSolar/ss_work/analysis"\
                             "/Owen/Electralink/MPAN_performance_analysis/good_sites.csv"
        self.cache_file = r"C:/Users/owenh/Documents/PhD/Gitkraken/sensitivity_analysis/"\
                           "MPAN_performance_analysis/mpan_cache.p"
        self.transition_dates = None
        self.data = None
        self.metadata = None
        self.neighbour_data = {}
        self.local = pytz.timezone("Europe/London")
        self.local_timestamp_dict = {}
        self.start_date = "2014-11-01"
        self.end_date = "2017-11-01"


    def load_meta(self):
        self.myprint("Loading metadata...", time_section="start")
        data = []
        with open(self.meta_file, "r") as file:
            csvreader = reader(file)
            next(csvreader)
            for i,line in enumerate(csvreader):
                if line[0] != "" and line[0] != "#N/A":
                    data.append([line[0], line[6], line[9], line[10], line[11]])
        #self.myprint("Finshed loading metadata.", time_section="stop")
        self.myprint("Finshed loading metadata.", time_section="stop")
        self.metadata = np.array(data).astype(float)
        return(np.array(data).astype(float))

    def load_data(self):
        self.myprint("Loading data...", time_section="start")
        # if os.path.isfile(self.cache_file):
        #     print("    Reading from local Pickle cache...")
        #     with open(self.cache_file, "rb") as fid:
        #         data = pickle.load(fid)
        #     self.myprint("Finshed loading data.", time_section="stop")
        #     return(data)

        dfs = []
        mpans = self.metadata[0, :]
        for mpan in mpans:
            dtindex = pd.date_range(self.start_date, self.end_date, freq = '30min')
            dfs.append(pd.DataFrame({'measurement_qty_id' : np.nan, 'SP' : dtindex, 
                       'actual_estimated_indicator' : np.nan, 'period_meter_consumption' : np.nan}).set_index('SP'))
        MIdf = pd.concat(dfs, keys = mpans)
        import pdb; pdb.set_trace()
        raw_data = []
        with open(self.data_file, "r") as file:
            next(file)
            i = 0
            # import pdb; pdb.set_trace()
            print_progress(i, 32228351) # remove hard code of file length
            for line in file:
                if i % 1000000 == 0:
                    print_progress(i, 32228351)
                y = [x for x in line.strip().split('|')]
                # settle_date = y[2]
                # period = y[3]
                if (y[2], y[3]) not in self.local_timestamp_dict: # converting settlement period strings into datetime objects
                    local_timestamp = to_unixtime(datetime.strptime(y[2], "%Y-%m-%d") + timedelta(minutes=30*int(y[3])), "UTC")
                    self.local_timestamp_dict[(y[2], y[3])] = local_timestamp
                data[i, :] = np.array([str(y[0]), str(y[1]), str(self.local_timestamp_dict[(y[2], y[3])]), str(y[4]), str(y[5])])
                i += 1
            print_progress(i, 32228351)
        self.myprint("\nFinished reading file into array.", time_section="stop")

        self.myprint("Converting settlement periods to timestamps...", time_section="start")
        ts_data = self.sp2ts(data)
        self.myprint("Finished converting settlement periods to timestamps.", time_section="stop")

        print("Writing to local Pickle cache...")
        with open(self.cache_file, "wb") as fid:
            pickle.dump(ts_data, fid, protocol=4)
        self.myprint("Finshed loading data.", time_section="stop")
        self.data = ts_data
        return(ts_data)

    def sp2ts(self, data):
        """
        A function to convert a date time recorded as a settlement
        date and a settlement period to a unix-time-stamp.

        Parameters
        ----------
        `settle_date` : string
            The settlement date.
        `period` : int
            The period associated with the settlement date.
        Returns
        -------
        `GMT_timestamp` : float
            Unixtime, i.e. seconds since epoch.
        Notes
        -----
        unixtime == seconds since epoch (Jan 01 1970 00:00:00 UTC)\n
        See Also
        --------
        `Python module pytz docs <http://pythonhosted.org/pytz/>`_,
        :func:`UKPVLiveTestCase.test_to_unixtime`
        """
        # creating a local timezone object
        #local = pytz.timezone("Europe/London")
        #import pdb; pdb.set_trace()
        if self.transition_dates is None:
            # creating list of all dates of clock change
            transition_dates = [x for x in self.local._utc_transition_times]
            # creating a list of tuples of all pairs of date changes
            offset_periods = [(transition_dates[i], transition_dates[i + 1])
                               for i in range(0, len(transition_dates) - 1, 2)]
            offset_timestamps = [[to_unixtime(x, "UTC") for x in line] for line in offset_periods]
        # checking if date is in BST and therefore needs to be corrected to GMT
        # day into clock change doesn't get adjusted when transitioning GMT -> BST
        # day into clock change does get adjusted when transitioning BST -> GMT
        # import pdb; pdb.set_trace()
        start_unixtime = np.min(data[:,2].astype(int))
        end_unixtime = np.max(data[:,2].astype(int))
        for CC_dates in offset_timestamps:
            if (int(CC_dates[1]) > int(start_unixtime)) and (int(CC_dates[0]) < int(end_unixtime)):
                # import pdb; pdb.set_trace()
                self.myprint("Working with data"
                         "in between {} and {}...".format(datetime.fromtimestamp(int(CC_dates[0])).strftime('%Y-%m-%d'),
                                                          datetime.fromtimestamp(int(CC_dates[1])).strftime('%Y-%m-%d')),
                                                          time_section="start")
                msk = (int(CC_dates[0]) < data[:, 2].astype(int)) & (data[:, 2].astype(int) <= int(CC_dates[1]))
                if np.any(msk):
                    data[msk, 2].astype(int) - int(3600)
                self.myprint("Finished, moving onto next pair of clock change dates.", time_section="stop")
        return(data)

    def mpan_performance(self, mpan): # I could delete data once I am finished with it.
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

        return(results)

    def get_neighbour_data(self, mpan):

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
    return(unixtime)

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