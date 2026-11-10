"""Paths relative to the repository root.

No absolute paths are hardcoded anywhere in the repo (CLAUDE.md §9): every
location is derived from :func:`repo_root`.

Downloads go through :func:`download_file`, which pins each raw file's SHA-256 in the
committed registry ``data/checksums.json`` so a silent change at the source is detected.
"""

import hashlib
import json
import shutil
import urllib.request
from datetime import date
from pathlib import Path

_CHUNK_BYTES = 1024 * 1024


class ChecksumMismatchError(ValueError):
    """A file's SHA-256 differs from the one recorded in the checksum registry."""


def repo_root() -> Path:
    """Return the repository root (the directory holding ``pyproject.toml`` and ``src/mrv_lab``).

    Raises:
        FileNotFoundError: if the package is not running from a checkout of the repo.
    """
    for parent in Path(__file__).resolve().parents:
        if (parent / "pyproject.toml").is_file() and (parent / "src" / "mrv_lab").is_dir():
            return parent
    raise FileNotFoundError("Could not locate the mrv-lab repository root.")


def data_dir() -> Path:
    """Return ``data/``."""
    return repo_root() / "data"


def raw_dir() -> Path:
    """Return ``data/raw/`` (gitignored by default)."""
    return data_dir() / "raw"


def processed_dir() -> Path:
    """Return ``data/processed/`` (committed only if the source license allows it)."""
    return data_dir() / "processed"


def analyses_dir() -> Path:
    """Return ``analyses/``."""
    return repo_root() / "analyses"


def analysis_dir(slug: str) -> Path:
    """Return ``analyses/<slug>/``, e.g. ``analysis_dir("01_cdr_buyers")``."""
    return analyses_dir() / slug


def figures_dir(slug: str) -> Path:
    """Return ``analyses/<slug>/figures/``."""
    return analysis_dir(slug) / "figures"


def checksums_path() -> Path:
    """Return ``data/checksums.json``: committed SHA-256 registry of every downloaded raw file."""
    return data_dir() / "checksums.json"


def sha256_of(path: Path) -> str:
    """Return the SHA-256 hex digest of the file at ``path``, read in 1 MiB chunks."""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(_CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def download_file(
    url: str,
    dest: Path,
    registry: Path | None = None,
    timeout_s: float = 120.0,
) -> Path:
    """Download ``url`` to ``dest`` once and pin its SHA-256 in a checksum registry.

    Behaviour:
        1. If ``dest`` does not exist, download it (to ``<dest>.part``, then rename, so an
           interrupted download never leaves a half file at ``dest``).
        2. Compute the file's SHA-256.
        3. First time this file is seen: record ``sha256``, ``url`` and ``first_recorded``
           in the registry. Later times: the hash must match the recorded one.

    Args:
        url: Source URL (``https://`` or ``file://``).
        dest: Local destination, normally under ``data/raw/``.
        registry: JSON registry path. Defaults to :func:`checksums_path`. Entries are keyed by
            ``dest`` relative to the registry's folder (e.g. ``raw/soilgrids/ph.tif``).
        timeout_s: Network timeout in seconds.

    Returns:
        ``dest``.

    Raises:
        ChecksumMismatchError: the file differs from the recorded version, i.e. the source
            changed or the local copy is corrupt. Nothing is overwritten: inspect, then delete
            the file and its registry entry to accept a new version deliberately.
    """
    registry = registry or checksums_path()
    dest.parent.mkdir(parents=True, exist_ok=True)

    if not dest.exists():
        part = dest.with_name(dest.name + ".part")
        with urllib.request.urlopen(url, timeout=timeout_s) as response, part.open("wb") as fh:
            shutil.copyfileobj(response, fh, _CHUNK_BYTES)
        part.replace(dest)

    actual = sha256_of(dest)
    entries: dict[str, dict[str, str]] = (
        json.loads(registry.read_text(encoding="utf-8")) if registry.exists() else {}
    )
    try:
        key = dest.resolve().relative_to(registry.resolve().parent).as_posix()
    except ValueError:
        key = dest.name

    recorded = entries.get(key)
    if recorded is None:
        entries[key] = {"sha256": actual, "url": url, "first_recorded": date.today().isoformat()}
        registry.parent.mkdir(parents=True, exist_ok=True)
        registry.write_text(json.dumps(entries, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    elif recorded["sha256"] != actual:
        raise ChecksumMismatchError(
            f"{key}: SHA-256 {actual} does not match recorded {recorded['sha256']} "
            f"(first recorded {recorded.get('first_recorded', '?')} "
            f"from {recorded.get('url', '?')})."
        )
    return dest
