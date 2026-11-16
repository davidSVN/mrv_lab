"""Dissolved fraction of applied rock (plan §5.2 step 2; F4 group weathering; decision D-52).

Model (Strefler et al. 2018, Eq. 2, plus an Arrhenius temperature correction)::

    d(x)   = SSA(x) * WR * M * seconds_per_year          # fraction dissolved per year
    SSA(x) = a * x**b                                     # m2/g, x = P80 in µm
    f_diss = min(1, d(x) * years * exp(-Ea/R * (1/T - 1/T_ref)))

WR is the grain-surface weathering rate at pH 7 and 25 °C (mol m-2 s-1), M the molar mass of the
rock (g/mol). The surface is held constant (Strefler's idealisation: overestimates long horizons).
No pH or water term (D-52): rates at pH 7; dry months are only a flag. Gabbro uses the basalt
values (proxy, as in the rock group, D-49).

Quoted numbers are checked against the source texts (:mod:`literature`).
"""

import numpy as np
import pandas as pd

from mrv_lab.erw_siting import literature, registry

SECONDS_PER_YEAR = 3.155e7  # as in Strefler et al. 2018, Eq. 2
GAS_CONSTANT_J_PER_MOL_K = 8.314462618  # CODATA 2018
KELVIN_OFFSET = 273.15

SOURCES: dict[str, dict] = {
    "strefler_2018": {
        "url": "https://iopscience.iop.org/article/10.1088/1748-9326/aaa9c4/pdf",
        "citation": "Strefler, J., Amann, T., Bauer, N., Kriegler, E. & Hartmann, J. (2018). "
        "Potential and costs of carbon dioxide removal by enhanced weathering of rocks. "
        "Environmental Research Letters 13, 034010",
        "doi": "doi:10.1088/1748-9326/aaa9c4",
        "locator": "§2, Eq. 2 (SSA = 69.18 x^-1.24; molar masses) and weathering rates "
        "at pH 7, 25 °C",
        "checks": [
            r"69\.18 ∗ x",
            r"\[𝜇m\]−1\.24",
            r"with 140\.7 g mol−1 \) or basalt \(125 g mol−1",
            r"10−10\.53 \(10−12\.63 −10−9\.55 \) mol m−2 s−1 for basalt",
            r"10−9\.86 \(10−9\.95 −10−9\.77 \) mol m−2 s−1 for dunite",
            r"pH of 7 and temperature of 25 ◦ C",
        ],
    },
    "palandri_kharaka_2004": {
        "url": "https://pubs.usgs.gov/of/2004/1068/OFR_2004_1068_old.pdf",
        "citation": "Palandri, J.L. & Kharaka, Y.K. (2004). A compilation of rate parameters of "
        "water-mineral interaction kinetics for application to geochemical modeling. U.S. "
        "Geological Survey Open-File Report 2004-1068",
        "doi": "doi:10.3133/ofr20041068",
        "locator": "Rate-parameter tables: neutral-mechanism activation energy E (kJ/mol)",
        "checks": [
            r"Labradorite\s+-7\.87\s+42\.1\s+0\.626\s+-10\.91\s+45\.2",
            r"Forsterite\s+-6\.85\s+67\.2\s+0\.470\s+-10\.64\s+79\.0",
            r"augite\s+-6\.82\s+78\.0\s+0\.700\s+-11\.97\s+78\.0",
            r"diopside\s+-6\.36\s+96\.1\s+0\.710\s+-11\.11\s+40\.6",
        ],
    },
}

#: Quoted values (checked by :func:`verify`).
SSA_COEF_M2_PER_G = 69.18
SSA_EXPONENT = -1.24
LOG10_WR = {
    "basalt": {"value": -10.53, "range": [-12.63, -9.55]},
    "ultramafic": {"value": -9.86, "range": [-9.95, -9.77]},  # Strefler: dunite
}
MOLAR_MASS_G_PER_MOL = {"basalt": 125.0, "ultramafic": 140.7}
#: Neutral-mechanism E (kJ/mol), Palandri & Kharaka 2004.
EA_NEUTRAL_KJ_PER_MOL = {"labradorite": 45.2, "forsterite": 79.0, "augite": 78.0, "diopside": 40.6}
REFERENCE_TEMPERATURE_C = 25.0
#: Rock type used for the kinetics of each rock class (gabbro: basalt proxy, D-49/D-52).
KINETIC_ROCK = {"basalt": "basalt", "gabbro": "basalt", "ultramafic": "ultramafic"}


