"""Tests for erw_siting.report (results entries, README block, curve; no network)."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from mrv_lab.erw_siting import registry
from mrv_lab.erw_siting import report as rp


def _table() -> pd.DataFrame:
    rows = []
    for scenario, net in (
        ("base", 0.02),
        ("grain_coarse", -0.01),
        ("grain_fine", 0.1),
        ("s1_x", 0.05),
    ):
        for i, dept in enumerate(["Meta", "Meta", "Tolima"]):
            rows.append(
                {
                    "cell_id": f"c{i}",
                    "scenario_id": scenario,
                    "department": dept,
                    "candidate": 1,
                    "area_in_department_km2": 1.0,
                    "lime_demand": 1,
                    "road_km": 100.0 + i,
                    "breakeven_km": 200.0,
                    "p_net_positive": 0.95 if dept == "Tolima" else 0.5,
                    "net_ha_p50_tco2_per_ha_yr": 0.01,
                    "net_tco2_per_t": net - 0.03 * i,
                }
            )
    return pd.DataFrame(rows)


def test_results_entries_follow_the_schema() -> None:
    entries = rp.results_entries(_table(), as_of="2026-11-21")
    keys = {e["key"] for e in entries}
    assert {"candidate_area_km2_meta", "share_cells_net_positive_medium_tolima"} <= keys
    assert "share_cells_net_positive_s1_x_meta" in keys
    for e in entries:
        assert set(e) == {"key", "value", "unit", "description", "as_of"}
        assert isinstance(e["value"], float) and e["as_of"] == "2026-11-21"
    by_key = {e["key"]: e["value"] for e in entries}
    assert by_key["candidate_area_km2_meta"] == 2.0
    assert by_key["share_cells_p_net_positive_ge_90_medium_tolima"] == 1.0


def test_readme_block_is_replaced_not_duplicated(tmp_path: Path) -> None:
    readme = tmp_path / "README.md"
    readme.write_text("## Result\n\n## Limitations\n")
    entries = rp.results_entries(_table(), as_of="2026-11-21")
    rp.update_readme(readme, rp.readme_results_block(entries))
    rp.update_readme(readme, rp.readme_results_block(entries))
    text = readme.read_text()
    assert text.count(rp.README_START) == 1 and "Candidate farmland" in text
    assert text.index("## Result") < text.index(rp.README_START) < text.index("## Limitations")


def test_breakeven_curve_falls_with_distance() -> None:
    table = registry.load()
    values = {r["id"]: float(r["value"]) for r in table[table["status"] == "ok"].to_dict("records")}
    km = np.array([0.0, 100.0, 500.0])
    curve = rp.breakeven_curve(values, 25.0, 5.0, km)
    assert curve["medium"][0] > curve["medium"][1] > curve["medium"][2]
    assert curve["fine"][0] > curve["medium"][0] > curve["coarse"][0]
    assert curve["coarse"][0] == pytest.approx(curve["coarse"][0])
