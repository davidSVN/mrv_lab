"""Soil losses: share of released cation charge that does not become captured CO2 (plan §5.2
step 3; F4 group soil_losses; decision D-54).

In acidic soil water, added alkalinity first consumes acidity (H+, exchangeable Al3+) instead of
forming bicarbonate: the carbon-capture efficiency of alkalinity is ~0 below pH 5 and ~1 between
pH 6 and 8 in freshwater, with the transition between pH 4.5 and 6.5 (Bertagni & Porporato 2022).
Measured in soil columns, CDR estimated from cation release exceeded the inorganic carbon formed
by 1.5-3.1 times, most in acidic soil (Su et al. 2026, abstract; wollastonite).

Two classes by topsoil pH (SoilGrids pH in water, 0-30 cm)::

    f_loss = f_loss_acid_soil     if pH < acid_soil_ph_threshold
             f_loss_neutral_soil  otherwise

    f_loss_acid    = 1 - 1/3.1  (largest overestimate, acidic soil)      range low: 1 - 1.30/2
    f_loss_neutral = 1 - 1/1.5  (smallest overestimate)                   range low: 0 (theory)
    threshold      = 5.5        (middle of the 4.5-6.5 transition)

Exchangeable Al is not used by this two-class rule (it would be needed for an acidity mass
balance); it stays ``missing`` (gap G-02).
"""

import numpy as np

from mrv_lab.erw_siting import literature

SOURCES: dict[str, dict] = {
    "est_2026_soil_acidity": {
        # PubMed record (NCBI E-utilities): the abstract is public; the ACS full text is not.
        "url": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=42611468"
        "&retmode=xml",
        "suffix": ".xml",
        "citation": "Su, C., Kang, R., Driscoll, C.T., Zhu, W., Goll, D.S., Huang, W., Wang, A. & "
        "Fang, Y. (2026). Overlooked soil acidity leads to significant overestimation of carbon "
        "sequestration in enhanced rock weathering. Environmental Science & Technology 60(32), "
        "22505-22516 (abstract, PubMed 42611468)",
        "doi": "doi:10.1021/acs.est.6c05139",
        "locator": "Abstract: CDR from cation release exceeded measured inorganic carbon by "
        "1.5-3.1 times; 0.63-1.30 mol CO2 per mol divalent cation under acidic conditions",
        "checks": [
            r"exceeded measured inorganic carbon formation by 1\.5[-–]3\.1 times, with the "
            r"largest discrepancy in acidic soil",
            r"only 0\.63[-–]1\.30 mol CO2 fixed per mol divalent cation released, well below the "
            r"theoretical value of 2\.0",
            r"pH 4, 6, and 8",
            r"Su\s+Chenxia",
        ],
    },
    "bertagni_porporato_2022": {
        "url": "https://iris.polito.it/retrieve/handle/11583/2994886/769438",
        "citation": "Bertagni, M.B. & Porporato, A. (2022). The carbon-capture efficiency of "
        "natural water alkalinization: implications for enhanced weathering. Science of the "
        "Total Environment 838, 156524",
        "doi": "doi:10.1016/j.scitotenv.2022.156524",
        "locator": "§3.1 and Fig. 1a: ACE ~0 at pH<5, ~1 in freshwater, transition pH 4.5-6.5",
        "checks": [
            r"ACE is basically zero at pH<5",
            r"ACE ≈ 1 for freshwater",
            r"the pH range 4\.5 to 6\.5",
        ],
    },
}

OVERESTIMATE_ACID = 3.1  # cation-based CDR / measured inorganic C, acidic soil
OVERESTIMATE_LEAST = 1.5  # smallest discrepancy
MOL_CO2_PER_DIVALENT_MAX_ACID = 1.30  # upper end under acidic conditions
THEORETICAL_MOL_CO2_PER_DIVALENT = 2.0
TRANSITION_PH = (4.5, 6.5)  # Bertagni & Porporato 2022


def texts() -> dict[str, str]:
    """Download (if needed) and read the sources."""
    return literature.texts(SOURCES, "soil_losses")


def verify(source_texts: dict[str, str]) -> list[str]:
    """Every quoted number must appear in its source text."""
    return literature.verify(SOURCES, source_texts)


def registry_values() -> dict[str, dict]:
    """Expected value and range of the soil-loss parameters (exchangeable Al stays missing)."""
    acid = round(1 - 1 / OVERESTIMATE_ACID, 2)
    acid_low = round(1 - MOL_CO2_PER_DIVALENT_MAX_ACID / THEORETICAL_MOL_CO2_PER_DIVALENT, 2)
    neutral = round(1 - 1 / OVERESTIMATE_LEAST, 2)
    return {
        "f_loss_acid_soil": {"value": acid, "range": [acid_low, acid]},
        "f_loss_neutral_soil": {"value": neutral, "range": [0.0, neutral]},
        "acid_soil_ph_threshold": {
            "value": sum(TRANSITION_PH) / 2,
            "range": list(TRANSITION_PH),
        },
    }


def loss_fraction(
    ph: np.ndarray | float, threshold: float, f_loss_acid: float, f_loss_neutral: float
) -> np.ndarray:
    """f_loss per cell from topsoil pH (two classes); NaN pH gives NaN."""
    ph = np.asarray(ph, dtype="float64")
    out = np.where(ph < threshold, f_loss_acid, f_loss_neutral)
    return np.where(np.isnan(ph), np.nan, out)