def texts() -> dict[str, str]:
    """Download (if needed) and read both sources."""
    return literature.texts(SOURCES, "weathering")


def verify(source_texts: dict[str, str]) -> list[str]:
    """Every quoted number must appear in its source text."""
    return literature.verify(SOURCES, source_texts)


def registry_values() -> dict[str, dict]:
    """Expected value and range of every weathering parameter."""
    ea = EA_NEUTRAL_KJ_PER_MOL
    pyroxenes = [ea["diopside"], ea["augite"]]
    return {
        "ssa_coef_m2_per_g": {"value": SSA_COEF_M2_PER_G, "range": None},
        "ssa_exponent": {"value": SSA_EXPONENT, "range": None},
        "log10_wr_basalt_mol_m2_s": LOG10_WR["basalt"],
        "log10_wr_ultramafic_mol_m2_s": LOG10_WR["ultramafic"],
        "molar_mass_basalt_g_per_mol": {"value": MOLAR_MASS_G_PER_MOL["basalt"], "range": None},
        "molar_mass_ultramafic_g_per_mol": {
            "value": MOLAR_MASS_G_PER_MOL["ultramafic"],
            "range": None,
        },
        "activation_energy_kj_per_mol_basalt": {
            "value": ea["labradorite"],
            "range": [min(pyroxenes + [ea["labradorite"]]), max(pyroxenes + [ea["labradorite"]])],
        },
        "activation_energy_kj_per_mol_ultramafic": {"value": ea["forsterite"], "range": None},
        "reference_temperature_c": {"value": REFERENCE_TEMPERATURE_C, "range": None},
    }


def specific_surface_m2_per_g(p80_um: float, coef: float, exponent: float) -> float:
    """SSA = coef * P80**exponent (m2/g, P80 in µm)."""
    return coef * p80_um**exponent


def arrhenius_factor(
    temperature_c: np.ndarray | float, ea_kj_per_mol: float, reference_c: float
) -> np.ndarray | float:
    """Rate at ``temperature_c`` relative to the rate at ``reference_c``."""
    t = np.asarray(temperature_c, dtype="float64") + KELVIN_OFFSET
    t_ref = reference_c + KELVIN_OFFSET
    return np.exp(-ea_kj_per_mol * 1000 / GAS_CONSTANT_J_PER_MOL_K * (1 / t - 1 / t_ref))


def dissolved_fraction(
    p80_um: float,
    years: float,
    temperature_c: np.ndarray | float,
    log10_wr_mol_m2_s: float,
    molar_mass_g_per_mol: float,
    ea_kj_per_mol: float,
    reference_c: float,
    ssa_coef: float,
    ssa_exponent: float,
) -> np.ndarray:
    """Fraction of the applied rock dissolved after ``years`` (0-1), per cell temperature."""
    per_year = (
        specific_surface_m2_per_g(p80_um, ssa_coef, ssa_exponent)
        * 10**log10_wr_mol_m2_s
        * molar_mass_g_per_mol
        * SECONDS_PER_YEAR
    )
    factor = arrhenius_factor(temperature_c, ea_kj_per_mol, reference_c)
    return np.minimum(1.0, per_year * years * factor)


def dissolved_fraction_from_registry(
    table: pd.DataFrame,
    rock_class: str,
    p80_um: float,
    years: float,
    temperature_c: np.ndarray | float,
) -> np.ndarray:
    """:func:`dissolved_fraction` with the registry values for ``rock_class``."""
    rock = KINETIC_ROCK[rock_class]

    def v(pid: str) -> float:
        return registry.value(table, pid)

    return dissolved_fraction(
        p80_um=p80_um,
        years=years,
        temperature_c=temperature_c,
        log10_wr_mol_m2_s=v(f"log10_wr_{rock}_mol_m2_s"),
        molar_mass_g_per_mol=v(f"molar_mass_{rock}_g_per_mol"),
        ea_kj_per_mol=v(f"activation_energy_kj_per_mol_{rock}"),
        reference_c=v("reference_temperature_c"),
        ssa_coef=v("ssa_coef_m2_per_g"),
        ssa_exponent=v("ssa_exponent"),
    )
