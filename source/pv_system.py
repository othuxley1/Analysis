import random
from site_list_exceptions import DecommissionedError
import numpy as np
import pandas as pd
import time as TIME


class PVSystem:

    def __init__(self, site_tuple, SL_instance, verbose=False):
        self.error_type = None # update on the fly (default set to None)
        self.site_tuple = site_tuple
        self.capacity = getattr(site_tuple, "Capacity")
        self.eastings = getattr(site_tuple, "Eastings")
        self.northings = getattr(site_tuple, "Northings")
        self.system_type = getattr(site_tuple, "system_type")
        self.SL_instance = SL_instance
        self.verbose = verbose
        self.simulation_id = SL_instance.simulation_id
        self.site_id = getattr(site_tuple, "Index")
        self.unreported = getattr(site_tuple, "unreported")
        self.decommissioned_flag = False
        # import pdb; pdb.set_trace()
        # self.start = datetime.date

    def _verbose(message):
        "Define a decorator to run the function in verbose mode."
        def decorator(fn):
            def wrapper(self):
                tstart = TIME.time()
                if self.verbose:
                    print("\nSimulating {}...".format(message))
                    print("\tCapacity before {}: {}."
                          .format(message, self.capacity))
                fn(self)
                if self.verbose:
                    print("\tCapacity after {}: {}."
                          .format(message, self.capacity))
                    print("\t-> Finished, time taken: {}"
                          .format(TIME.time() - tstart))
            return wrapper
        return decorator

    @_verbose("decommissioning")
    def decommissioned(self):
        """Decommission systems probabilistically."""
        # set error_type
        self.error_type = "decommissioned"
        error = self.SL_instance.return_error(self.error_type, self.system_type)
        probability = abs(error) / 100
        random_number = random.uniform(0,1)

        if random_number < probability:
            self.decommissioned_flag = True
            raise DecommissionedError
        else:
            pass

    @_verbose("offline")
    def offline(self):
        """Simulate systems going offline probabilistically."""
        # TODO
        #  The probability of being offline should increase if the system is already offline
        # import pdb; pdb.set_trace()
        self.error_type = "offline"
        error = self.SL_instance.return_error(self.error_type, self.system_type)
        probability = abs(error) / 100
        offline_days = 0
        for hour in range(365):
            random_number = random.uniform(0,1)
            if random_number < probability:
                offline_days += 1
            else:
                pass
        de_rating = (365 - offline_days) / 365
        self.capacity = self.capacity * de_rating
        # TODO
        #  time series of offline hours???

    @_verbose("revision up")
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
        # import pdb; pdb.set_trace()

    @_verbose("revision down")
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
        # pdb.set_trace()

    @_verbose("site uncertainty")
    def site_uncertainty(self):
        self.error_type = "site_uncertainty"
        if self.system_type == "non-domestic":
            error = np.random.normal(0.95, 0.1)
        elif self.system_type == "domestic":
            error = np.random.normal(1, 0.15)
        else:
            raise ValueError("Unrecognised string '{}' in system_type field."
                             .format(self.system_type))
        self.capacity *= error
        # import pdb; pdb.set_trace()

    @_verbose("string outage")
    def string_outage(self):
        self.error_type = "string_outage"

        if self.system_type == "domestic":
            prob_invtr_fail = np.random.normal(0.02, 0.06)
            prob_invtr_fail = prob_invtr_fail if (prob_invtr_fail > 0) else 0
            random_number = random.uniform(0, 1)
            if random_number < prob_invtr_fail:
                # inverter has failed
                fail_time = np.random.normal(14, 7) # length of failure in days
                fail_time = fail_time if fail_time > 0 else 0
                self.capacity *= (fail_time/365)

        elif self.system_type == "non-domestic":
            prob_invtr_fail = np.random.normal(0.01, 0.03)
            prob_invtr_fail = prob_invtr_fail if prob_invtr_fail > 0 else 0
            random_number = random.uniform(0, 1)
            if random_number < prob_invtr_fail:
                # inverter has failed
                fail_time = np.random.normal(56, 28) # length of failure in days
                fail_time = fail_time if fail_time > 0 else 0
                self.capacity *= 2 * (fail_time / 365)

        else:
            raise ValueError("Unrecognised string '{}' in system_type field."
                             .format(self.system_type))

    @_verbose("network outage")
    def network_outage(self):
        if self.system_type == "non-domestic":
            self.capacity *= 0.99
        elif self.system_type== "domestic":
            pass
        else:
            raise ValueError("Unrecognised string '{}' in system_type field."
                             .format(self.system_type))

    def pvsystem_to_list(self):
        csf = ".8g"
        # import pdb; pdb.set_trace()
        self.eastings = self.eastings if not np.isnan(self.eastings) else None
        self.northings = self.northings if not np.isnan(self.northings) else None
        return [
            self.simulation_id,
            self.site_id,
            self.unreported,
            self.decommissioned_flag,
            float(format(self.capacity, csf)),
            self.eastings,
            self.northings
        ]

