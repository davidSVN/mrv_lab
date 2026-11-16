"""Tests for io.download_file: download once, pin SHA-256, detect changes. No network (file://)."""

import json
from pathlib import Path

import pytest

from mrv_lab import io


@pytest.fixture
def source(tmp_path: Path) -> Path:
    """A fake remote file served through a file:// URL."""
    path = tmp_path / "remote" / "layer.csv"
    path.parent.mkdir()
    path.write_text("cell,ph\n1,4.8\n", encoding="utf-8")
    return path


def test_first_download_records_checksum(tmp_path: Path, source: Path) -> None:
    registry = tmp_path / "data" / "checksums.json"
    dest = tmp_path / "data" / "raw" / "layer.csv"

    io.download_file(source.as_uri(), dest, registry=registry)

    assert dest.read_bytes() == source.read_bytes()
    entry = json.loads(registry.read_text(encoding="utf-8"))["raw/layer.csv"]
    assert entry["sha256"] == io.sha256_of(source)
    assert entry["url"] == source.as_uri()
    assert not dest.with_name("layer.csv.part").exists()


def test_second_call_does_not_download_again(tmp_path: Path, source: Path) -> None:
    registry = tmp_path / "data" / "checksums.json"
    dest = tmp_path / "data" / "raw" / "layer.csv"
    io.download_file(source.as_uri(), dest, registry=registry)

    source.unlink()  # Any new download attempt would now fail.
    assert io.download_file(source.as_uri(), dest, registry=registry) == dest


def test_changed_file_raises(tmp_path: Path, source: Path) -> None:
    registry = tmp_path / "data" / "checksums.json"
    dest = tmp_path / "data" / "raw" / "layer.csv"
    io.download_file(source.as_uri(), dest, registry=registry)

    dest.write_text("cell,ph\n1,9.9\n", encoding="utf-8")  # Source silently changed.
    with pytest.raises(io.ChecksumMismatchError, match="raw/layer.csv"):
        io.download_file(source.as_uri(), dest, registry=registry)


def test_pdf_destination_refuses_non_pdf_content(tmp_path: Path) -> None:
    page = tmp_path / "botcheck.html"
    page.write_text("<html>please verify you are human</html>")
    registry = tmp_path / "checksums.json"
    dest = tmp_path / "raw" / "paper.pdf"
    with pytest.raises(io.NotAPdfError):
        io.download_file(page.as_uri(), dest, registry=registry)
    assert not dest.exists() and not registry.exists()
