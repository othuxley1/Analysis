import json
import os
import errno
import numpy as np
from scipy.stats import johnsonsu
from scipy.stats import truncnorm

class CapacityError:
    """
    A class to estimate the error associated with each capacity error type.
    """

    def __init__(self):
        self.config = self.load_config("Config/capacity_error.txt")
        # self.jsu = None

    @staticmethod
    def load_config(file_location=None):
        try:
            if not file_location:
                file_location = (os.path.dirname(os.path.realpath(__file__))
                                 + os.sep + "Config"
                                 + os.sep + "capacity_error.ini")
            with open(file_location, "r") as json_file:
                config = json.load(json_file)
        except FileNotFoundError:
            raise FileNotFoundError(
                errno.ENOENT, os.strerror(errno.ENOENT), file_location)
        except AssertionError:
            raise AssertionError("Error loading config, please check that"
                                 "the config file {} exists and lists all of "
                                 "the required values.".format(file_location))
        return config

    def error_pdf(self, system_type, order=None, _error=None, size=1, bounds =(-1,1)):
        """A wrapper function to call the required pdf function."""

        pdf = self.config[_error][system_type][order][0]

        if pdf == "normal":
            return self.normal_pdf(system_type, order, _error, size, bounds)
        elif pdf == "uniform":
            return self.uniform_pdf(system_type, order, _error, size)
        elif pdf == "johnson_su":
            return self.johnson_su_pdf(system_type, order, _error, size)
        else:
            raise ValueError("Incorrect pdf name in the config file at: "
                             "{}, {}, {}".format(_error, system_type, order))

    def normal_pdf(self, system_type, order=None, _error=None, size=1, bounds=(-1,1)):
        """

        Parameters
        ----------
        system_type
        order
        _error
        size

        Returns
        -------

        """
        params = self.config[_error][system_type][order][1]
        return self.get_truncated_normal(*params, bounds=bounds, size=size)

    def uniform_pdf(self, system_type, order=None, _error=None, size=1):
        """

        Parameters
        ----------
        system_type
        order
        _error

        Returns
        -------

        """
        params = self.config[_error][system_type][order][1]
        if len(params) == 1:
            return np.full(shape=size, fill_value=params[0])
        else:
            raise ValueError("Error in value of uniform pdf at: {}, {}, {}"
                             .format(_error, system_type, order))

    def johnson_su_pdf(self, system_type, order=None, _error=None, size=1):
        """

        Parameters
        ----------
        system_type
        order
        _error

        Returns
        -------

        """
        params = self.config[_error][system_type][order][1]
        shape, shape, location, _scale, bounds = params
        rv = johnsonsu.rvs(shape, shape, loc=location, scale=_scale, size=size)

        import pdb; pdb.set_trace()
        while not ((-100 < rv) & (rv < 100)):
            rv = johnsonsu.rvs(shape, shape, loc=location, scale=_scale, size=size)
        return rv / 100



    @staticmethod
    def get_truncated_normal(mean, sd, size=1, bounds=(-1,1)):
        """

        A function to return a scipy object for a truncated normal pdf.

        Parameters
        ----------
        mean: float,
            The pdf mean.
        sd: float,
            The pdf standard deviation.
        low: float,
            The lower boundary of the pdf.
        upp: float,
            The upper boundary of the pdf.
        size:

        Returns
        -------
        object, A scipy.stats.truncnorm object.
        """
        low = bounds[0]
        upp = bounds[1]

        a, b = (low - mean) / sd, (upp - mean) / sd
        return truncnorm.rvs(a, b, loc=mean, scale=sd, size=size)


if __name__ == "__main__":
    self = CapacityError()
