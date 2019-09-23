import configparser
import datetime
import os
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
config["mysql_files"] = {}
config["mysql_files"]["mysql_options_ssfdb2_readwrite_capacity_analysis"] = "C:/Users/owenh/Documents/GitRepos/Analysis/data/mysql_defaults/mysql_defaults.ssfdb2.readwrite.capacity_analysis"

config["other"] = {}
config["other"]["error_logfile"] = "PV_site_list_derivation_errors.txt"

config["mysql_tables"] = {}
config["mysql_tables"]["solarsite_table"] = "solarsite_20181130"


with open(os.path.join(os.path.dirname(os.path.realpath(__file__)),'Config/PV_site_list_derivation.ini'), 'w') as configfile:
    config.write(configfile)