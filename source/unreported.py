"""
A script to estimate the number of unreported systems.

- First authored: 2020-01-20
- Owen Huxley <othuxley1@sheffield.ac.uk>
"""

import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt
from matplotlib import rcParams
rcParams.update({'figure.autolayout': True})
import seaborn as sns
plt.style.use('seaborn')

from FIT_rate import FITRate


class InstallRate:

    """
    A class to handle the solar pv install deployment data and
    estimate the number of unreported solar pv systems.
    """

    def __init__(self):
        self.install_count_file = "../data/solar_pv_install_count.csv"
        self.cum_count = None
        self.cc_cols = None
        self.cum_count_unstacked = None
        self.results = None
        self.fit_rate_instance = FITRate()

    def read_install_csv(self):
        """
        A function to read the csv file containing the cumulative count of
        installed solar pv systems.
        Returns
        -------
        unstacked : pandas.DataFrame
            A DataFrame of the transpose of csv data and
            with the  the columns unstacked into rows.
        data_T : pandas.DataFrame
            A DataFrame of the transpose of the csv data.

        See Also
        --------
        The data in the csv file was taken from the
        "Solar_Photovoltaics_Deployment_November_2019.xlsx" file. The sheet
        used was "Table 1 - By Capacity" and the cells were B34 -> DQ40.
        """

        data = pd.read_csv(self.install_count_file,)
        data.rename({"Cumulative Count" : "Install Size"},
                    axis="columns", inplace=True)

        # create data_T DataFrame
        # =========================
        data_T = data.T
        # renaming columns in data_T
        old_cols = data_T.columns.values.tolist()
        new_cols = data_T.iloc[0, :].values.tolist()
        cols_dict = {old : new for old, new in zip(old_cols, new_cols)}
        data_T.rename(cols_dict, axis="columns", inplace=True)
        # dropping duplicated header row from DataFrame values
        data_T.drop(["Install Size"], inplace=True)

        # create dict with column header alias'
        # I want to keep the less then or equal to sign for plotting
        aliases = ["0to4", "4to10", "10to50", "50to5", "5to25", "25+"]
        cols = {alias : header
                for alias, header in zip(aliases, data_T.columns.tolist())}

        # remove commas from counts aka. 2,500 --> 2500
        for alias in cols.keys():
            data_T[cols[alias]] = data_T[cols[alias]]\
                .str.replace(",", "").astype(int)

        self.cum_count = data_T
        self.cc_cols = cols

        # create unstacked DataFrame
        # ===========================
        unstacked = data_T.unstack().reset_index()
        unstacked.rename(
            { "level_0" : "Install Size",
              "level_1" : "Date",
              0 : "Cumulative Count"},
            axis="columns", inplace=True
        )
        unstacked["Date"] = pd.to_datetime(unstacked["Date"])
        unstacked.set_index("Date", inplace=True)
        # remove commas from counts and set column to int dtype
        unstacked["Cumulative Count"] = unstacked["Cumulative Count"]\
            .astype(str).str.replace(",", "").astype(int)
        self.cum_count_unstacked = unstacked

        return unstacked, data_T

    def linear_relationship(self, fit_rate, m=-1, c=1):
        """
        A function to calculate the probability that a solar pv
        system is installed and not reported based on an inverse linear
        relationship between the FIT rate and reporting probability.
        The transformation used is y = ((gradient/range) * (x-min)) + c
        Where
            - y is the probability that a pv system is not reported
            - x is the FIT rate in pence
            - min is the minimum fit rate
            - range is the range of the fit rate in pence

        Parameters
        ----------
        fit_rate : float
            The fit_rate in pence for which we want to calculate the probability
            that a pv system is unreported (e.g. the owner does not claim
            subsidy).
        m : int, float
            The gradient of the linear relationship that you would like to
            simulate.
        c : int, float
            The y intercept of the linear relationship that you would like to
            simulate.

        Returns
        -------
        float
            The probability that, for the given FIT rate in pence (fit_rate),
            any given system will be unreported (aka. will not claim subsidy).

        """
        min_fit = self.fit_rate_instance.min_fit   # pence
        max_fit = self.fit_rate_instance.max_fit   # pence
        fit_range = np.abs(max_fit - min_fit)      # pence
        if fit_rate < min_fit:
            return 1.
        elif fit_rate > max_fit:
            return 0.
        elif min_fit < fit_rate < max_fit:
            return (m/fit_range * (fit_rate - min_fit)) + c

    def power_relationship(self, fit_rate, m=-1, c=1, a=2):
        """
        A function to calculate the probability that a solar pv
        system is installed and not reported based on  power of x
        relationship between the FIT rate and reporting probability.
        The transformation used is y = -((gradient/range) * (x-min)) ** a + c
        Where
            - y is the probability that a pv system is not reported
            - x is the FIT rate in pence
            - min is the minimum fit rate
            - range is the range of the fit rate in pence

        Parameters
        ----------
        fit_rate : float
            The fit_rate in pence for which we want to calculate the probability
            that a pv system is unreported (e.g. the owner does not claim
            subsidy).
        m : int, float
            The gradient of the power of x relationship that you would like to
            simulate.
        c : int, float
            The y intercept of the power of x relationship that you would
            like to simulate.
        a : int
            The power to use, where `a` is any positive real number.

        Returns
        -------
        float
            The probability that, for the given FIT rate in pence (fit_rate),
            any given system will be unreported (aka. will not claim subsidy).

        """

        min_fit = self.fit_rate_instance.min_fit    # pence
        max_fit = self.fit_rate_instance.max_fit    # pence
        fit_range = np.abs(max_fit - min_fit)       # pence

        if fit_rate < min_fit:
            return 1
        elif fit_rate > max_fit:
            return 0
        elif min_fit < fit_rate < max_fit:
            return -(m/fit_range * (fit_rate - min_fit)) ** a + c

    def exponential_relationship(self, fit_rate, a=1):
        """
        A function to calculate the probability that a solar pv
        system is installed and not reported based on an exponential
        relationship between the FIT rate and reporting probability.
        The transformation used is y = exp(-((gradient/range) * (x-min)))
        Where
            - y is the probability that a pv system is not reported
            - x is the FIT rate in pence
            - min is the minimum fit rate
            - range is the range of the fit rate in pence

        Parameters
        ----------
        fit_rate : float
            The fit_rate in pence for which we want to calculate the probability
            that a pv system is unreported (e.g. the owner does not claim
            subsidy).
        a : int
            The power which we will raise e^-x to.

        Returns
        -------
        float
            The probability that, for the given FIT rate in pence (fit_rate),
            any given system will be unreported (aka. will not claim subsidy).

        """

        # to reduce the probability of unreporting at low FIT rates
        # I have subtracted 1 from the min of the fit price
        min_fit = self.fit_rate_instance.min_fit - 1    # pence
        max_fit = self.fit_rate_instance.max_fit        # pence
        fit_range = np.abs(max_fit - min_fit)           # pence

        if fit_rate < min_fit:
            return 1
        elif fit_rate > max_fit:
            return 0
        elif min_fit <= fit_rate <= max_fit:
            return math.exp( -a * ((1/fit_range) * (fit_rate - min_fit)))

    def plot_unreported_relationships(self, params):
        """
        Plot relationships between the FIT rate and the probability of
        unreporting.

        Parameters
        ----------
        params : tuple
            A tuple of tuples. The inner tuple should be contain
                - the function to plot
                - a list of arguments to pass to the function
                - the name of the function to use for the plot legend
        """
        # create DataFrame with data to plot
        fit_rates = np.arange(0, 55, 0.1)
        unreported = {func_name : [func(x, **func_args) for x in fit_rates]
                      for func, func_args, func_name in params}
        unreported["FIT Rate (p)"] = fit_rates
        unrp_df = pd.DataFrame(unreported).set_index("FIT Rate (p)")

        # plot graph
        fig = plt.figure()
        ax = sns.lineplot(data=unrp_df)
        ax.set_ylabel("Probability of unreporting", fontsize=18)
        ax.set_xlabel("FIT Rate (p)", fontsize=18)
        plt.setp(ax.get_legend().get_texts(), fontsize='14') # for legend text
        plt.setp(ax.get_legend().get_title(), fontsize='16') # for legend title
        fig.savefig("../graphs/unreported_fit_relationships.png", dpi=600)
        plt.show()
    
    def calculate_unreported(self):
        columns = [
            self.cc_cols["0to4"],
            self.cc_cols["4to10"],
            self.cc_cols["10to50"],
            self.cc_cols["50to5"]
        ]
        # calculate the number of unreported systems for
        # all systems under 5 MW and binned as in the `columns`
        # variable
        unreported_dfs = [self.calc_unrep(col) for col in columns]
        _index = unreported_dfs[0].index
        # import pdb; pdb.set_trace()
        unreported_cc_dfs = [
            df[["Cumulative Count", "Cumulative Count Unreported exp(-7x)"]]
            for df in unreported_dfs
        ]
        unreported_cc_df = pd.concat(unreported_cc_dfs, axis=1,
                                     keys=columns)
        unreported_cc_df.index = pd.DatetimeIndex(unreported_cc_df.index)
        self.results = unreported_cc_df
        return unreported_cc_df

    def plot_results(self):

        """Plot results of analysis."""

        df = self.results.rename(
            {"Cumulative Count" : "Reported",
             "Cumulative Count Unreported exp(-7x)" : "Unreported"},
            axis=1
        )
        df = df /1000

        fig, axes = plt.subplots(2, 2, figsize=[7,7], sharex=True, sharey=False)
        # fig.subplots_adjust(left=1, right=0.9, bottom=1)
        ax1, ax2, ax3, ax4 = axes[0,0], axes[0, 1], axes[1, 0], axes[1, 1]

        df[self.cc_cols["0to4"]].plot.area(stacked=True, ax=ax1,
                                           color=['#55A868', '#4C72B0'])
        ax1.set_title(self.cc_cols["0to4"], fontsize=12)
        ax1.legend('')
        ax1.set_xlabel('')
        ax1.set_ylabel('')

        df[self.cc_cols["4to10"]].plot.area(stacked=True, ax=ax2,
                                            color=['#55A868', '#4C72B0'])
        ax2.set_title(self.cc_cols["4to10"], fontsize=12)
        ax2.set_xlabel('')
        ax2.set_ylabel('')

        df[self.cc_cols["10to50"]].plot.area(stacked=True, ax=ax3,
                                             color=['#55A868', '#4C72B0'])
        ax3.set_title(self.cc_cols["10to50"], fontsize=12)
        ax3.set_xlabel('')
        ax3.set_ylabel('')
        ax3.legend('')
        ax3.tick_params(axis="x", labelrotation=90.0)

        df[self.cc_cols["50to5"]].plot.area(stacked=True, ax=ax4,
                                            color=['#55A868', '#4C72B0'])
        ax4.set_title(self.cc_cols["50to5"], fontsize=12)
        ax4.set_xlabel('')
        ax4.set_ylabel('')
        ax4.legend('')
        ax4.tick_params(axis="x", labelrotation=90.0)

        fig.text(0.42, 0.02, 'Date (Y)', ha='center')
        fig.text(0.02, 0.5, "PV System Count (000's)", va='center',
                 rotation='vertical')
        leg = ax2.legend(fontsize='small', loc='center left',
                         bbox_to_anchor=(1, 0.5))
        leg.set_title('Data Source', prop={'size':'small'})
        plt.tight_layout(pad=5)
        plt.show()

        fig.savefig("../graphs/unreported_grid_area_plot.png", dpi=600)

        fig2 = plt.figure()
        # sum over all system sizes, for reported and unreported
        df = df.sum(axis=1, level=1)
        df.plot.area(stacked=True, color=['#55A868', '#4C72B0'])
        plt.ylabel("PV System Count (000's)")
        plt.show()
        fig2.savefig("../graphs/unreported_area_plot.png", dpi=600)

    def calc_unrep(self, col):

        """
        A function to calculate the number of unreported systems using a
        simulated relationship between FIT rate in pence and the probability of
        a solar pv system being unreported.

        Returns
        -------
        col_data : pandas.DataFrame
            A DataFrame containing the simualted unreported systems.
        """

        # create an instance of the FITRate class
        FR_instance = FITRate()

        # create DataFrame with the col_data count
        # for all systems covered by the FIT
        col_data = self.cum_count[[col]]
        # import pdb; pdb.set_trace()
        col_data = pd.DataFrame(col_data)
        # import pdb; pdb.set_trace()
        col_data.index.rename("Date", inplace=True)
        col_data.rename({col : "Cumulative Count"}, axis=1, inplace=True)
        # import pdb; pdb.set_trace()

        # create a column of the monthly count of installed systems
        col_data["Count"] = col_data.diff()
        col_data.iloc[0, -1] = col_data.iloc[0, -2]
        col_data.reset_index(inplace=True)
        # get the FIT rate for each row, calculated from the
        # date using the instance of the FITRate class.
        col_data["FIT"] = col_data["Date"] \
            .apply(FR_instance.get_fit_rate).astype(float)

        # calculate the probability of unreporting using a
        # y = exp(-5x) relationship between FIT rate in pence and
        # the probability of unreporting
        col_data["exp(-7x)"] = col_data["FIT"] \
            .apply(self.exponential_relationship, a=9)

        col_data["Count Unreported exp(-7x)"] = \
            col_data["Count"] * col_data["exp(-7x)"]
        col_data["Cumulative Count Unreported exp(-7x)"] = \
            col_data["Count Unreported exp(-7x)"].cumsum()

        col_data.set_index("Date", inplace=True)
        return col_data

    def save_results(self):
        df = self.results.unstack(level=1)
        df = df.reset_index()
        df = df.rename({"level_0" : "System Size",
                        "level_1" : "Status",
                        0 : "Cumulative Count"}, axis=1)
        df.to_csv("../data/unreported_results.csv")


if __name__ == "__main__":
    instance = InstallRate()
    unstacked_, data_T_ = instance.read_install_csv()
    instance.plot_unreported_relationships(
        ((instance.exponential_relationship, {"a" : 7}, "y = e^-7x"),)
    )
    instance.calculate_unreported()
    instance.plot_results()
    instance.save_results()

