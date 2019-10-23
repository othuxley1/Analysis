import os
import configparser

config = configparser.ConfigParser()
"""
store_name : str
    Name of HDF5 store used to store the midas data locally.
store_path : str
    Path of the HDF5 store.
meta_hdf_key : str
    Key of the object within HDF5 store containing metadata.
obs_hdf_key : str
    Name of the object within HDF5 store containing weather observation data.
default_earliest_date : date
    If no dates are specified for loading, this is the default start date to fall back onto.  The default end date is the date today.
query_settings > file_path : str
    Default path of files to be read into loads.
"""
config["mysql_defaults"] = {}
config["mysql_defaults"]["monte_carlo_sample_size_analysis"] = "C:/Users/owenh/Documents/GitRepos/capacity_mismatch_paper/data/mysql_defaults/mysql_defaults.ssfdb2.readwrite.monte_carlo_sample_size_analysis"

config["other"] = {}
config["other"]["error_logfile"] = "monte_carlo_site_list_errors.txt"

config["mysql_tables"] = {}
config["mysql_tables"]["original_site_list"] = ""
config["mysql_tables"]["results"] = "site_list_monte_carlo"

config["data_files"] = {}
config["data_files"]["sl"] = "../data/site_list.csv"
config["data_files"]["err_tbl"] = "../data/error_table.csv"


with open(os.path.join(os.path.dirname(os.path.realpath(__file__)),'Config/site_list.ini'), 'w') as configfile:
    config.write(configfile)