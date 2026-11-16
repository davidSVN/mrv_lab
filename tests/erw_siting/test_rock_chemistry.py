"""Tests for erw_siting.rock_chemistry on small synthetic copies of the source table layouts."""

import pandas as pd
import pytest

from mrv_lab.erw_siting import rock_chemistry as rc

KERR = """\
Table 1. Representative Major and Trace Element Data for Southwest Colombian Picritesa
                                Sample
           S1      S2      S3
Locality   LT      LT      EE
SiO2     52.61   50.13   42.47
MgO       8.80   10.00   17.20
CaO      11.68   10.00    7.20
Na2O      1.52    2.00    0.60
K2O       0.12    0.20    0.20
LOI       1.24    0.00    5.43
"""

GC = """\
Table 1. Whole-rock composition of samples.

     Sample       SiO2     TiO2    MgO      CaO     Na2O    K2O    LOI**   Total    Publication
A1                39.40    0.00    42.75    0.70    0.03    0.00   7.70    98.55    This study
B2                42.86            33.65    1.03                   8.77    98.78    Other (2016)

Source: test.
"""


def test_parse_kerr_and_convert_to_quarried_rock() -> None:
    table = rc.parse_kerr2002(KERR)
    assert list(table.index) == ["S1", "S2", "S3"]
    assert table.loc["S1", "CaO"] == 11.68
    quarried = rc.as_quarried(table)
    assert quarried.loc["S1", "CaO"] == pytest.approx(11.68 * (1 - 0.0124))
    assert quarried.loc["S2", "MgO"] == 10.0  # LOI 0 -> unchanged


def test_parse_garcia_casco_keeps_blank_cells_empty() -> None:
    table = rc.parse_garcia_casco2020(GC)
    assert table.loc["A1", "MgO"] == 42.75
    assert table.loc["B2", "MgO"] == 33.65 and table.loc["B2", "CaO"] == 1.03
    assert pd.isna(table.loc["B2", "TiO2"]) and pd.isna(table.loc["B2", "Na2O"])
    assert table.loc["B2", "LOI"] == 8.77


def test_registry_values_split_basalt_from_picrite_and_proxy_gabbro() -> None:
    values = rc.registry_values({"kerr2002": KERR, "garcia_casco2020": GC})
    basalt = values["mgo_wt_pct_basalt"]  # S1, S2 (MgO <= 12); S3 is a picrite
    assert basalt["n"] == 2
    assert basalt["range"][1] == 10.0
    assert values["cao_wt_pct_gabbro"] == values["cao_wt_pct_basalt"]
    assert values["na2o_wt_pct_ultramafic"]["n"] == 1  # blank cell excluded


def test_check_registry_flags_differences() -> None:
    expected = {"x": {"value": 1.0, "range": [0.5, 2.0]}}
    good = pd.DataFrame([{"id": "x", "value": 1.0, "range": [0.5, 2.0]}])
    assert rc.check_registry(good, expected) == []
    bad = pd.DataFrame([{"id": "x", "value": 1.1, "range": [0.5, 2.0]}])
    assert rc.check_registry(bad, expected)
