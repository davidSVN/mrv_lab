"""Tests for the viewer manifest schema (P6.0).

Validates:
- manifest.schema.json is valid JSON Schema
- manifest.example.json validates against the schema
- every variable with status='available' has a non-null file path
- no duplicate variable IDs
- pending/missing variables have null file
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

SCHEMA_FILE = Path(__file__).parent.parent.parent / "viz" / "schema" / "manifest.schema.json"
EXAMPLE_FILE = Path(__file__).parent.parent.parent / "viz" / "schema" / "manifest.example.json"


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads(SCHEMA_FILE.read_text())


@pytest.fixture(scope="module")
def example() -> dict:
    return json.loads(EXAMPLE_FILE.read_text())


def test_schema_file_exists() -> None:
    assert SCHEMA_FILE.exists(), "manifest.schema.json not found"


def test_example_file_exists() -> None:
    assert EXAMPLE_FILE.exists(), "manifest.example.json not found"


def test_example_validates_against_schema(schema: dict, example: dict) -> None:
    """Example manifest must be valid per the schema."""
    validator = jsonschema.Draft202012Validator(schema)
    errors = list(validator.iter_errors(example))
    messages = [f"{'.'.join(str(p) for p in e.absolute_path)}: {e.message}" for e in errors]
    assert not errors, "manifest.example.json has validation errors:\n" + "\n".join(messages)


def test_no_duplicate_variable_ids(example: dict) -> None:
    ids = [v["id"] for v in example["variables"]]
    duplicates = [i for i in ids if ids.count(i) > 1]
    assert not duplicates, f"Duplicate variable IDs in manifest: {set(duplicates)}"


def test_available_variables_have_file(example: dict) -> None:
    bad = [
        v["id"] for v in example["variables"] if v["status"] == "available" and not v.get("file")
    ]
    assert not bad, f"Available variables must have a non-null file path: {bad}"


def test_pending_and_missing_have_null_file(example: dict) -> None:
    bad = [
        v["id"]
        for v in example["variables"]
        if v["status"] in ("pending", "missing") and v.get("file") is not None
    ]
    assert not bad, f"Pending/missing variables must have file=null: {bad}"


def test_grid_has_required_fields(example: dict) -> None:
    grid = example["grid"]
    for field in ("crs", "bbox", "cell_size_m", "nx", "ny", "depth_layers_m"):
        assert field in grid, f"Grid missing required field: {field}"


def test_version_semver(example: dict) -> None:
    import re

    assert re.match(r"^\d+\.\d+\.\d+$", example["version"]), (
        f"Version must be semver: {example['version']}"
    )
