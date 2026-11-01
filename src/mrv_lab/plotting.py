"""Single figure style for every mrv-lab chart (CLAUDE.md §8).

Typical use::

    fig, ax = plotting.new_figure()
    ax.bar(labels, values, color=plotting.highlight_colors(labels, highlight="Top 4"))
    plotting.add_title(fig, "4 buyers hold X% of contracted tonnes", "Share of tCO2e, 2020-2025")
    plotting.add_footer(fig, source="CDR.fyi", accessed="2026-11-01")
    plotting.export_figure(fig, "buyer_concentration", io.figures_dir("01_cdr_buyers"))

Rules enforced here: title = the finding, subtitle = what/unit/period, footer
with source and access date, colorblind-safe palette with one highlighted
series and the rest grey, export to PNG 1080x1350 px (LinkedIn 4:5) + SVG.
"""

import textwrap
from collections.abc import Sequence
from datetime import date
from pathlib import Path

import matplotlib as mpl
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.text import Text

REPO_URL = "github.com/davidSVN/mrv_lab"

# Okabe & Ito (2008), "Color Universal Design": distinguishable under the
# common forms of color vision deficiency.
OKABE_ITO: dict[str, str] = {
    "black": "#000000",
    "orange": "#E69F00",
    "sky_blue": "#56B4E9",
    "bluish_green": "#009E73",
    "yellow": "#F0E442",
    "blue": "#0072B2",
    "vermillion": "#D55E00",
    "reddish_purple": "#CC79A7",
}

HIGHLIGHT = OKABE_ITO["blue"]
ACCENT = OKABE_ITO["vermillion"]
GREY = "#B8B8B8"
TEXT_COLOR = "#1A1A1A"
MUTED_TEXT_COLOR = "#5F5F5F"

# Order used when several series need their own color (yellow last: low contrast on white).
CYCLE: list[str] = [
    OKABE_ITO[name]
    for name in ("blue", "vermillion", "bluish_green", "orange", "reddish_purple", "sky_blue")
]

FIG_WIDTH_PX = 1080
FIG_HEIGHT_PX = 1350
EXPORT_DPI = 150  # 1080 / 150 = 7.2 in, 1350 / 150 = 9.0 in: exact pixel sizes.

# Left margin shared by title, subtitle and footer (figure fraction).
_MARGIN_X = 0.06

STYLE: dict[str, object] = {
    "figure.figsize": (FIG_WIDTH_PX / EXPORT_DPI, FIG_HEIGHT_PX / EXPORT_DPI),
    "figure.dpi": EXPORT_DPI,
    "savefig.dpi": EXPORT_DPI,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "font.family": "sans-serif",
    "font.sans-serif": ["Inter", "Helvetica", "Arial", "DejaVu Sans"],
    "font.size": 12,
    "text.color": TEXT_COLOR,
    "axes.labelcolor": TEXT_COLOR,
    "axes.labelsize": 12,
    "axes.edgecolor": MUTED_TEXT_COLOR,
    "axes.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "axes.grid.axis": "y",
    "axes.axisbelow": True,
    "axes.prop_cycle": mpl.cycler(color=CYCLE),
    "grid.color": "#E3E3E3",
    "grid.linewidth": 0.8,
    "xtick.color": MUTED_TEXT_COLOR,
    "ytick.color": MUTED_TEXT_COLOR,
    "xtick.labelsize": 11,
    "ytick.labelsize": 11,
    "legend.frameon": False,
    "legend.fontsize": 11,
    "lines.linewidth": 2.2,
    "svg.fonttype": "none",  # keep text as text in SVG (editable, searchable)
}


def apply_style() -> None:
    """Apply the mrv-lab style to matplotlib's global rcParams."""
    mpl.rcParams.update(STYLE)


