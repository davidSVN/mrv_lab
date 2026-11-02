"""Parameter registry for the virtual ERW field.

Schema definition (Pydantic v2) for every fixed and calibrated parameter.
Rules (plan §2):
- Every parameter MUST have a source (doi_or_url or citation).
- Unknown values get status='missing' and appear in the missing-params report.
- Value must be inside [range_min, range_max] when both are set.
- Calibrated parameters must have pre-defined bounds.
- Units are validated with pint.

Usage::

    from mrv_lab.erw.registry import Parameter, load_registry, missing_params

    params = load_registry()
    for p in missing_params(params):
        print(p.id, p.group)
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any

import pint
import yaml
from pydantic import BaseModel, field_validator, model_validator
from pydantic import Field as PydanticField

ureg = pint.UnitRegistry()
# Soil-chemistry units not in pint's default registry
# cmolc = centimol of charge = mmol (1:1 for monovalent, n:1 for n-valent)
# We register it as an alias to make unit validation work.
ureg.define("cmolc = 0.01 * mol")  # centimol of charge, alias for exchange capacity

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class ParameterKind(StrEnum):
    fixed = "fixed"
    calibrated = "calibrated"


class ParameterStatus(StrEnum):
    ok = "ok"
    missing = "missing"


class SourceType(StrEnum):
    dataset = "dataset"
    paper = "paper"
    default = "default"


class SourceQuality(StrEnum):
    primary = "primary"
    secondary = "secondary"
    literature = "literature"


class DistributionType(StrEnum):
    normal = "normal"
    lognormal = "lognormal"
    uniform = "uniform"
    loguniform = "loguniform"
    triangular = "triangular"
    fixed = "fixed"


class ParameterGroup(StrEnum):
    soil = "soil"
    hydraulics = "hydraulics"
    minerals = "minerals"
    exchange = "exchange"
    soil_co2 = "soil_co2"
    crop = "crop"
    fertilizer = "fertilizer"
    feedstock = "feedstock"
    lca = "lca"


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class Distribution(BaseModel):
    """Probability distribution for Monte Carlo sampling."""

    type: DistributionType
    params: dict[str, float]
    """Distribution parameters, e.g. {'mean': 6.2, 'std': 0.4} for normal."""


class Source(BaseModel):
    """Provenance of a parameter value."""

    type: SourceType
    citation: str
    """Human-readable citation (author, year, title)."""
    doi_or_url: str | None = None
    locator: str | None = None
    """Page, table or section inside the source (e.g. 'Table 2, col. k_25')."""


# ---------------------------------------------------------------------------
# Main model
# ---------------------------------------------------------------------------


class Parameter(BaseModel):
    """Single parameter in the registry.

    All numeric values carry explicit units (pint-parseable strings).
    """

    id: str
    """Unique snake_case identifier, e.g. 'plagioclase_k25_acid'."""
    name: str
    symbol: str | None = None
    group: ParameterGroup
    applies_to: list[str] = PydanticField(default_factory=list)
    """Which module or YAML section uses this parameter."""

    value: float | None = None
    unit: str | None = None
    """Pint-parseable unit string, e.g. 'mol/m^2/s', 'cmolc/kg', 'kJ/mol'."""

    distribution: Distribution | None = None
    range_min: float | None = None
    range_max: float | None = None

    kind: ParameterKind
    source: Source
    quality: SourceQuality

    status: ParameterStatus = ParameterStatus.missing
    notes: str | None = None

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------

    @field_validator("unit")
    @classmethod
    def unit_is_parseable(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            ureg.parse_expression(v)
        except pint.UndefinedUnitError as exc:
            raise ValueError(f"Unit '{v}' not parseable by pint: {exc}") from exc
        return v

    @model_validator(mode="after")
    def value_inside_range(self) -> Parameter:
        if self.value is None or self.status == ParameterStatus.missing:
            return self
        if self.range_min is not None and self.value < self.range_min:
            raise ValueError(
                f"Parameter '{self.id}': value {self.value} < range_min {self.range_min}"
            )
        if self.range_max is not None and self.value > self.range_max:
            raise ValueError(
                f"Parameter '{self.id}': value {self.value} > range_max {self.range_max}"
            )
        return self

    @model_validator(mode="after")
    def calibrated_must_have_bounds(self) -> Parameter:
        if (
            self.kind == ParameterKind.calibrated
            and self.status == ParameterStatus.ok
            and (self.range_min is None or self.range_max is None)
        ):
            raise ValueError(
                f"Calibrated parameter '{self.id}' must define range_min and range_max."
            )
        return self


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------

_PARAM_DIR = Path(__file__).parent.parent.parent.parent / "config" / "parameters"


def load_registry(param_dir: Path | None = None) -> list[Parameter]:
    """Load all parameter YAML files from config/parameters/.

    Returns a list of validated Parameter objects.
    Raises ValueError on the first validation failure.
    """
    d = param_dir or _PARAM_DIR
    params: list[Parameter] = []
    for yaml_file in sorted(d.glob("*.yaml")):
        raw: list[dict[str, Any]] = yaml.safe_load(yaml_file.read_text()) or []
        for entry in raw:
            params.append(Parameter.model_validate(entry))
    return params


def missing_params(params: list[Parameter]) -> list[Parameter]:
    """Return parameters with status='missing'."""
    return [p for p in params if p.status == ParameterStatus.missing]


def registry_report(params: list[Parameter]) -> str:
    """Return a plain-text summary of the registry."""
    total = len(params)
    ok = sum(1 for p in params if p.status == ParameterStatus.ok)
    missing = total - ok
    lines = [
        f"Registry: {total} parameters | {ok} ok | {missing} missing",
        "",
    ]
    if missing:
        lines.append("Missing parameters (no verified value):")
        for p in sorted(missing_params(params), key=lambda x: (x.group, x.id)):
            lines.append(f"  [{p.group.value}] {p.id} ({p.symbol or '—'}) — {p.notes or ''}")
    return "\n".join(lines)
