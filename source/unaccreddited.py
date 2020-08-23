"""
A script to join deployment data for unaccredited systems with the average FIT
rate available at the time of installation.

- First Authored 2020-04-15
- Owen Huxley <othuxley1@sheffield.ac.uk>
"""

import pandas as pd

from FIT_rate import FITRate


def main():
    unaccredited_file = "../data/Unaccredited.csv"
    unaccredited_data = pd.read_csv(unaccredited_file)
    fit_rate_instance = FITRate()
    unaccredited_data["FIT Rate (p)"] = unaccredited_data["Date"] \
        .apply(FITRate().get_fit_rate).astype(float)
    unaccredited_data.to_csv("../data/Unaccredited_with_FIT_rate.csv")
    return


if __name__ == "__main__":
    main()



