"""
A module of generic, reusable tools.

- Jamie Taylor <jamie.taylor@sheffield.ac.uk>
- First Authored: 2015-01-16

"""

from datetime import datetime
import os
import sys
import pytz
import pickle

class GenericException(Exception):
    """A generic exception for anticipated errors."""
    def __init__(self, msg, msg_id=None, filename=None, err=None):
        if msg_id is not None:
            self.msg = "%s: %s" % (msg_id, msg)
        else:
            self.msg = msg
        if err is not None:
            self.msg += "\n    %s" % repr(err)
        if filename:
            logger = GenericErrorLogger(filename)
            logger.write_to_log(self.msg)
    def __str__(self):
        return self.msg

class GenericErrorLogger:
    """Basic error logging to a file (optional)."""
    def __init__(self, filename):
        self.logfile = filename

    def write_to_log(self, msg):
        """Log the error message to the logfile along with a datestamp and the name of the script
        (in case of shared logfiles).

        Parameters
        ----------
        `msg` : string
            Message to be recorded in *self.logfile*.
        """
        timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
        scriptname = os.path.basename(__file__)
        fid = open(self.logfile, 'a')
        fid.write(timestamp + " " + scriptname + ": " + str(msg) + "\n")
        fid.close()
        return

def email_alert(message, recipient=None, carbon_copy=None, subject='Sheffield Solar', reply_to=None,
                attachments=None):
    """
    Send an email alert using sendmail.

    Warning
    -------
    Only tested on Linux systems. Sendmail must already be configured.
    """
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.application import MIMEApplication
    from subprocess import Popen, PIPE
    msg = MIMEMultipart()
    msg['Subject'] = subject
    msg['From'] = 'solarfarm@sheffield.ac.uk'
    if recipient is None:
        recipient = 'jamie.taylor@sheffield.ac.uk'
    if carbon_copy is not None:
        msg["Cc"] = carbon_copy
    msg['To'] = recipient
    if reply_to is not None:
        msg["Reply-To"] = reply_to
    msg.attach(MIMEText(message))
    if attachments is not None:
        for att in attachments:
            with open(att, 'rb') as f:
                filename = os.path.split(att)[1]
                attachment = MIMEApplication(f.read(), 'subtype')
                attachment['Content-Disposition'] = 'attachment; filename="%s";' % filename
                msg.attach(attachment)
    mailer = Popen(["/usr/sbin/sendmail", "-t"], stdin=PIPE)
    mailer.communicate(msg.as_string())
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
    if not timezone_ and not datetime_.tzinfo:
        raise GenericException(msg_id="ukpv_live.to_unixtime", msg=("EITHER datetime_ must contain "
                                                                    "tzinfo OR timezone_must be "
                                                                    "passed."))
    if timezone_ and not datetime_.tzinfo:
        utc_datetime = pytz.timezone(timezone_).localize(datetime_).astimezone(pytz.utc)
    else:
        utc_datetime = datetime_.astimezone(pytz.utc)
    unixtime = int((utc_datetime - datetime(1970, 1, 1, 0, 0, 0, 0, pytz.utc)).total_seconds())
    return unixtime

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

def myround(number, base=5):
    """Round to the nearest *base*."""
    return int(base * round(float(number)/base))

def query_yes_no(question, default="yes"):
    """
    Ask a yes/no question via raw_input() and return the answer as boolean.

    Parameters
    ----------
    `question` : string
        The question presented to the user.
    `default` : string
        The presumed answer if the user just hits <Enter>. It must be "yes" (the default), "no" or
        None (meaning an answer is required of the user).
    Returns
    -------
    boolean
        Return value is True for "yes" or False for "no".
    Notes
    -----
    See http://stackoverflow.com/a/3041990
    """
    valid = {"yes": True, "y": True, "ye": True,
             "no": False, "n": False}
    if default is None:
        prompt = " [y/n] "
    elif default == "yes":
        prompt = " [Y/n] "
    elif default == "no":
        prompt = " [y/N] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)
    while True:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return valid[default]
        elif choice in valid:
            return valid[choice]
        else:
            sys.stdout.write("Please respond with 'yes' or 'no' "
                             "(or 'y' or 'n').\n")

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