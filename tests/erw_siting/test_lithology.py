"""Tests for erw_siting.lithology with descriptions in the SGC style (no network)."""

from pathlib import Path

import pandas as pd
import pytest

from mrv_lab.erw_siting import lithology as lt


@pytest.mark.parametrize(
    ("description", "expected"),
    [
        ("Basaltos toleíticos, y doleritas, picritas, tobas básicas y brechas volcánicas.", "Apta"),
        ("Gabros que varían de olivínicos a cuarzogabros, a través de noritas.", "Apta"),
        ("Harzburgitas, lerzolitas, dunitas y websteritas. Serpentinitas.", "Apta"),
        ("Basaltos y andesitas intercalados con arenitas lodosas líticas y calizas.", "Mixta"),
        (
            "Tonalitas a granodioritas con algunas variaciones a dioritas, aplitas y gabros.",
            "No apta",
        ),
        ("Ignimbritas riolíticas ricas en fragmentos líticos de limolitas, basaltos.", "No apta"),
        ("Capas rojas constituidas por arenitas, conglomerados y limolitas.", "No apta"),
    ],
)
def test_classify_real_style_descriptions(description: str, expected: str) -> None:
    assert lt.classify(description)[0] == expected


def test_rock_types_in_order_and_basaltic_andesite_is_not_andesite() -> None:
    assert lt.rock_types("Basaltos y andesitas basálticas") == ["basalt", "basaltic andesite"]
    assert lt.rock_types("Andesitas porfiríticas y dacitas") == ["andesite", "dacite"]


def test_review_template_created_once_and_applied(tmp_path: Path) -> None:
    table = pd.DataFrame(
        {
            "unit_code": [1, 2],
            "symbol": ["A", "B"],
            "description": ["Basaltos", "Calizas"],
            "rock_types": ["basalt", "limestone"],
            "proposed_class": ["Apta", "No apta"],
            "reason": ["main rock basalt", "no mafic or ultramafic rock named"],
        }
    )
    review = tmp_path / "review.csv"
    first = lt.apply_review(table, review)
    assert review.exists()
    assert list(first["final_class"]) == ["Apta", "No apta"]

    edited = pd.read_csv(review, dtype={"review_class": "string", "review_note": "string"})
    edited.loc[edited["unit_code"] == 1, "review_class"] = "Mixta"
    edited.to_csv(review, index=False)
    second = lt.apply_review(table, review)
    assert list(second["final_class"]) == ["Mixta", "No apta"]
    assert list(second["reviewed"]) == [True, False]

    edited.loc[edited["unit_code"] == 2, "review_class"] = "Maybe"
    edited.to_csv(review, index=False)
    with pytest.raises(ValueError, match="Unknown review_class"):
        lt.apply_review(table, review)


def test_missing_description_is_not_suitable() -> None:
    assert lt.rock_types(float("nan")) == []
    assert lt.classify(None)[0] == "No apta"
