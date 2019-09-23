"""
A script to upload the electralink reading data to the electralink database.

- First Authored 2018-09-04
- Owen Huxley <othuxley1@sheffield.ac.uk>
"""
import sys
from datetime import datetime, timedelta
import time as TIME
import pytz

from dbconnector import DBConnector

from generic_tools import GenericException


def main():
    """
    The function that runs upload.
    """
    electralink_instance = Electralink()
    electralink_instance.myprint("Munging Electralink file...", time_section="start")
    electralink_instance.open_file()
    electralink_instance.myprint("--> Finished munging.", time_section="stop")
    return


class Electralink:
    """
    A class to handle munging and uploading the Electralink data.
    """
    def __init__(self, quiet=False):
        self.quiet = quiet
        self.timer = 0
        self.data_file = r"C:/Users/owenh/Google Drive/PhD/SheffieldSolar/ss_work/analysis"\
                          "/Owen/Electralink/raw_data/Solar_Sheffield_Output.psv"
        self.mysql_defaults = r"C:/Users/owenh/Google Drive/PhD/Analysis/Electralink/"\
                               "Code/mysql_defaults.ssfdb2.readwrite.electralink"
        self.transition_dates = None
        self.local = pytz.timezone("Europe/London")
        self.local_timestamp_dict = {}
        self.readings_table = 'readings_20171115'

    def open_file(self):
        """
        A function which opens the Electralink readings file and converts the Elexon settlement
        periods to UTC timestamps.

        Parameters
        ----------
        `parameter` :

        Returns
        -------
        `parameter` :

        Notes
        -----
        settle_date = line[2]
        period = line[3]

        """

        f_length = file_length(self.data_file)

        with open(self.data_file, 'r') as file:
            i = 0
            j = 0
            next(file)
            data = []
            for line in file:

                line = [x for x in line.strip().split('|')]
                # settle_date = y[2]
                # period = y[3]
                data.append([line[0], line[1],
                             to_unixtime(datetime.strptime(line[2], "%Y-%m-%d"), timezone_="UTC"),
                             int(line[3]), self.sp2ts(line[2], line[3]),
                             line[4], float(line[5].replace(",", ""))])
                i += 1
                j += 1
                if i == 5000:
                    i = 0
                    print_progress(j, f_length, prefix='    ', suffix='',
                                   decimals=2, bar_length=100)
                    self.upload_to_database(data)
                    data = []
            self.upload_to_database(data)
        return

    def prepare_db(self):
        """
        Truncates the database table.
        """
        with DBConnector(mysql_defaults=self.mysql_defaults, session_tz="UTC") as dbc:
            sql_template = ("TRUNCATE TABLE `{}`;".format(self.readings_table))
            dbc.iud_query(sql_template)
        return

    def upload_to_database(self, data):
        """
        Uploads data to a table in the electralink database.

        Parameters
        ----------
        `data` : list
            A list of lists which contains the data to be uploaded.
        """
        with DBConnector(mysql_defaults=self.mysql_defaults, session_tz="UTC") as dbc:
            sql_template = ("insert into `{}` (`MPAN`, `measurement_qty_id`, `settlement_date`, "
                            "`period_no`, `utc_timestamp`,  `actual_estimated_indicator`, "
                            "`period_meter_consumption`) values (%s, %s, FROM_UNIXTIME(%s), "
                            "%s, FROM_UNIXTIME(%s), %s, %s);")
            sql = sql_template.format(self.readings_table)
            dbc.iud_query(sql, data)
        return


    def sp2ts(self, settle_date, period):
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
        checking if date is in BST and therefore needs to be corrected to GMT\n
        --> day into clock change doesn't get adjusted when transitioning GMT -> BST\n
        --> day into clock change does get adjusted when transitioning BST -> GMT\n
        unixtime == seconds since epoch (Jan 01 1970 00:00:00 UTC)\n
        See Also
        --------
        `Python module pytz docs <http://pythonhosted.org/pytz/>`_,
        :func:`UKPVLiveTestCase.test_to_unixtime`
        """
        settle_dt = datetime.strptime(settle_date, "%Y-%m-%d")
        settle_date = settle_dt.date()
        ts_local = to_unixtime(settle_dt + timedelta(minutes=30*int(period)), "UTC")
        if self.transition_dates is None:
            self.transition_dates = [x.date() for x in self.local._utc_transition_times]
        offset_periods = [(self.transition_dates[i], self.transition_dates[i + 1])
                          for i in range(0, len(self.transition_dates) - 1, 2)]
        if any([x[0] < settle_date <= x[1] for x in offset_periods]):
            ts_local -= 3600
        return ts_local

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
        return

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

def file_length(file):
    """
    A function to count the number of lines in a file.

    Parameters
    ----------
    `file` : str
        The path of the file.
    Returns
    -------
    `i` : int
        The number of lines in the file.

    """
    i = 0
    with open(file, 'r') as file:
        for line in file:
            i += 1
    return i

if __name__ == "__main__":
    main()
