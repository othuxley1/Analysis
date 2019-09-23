import pandas as pd
import numpy as np
from configparser import ConfigParser
import sys
import os
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib import gridspec
from cycler import cycler
from collections import OrderedDict
import plotly.plotly as py
import plotly.tools as tls
import argparse
from datetime import datetime
import pytz

sys.path.append("C:/Users/owenh/OneDrive/Documents/Gitkraken/ss-utilities/ss_utilities")

from dbconnector import DBConnector
from generic_tools import query_yes_no


class PVLiveStats:


    """ A module to calculate validation statistics for PV Live"""

    def __init__(self, options=None):
        self.config = self.load_config()
        if options is None:
            self.options = self.parse_options()
        else:
            self.options = dotdict(options)
        self.run()
    
    @staticmethod
    def load_config(file_location=None):

        """
        Load the config from file.

        Parameters
        ----------
        `file_location` : string
            Optionally provide the location of the config file as full absolute path. If not
            provided, config is assumed to be in 'Config/config.ini'.
        Returns
        -------
        dict
            A dictionary of config parameters whose keys match the names used in the config file.
        Notes
        -----
        Must have the os, and SafeConfigParser modules imported otherwise the try condition will
        always raise an exception.
        """

        try:
            if not file_location:
                file_location = (os.path.dirname(os.path.realpath(__file__)) + os.sep + "Config"
                                 + os.sep + "config.ini")
            parser = ConfigParser()
            parser.read(file_location)
            config = {}
            config["config_location"] = file_location
            config["mysql_options_readwrite_nationalgrid"] = parser.get("mysql_defaults",
                                                                       "mysql_options_readwrite"
                                                                       "_nationalgrid")
            config["pvgen_table"] = parser.get("mysql_defaults", "pvgen_table")
        except:
            raise Exception("Error loading config, please check that the config file (%s) exists"
                            " and lists all of the required values." % file_location)
        return config
    
    @staticmethod
    def parse_options():
        parser = argparse.ArgumentParser(description=("This is a command line interface (CLI) for"
                                                      "the PVLive_stats module"),
                                         epilog="Owen Huxley 2019-01-24")
        parser.add_argument("-s", "--start", metavar="\"<yyyy-mm-dd>\"", dest="start",
                            action="store", type=str, required=False, default=None,
                            help="Specify the start date in 'yyyy-mm-dd' format (inclusive).")
        parser.add_argument("-e", "--end", metavar="\"<yyyy-mm-dd>\"", dest="end",
                            action="store", type=str, required=False, default=None,
                            help="Specify the end date in 'yyyy-mm-dd' format (inclusive).")
        parser.add_argument("-f", "--outfolder", metavar="<path-to-file>", dest="outfolder",
                            action="store", type=str, required=False, default=None,
                            help="Specify a filename to print results to.")
        parser.add_argument("-tz", "--time-zone", dest="tz_string", action="store", required=False,
                            metavar="\"<Olson timezone string>\"", type=str, default="Europe/London",
                            help="Specify the time zone used for the -s / --start and -e / --end "
                                "options. Default is 'Europe/London' i.e. the local timezone in "
                                "Sheffield.")
        options = parser.parse_args()
        def handle_options(options):
            options.time_zone = pytz.timezone(options.tz_string)
            if not os.path.exists(options.outfolder):
                os.makedirs(options.outfolder)
            else:
                raise Exception("This folder already exists. Either choose a different folder name"
                                " or delete the folder and try again.")
                if check is False:
                    print("Quitting...")
                    sys.exit(0)
            if options.start is not None and options.end is not None:
                try:
                    options.start = options.time_zone.localize(
                        datetime.strptime(options.start, "%Y-%m-%d")
                    )
                    options.end = options.time_zone.localize(
                        datetime.strptime(options.end, "%Y-%m-%d")
                    )
                except:
                    raise Exception("OptionsError: Failed to parse start and end datetime, make sure "
                                    "you use 'yyyy-mm-dd' format.")
            return options
        return handle_options(options)


    def run(self):

        """Execute method"""

        pvlive_all_sites = self.download_pvlive_from_db(46)
        versions = [246, 237, 253, 230, 238, 231, 239, 232, 240, 233, 241, 234, 242] 
        pvlive_data = {} # key = sample size
        stats = OrderedDict({}) # key = sample size

        for version in versions:

            print("Downloading data for version {}...".format(version))
            data = self.download_pvlive_from_db(version)
            optimised_sample_size = int(np.nanmax(data["site count"]))
            pvlive_data[optimised_sample_size] = data
            print("Version {} has {} sites in its sample.".format(version, data["site count"].mean()))
            
            # compare test pvlive data with latest full pvlvie version
            stats[optimised_sample_size] = self.calc_stats(pvlive_all_sites, data)
            print("    --> Finished.")

        self.plot_rolling_average_weekly_wmape(stats)
        self.plot_yearly_rsq_wmape(stats)
        self.plot_weekly_wmape_boxplots(stats)
        self.plot_mean_daily_rsq_wmape(stats)
        self.save_results(stats)
        print("FINISHED.")

        return

    def calc_stats(self, comparator, test):

        """
        statistics for the period
        expects a DataFrame with columns for 'forecast' and 'outturn' and indexed by datetime
        capacity is provided as a parameter
        """
        # empty data frame to populate with results
        results = pd.DataFrame()

        # limiting analysis to between 9am and 3pm
        comparator_9to3 = comparator.between_time("9:30", "15:00")
        test_9to3 = test.between_time("9:30", "15:00")

        results["actuals"] = comparator_9to3["generation MW"]
        results["all sites count"] = comparator_9to3["site count"]
        results["subset count"] = test_9to3["site count"]
        results["predictions"] = test_9to3["generation MW"]
        results["capacity"] = comparator_9to3["capacity MWp"]
        results['diff'] = comparator_9to3['generation MW'] - test_9to3['generation MW']
        results['abs_diff'] = np.abs(results['diff'])
        results['s_diff'] = results['diff'] * results['diff']

        # calculating daily wmape and rsquared
        daily_group = results.groupby(results.index.date)
        daily_corr = daily_group.corr()
        daily_wmape = daily_group.apply(self.wmape)
        daily_rsquared = daily_group.apply(self.r_squared)

        # calculating weekly wmape and rsquared
        weekly_group = results.groupby([results.index.year, results.index.week])
        weekly_corr = weekly_group.corr()
        weekly_wmape = weekly_group.apply(self.wmape)
        weekly_rsquared = weekly_group.apply(self.r_squared)

        # calculating yearly wmape and rsquared
        yearly_wmape  = self.wmape(results)
        yearly_rsquared = self.r_squared(results)

            
        return ({
                "wmape": yearly_wmape,
                "r sq": yearly_rsquared,
                "daily wmape": daily_wmape,
                "daily r sq": daily_rsquared,
                "weekly wmape": weekly_wmape,
                "weekly r sq": weekly_rsquared
                })

    def save_results(self, stats):

        """Saving results to file"""
        
        keys = stats.keys()

        # saving wmape and rsquared
        outfile = self.options.outfolder + "/wmape_rsquared.csv"
        with open(outfile, "w") as out:
            out.write("Optimised Sample Size, wMAPE, R Squared\n")
            for key in keys:
                out.write("{}, {}, {}\n".format(key, stats[key]["wmape"], stats[key]["r sq"]))

        # saving daily wmape and r squared
        outfile = self.options.outfolder + "/daily_wmape_rsquared.csv"
        with open(outfile, "w") as out:
            out.write("Optmised Sample Size, Date, wMAPE, R Squared\n")
            for key in keys:
                wmape = stats[key]["daily wmape"]
                rsq = stats[key]["daily r sq"]
                for date in wmape.index:
                    date_str = datetime.strftime(date, "%Y-%m-%d")
                    out.write("{}, {}, {}, {}\n".format(key, date_str, wmape[date], rsq[date]))

        # saving weekly wmape and r squared
        outfile = self.options.outfolder + "/weekly_wmape_rsquared.csv"
        with open(outfile, "w") as out:
            out.write("Optmised Sample Size, Year, Week, wMAPE, R Squared\n")
            for key in keys:
                wmape = stats[key]["daily wmape"]
                rsq = stats[key]["daily r sq"]
                for date in wmape.index:
                    date_str = datetime.strftime(date, "%Y-%m-%d")
                    out.write("{}, {}, {}, {}\n".format(key, date_str, wmape[date], rsq[date]))
        
            

    def plot_yearly_rsq_wmape(self, stats):

        """
        A function to plot two graphs.
        The weighted mean absolute percentage error vs sample size.
        The pearson's R correlation coefficient vs optimised sample size.
        Both graphs have optimised samples ranging from 500 -> 7000
        in increments of 500.
        """

        yearly_rsq = []
        yearly_wmape = []
        keys = stats.keys()
        num_lines = len(keys)
        for key in keys:
            yearly_wmape.append(stats[key]["wmape"])
            yearly_rsq.append(stats[key]["r sq"])

        #set matplotlib up
        plt.style.use('bmh')
        plt.rc('text', usetex=False)
        plt.rc('font', family='serif')
        SMALL = 4
        MEDIUM = 4
        LARGE = 6
        plt.rc('font', size=MEDIUM)         # controls default text sizes
        plt.rc('axes', titlesize=LARGE)     # fontsize of the axes title
        plt.rc('axes', labelsize=LARGE)     # fontsize of the x and y labels
        plt.rc('xtick', labelsize=SMALL)    # fontsize of the tick labels
        plt.rc('ytick', labelsize=SMALL)    # fontsize of the tick labels
        plt.rc('legend', fontsize=SMALL)    # legend fontsize
        plt.rc('text.latex', preamble=r'\usepackage{mathtools}')
        colors = [plt.cm.Spectral(i) for i in np.linspace(0, 1, num_lines)]
        #set matplotlib up

        #make a grid for plots
        gs=gridspec.GridSpec(2, 1)
        gs.update(wspace=0.2, hspace=0.2) 

        # setting up figure
        fig=plt.figure(figsize=(6, 4), edgecolor='k')

        # plot 1
        ax=fig.add_subplot(gs[0])
        ax.set_prop_cycle(cycler('color', colors))
        ax.spines['bottom'].set_color('k')
        ax.spines['top'].set_color('k') 
        ax.spines['right'].set_color('k')
        ax.spines['left'].set_color('k')
        ax.set_facecolor('w')
        ax.grid(True)
        ax.xaxis.tick_top()
        ax.xaxis.set_label_position('top')
        ax.yaxis.set_label_position('left')
        ax.tick_params(direction='out')
        ax.plot(keys, yearly_rsq,"-", label="$Yearly\; R^2$", linewidth=0.5)
        ax.set_ylabel("$Yearly\; R^2$")

        # plot 2
        ax2=fig.add_subplot(gs[1])
        ax2.set_prop_cycle(cycler('color', colors))
        ax2.spines['bottom'].set_color('k')
        ax2.spines['top'].set_color('k') 
        ax2.spines['right'].set_color('k')
        ax2.spines['left'].set_color('k')
        ax2.set_facecolor('w')
        ax.xaxis.set_label_position('bottom')
        ax.yaxis.set_label_position('left')
        ax2.set_ylabel("$Yearly\; wMAPE\; [\%]$")
        ax2.set_xlabel("$Optimised\; Sample\; Size$")
        ax2.grid(True)
        ax2.tick_params(direction='out')
        ax2.plot(keys, yearly_wmape, "-", label="$Yearly\; wMAPE$", linewidth=0.5)
        out = self.options.outfolder + "/yearly_rolling_mean_rsq_wmape.png"
        plt.savefig(out, dpi=500)
        # plt.show()


    def plot_mean_daily_rsq_wmape(self, stats):

        """
        A function to plot two graphs.
        The weighted mean absolute percentage error vs sample size.
        The pearson's R correlation coefficient vs optimised sample size.
        Both graphs have optimised samples ranging from 500 -> 7000
        in increments of 500.
        """

        keys = stats.keys()
        num_lines = len(keys)
        mean_wmape = []
        mean_rsq = []
        sd_wmape = []
        sd_rsq = []
        for key in keys:
            mean_wmape.append(np.mean(stats[key]["daily wmape"]))
            mean_rsq.append(np.mean(stats[key]["daily r sq"]))
            sd_wmape.append(np.std(stats[key]["daily wmape"]))
            sd_rsq.append(np.std(stats[key]["daily r sq"]))

        #set matplotlib up
        plt.style.use('bmh')
        plt.rc('text', usetex=False)
        plt.rc('font', family='serif')
        SMALL = 4
        MEDIUM = 4
        LARGE = 6
        plt.rc('font', size=MEDIUM)         # controls default text sizes
        plt.rc('axes', titlesize=LARGE)     # fontsize of the axes title
        plt.rc('axes', labelsize=LARGE)     # fontsize of the x and y labels
        plt.rc('xtick', labelsize=SMALL)    # fontsize of the tick labels
        plt.rc('ytick', labelsize=SMALL)    # fontsize of the tick labels
        plt.rc('legend', fontsize=SMALL)    # legend fontsize
        plt.rc('text.latex', preamble=r'\usepackage{mathtools}')
        colors = [plt.cm.Spectral(i) for i in np.linspace(0, 1, num_lines)]
        #set matplotlib up

        #make a grid for plots
        gs=gridspec.GridSpec(2, 1)
        gs.update(wspace=0.2, hspace=0.2) 

        # setting up figure
        fig=plt.figure(figsize=(6, 4), edgecolor='k')

        # plot 1
        ax=fig.add_subplot(gs[0])
        ax.set_prop_cycle(cycler('color', colors))
        ax.spines['bottom'].set_color('k')
        ax.spines['top'].set_color('k') 
        ax.spines['right'].set_color('k')
        ax.spines['left'].set_color('k')
        ax.set_facecolor('w')
        ax.grid(True)
        ax.xaxis.tick_top()
        ax.xaxis.set_label_position('top')
        ax.yaxis.set_label_position('left')
        ax.tick_params(direction='out')
        ax.plot(keys, mean_rsq,"-", label="$Yearly\; R^2$", linewidth=0.5)
        ax.errorbar(keys, mean_rsq, yerr=sd_rsq, fmt="x")
        ax.set_ylabel("$Yearly\; R^2$")

        # plot 2
        ax2=fig.add_subplot(gs[1])
        ax2.set_prop_cycle(cycler('color', colors))
        ax2.spines['bottom'].set_color('k')
        ax2.spines['top'].set_color('k') 
        ax2.spines['right'].set_color('k')
        ax2.spines['left'].set_color('k')
        ax2.set_facecolor('w')
        ax.xaxis.set_label_position('bottom')
        ax.yaxis.set_label_position('left')
        ax2.set_ylabel("$Yearly\; wMAPE\; [\%]$")
        ax2.set_xlabel("$Optimised\; Sample\; Size$")
        ax2.grid(True)
        ax2.tick_params(direction='out')
        ax2.plot(keys, mean_wmape, "-", label="$Yearly\; wMAPE$", linewidth=0.5)
        ax2.errorbar(keys, mean_wmape, yerr=sd_wmape, fmt="x")
        out = self.options.outfolder + "/mean_daily_rsq_wmape_errorbars.png"
        plt.savefig(out, dpi=500)
        # plt.show()

    def plot_rolling_average_weekly_wmape(self, stats):
        keys = stats.keys()
        num_lines = len(keys)

        window = 4

        #set matplotlib up
        plt.style.use('bmh')
        plt.rc('text', usetex=False)
        plt.rc('font', family='serif')
        SMALL = 4
        MEDIUM = 4
        LARGE = 6
        plt.rc('font', size=MEDIUM)         # controls default text sizes
        plt.rc('axes', titlesize=LARGE)     # fontsize of the axes title
        plt.rc('axes', labelsize=LARGE)     # fontsize of the x and y labels
        plt.rc('xtick', labelsize=SMALL)    # fontsize of the tick labels
        plt.rc('ytick', labelsize=SMALL)    # fontsize of the tick labels
        plt.rc('legend', fontsize=SMALL)    # legend fontsize
        plt.rc('text.latex', preamble=r'\usepackage{mathtools}')
        colors = [plt.cm.Spectral(i) for i in np.linspace(0, 1, num_lines)]
        #set matplotlib up

        #make a grid for plots
        gs=gridspec.GridSpec(2, 1)
        gs.update(wspace=0.15, hspace=0.15) 

        # setting up figure
        fig=plt.figure(figsize=(6, 4), edgecolor='k')

        # plot 1
        ax=fig.add_subplot(gs[0])
        ax.set_prop_cycle(cycler('color', colors))
        ax.spines['bottom'].set_color('k')
        ax.spines['top'].set_color('k') 
        ax.spines['right'].set_color('k')
        ax.spines['left'].set_color('k')
        ax.set_facecolor('w')
        ax.grid(True)
        ax.xaxis.tick_top()
        ax.xaxis.set_label_position('top')
        ax.yaxis.set_label_position('left')
        ax.tick_params(direction='out')
        for key in keys:
            df1 = stats[key]["daily r sq"]
            mma1 = df1.rolling(window, min_periods=3, center=True).mean()
            ax.plot(mma1.index, mma1.values,"-", label=key, linewidth=0.5)
        ax.set_ylabel("$Daily\; R^2$")
        # ax.set_xlabel("$Week of Year$")
        ax.legend()

        # plot 2
        ax2=fig.add_subplot(gs[1])
        ax2.set_prop_cycle(cycler('color', colors))
        ax2.spines['bottom'].set_color('k')
        ax2.spines['top'].set_color('k') 
        ax2.spines['right'].set_color('k')
        ax2.spines['left'].set_color('k')
        ax2.set_facecolor('w')
        ax.xaxis.set_label_position('bottom')
        ax.yaxis.set_label_position('left')
        ax2.set_ylabel("$Daily\; wMAPE\; [\%]$")
        ax2.set_xlabel("$Week\; of\; Year$")
        ax2.grid(True)
        ax2.tick_params(direction='out')
        for key in keys:
            df2 = stats[key]["daily wmape"]
            mma2 = df2.rolling(window, min_periods=3, center=True).mean()
            ax2.plot(mma2.index, mma2.values, "-", label=key, linewidth=0.5)
        ax2.legend(bbox_to_anchor=(5.5, 1.5))
        out = self.options.outfolder + "/weekly_rolling_mean_rsq_wmape.png"
        plt.savefig(out, dpi=500)
        # plt.show()

    def plot_weekly_wmape_boxplots(self, stats):
        keys = list(stats.keys()) # In python 3.x dict.keys returns a set
                                  # and so does not support indexing.
        num_lines = len(keys)

        #set matplotlib up
        plt.style.use('bmh')
        plt.rc('text', usetex=False)
        plt.rc('font', family='serif')
        SMALL = 4
        MEDIUM = 4
        LARGE = 6
        plt.rc('font', size=MEDIUM)         # controls default text sizes
        plt.rc('axes', titlesize=LARGE)     # fontsize of the axes title
        plt.rc('axes', labelsize=LARGE)     # fontsize of the x and y labels
        plt.rc('xtick', labelsize=SMALL)    # fontsize of the tick labels
        plt.rc('ytick', labelsize=SMALL)    # fontsize of the tick labels
        plt.rc('legend', fontsize=SMALL)    # legend fontsize
        plt.rc('text.latex', preamble=r'\usepackage{mathtools}')
        colors = [plt.cm.Spectral(i) for i in np.linspace(0, 1, num_lines)]
        #set matplotlib up
        
        # box plot data
        data = [stats[key]["weekly wmape"] for key in keys]

        # boxplots
        fig = plt.figure()
        plt.boxplot(data, positions=keys)
        out = self.options.outfolder + "/weekly_wmape_boxplots.png"
        plt.savefig(out, dpi=500)
        # plt.show()

        # import pdb; pdb.set_trace()


    def plot_mean_daily_wmape(self, stats):

        #set matplotlib up
        plt.style.use('bmh')
        plt.rc('text', usetex=False)
        plt.rc('font', family='serif')
        SMALL = 4
        MEDIUM = 4
        LARGE = 6
        plt.rc('font', size=MEDIUM) 			# controls default text sizes
        plt.rc('axes', titlesize=LARGE)     # fontsize of the axes title
        plt.rc('axes', labelsize=LARGE)     # fontsize of the x and y labels
        plt.rc('xtick', labelsize=SMALL)    # fontsize of the tick labels
        plt.rc('ytick', labelsize=SMALL)    # fontsize of the tick labels
        plt.rc('legend', fontsize=SMALL)    # legend fontsize
        plt.rc('text.latex', preamble=r'\usepackage{mathtools}')
        colors = [plt.cm.Spectral(i) for i in np.linspace(0, 1, num_lines)]
        #set matplotlib up


    @staticmethod
    def wmape(df, norms=None, weights=None):
        """
        Calculate the weighted Mean Absolute Percent Error (MAPE).
        
        Parameters
        ----------
        `predictions` : numpy array of floats
            Predictions being tested.
        `actuals` : numpy array of floats
            Actual values corresponding to `predictions`. Must be same size as `predictions`.
        `norms` : numpy array of floats
            Normalisation values. Must be same size as `predictions`. Default is to use `actuals`.
        `weights` : numpy array of floats
            Weighting values. Must be same size as `predictions`. Default is to use `actuals`.

        Returns
        -------
        float
            wMAPE.

        Notes
        -----
        .. math::
            \begin{gathered}
            y=Actuals,\quad f=Predictions,\quad n=Normalisations,\quad w=Weights\\
            \mathit{wMAPE}=
            \frac{\sum_i{w_i\times\mathrm{abs}\left(\frac{f_i-y_i}{n_i}\right)\times100\%}}{\sum_i{w_i}}
            \end{gathered}
        """
        norms = df["actuals"] if norms is None else norms
        weights = df["actuals"] if weights is None else weights
        mapes = np.abs((df["predictions"] - df["actuals"]) / norms) * 100.
        return (weights * mapes).sum() / weights.sum()
    
    @staticmethod
    def pearson_coefficient(df):

        """
        Calculate the Pearson correlation coefficient [1]_.
        
        Parameters
        ----------
        `predictions` : numpy array of floats
            Predictions being tested.
        `actuals`: numpy array of floats
            Actual values corresponding to `predictions`. Must be same size as `predictions`.

        Returns
        -------
        float
            Pearson correlation coefficient.

        Notes
        -----
        .. math::
            \begin{align*}
            \rho_{x,y}=\frac{\mathrm{cov}(x, y)}{\sigma_x\sigma_y}
            \end{align*}

        References
        ----------
        .. [1] https://en.wikipedia.org/wiki/Pearson_correlation_coefficient
        """

        return np.corrcoef(predictions, actuals)[0, 1]

    @staticmethod
    def r_squared(df):

        """
        Calculate the coefficient of determination (a.k.a R-Squared) [1]_.
        
        Parameters
        ----------
        `predictions` : numpy array of floats
            Predictions being tested.
        `actuals`: numpy array of floats
            Actual values corresponding to `predictions`. Must be same size as `predictions`.

        Returns
        -------
        float
            Coefficient of determination.

        Notes
        -----
        .. math::
            \begin{align*}
            y=Actuals,\quad f&=Predictions,\quad \bar{y}=\frac{1}{n}\sum_{i=1}^n{y_i}\\
            SS_{tot}&=\sum_i{(y_i-\bar{y})^2}\\
            SS_{res}&=\sum_i{(y_i-f_i)^2}\\
            R^2&=1-\frac{SS_{res}}{SS_{tot}}
            \end{align*}

        References
        ----------
        .. [1] https://en.wikipedia.org/wiki/Coefficient_of_determination
        """
        df_ = df.dropna()
        mean_actual = df_["actuals"].mean()
        diff = df_["actuals"] - df_["predictions"]
        ss_res = (diff * diff).sum()
        tot = df_["actuals"] - mean_actual
        ss_tot = (tot * tot).sum()            
        R = 1 - (ss_res / ss_tot)
        # if R < -1:
        #     import pdb; pdb.set_trace()
        return 1 - (ss_res / ss_tot)

    def download_pvlive_from_db(self, version):

        """Download the pvgeneration data from ssfdb3"""

        with DBConnector(mysql_defaults=self.config["mysql_options_readwrite_nationalgrid"], session_tz="UTC") as dbc:
            sql_template = ("SELECT UNIX_TIMESTAMP(`datetime_GMT`), `generation_MW`, `capacity_MWp`,"
                            "`site_count` from {} WHERE `version_id` = {} and `datetime_GMT` > "
                            "'{}' and `datetime_GMT` < '{}';")
            sql = sql_template.format(self.config["pvgen_table"], version,
                                      datetime.strftime(self.options.start, "%Y-%m-%d"),
                                      datetime.strftime(self.options.end, "%Y-%m-%d"))
            # import pdb; pdb.set_trace()
            data = dbc.query(sql)
        df = pd.DataFrame(data, columns=["utc timestamp", "generation MW", "capacity MWp", "site count"])
        df.index = pd.DatetimeIndex(pd.to_datetime(df["utc timestamp"], utc=True, unit="s"), tz="UTC")
        return df


if __name__ == "__main__":
    PVLiveStats()