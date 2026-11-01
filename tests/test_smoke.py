"""Smoke tests: the package imports and the plotting pipeline produces valid figures."""

import json
from datetime import date

import matplotlib.image as mpimg
import pytest

import mrv_lab
from mrv_lab import io, lca, plotting, sampling, uncertainty


def test_package_imports() -> None:
    assert mrv_lab.__version__
    for module in (io, plotting, uncertainty, sampling, lca):
        assert module.__doc__


def test_repo_root_and_data_dirs() -> None:
    root = io.repo_root()
    assert (root / "pyproject.toml").is_file()
    assert io.raw_dir() == root / "data" / "raw"
    assert io.processed_dir() == root / "data" / "processed"
    assert io.figures_dir("00_template") == root / "analyses" / "00_template" / "figures"


def test_template_results_is_empty_list() -> None:
    results_path = io.analysis_dir("00_template") / "results.json"
    assert json.loads(results_path.read_text(encoding="utf-8")) == []


def test_palette_is_okabe_ito() -> None:
    assert len(plotting.OKABE_ITO) == 8
    assert plotting.HIGHLIGHT in plotting.OKABE_ITO.values()
    assert set(plotting.CYCLE) <= set(plotting.OKABE_ITO.values())


def test_highlight_colors() -> None:
    colors = plotting.highlight_colors(["a", "b", "c"], highlight="b")
    assert colors == [plotting.GREY, plotting.HIGHLIGHT, plotting.GREY]
    with pytest.raises(ValueError):
        plotting.highlight_colors(["a", "b"], highlight="z")


def test_footer_text() -> None:
    expected = "Source: CDR.fyi (accessed 2026-11-01) · Analysis: github.com/davidSVN/mrv_lab"
    assert plotting.footer_text("CDR.fyi", "2026-11-01") == expected
    assert plotting.footer_text("CDR.fyi", date(2026, 11, 1)) == expected
    with pytest.raises(ValueError):
        plotting.footer_text("CDR.fyi", "01/11/2026")
    with pytest.raises(ValueError):
        plotting.footer_text("  ", "2026-11-01")


def test_export_figure_png_size_and_svg(tmp_path) -> None:
    fig, ax = plotting.new_figure()
    labels = ["A", "B", "C"]
    ax.bar(labels, [3.0, 2.0, 1.0], color=plotting.highlight_colors(labels, highlight="A"))
    ax.set_ylabel("Contracted (tCO2e)")
    plotting.add_title(fig, "A test finding that is long enough to wrap", "Test, tCO2e, 2026")
    plotting.add_footer(fig, source="Synthetic test data", accessed="2026-11-01")

    png_path, svg_path = plotting.export_figure(fig, "smoke", tmp_path)

    height_px, width_px = mpimg.imread(png_path).shape[:2]
    assert (width_px, height_px) == (plotting.FIG_WIDTH_PX, plotting.FIG_HEIGHT_PX)
    svg = svg_path.read_text(encoding="utf-8")
    assert svg.lstrip().startswith("<?xml")
    assert "Source: Synthetic test data (accessed 2026-11-01)" in svg
