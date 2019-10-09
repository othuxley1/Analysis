import random
from site_list_exceptions import DecommissionedError
import numpy as np
import pandas as pd


class PVSystem:

    def __init__(self, site_tuple, SL_instance):
        self.error_type = None # update on the fly (default set to None)
        self.site_tuple = site_tuple
        self.capacity = getattr(site_tuple, "Capacity")
        self.eastings = getattr(site_tuple, "Eastings")
        self.northings = getattr(site_tuple, "Northings")
        self.system_type = getattr(site_tuple, "system_type")
        self.SL_instance = SL_instance
        # self.start = datetime.date

    def decommissioned(self):
        """Decommission systems probabilistically."""
        # set error_type
        self.error_type = "decommissioned"
        error = self.SL_instance.return_error(self.error_type, self.system_type)
        probability = abs(error) / 100
        random_number = random.uniform(0,1)

        if random_number < probability:
            raise DecommissionedError
        else:
            pass

    def offline(self):
        """Simulate systems going offline probabilistically."""
        # TODO
        #  The probability of being offline should increase if the system is already offline
        self.error_type = "offline"
        error = self.SL_instance.return_error(self.error_type, self.system_type)
        probability = abs(error) / 100
        offline_days = 0
        for hour in range(365):
            random_number = random.uniform(0,1)
            if random_number < error:
                offline_days += 1
            else:
                pass
        de_rating = offline_days / 365
        self.capacity = self.capacity * de_rating
        # TODO
        #  time series of offline hours???


    def revised_up(self):
        self.error_type = "revised_up"
        error = self.SL_instance.return_error(self.error_type, self.system_type)
        probability = abs(error) / 100 # of a system being revised-up
        # assume that system revised up for whole year
        # TODO
        #  have revisioin happen with time series approach
        #  determine the likely increase in capacity for different types of system
        random_number = random.uniform(0,1)
        if random_number < probability:
            normal = np.random.normal(0.3, 0.1)
            if normal < 0:
                normal = 0
            elif normal > 1:
                normal = 1
            up_rating = 1 + normal
            self.capacity  *= up_rating
        import pdb; pdb.set_trace()

    def revised_down(self):
        self.error_type = "revised_down"
        error = self.SL_instance.return_error(self.error_type, self.system_type)
        probability = abs(error) / 100  # of a system being revised-up
        # assume that system revised up for whole year
        # TODO
        #  have revision happen with time series approach
        #  determine the likely increase in capacity for different types of system
        random_number = random.uniform(0, 1)
        if random_number < probability:
            de_rating = np.random.normal(0.7, 0.1)
            if de_rating > 1:
                de_rating = 1
            elif de_rating < 0:
                de_rating = 0
            self.capacity *= de_rating
        import pdb;
        pdb.set_trace()

    def site_uncertainty(self):
        self.error_type = "site_uncertainty"
        if self.system_type == "non_domestic":
            error = np.random.normal(0.95, 0.1)
        elif self.system_type == "domestic":
            error = np.random.normal(1, 0.15)
        self.capacity *= error
        import pdb; pdb.set_trace()

    def string_outage(self):
        
    def pvsystem_list(self):