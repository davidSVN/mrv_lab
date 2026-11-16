"""Tests for erw_siting.registry (the real config and synthetic cases)."""

from pathlib import Path

import pytest
import yaml

from mrv_lab.erw_siting import registry as reg


def test_real_registry_is_valid() -> None:
    table = reg.load()
    assert len(table) > 0
    assert reg.validate(table) == []


def _write(tmp_path: Path, params: list[dict]) -> Path:
    (tmp_path / "g.yaml").write_text(yaml.safe_dump({"group": "g", "parameters": params}))
    return tmp_path


def _ok(**overrides) -> dict:  # noqa: ANN003
    base = {
        "id": "x",
        "name": "x",
        "value": 2.0,
        "unit": "t/ha",
        "distribution": None,
        "range": [1.0, 3.0],
        "quality": "literature",
        "status": "ok",
        "source": {"citation": "Author 2020", "doi_or_url": "doi:10/x", "locator": "Table 1"},
    }
    return {**base, **overrides}


def test_ok_parameter_needs_source_and_value_in_range(tmp_path: Path) -> None:
    good = reg.load(_write(tmp_path, [_ok()]))
    assert reg.validate(good) == []
    bad = reg.load(_write(tmp_path, [_ok(value=5.0, source={"citation": "A"})]))
    problems = " ".join(reg.validate(bad))
    assert "outside range" in problems and "source" in problems


def test_missing_parameter_cannot_carry_a_value(tmp_path: Path) -> None:
    table = reg.load(_write(tmp_path, [_ok(status="missing", source=None)]))
    assert any("must not carry a value" in p for p in reg.validate(table))


def test_value_refuses_missing(tmp_path: Path) -> None:
    table = reg.load(_write(tmp_path, [_ok(id="a"), _ok(id="b", status="missing", value=None)]))
    assert reg.value(table, "a") == 2.0
    with pytest.raises(ValueError, match="missing"):
        reg.value(table, "b")
