"""Shared helpers for parameters quoted from documents (plan F4).

A source is a dict with ``url`` and ``checks`` (regex patterns of the quoted numbers). Sources are
downloaded once and SHA-256 pinned; :func:`verify` confirms every quoted number is in the text,
so a mistyped value or a changed document stops the analysis.
"""

import html
import re
from pathlib import Path

from mrv_lab import io


def download(sources: dict[str, dict], folder: str) -> dict[str, Path]:
    """Download every source to ``data/raw/<folder>/`` (SHA-256 pinned)."""
    paths = {}
    for key, src in sources.items():
        suffix = ".htm" if src["url"].endswith(".htm") else ".pdf"
        dest = io.raw_dir() / folder / f"{key}{suffix}"
        paths[key] = io.download_file(src["url"], dest, timeout_s=300)
    return paths


def source_text(path: Path) -> str:
    """Plain text of a downloaded source (PDF layout + raw text, or HTML without tags)."""
    if path.suffix == ".htm":
        raw = path.read_bytes().decode("utf-8", errors="replace")
        return html.unescape(re.sub(r"<[^>]+>", " ", raw))
    return io.pdf_text(path, layout=True) + "\n" + io.pdf_text(path, layout=False)


def verify(sources: dict[str, dict], texts: dict[str, str]) -> list[str]:
    """Every quoted number must appear in its source text."""
    return [
        f"{key}: pattern not found: {pattern}"
        for key, src in sources.items()
        for pattern in src["checks"]
        if not re.search(pattern, texts[key])
    ]


def texts(sources: dict[str, dict], folder: str) -> dict[str, str]:
    """Download (if needed) and read every source."""
    return {k: source_text(p) for k, p in download(sources, folder).items()}
