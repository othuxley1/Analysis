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


class SiteListVariation:
    """
    Modifying the site list in accordance with the
    categorised errors.
    """

    def __init__(self, simulation_id, verbose=False):
        # TODO
        #  add options as class input and write cli script
        self.config = self.load_config()
        self.verbose = verbose
        self.SL_df = None
        self.err_tbl_df = None
        self.modified_SL = None
        self.pv_system = None
        self.random_error_values = {}
        self.test = False
        self.simulation_id = simulation_id
        self.new_site_list = None
    
    def run(self):
        self.load_err_tbl()
        self.load_SL()
        self.categorise_systems()
        self.new_site_list = self.simulate_new_site_list()
        # TODO
        #  add check for optional -u upload flag in cli options
        self.upload_results()

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
        except FileNotFoundError as fnferr:
            raise fnferr(errno.ENOENT, os.strerror(errno.ENOENT),file_location)
        except AssertionError as error:
            raise Exception("Error loading config, please check that"
                            "the config file {} exists and lists all of "
                            "the required values. {}".format(file_location))
        return config

    def load_SL(self):
        "Load the site list csv file into a pandas dataframe."
        self.SL_df = pd.read_csv(self.config["sl_file"])
        self.modified_SL_df = pd.read_csv(self.config["sl_file"])
    
    def load_err_tbl(self):
        "Load the error table into a pandas dataframe."
        self.err_tbl_df = pd.read_csv(self.config["err_tbl_file"])
    
    def categorise_systems(self, cut_off=0.01):
        """
        Add a column to the dataframe which categorises systems as either
        domestic or non-domestic.

        Parameters
        ----------
        `cut_off` : float
            The cut off, as measured by capacity in MW, used to separate 
            domestic and non-domestic systems .
        """
    
        self.SL_df["system_type"] = None
        self.SL_df.loc[self.SL_df.loc[:, "Capacity"] < 0.01, "system_type"] = "domestic"
        self.SL_df.loc[~(self.SL_df.loc[:, "Capacity"] < 0.01), "system_type"] = "non-domestic"

    def return_error(self, error_type, system_type):
        """
        Randomly remove sites from the sitelist to simulate decomissioned
        systems.
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
            return error

        else:
            return self.random_error_values[system_type][error_type]

    def unreported_systems(self):

        domestic_error = self.return_error("unreported", "domestic")
        non_domestic_error = self.return_error("unreported", "non-domestic")

        # import pdb; pdb.set_trace()

        # random domestic system subset
        domestic_count = self.SL_df["system_type"].shape[0]
        domestic_subset = self.SL_df.sample(int(domestic_count * domestic_error / 100))

        #
        non_domestic_count = self.SL_df["system_type"].shape[0]
        non_domestic_subset = self.SL_df.sample(int(non_domestic_count * non_domestic_error / 100))

        return pd.concat((domestic_subset, non_domestic_subset))

    @cached("../data/pickle_files/simulate_new_site_list.pickle")
    def simulate_new_site_list(self):

        unreported_systems = self.unreported_systems()
        unreported_systems["unreported"] = "simulated"
        self.SL_df["unreported"] = "original"
        site_list = pd.concat((unreported_systems, self.SL_df))
        new_site_list = []

        tstart = TIME.time()
        for site in site_list.itertuples():
            # TODO
            #   error handling for getattr()
            try:
                # instantiate pvsystem class
                pvs = PVSystem(site, self, verbose=self.verbose)


                # simulate decomissioned systems
                pvs.decommissioned()
                # simulate offline systems
                pvs.offline()
                # simulate revised up
                pvs.revised_up()
                # simulate revised down
                pvs.revised_down()
                # simulate network_outage
                pvs.network_outage()
                # simulate site_uncertainty
                pvs.site_uncertainty()
                # simulate string_outage
                pvs.string_outage()
                # store new system information
                new_site_list.append(pvs.pvsystem_to_list())
                # import pdb;
                # pdb.set_trace()
            except DecommissionedError:
                new_site_list.append(pvs.pvsystem_to_list())
            except:
                raise Exception("Problem simulating errors...")
                import pdb; pdb.set_trace()

        # import pdb; pdb.set_trace()
        # TODO
        #  step through error simulations and work out why alll capacities are zero
        print("Time taken for itertuples(): {}".format(TIME.time() - tstart))

        return new_site_list

    def upload_results(self):
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