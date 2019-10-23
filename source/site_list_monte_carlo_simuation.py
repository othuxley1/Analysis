
import time as TIME
import pandas as pd
import os
import gc
from itertools import zip_longest

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
        self.out_file = "../data/results_from_seed_{}N.csv".format(self.N)

    @staticmethod
    def grouper(iterable, n, fillvalue=None):
        """Collect data into fixed-length chunks or blocks"""
        # grouper('ABCDEFG', 3, 'x') --> ABC DEF Gxx"
        args = [iter(iterable)] * n
        yield from zip_longest(*[iter(iterable)] * n, fillvalue=fillvalue)

    def run(self):

        """Execute methods and save data to file."""

        if os.path.isfile(self.out_file):
            raise FileExistsError("Please change the output file "
                                  "and try again.")
        tstart = TIME.time()

        if self.random_seeds is None:
            print("executing MC simulation...")
            count = 0
            while not count // self.N:
                # print("here")
                self.run_MC_without_seed(self.n)
                self.write_results_to_csv(self.clock_seeds,
                                          self.national_capacity)
                self.clock_seeds = []
                self.national_capacity = []
                count += self.n
        else:
            for chunk in MonteCarloSiteList.grouper(self.random_seeds, self.n):
                self.run_MC_with_seed(chunk)
                self.write_results_to_csv(chunk,
                                          self.national_capacity)
                self.national_capacity = []

        print("Finished, time taken {}...".format(TIME.time() - tstart))

        # TODO
        #  rewrite with/without as one function

    def run_MC_with_seed(self, chunk):
        """
        A function to run the SiteListVariation using a pre-determined list of
        seeds for the numpy random number generator.
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
        # TODO
        #  fix sim parameter in SiteListVariation - not acting as intended here
        sl_variants = []
        for index, seed in enumerate(chunk):
            domestic = SiteListVariation(index, verbose=False,
                                         system_type="domestic",
                                         seed=seed)
            non_domestic = SiteListVariation(index, verbose=False,
                                             system_type="non-domestic",
                                             seed=seed)
            domestic.run()
            non_domestic.run()
            sl = pd.concat((domestic.new_SL, non_domestic.new_SL))
            sl_variants.append(sl)
            self.sim_stats(sl)
            del domestic
            del non_domestic
        return sl_variants



    def run_MC_without_seed(self, N):
        """
        A function to run the SiteListVariation using clock time to seed the
        numpy random number generator.
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
        for sim in range(N):
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
            del domestic
            del non_domestic
        return sl_variants

    def sim_stats(self, sl):
        """

        Calculate population statistics for each permutation of the site list
        in the analysis.

        Parameters
        ----------
        sl: object,
            A pandas datafrome object containing the resultant site list after
            the analysis has been completed.

        """
        # import pdb; pdb.set_trace()
        national_capacity = sl.loc[sl.loc[:, "decommissioned"] == 0].Capacity.sum()
        print(national_capacity)
        self.national_capacity.append(national_capacity)

    def write_results_to_csv(self, seeds, capacities):
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


def load_seed_data(file):
    seeds = []
    with open(file, 'r') as fid:
        next(fid)
        for line in fid.readlines():
            # import pdb; pdb.set_trace()
            data = [x for x in line.strip('\n').split(',')]
            seeds.append(int(data[0]))
    return seeds

input_seeds_file = "../data/results_10N.csv"
input_seeds = load_seed_data(input_seeds_file)
MC_instance = MonteCarloSiteList(random_seeds=input_seeds, N=len(input_seeds), n=1)
MC_instance.run()