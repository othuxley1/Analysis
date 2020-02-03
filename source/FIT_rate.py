"""
Code to load in the FIT payment data as an excel file and collate information
relating to photovoltaics into one place.

- First authored: 2020-01-20
- Owen Huxley <othuxley1@sheffield.ac.uk>
"""

import pandas as pd
import numpy as np
import seaborn as sns; sns.set()
import matplotlib.pyplot as plt


class FITExcelFile:
    """A class to extract information on the decline of the FIT rate."""

    def __init__(self, plot=False, verbose=False):

        """
        Parameters
        ----------
        plot: boolean
            Whether to plot graphs or not. Set to True to plot graphs.
            Default is False.
        verbose: boolean
            Whether to print to stdout or not. Set to True to print.
            Default is False.
        """

        self.FIT_excel_file = (
            "../data/2019_rpi_adjusted_tariff_table_publication.xlsx"
        )
        self.xlsx = pd.ExcelFile(self.FIT_excel_file)
        self.plot = plot
        self.verbose = verbose
        self.sheet_dfs = None
        self.data_group_capacity_date = []

    def run(self):
        """Run class methods."""
        self.load_excel_data()
        self.collate_data()

    def load_excel_data(self):
        """Load FIT excel file."""
        dfs = []
        sheets = self.xlsx.sheet_names
        for sheet in sheets[2:11]:
            pv_fit_df = self.load_excel_sheet(sheet)
            pv_fit_df["Sheet Name"] = sheet
            dfs.append(pv_fit_df)
            if self.plot:
                self.plot_heat_map(pv_fit_df, sheet)
        self.sheet_dfs = dfs
        return dfs

    def load_excel_sheet(self, sheet):

        """
        A function to load the FIT data from individual sheets in the
        FIT excel file.

        Parameters
        ----------
        sheet: str
            The sheet which is to be loaded.

        Returns
        -------
        pv: pandas.DataFrame
            A Pandas DataFrame with FIT data for solar PV systems only.
        """

        column_types = {
            "Solar PV Installation  Type" : str,
            "Maximum Capacity (kW)" : np.float32,
            "Tariff" : np.float32,
            "Technology Type" : str,
        }
        date_cols = [-1, -2]
        df = pd.read_excel(self.xlsx, sheet, dtype=column_types,
                           parse_dates=date_cols)
        pv = df.loc[df["Technology Type"] == "Photovoltaic"]
        standard = pv[pv["Solar PV Installation  Type"] == "Standard"]

        if "Energy Efficiency Requirement rating" in standard.columns:
            standard_higher = standard[
                standard["Energy Efficiency Requirement rating"] == "Higher"
                ]
        else:
            standard["Energy Efficiency Requirement rating"] = "Higher"
            standard_higher = standard.copy()

        standard_higher = standard_higher[
            ["Solar PV Installation  Type",
             "Maximum Capacity (kW)",
             "Tariff",
             "Technology Type",
             "Tariff Start Date",
             "Tariff End Date",
             "Energy Efficiency Requirement rating"]
        ]
        standard_higher = standard_higher[
            ~standard_higher["Tariff"].isnull().values
        ]
        return standard_higher

    def collate_data(self):

        """Collate all of the sheets in the FIT excel file."""

        for df in self.sheet_dfs:
            df["Tariff Start Date"] = df["Tariff Start Date"]\
                .dt.strftime("%Y-%m-%d")
            df["Tariff End Date"] = df["Tariff End Date"]\
                .dt.strftime("%Y-%m-%d")
            if df["Tariff End Date"].isnull().sum() >0:
                raise

            # group by max cap and date to ensure 
            # that there are no duplicate rows
            grouped = df.groupby([
                "Maximum Capacity (kW)",
                "Tariff End Date"]).max()
            # grouped has multiindex, we need to get data into list form
            # so that all the sheets can be consolidated
            data_max = [[i, j, *v] for (i,j), v in zip(grouped.index,
                                                       grouped.values)]
            self.data_group_capacity_date += data_max

        def list_to_df(_data, header):
            """
            Create a DataFrame for the FIT data.
            Parameters
            ----------
            _data: list
                A list to create DataFrame.
            header: list
                Column headers for the DataFrame.

            Returns
            -------
            df: pandas.DataFrame

            """
            _df = pd.DataFrame(_data, columns=header)
            _df["Tariff Start Date"] = pd.to_datetime(_df["Tariff Start Date"])
            _df["Tariff End Date"] = pd.to_datetime(_df["Tariff End Date"])
            return _df

        column_headers = ["Maximum Capacity (kW)", "Tariff End Date"] \
                         + grouped.columns.values.tolist()
        self.data_group_capacity_date = list_to_df(
            self.data_group_capacity_date,
            column_headers
        )

        if self.plot:
            self.plot_graphs()

        return

    def plot_graphs(self):

        """Plot linegraphs of the FIT rate."""

        # df = self.data_group_capacity_date
        # f = sns.FacetGrid(df, col="Solar PV Installation  Type",
        #                   hue="Maximum Capacity (kW)", height=5,
        #                   aspect=1.5, col_wrap=2)
        # f.map(plt.step, "Tariff End Date", "Tariff")
        # f.add_legend()
        # f.savefig("../graphs/grid_lineplot.png", dpi=300)
        # plt.show()

        df = self.data_group_capacity_date
        df.reset_index(inplace=True)
        g = plt.figure()
        sns.lineplot(x="Tariff End Date", y="Tariff", data=df,
                     drawstyle='steps-pre')
        g.savefig("../graphs/mean_lineplot.png", dpi=300)
        plt.show()

    def save_data(self):

        """Save data to csv file."""

        self.data_group_capacity_date.drop("index", axis=1, inplace=True)
        self.data_group_capacity_date.to_csv(
            "../data/FIT_payment_rate_standard_group_by_capacity_and_date.csv",
            index=False
        )

class FITRate:

    """A class to calculate the FIT rate on a given date."""

    def __init__(self):
        self.fit_rate_file = "../data/FIT_payment_rate_standard_group_by_capacity_and_date.csv"
        self.data = pd.read_csv(self.fit_rate_file)
        self.data["Tariff End Date"] = pd.to_datetime(
            self.data["Tariff End Date"]
        )
        self.max_fit = self.data.Tariff.max()
        self.min_fit = self.data.Tariff.min()

    def get_fit_rate(self, _date, capacity):
        if self.data[self.data["Tariff End Date"] >= _date].empty:
            return 0
        else:
            cap = self.data[self.data["Maximum Capacity (kW)"] == capacity]
            cap_date = cap[cap["Tariff End Date"] >= _date][["Tariff",
                                                             "Tariff End Date"]]
            tariff = cap_date.sort_values("Tariff End Date").iloc[0,0]
            return tariff


if __name__ == "__main__":
    fit_excel_file_instance = FITExcelFile(plot=False, verbose=False)
    fit_excel_file_instance.run()
    fit_excel_file_instance.plot_graphs()
    fit_excel_file_instance.save_data()

    self = FITRate()
