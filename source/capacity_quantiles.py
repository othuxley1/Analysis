"""
A script to select boxplot quantile data from the capacity
 results and re-run the site list variation code to regenerate each
 site list permutation.

 - First authored: 2020-04-30
 - Owen Huxley <othuxley1@sheffield.ac.uk>
"""

import pandas as pd
from site_list_variation import SiteListVariation
from dbconnector import DBConnector
from generic_tools import cached


class CapacitySitelistUploader:

    def __init__(self):
        ### Config ###
        self.capacity_file = "C:/Users/owenh/Documents/GitRepos/capacity_mismatch_paper/data/MC_results_v2_T0only_no_unreported_20200430_1000N.csv"
        self.mysql__file = "C:/Users/owenh/Documents/GitRepos/capacity_mismatch_paper/" \
                      "data/mysql_defaults/" \
                      "mysql_defaults.ssfdb2.readwrite.capacity_analysis"
        self.db_tables = {
            "0.01" : "solarsite_20190205_t0only_no_unreported_0.01pc",
            "0.25" : "solarsite_20190205_t0only_no_unreported_0.25pc",
            "0.5" : "solarsite_20190205_t0only_no_unreported_0.5pc",
            "0.75" : "solarsite_20190205_t0only_no_unreported_0.75pc",
            "0.99" : "solarsite_20190205_t0only_no_unreported_0.99pc"
        }
        ##############
    
    def run(self):

        data = pd.read_csv(self.capacity_file)
        data.rename({" national_capacity (MW)": "national_capacity_MW"}, inplace=True, axis=1)

        site_lists = self.get_site_lists(data)
        return

    def get_quantile_seeds(self, data):
        """
        Calculate quantiles for capacity data and return corresponcing seed
        values.
        Parameter
        ----------
        `data` : pd.DataFrame
            The capacity data.
        Returns
        -------
            list
            A list of dataframes containing the quantiles: .01, .25, .5, .75, .99
        """
        def idxquantile(s, q=0.5, *args, **kwargs):
            qv = s.quantile(q, *args, **kwargs)
            return (s.sort_values(by="national_capacity_MW")[::-1] <= qv).idxmax()

        q50 = data.loc[idxquantile(data[["national_capacity_MW"]], q=.5)]
        q75 = data.loc[idxquantile(data[["national_capacity_MW"]], q=.75)]
        q25 = data.loc[idxquantile(data[["national_capacity_MW"]], q=.25)]
        q99 = data.loc[idxquantile(data[["national_capacity_MW"]], q=.99)]
        q01 = data.loc[idxquantile(data[["national_capacity_MW"]], q=.01)]
        quantiles_dict = {
            "0.01" : q01,
            "0.25" : q25,
            "0.5" : q50,
            "0.75" : q75,
            "0.01" : q99,
        }
        return quantiles_dict

    def get_site_lists(self, data):
        site_lists = {}
        seed_data = self.get_quantile_seeds(data)
        # import pdb; pdb.set_trace()
        for i, quantile in enumerate(seed_data):
            seed_df = seed_data[quantile]
            # import pdb; pdb.set_trace()
            instance = SiteListVariation(1, verbose=True, seed=int(seed_df.values[0][0]), test=False)
            # instance.unreported_systems()
            instance.simulate_effective_capacity_site_list()
            nc = instance.SL.Capacity.sum()
            if not int(nc) == int(seed_df.values[0][1]):
                print("50th percentile is: {}, capacity from results is: {}"
                      .format(nc, seed_df.values[0][1]))
                raise ValueError("National capacity of site list does not national"
                                 "capacity from results.")
            # hanndle missing location data
            # import pdb; pdb.set_trace()
            
            ################################
            instance.SL.reset_index(inplace=True)
            instance.SL.rename({"install_date": "installdate",
                                "Capacity" : "installedcapacity"},
                               inplace=True, axis=1)
            instance.SL["latitude_rounded"] = instance.SL["latitude"].round(decimals=1)
            instance.SL["longitude_rounded"] = instance.SL["longitude"].round(decimals=1)
            instance.SL["gen_id"] = instance.SL.index + 1
            db_SL = instance.SL[["gen_id", "latitude", "longitude",
                                 "latitude_rounded", "longitude_rounded",
                                 "installdate", "installedcapacity"]].copy()
            unlocated = db_SL[db_SL.isnull().any(axis=1)][["latitude", "longitude"]]
            located = db_SL[~db_SL.isnull().any(axis=1)][["latitude", "longitude"]]
            db_SL.loc[db_SL.isnull().any(axis=1), ["latitude", "longitude"]] = located.sample(unlocated.shape[0]).values
            db_SL["latitude_rounded"] = db_SL["latitude"].round(decimals=1)
            db_SL["longitude_rounded"] = db_SL["longitude"].round(decimals=1)
            
            site_lists[quantile] = db_SL
            self.upload_to_db(db_SL.values.tolist(), self.db_tables[quantile], self.mysql__file)
            self.test_count_in_DB(self.db_tables[quantile], self.mysql__file, db_SL)
        return db_SL


    def upload_to_db(self, data, table, mysql_options_file):
        # data = [row if  for row in data]
        # import pdb; pdb.set_trace()
        print("\nUploading to database...\n")
        if type(data) is not list:
            raise ValueError("Data to upload must be list of lists...")
        sql = f"INSERT INTO `{table}` (`gen_id`, `latitude`, `longitude`, " \
              f"`latitude_rounded`, `longitude_rounded`, `installdate`, " \
              f"`installedcapacity`) VALUES (%s,%s,%s,%s,%s,%s,%s)" \
              f"ON DUPLICATE KEY UPDATE " \
              f"`latitude` = VALUES(`longitude`)," \
              f"longitude = VALUES(`longitude`)," \
              f"`installedcapacity` = VALUES(`installedcapacity`);"
        with DBConnector(mysql_options_file, session_tz="UTC") as dbc:
            dbc.iud_query(sql, data)
        print("\t--> done.")

    def test_count_in_DB(self, table, mysql_options_file, data):
        SL_count = len(data)
        sql = f"SELECT count(*) FROM `{table}`;"
        with DBConnector(mysql_options_file, session_tz="UTC") as dbc:
            DB_count = dbc.query(sql)
        if int(DB_count[0][0]) != int(SL_count):
            import pdb; pdb.set_trace()
            raise Exception("Wrong number of rows inserted into DB...")


    @staticmethod
    def system_in_gb(vec):
        in_gb = vec[0]
        latitude = vec[1]
        longitude = vec[2]

        test1 = (float(49.87) < float(latitude) < float(59.59)) and \
                (float(-8.15) < float(longitude) < float(1.94))

        test2 = (float(51.35) < float(latitude) < float(55.40)) and \
                (float(-8.15) < float(longitude) < float(4.50))

        test3 = (float(49.87) < float(latitude) < float(51.09)) and \
                (float(1.47) < float(longitude) < float(1.94))

        if not int((test1 and not test2 and not test3)) == int(in_gb):
            import pdb; pdb.set_trace()
        return int(test1 and not test2 and not test3)

    @staticmethod
    def test_system_in_gb():
        file = "C:/Users/owenh/Documents/GitRepos/capacity_mismatch_paper/data/solarsite20190205.csv"
        data = pd.read_csv(file)
        data["in_gb2"] = data[["in_gb", "latitude", "longitude"]].apply(system_in_gb, axis=1)
        data.to_csv("../data/solarsite20190205_edited.csv")
        return


if __name__ == "__main__":
    # test_system_in_gb()
    instance = CapacitySitelistUploader()
    instance.run()
