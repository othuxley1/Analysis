"""
A script to calculate the error on the national capacity
as defined by the national PV site list.
"""

import os
import pandas as pd
from configparser import ConfigParser
import numpy as np
import errno
from capacity_error import CapacityError as ce


class SiteListVariation:
    """
    Modifying the site list in accordance with the
    categorised errors.
    """

    def __init__(self, simulation_id, verbose=False, seed=1, test=False):
        self.config = self.load_config()
        self.verbose = verbose
        self.test = test # test with subset of 1000 sites
        self.SL =self.load_site_list()
        self.simulation_id = simulation_id
        self.random_seed = np.random.seed(seed)
        print(seed)
        self.ce = ce()

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
            config["sl_file"] = parser.get("data_files", "sl")
            config["results_table"] = parser.get("mysql_tables", "results")
        except FileNotFoundError:
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT),
                                    file_location)
        except AssertionError:
            raise AssertionError("Error loading config, please check that"
                                 "the config file {} exists and lists all of "
                                 "the required values.".format(file_location))
        return config

    def unreported_systems(self):
        """Augmenting the site list with unreported sites."""
        # import pdb; pdb.set_trace()
        counts = self.ce.config["unreported"]
        # import pdb; pdb.set_trace()

        mask_0to4 = (self.SL["Capacity"] < 4)
        self.SL = pd.concat((self.SL, self.SL.loc[mask_0to4].sample(int(counts["0to4"]))), axis=0)

        mask_4to10 = (4 < self.SL["Capacity"]) & (self.SL["Capacity"] <= 10)
        self.SL = pd.concat((self.SL, self.SL.loc[mask_4to10].sample(int(counts["4to10"]))), axis=0)

        mask_10to50 = (10 < self.SL["Capacity"]) & (self.SL["Capacity"] <= 40)
        self.SL = pd.concat((self.SL, self.SL.loc[mask_10to50].sample(int(counts["10to50"]))), axis=0)

        mask_50to5 = (50 < self.SL["Capacity"]) & (self.SL["Capacity"] <= 5000)
        self.SL = pd.concat((self.SL, self.SL.loc[mask_50to5].sample(int(counts["50to5"]))), axis=0)

    def test_negative(self, error):
        # import pdb; pdb.set_trace()
        if sum(self.SL.Capacity < 0) > 0:
            raise Exception("Negative capacity values following error: {}"
                            .format(error))

    def simulate_effective_capacity_site_list(self):
        if self.verbose: print("Initialising CapacityError object...\n")
        ce = self.ce
        if self.verbose: print("\t--> done.\n")

        self.test_negative("None")

        if self.verbose: print("Decommissioning...\n")
        self.apply_error("decommissioned", ce.error_pdf)
        if self.verbose: print("\t--> done.")

        self.test_negative("Decommissioned")

        if self.verbose: print("Site uncertainty...\n")
        self.apply_error("site_uncertainty", ce.error_pdf)
        if self.verbose: print("\t--> done.")

        # import pdb; pdb.set_trace()

        self.test_negative("Site uncertainty")

        if self.verbose: print("Revising systems up...\n")
        self.apply_error("revised_up", ce.error_pdf)
        if self.verbose: print("\t--> done.")

        self.test_negative("Revision (up)")

        if self.verbose: print("Revising systems down...\n")
        self.apply_error("revised_down", ce.error_pdf)
        if self.verbose: print("\t--> done.")

        self.test_negative("Revision (down)")

        if self.verbose: print("Offline...\n")
        self.apply_error("offline", ce.error_pdf)
        if self.verbose: print("\t--> done.")

        self.test_negative("Offline")

        if self.verbose: print("Network outage...\n")
        self.apply_error("network_outage", ce.error_pdf)
        if self.verbose: print("\t--> done.")

        self.test_negative("network outage")
        return

    def apply_error(self, error_category, pdf):
        # domestic_count = self.SL.loc[self.SL["system_type"] == "domestic"].shape[0]
        # non_domestic_count = self.SL.loc[self.SL["system_type"] == "non_domestic"].shape[0]
        system_count = self.SL.shape[0]
        system_types = ["domestic", "non_domestic"]
        for system_type in system_types:
            random_numbers = np.random.uniform(0, 1, system_count)
            probability_error_occurs = pdf(system_type, order="p1", _error=error_category, size=1)[0]
            if error_category == "site_uncertainty" and system_type == "domestic":
                effect_of_error = pdf(system_type, order="p2", _error=error_category, size=system_count, bounds = (0,1))
            else:
                effect_of_error = pdf(system_type, order="p2", _error=error_category, size=system_count) + 1
            mask = random_numbers < probability_error_occurs
            sl_mask = (self.SL["system_type"] == system_type).values & mask
            # import pdb; pdb.set_trace()
            if error_category == "site_uncertainty" and system_type == "domestic":
                self.SL.loc[sl_mask, "Capacity"] += effect_of_error[sl_mask]
                # import pdb; pdb.set_trace()
            else:
                self.SL.loc[sl_mask, "Capacity"] *= effect_of_error[sl_mask]


    def load_site_list(self, cut_off=10, n_rows=1000):
        """Load the site list csv file into a pandas DataFrame."""
        if self.test:
            SL = pd.read_csv(self.config["sl_file"], nrows=n_rows)
        else:
            SL = pd.read_csv(self.config["sl_file"])

        # rename site list columns
        SL.rename({"dc_capacity" : "Capacity"}, inplace=True, axis=1)

        # categorise systems as domestic / non-domestic
        SL["system_type"] = None
        SL.loc[SL.loc[:, "Capacity"] < cut_off, "system_type"] = "domestic"
        SL.loc[SL.loc[:, "Capacity"] >= cut_off, "system_type"] = "non_domestic"
        return SL

if __name__ == "__main__":
    self = SiteListVariation(1, verbose=True, seed=1, test=False)
    self.unreported_systems()
    self.simulate_effective_capacity_site_list()
