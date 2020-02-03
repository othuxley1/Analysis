"""
A script to estimate the number of unreported systems.

- First authored: 2020-01-20
- Owen Huxley <othuxley1@sheffield.ac.uk>
"""

import pandas as pd
import numpy as np
import math
import matplotlib.pyplot as plt
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

        # prepare data_T DataFrame
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
        for alias in cols.keys():
            data_T[cols[alias]] = data_T[cols[alias]]\
                .str.replace(",", "").astype(int)

        self.cum_count = data_T
        self.cc_cols = cols

        # create unstacked DataFrame
        # data_T.unstack(level=1).reset_index() # redundant???
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
        fit_rates = np.arange(0, 70)
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
        """
        A function to calculate the number of unreported systems using a
        simulated relationship between FIT rate in pence and the probability of
        a solar pv system being unreported.

        Returns
        -------
        total : pandas.DataFrame
            A DataFrame containing the simualted unreported systems.
        """
        # create an instance of the FITRate class
        FR_instance = FITRate()

        # create DataFrame with the total count
        # for all systems covered by the FIT
        total = self.cum_count[
            [
                self.cc_cols["0to4"],
                self.cc_cols["4to10"],
                self.cc_cols["10to50"],
                self.cc_cols["50to5"]
            ]
        ].sum(axis=1)
        total = pd.DataFrame(total, columns=["Cumulative Count"])
        total.index.rename("Date", inplace=True)

        # create a column of the monthly count of installed systems
        total["Count"] = total.diff()
        total.iloc[0, -1] = total.iloc[0, -2]
        total.reset_index(inplace=True)

        # get the FIT rate for each row, calculated from the
        # date using the instance of the FITRate class.
        import pdb; pdb.set_trace()
        total["FIT"] = total["Date"]\
            .apply(FR_instance.get_fit_rate).astype(float)

        # calculate the probability of unreporting using a
        # y = exp(-5x) relationship between FIT rate in pence and
        # the probability of unreporting
        import pdb; pdb.set_trace()
        total["exp(-5x)"] = total["FIT"]\
            .apply(self.exponential_relationship, a=5)

        total["Count Unreported exp(-5x)"] = total["Count"] * total["exp(-5x)"]
        total["Cumulative Count Unreported exp(-5x)"] = \
            total["Count Unreported exp(-5x)"].cumsum()

        return total

    def plot_graphs(self):
        """
        A function to plot a stacked area plot of the cumulative count
        of all deployed solar pv system from the input data.
        """
        fig = plt.figure()
        df = self.cum_count
        df.plot.area()
        plt.show()


if __name__ == "__main__":
    instance = InstallRate()
    unstacked_, data_T_ = instance.read_install_csv()
    instance.plot_unreported_relationships(
        (
            (instance.linear_relationship, {}, "y = x"),
            (instance.power_relationship, {"a" : 2}, "y = -x^a + 1"),
            # (instance.exponential_relationship, {"a" : 1}, "y = e^-x"),
            (instance.exponential_relationship, {"a" : 2}, "y = e^-2x"),
            (instance.exponential_relationship, {"a" : 3}, "y = e^-3x"),
            (instance.exponential_relationship, {"a" : 4}, "y = e^-4x"),
            (instance.exponential_relationship, {"a" : 5}, "y = e^-5x")
        )

    )
    fig = plt.figure()
    unr = instance.calculate_unreported()
    unr[["Cumulative Count", "Cumulative Count Unreported exp(-5x)"]].plot.area()

    fig.savefig("../graphs/unreported_results_area.png", dpi=600)
    plt.show()

