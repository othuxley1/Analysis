"""
A script to calculate the error on the national capacity
as defined by the national PV site list.
"""

# TODO
#  add function to randomly select error values done
#  store in global variable dict done
#  function to simulate unreported systems e.g. duplicate systems
#  Method: modify_site_list()

import os
import pandas as pd
import time as TIME
from pv_system import PVSystem
from site_list_exceptions import DecommissionedError
from configparser import ConfigParser
from generic_tools import cached
from dbconnector import DBConnector
import numpy as np
from scipy.stats import truncnorm
import errno

class SiteListVariation:
    """
    Modifying the site list in accordance with the
    categorised errors.
    """

    def __init__(self, simulation_id, verbose=False,
                 system_type="domestic", seed=1):
        # TODO
        #  add options as class input and write cli script
        self.config = self.load_config()
        self.verbose = verbose
        self.SL = None
        self.err_tbl_df = None
        # self.modified_SL = None
        self.pv_system = None
        self.random_error_values = {}
        self.test = False
        self.simulation_id = simulation_id
        self.new_SL = None
        self.system_type = system_type
        self.random_seed = np.random.seed(seed)

    def run(self):
        self.load_err_tbl()
        self.load_SL()
        self.categorise_systems()
        # self.new_site_list = self.simulate_new_site_list()
        self.simulate_new_site_list()
        # TODO
        #  add check for optional -u upload flag in cli options
        # self.upload_results()

    @staticmethod
    def load_config(file_location=None):
        """
        Load the config from file.

        Parameters
        ----------
        `file_location` : string
            Optionally provide the location of the config file as full
            absolute path. If not provided, config is assumed to be in
            'Config/config.ini'.
        Returns
        -------
        dict
            A dictionary of config parameters whose keys match the names used
            in the config file.
        """

        try:
            if not file_location:
                file_location = (os.path.dirname(os.path.realpath(__file__))
                                 + os.sep + "Config"
                                 + os.sep + "site_list.ini")
            parser = ConfigParser()
            parser.read(file_location)
            config = {}
            config["config_location"] = file_location

            config["mysql_defaults_monte_carlo_sample_size_analysis"] = \
                parser.get("mysql_defaults", "monte_carlo_sample_size_analysis")
            config["sl_file"] = parser.get("data_files", "sl")
            config["err_tbl_file"] = parser.get("data_files", "err_tbl")
            config["results_table"] = parser.get("mysql_tables", "results")
        except FileNotFoundError:
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT),
                                    file_location)
        except AssertionError:
            raise AssertionError("Error loading config, please check that"
                                 "the config file {} exists and lists all of "
                                 "the required values.".format(file_location))
        return config

    def load_SL(self):
        "Load the site list csv file into a pandas dataframe."
        self.SL = pd.read_csv(self.config["sl_file"])
        self.test =  1000
        self.modified_SL = pd.read_csv(self.config["sl_file"])
    
    def load_err_tbl(self):
        "Load the error table into a pandas dataframe."
        self.err_tbl_df = pd.read_csv(self.config["err_tbl_file"])
    
    def categorise_systems(self, cut_off=0.01):
        """
        Add a column to the dataframe which categorises systems as either
        domestic or non-domestic.

        Parameters
        ----------
        cut_off : float,
            The cut off, as measured by capacity in MW, used to separate 
            domestic and non-domestic systems .
        """
    
        self.SL["system_type"] = None
        self.SL.loc[self.SL.loc[:, "Capacity"] < 0.01, "system_type"] = "domestic"
        self.SL.loc[~(self.SL.loc[:, "Capacity"] < 0.01), "system_type"] = "non-domestic"

    def return_error(self, error_type: str, system_type: str) -> float:
        """

        A function to select the appropriate error value for any given error
        category and system type.

        Parameters
        ----------
        error_type: str,
            The category of the error to select data for.
        system_type: str,
            Specify whether to get the error data for domestic or non-domestic
            systems.

        Returns
        -------
        error: float,
            Error value for the requested category and system type.

        """
        # TODO
        #  randomly select errors from err_tbl

        # randomly select error for error_type specified in PVSystem class
        if system_type not in self.random_error_values:
            # add system_type to dict
            self.random_error_values[system_type] = {}

            # select rows matching system_type
            error_table = self.err_tbl_df.loc[
                          self.err_tbl_df.loc[:, "system_type"] == system_type, :
                          ]
            # select row of table for system_type and error_category
            # import pdb; pdb.set_trace()
            all_errors = error_table.loc[
                error_table.loc[:, "error_category"] == error_type
            ].loc[:, ["err1", "err2", "err3", "err4"] ]
            error = all_errors.sample(1, axis=1).values[0][0]
            return error

        elif error_type not in self.random_error_values[system_type]:
            error_table = self.err_tbl_df.loc[
                          self.err_tbl_df.loc[:, "system_type"] == system_type, :
                          ]
            all_errors = error_table.loc[
                error_table.loc[:, "error_category"] == error_type
            ].loc[:, ["err1", "err2", "err3", "err4"] ]
            error = all_errors.sample(1, axis=1).values[0][0]
            self.random_error_values[system_type][error_type] = error
            return float(error)

        else:
            return self.random_error_values[system_type][error_type]

    def unreported_systems(self):

        error = self.return_error("unreported", self.system_type)
        # random domestic system subset
        count = self.SL["system_type"].shape[0]
        subset = self.SL.sample(int(count * error / 100))
        return subset

    def simulate_new_site_list(self):
        unreported_systems = self.unreported_systems()
        unreported_systems["unreported"] = "simulated"
        self.SL["unreported"] = "original"
        self.new_SL = pd.concat((unreported_systems, self.SL))

        # import pdb; pdb.set_trace()
        self.new_SL = self.new_SL.loc[self.new_SL.loc[:,"system_type"] == self.system_type, :]

        # simulate decomissioning
        self.decomission()

        # simulate offline
        self.offline()
        # import pdb; pdb.set_trace()

        # simulate revised_up
        self.revision("revised_up", 0.3, 0.1)

        # simulate revised_down
        self.revision("revised_down", -0.3, 0.1)

        if self.system_type == "domestic":
            # simulate site_uncertainty
            self.revision("site_uncertainty", 0, 0.15)
            # simulate string_outage
            self.string_outage((0.02, 0.06), (56, 28))

        elif self.system_type == "non-domestic":
            # simulate site_uncertainty
            self.revision("site_uncertainty", -0.05, 0.1)
            # simulate string_outage
            self.string_outage((0.01, 0.03), (14, 7))
        else:
            raise ValueError("Problem with SiteListVariation.system_type variable")

        self.network_outage()
        # import pdb; pdb.set_trace()

    def decomission(self):
        # np.random.seed(seed)
        error = self.return_error("decommissioned", self.system_type)
        probability = abs(error) / 100
        self.new_SL["decommissioned"] = np.random.uniform(0, 1, self.new_SL.shape[0]) < probability
        import pdb;
        # pdb.set_trace()

    def offline(self):
        # TODO
        #  probability of being offline seems too large
        # np.random.seed(seed)
        error = self.return_error("offline", self.system_type)
        probability = abs(error) / 100
        random_numbers_array = np.random.uniform(0, 1, (self.new_SL.shape[0], 365))
        offline = random_numbers_array < probability
        de_rating = (365 - np.sum(offline, axis=1)) / 365
        self.new_SL["Capacity"] *= de_rating
        # import pdb; pdb.set_trace()

    @staticmethod
    def get_truncated_normal(mean: float, sd: float,
                             low: float = 0., upp: float = 1) -> object:
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

        Returns
        -------
        object, A scipy.stats.truncnorm object.
        """

        a, b = (low - mean) / sd, (upp - mean) / sd
        return truncnorm(a, b, loc=mean, scale=sd)

    def revision(self, error_type: str,  mean: float,
                 sd: float, low: int = -1, upp: int = 1):

        error = self.return_error(error_type, self.system_type)
        probability = abs(error) / 100

        rows = self.new_SL.shape[0]
        random_number_array = np.random.uniform(0, 1, size=rows)

        truncnorm_instance = SiteListVariation.get_truncated_normal(mean, sd, low, upp)
        normal_array = truncnorm_instance.rvs(rows)

        revision_indices = random_number_array < probability
        normal_array[~revision_indices] = 0
        normal_array += 1

        self.new_SL["Capacity"] *= normal_array
        # import pdb; pdb.set_trace()

    def string_outage(self, inv_fail: (float, float), fail_period: (float, float)):

        """

        Simulate the impact of inverter string failure on the representative
        capacity for each individual PV system.

        Parameters
        ----------
        inv_fail: (float, float),
            A tuple containing the (mean, standard deviation) for the
            probability that an inverter will fail.
        fail_period: (float, float),
            A tuple containing the (mean, standard deviation) for the
            distribution of  failure period.

        """

        inv_fail_mean, inv_fail_sd = inv_fail
        fail_period_mean, fail_period_sd = fail_period

        rows = self.new_SL.shape[0]
        random_number_array = np.random.uniform(0, 1, size=rows)

        inverter_fail_normal = np.random.normal(inv_fail_mean, inv_fail_sd, size=rows)
        failed = random_number_array < inverter_fail_normal

        fail_period_instance = SiteListVariation.get_truncated_normal(fail_period_mean, fail_period_sd, 0, 365)
        fail_period = fail_period_instance.rvs(rows)

        de_rating = (365 - fail_period) / 365
        de_rating[~failed] = 1

        self.new_SL["Capacity"] *= de_rating
        # import pdb; pdb.set_trace()

    def network_outage(self):

        """Simulate network outage impact on representative system capacity"""

        if self.system_type == "domestic":
            self.new_SL["Capacity"] *= 0.99
        else:
            pass

    def upload_results(self):

        """Upload results to db."""

        # TODO
        #  change nans to None
        # import pdb; pdb.set_trace()
        with DBConnector(mysql_defaults=
                         self.config["mysql_defaults_monte_carlo_sample_size_analysis"]) as dbc:
            sql_template = ("INSERT into `{}` (`simulation_id`, `site_id`, `unreported`, "
                            "`decommissioned`, `capacity`, `eastings`, `northings`) "
                            "values (%s, %s, %s, %s, %s, %s, %s);")
            sql = sql_template.format(self.config["results_table"])
            import pdb;
            pdb.set_trace()
            dbc.iud_query(sql, self.new_site_list)


if __name__ == "__main__":
    instance = SiteListVariation(1)
    instance.run()