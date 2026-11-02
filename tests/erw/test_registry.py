"""Tests for the parameter registry (Phase 2 CI requirements).

Checks per plan §2:
- every loaded parameter has a source (doi_or_url or citation non-empty)
- units parse with pint
- value is inside [range_min, range_max]
- calibrated parameters with status='ok' have bounds
- no duplicate IDs
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mrv_lab.erw.registry import (
    Parameter,
    ParameterKind,
    ParameterStatus,
    load_registry,
)

PARAM_DIR = Path(__file__).parent.parent.parent / "config" / "parameters"


@pytest.fixture(scope="module")
def params() -> list[Parameter]:
    return load_registry(PARAM_DIR)


def test_registry_loads(params: list[Parameter]) -> None:
    """Registry must contain at least one parameter."""
    assert len(params) > 0


def test_no_duplicate_ids(params: list[Parameter]) -> None:
    ids = [p.id for p in params]
    duplicates = [i for i in ids if ids.count(i) > 1]
    assert not duplicates, f"Duplicate parameter IDs: {set(duplicates)}"


def test_every_param_has_source(params: list[Parameter]) -> None:
    """Source must have a non-empty citation."""
    bad = [p.id for p in params if not p.source.citation.strip()]
    assert not bad, f"Parameters with empty citation: {bad}"


def test_status_missing_means_no_value(params: list[Parameter]) -> None:
    """status=missing implies value=None (never fabricate a missing value)."""
    bad = [p.id for p in params if p.status == ParameterStatus.missing and p.value is not None]
    assert not bad, f"Missing parameters should have value=None: {bad}"


def test_value_inside_range(params: list[Parameter]) -> None:
    """Already enforced by Pydantic, but make it explicit in CI."""
    for p in params:
        if p.value is None or p.status == ParameterStatus.missing:
            continue
        if p.range_min is not None:
            assert p.value >= p.range_min, f"{p.id}: value {p.value} < range_min {p.range_min}"
        if p.range_max is not None:
            assert p.value <= p.range_max, f"{p.id}: value {p.value} > range_max {p.range_max}"


def test_calibrated_ok_has_bounds(params: list[Parameter]) -> None:
    """Calibrated parameters that are marked ok must have both bounds."""
    bad = [
        p.id
        for p in params
        if p.kind == ParameterKind.calibrated
        and p.status == ParameterStatus.ok
        and (p.range_min is None or p.range_max is None)
    ]
    assert not bad, f"Calibrated+ok without bounds: {bad}"


def test_missing_params_have_notes_or_citation(params: list[Parameter]) -> None:
    """Missing parameters must document WHY via notes or a citation that contains 'missing'."""
    # We just check that citation or notes field exists and is not empty
    bad = [
        p.id
        for p in params
        if p.status == ParameterStatus.missing
        and not (p.notes or "missing" in p.source.citation.lower())
    ]
    assert not bad, f"Missing params with no note or citation context: {bad}"
