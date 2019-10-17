
import time as TIME
import pandas as pd
import os

# from generic_tools import print_progress
from site_list_variation import SiteListVariation


class MonteCarloSiteList:

    """
    A class to run a monte carlo simulation for the
    installed PV site list
    """

    def __init__(self, random_seeds=None, N=100, n=10):
        self.random_seeds = random_seeds
        self.clock_seeds = []
        self.N = int(N)
        self.n = int(n)
        self.national_capacity = []
        self.out_file = "../data/results_{}N.csv".format(self.N)

    def run(self):

        """Execute methods and save data to file."""

        if os.path.isfile(self.out_file):
            raise FileExistsError("Please change the output file "
                                  "and try again.")
        count = 0
        if self.random_seeds is None:
            print("executing MC simulation...")
            while not count // self.N:
                # print("here")
                self.run_MC_without_seed(self.n)
                self.write_results_to_csv(self.clock_seeds,
                                          self.national_capacity)
                count += self.n

        # TODO
        #  make this bit work
        # if self.random_seeds is not None:
        #     self.run_MC_with_seed()
        #     self.write_results_to_csv(self.random_seeds, self.national_capacity)



    def run_MC_without_seed(self, N: int) -> list:
        """
        A function to run the SiteListVariation
        Parameters
        ----------
        N: int,
            The number of site list permutations to calculate.

        Returns
        -------
        sl_variants: list,
            A list of pandas dataframe objects containing the site list
            permutations.
        """

        sl_variants = []
        for sim in range(N+1):
            # get clock time to seed SiteListVariation random generator
            clock_seed = int(TIME.time())
            self.clock_seeds.append(clock_seed)
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
        return sl_variants

    def sim_stats(self, sl: object) -> None:
        """

        Calculate population statistics for each permutation of the site list
        in the analysis.

        Parameters
        ----------
        sl: object,
            A pandas datafrome object containing the resultant site list after
            the analysis has been completed.

        """
        national_capacity = sl.Capacity.sum()
        print(national_capacity)
        self.national_capacity.append(national_capacity)

    def write_results_to_csv(self, seeds: list, capacities: list) -> None:
        """

        Write results to csv using append method.

        Parameters
        ----------
        seeds: list,
            Random seeds used in analysis
        capacities: list,
            National capacities generated from the site list permutations.

        """
        if os.path.isfile(self.out_file):
            with open(self.out_file, 'a') as out:
                for seed, capacity in zip(seeds, capacities):
                    out.write("{},{}\n".format(seed, capacity))
        else:
            with open(self.out_file, 'w') as out:
                out.write("random_seed, national_capacity (MW)\n")
                for seed, capacity in zip(seeds, capacities):
                    out.write("{},{}\n".format(seed, capacity))

# if __name__ == "__main__":
MC_instance = MonteCarloSiteList(N=2, n=1)
MC_instance.run()
