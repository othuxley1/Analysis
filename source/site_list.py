"""
A script to calculate the error on the national capacity
as defined by the national PV site list.
"""

# TODO
#  add function to randomly select error values done
#  store in global variable dict done
#  function to simulate unreported systems e.g. duplicate systems
#  Method: modify_site_list()



import pandas as pd
import time as TIME
from pv_system import PVSystem

class SiteListVariation:
    """
    Modifying the site list in accordance with the
    categorised errors.
    """

    def __init__(self):
        self.SL_file = "../data/site_list/site_list.csv"
        self.err_tbl_file = "../data/site_list/error_table.csv"
        self.SL_df = None
        self.err_tbl_df = None
        self.modified_SL = None
        self.pv_system = None
        self.random_error_values = {}
        self.test = False
    
    def run(self):
        self.load_err_tbl()
        self.load_SL()
        self.categorise_systems()
        self.simulate_new_site_list()
    

    def load_SL(self):
        "Load the site list csv file into a pandas dataframe."
        self.SL_df = pd.read_csv(self.SL_file)
        self.modified_SL_df = pd.read_csv(self.SL_file)
    
    def load_err_tbl(self):
        "Load the error table into a pandas dataframe."
        self.err_tbl_df = pd.read_csv(self.err_tbl_file)
    
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
            error_table = self.err_tbl_df.loc[self.err_tbl_df.loc[:, "system_type"] == system_type, :]
            # select row of table for system_type and error_category
            # import pdb; pdb.set_trace()
            all_errors = error_table.loc[
                error_table.loc[:, "error_category"] == error_type
            ].loc[:, ["err1", "err2", "err3", "err4"] ]
            error = all_errors.sample(1, axis=1).values[0][0]
            return error

        elif error_type not in self.random_error_values[system_type]:
            error_table = self.err_tbl_df.loc[ self.err_tbl_df.loc[:, "system_type"] == system_type, :]
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

    def simulate_new_site_list(self):

        unreported_systems = self.unreported_systems()
        site_list = pd.concat((unreported_systems, self.SL_df))

        tstart = TIME.time()
        for site in site_list.itertuples():
            # TODO
            #   error handling for getattr()
            # instantiate pvsystem class
            pvs = PVSystem(site, self)
            pvs.decommissioned()
            # import pdb; pdb.set_trace()
        print("Time taken for itertuples(): {}".format(TIME.time() - tstart))











if __name__ == "__main__":
    instance = SiteListVariation()
    instance.run()