def new_figure() -> tuple[Figure, Axes]:
    """Create a 1080x1350 px figure with one axes, leaving room for title, subtitle and footer.

    Uses :class:`matplotlib.figure.Figure` directly (no pyplot), so it works on
    headless machines and never opens a window.
    """
    apply_style()
    fig = Figure(figsize=STYLE["figure.figsize"], dpi=EXPORT_DPI)
    fig.subplots_adjust(left=0.13, right=0.95, top=0.80, bottom=0.12)
    ax = fig.add_subplot()
    return fig, ax


def highlight_colors(labels: Sequence[str], highlight: str | Sequence[str]) -> list[str]:
    """Return one color per label: :data:`HIGHLIGHT` if highlighted, :data:`GREY` otherwise."""
    highlighted = {highlight} if isinstance(highlight, str) else set(highlight)
    missing = highlighted.difference(labels)
    if missing:
        raise ValueError(f"Highlighted label(s) not in labels: {sorted(missing)}")
    return [HIGHLIGHT if label in highlighted else GREY for label in labels]


def add_title(fig: Figure, finding: str, subtitle: str, *, wrap_chars: int = 42) -> None:
    """Add a left-aligned title (the finding) and subtitle (what is measured, unit, period).

    Args:
        finding: the takeaway, e.g. "4 buyers hold X% of contracted tonnes".
        subtitle: measure, unit and period, e.g. "Share of contracted tCO2e, 2020-2025".
        wrap_chars: maximum characters per title line before wrapping.
    """
    if not finding.strip() or not subtitle.strip():
        raise ValueError("Both the finding (title) and the subtitle are required.")
    title_lines = textwrap.wrap(finding, wrap_chars)
    fig.text(
        _MARGIN_X,
        0.965,
        "\n".join(title_lines),
        ha="left",
        va="top",
        fontsize=22,
        fontweight="bold",
        linespacing=1.15,
    )
    subtitle_y = 0.965 - 0.034 * len(title_lines) - 0.012
    fig.text(
        _MARGIN_X,
        subtitle_y,
        "\n".join(textwrap.wrap(subtitle, int(wrap_chars * 1.6))),
        ha="left",
        va="top",
        fontsize=14,
        color=MUTED_TEXT_COLOR,
    )


def footer_text(source: str, accessed: str | date) -> str:
    """Build the footer string: ``Source: <source> (accessed YYYY-MM-DD) · Analysis: <repo>``.

    Raises:
        ValueError: if ``source`` is empty or ``accessed`` is not an ISO date.
    """
    if not source.strip():
        raise ValueError("A source is required in every figure footer.")
    accessed_date = accessed if isinstance(accessed, date) else date.fromisoformat(accessed)
    return f"Source: {source} (accessed {accessed_date.isoformat()}) · Analysis: {REPO_URL}"


def add_footer(fig: Figure, source: str, accessed: str | date) -> Text:
    """Add the source footer at the bottom-left of the figure. See :func:`footer_text`."""
    return fig.text(
        _MARGIN_X,
        0.025,
        footer_text(source, accessed),
        ha="left",
        va="bottom",
        fontsize=10,
        color=MUTED_TEXT_COLOR,
    )


def export_figure(fig: Figure, name: str, out_dir: Path) -> tuple[Path, Path]:
    """Save ``<out_dir>/<name>.png`` (exactly 1080x1350 px) and ``<out_dir>/<name>.svg``.

    The figure size is reset before saving and ``bbox_inches`` is not used, so
    the PNG always has the LinkedIn 4:5 pixel size.

    Returns:
        Paths of the PNG and the SVG.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    fig.set_size_inches(FIG_WIDTH_PX / EXPORT_DPI, FIG_HEIGHT_PX / EXPORT_DPI)
    png_path = out_dir / f"{name}.png"
    svg_path = out_dir / f"{name}.svg"
    fig.savefig(png_path, dpi=EXPORT_DPI, facecolor="white")
    # No date in SVG metadata: re-running an analysis yields identical files.
    fig.savefig(svg_path, facecolor="white", metadata={"Date": None})
    return png_path, svg_path
