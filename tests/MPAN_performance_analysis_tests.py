"""
A script of test functions to go with the source code in
MPAN_performance_analysis.py.

- First Authored 2018-05-09
- Owen Huxley <othuxley1@sheffield.ac.uk
"""

import pytest
import numpy as np

from MPAN_performance_analysis import PerformanceAnalyser


class TestSP2TS:

    def test_gmt(self):
        data = np.array([["mpan", "AE", "1544576400", "0.1"], ["mpan", "AE", "1544576400", "0.1"]])
        instance = PerformanceAnalyser()
        actual = instance.sp2ts(data)[0,2].astype(int)
        # assert type(actual) == int
        assert actual == 1544576400

    def test_bst(self):
        data = np.array([["mpan", "AE", "2018-07-26", "4", "0.1"], ["mpan", "AE", "2018-07-26", "4", "0.1"]])
        instance = PerformanceAnalyser()
        actual = instance.sp2ts(data)[2].astype(int)
        # assert type(actual) == int
        assert actual == 1532566800

    def test_gmt2bst_intoCC(self):
        settle_date = "2018-03-25"
        settle_period = "2"
        instance = PerformanceAnalyser()
        actual = instance.sp2ts(settle_date, settle_period)
        assert type(actual) == int
        assert actual == 1521939600

    def test_gmt2bst_outCC(self):
        settle_date = "2018-03-26"
        settle_period = "4"
        instance = PerformanceAnalyser()
        actual = instance.sp2ts(settle_date, settle_period)
        assert type(actual) == int
        assert actual == 1522026000

    def test_bst2gmt_intoCC(self):
        settle_date = "2018-10-28"
        settle_period = "4"
        instance = PerformanceAnalyser()
        actual = instance.sp2ts(settle_date, settle_period)
        assert type(actual) == int
        assert actual == 1540688400

    def test_bst2gmt_outCC(self):
        settle_date = "2018-10-29"
        settle_period = "2"
        instance = PerformanceAnalyser()
        actual = instance.sp2ts(settle_date, settle_period)
        assert type(actual) == int
        assert actual == 1540774800

if __name__ == "__main__":
    main()
