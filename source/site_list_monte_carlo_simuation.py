
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

    def __init__(self, sd_file=None, N=100, n=10):
        self.random_seeds = MonteCarloSiteList.load_seeds(sd_file) if sd_file is not None else None
        self.N = int(N) if sd_file is None else len(self.random_seeds)
        self.n = int(n)
        if self.random_seeds is not None:
            assert len(self.random_seeds) == self.N, \
                "N must match the number of random_seeds"
        self.clock_seeds = []
        self.national_capacity = []
        self.out_file = "../data/MC_results_v2_T0only_20200430_{}N.csv".format(self.N)

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
        print("Executing Monte Carlo simulation...")
        # TODO
        #  self.clock_seeds variable needs a better name
        count = 0
        for sim in range(self.N):
            seed = int(TIME.time()) if self.random_seeds is None else self.random_seeds[sim]
            self.clock_seeds.append(seed)
            self.run_mc(seed, sim)
            count += 1
            if count // self.n:
                self.write_results_to_csv(self.clock_seeds,
                                          self.national_capacity)
                count = 0
                self.clock_seeds = []
                self.national_capacity = []

        print("Finished, time taken {}...".format(TIME.time() - tstart))

    def run_mc(self, seed, index):
        """
        A function to run the SiteListVariation using a seed
         for the numpy random number generator.
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
        sl_rvs = SiteListVariation(index, verbose=False, seed=seed, test=False)
        sl_rvs.unreported_systems()
        sl_rvs.simulate_effective_capacity_site_list()
        sl = sl_rvs.SL.copy()
        self.sim_stats(sl)
        del sl_rvs
        return sl

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
        national_capacity = sl.Capacity.sum()
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
    @staticmethod
    def load_seeds(file):
        seeds = []
        with open(file, 'r') as fid:
            next(fid)
            for line in fid.readlines():
                # import pdb; pdb.set_trace()
                data = [x for x in line.strip('\n').split(',')]
                seeds.append(int(data[0]))
        return seeds

input_seeds_file = "../data/results_10N.csv"
MC_instance = MonteCarloSiteList(N=1000, n=1)
MC_instance.run()