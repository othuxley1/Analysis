"""
A script to plot results for the monte carlo site list analysis.
- First Authored 2020-02-12
- Owen Huxley <othuxley1@sheffield.ac.uk>
"""

import pandas as pd
import matplotlib.pyplot as plt
from scipy.stats import johnsonsu
import numpy as np
import seaborn as sns


class MonteCarloAnalysisResults:

    """A class to plot graphs of results from monte carlo site list analysis."""

    def __init__(self):
        self.results_file = "C:/Users/owenh/Documents/GitRepos/" \
                            "capacity_mismatch_paper/data/" \
                            "MC_results_20200227_10000N.csv"
        self.data = pd.read_csv(self.results_file)
        self.rename_cols()
        self.min = self.data.capacity_MW.min()
        self.max = self.data.capacity_MW.max()
        # johnsonsu estimates
        self.shape_a = 1
        self.shape_b = 2
        self.loc = 1200
        self.scale = 360

    def rename_cols(self):
        self.data.rename(
            {" national_capacity (MW)": "capacity_MW"},
            inplace=True, axis=1
        )

    def plot_histogram(self):
        fig = plt.figure()
        self.data.plot.hist(by="capacity_MW")
        plt.show()
        fig.savefig("MC_results_histogram.png", dpi=300)

    def fit_johnson_su(self):
        jsu_fit = johnsonsu.fit(
            self.data["capacity_MW"],
            self.shape_a,
            self.shape_b,
            loc=self.loc,
            scale=self.scale
        )
        x = np.linspace(
            self.data.capacity_MW.min(),
            self.data.capacity_MW.max(),
            100
        )
        jsu_pdf = johnsonsu.pdf(x, *jsu_fit)

        fig = plt.figure()
        plt.plot(x, jsu_pdf)
        plt.show()
        return x, jsu_pdf

    def plot_results(self):

        sns.set_context("paper")

        bins = np.arange(self.min, self.max, 100)
        x, jsu = self.fit_johnson_su()


        fig = plt.figure()
        sns.distplot(
            self.data["capacity_MW"],
            rug=True, kde=True, color="black",
            vertical=True, rug_kws={"height": 0.025}
        )
        sns.despine()
        plt.ylabel("Capacity (MW)")
        plt.show()
        fig.savefig("Monte_Carlo_Histogram.png", dpi=600)

    def fit_normal(self):
        return

    def handle_outliers(self):
        return

if __name__ == "__main__":
    self = MonteCarloAnalysisResults()
    # import pdb; pdb.set_trace()
    self.rename_cols()
    self.plot_histogram()
    self.fit_johnson_su()
    self.plot_results()


