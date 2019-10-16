
import time as TIME
import pandas as pd

from generic_tools import print_progress
from site_list_variation import SiteListVariation


class MonteCarloSiteList:

    """
    A class to run a monte carlo simulation for the
    installed PV site list
    """

    def __init__(self, random_seeds=None, N=2):
        self.random_seeds = random_seeds
        self.simulations = int(N)
        self.national_capacity = []

    def run(self):
        if self.random_seeds is None:
            self.run_MC_without_seed()



    def run_MC_without_seed(self):

        sl_variants = []
        print_progress(0, self.simulations)
        for sim in range(self.simulations+1):
            # get clock time to seed SiteListVariation random generator
            clock_seed = int(TIME.time())
            # calculate site_list permutation
            domestic = SiteListVariation(sim, verbose=False,
                                         system_type="domestic",
                                         seed=clock_seed)
            non_domestic = SiteListVariation(sim, verbose=False,
                                             system_type="non-domestic",
                                            seed=clock_seed)
            domestic.run()
            non_domestic.run()
            sl = pd.concat((domestic.new_SL, non_domestic.new_SL))
            sl_variants.append(sl)
            self.sim_stats(sl)
            print_progress(sim, self.simulations)
        print_progress(self.simulation, self.simulation)

        return sl_variants


    def sim_stats(self, sl):
        national_capacity = sl.Capacity.sum()
        print(national_capacity)
        self.national_capacity.append(national_capacity)







# if __name__ == "__main__":
MC_instance = MonteCarloSiteList(N=100)
MC_instance.run()
