"""Theoretical CO2 capture per tonne of rock, application rate and horizon (plan §5.2 step 1;
F4 groups capture and application; decision D-53).

Capture counts charges (Lewis et al. 2021, Eq. 4): every mole of cation charge released and carried
to the ocean as alkalinity stores ``eta`` moles of CO2 (Renforth & Henderson 2017, Eq. 11)::

    CO2 (mol) = eta * (mol Na+ + mol K+) + 2 * eta * (mol Ca2+ + mol Mg2+)

Every oxide (CaO, MgO, Na2O, K2O) releases 2 moles of charge per mole of oxide, so::

    R_CO2 (t CO2 / t rock) = M_CO2 / 100 * 2 * eta * sum(wt%_oxide / M_oxide)

Lewis et al. 2021 Eq. 5 weights Na2O and K2O by 0.5*omega (omega = 2*eta), half of what the charge
count gives, and its Table 6 R_CO2 values are not reproduced by that equation; Eq. 4 is used.
Lewis also quotes eta = 0.86 for the conditions where the cited source gives 0.831; the primary
source is used. Ocean pathway assumed: if cations precipitate as soil carbonate, capture is about
halved (Renforth & Henderson 2017) — a limitation, not modelled.
"""

from mrv_lab.erw_siting import literature

#: Standard atomic weights (IUPAC / CIAAW conventional values), g/mol.
ATOMIC_WEIGHT = {"C": 12.011, "O": 15.999, "Ca": 40.078, "Mg": 24.305, "Na": 22.990, "K": 39.098}
OXIDE_MOLAR_MASS = {
    "CaO": ATOMIC_WEIGHT["Ca"] + ATOMIC_WEIGHT["O"],
    "MgO": ATOMIC_WEIGHT["Mg"] + ATOMIC_WEIGHT["O"],
    "Na2O": 2 * ATOMIC_WEIGHT["Na"] + ATOMIC_WEIGHT["O"],
    "K2O": 2 * ATOMIC_WEIGHT["K"] + ATOMIC_WEIGHT["O"],
}
CO2_MOLAR_MASS = ATOMIC_WEIGHT["C"] + 2 * ATOMIC_WEIGHT["O"]
#: Moles of cation charge released per mole of oxide (Ca2+, Mg2+: 1 x 2; Na+, K+: 2 x 1).
CHARGE_PER_OXIDE = {"CaO": 2, "MgO": 2, "Na2O": 2, "K2O": 2}

SOURCES: dict[str, dict] = {
    "renforth_henderson_2017": {
        # Typeset copy hosted by VLIZ (Flanders Marine Institute); publisher PDF refuses scripts.
        "url": "https://www.vliz.be/imisdocs/publications/ocrd/360528.pdf",
        "citation": "Renforth, P. & Henderson, G. (2017). Assessing ocean alkalinity for carbon "
        "sequestration. Reviews of Geophysics 55, 636-674",
        "doi": "doi:10.1002/2016RG000533",
        "locator": "§2.2, Eq. 11 and text: eta = 0.831 (pCO2 400 µatm, S 35, 17 °C); uptake 1.4 "
        "to 1.7 CO2 per divalent cation",
        "checks": [
            r"η = 0\.831",
            r"1\.66/mole of Ca",
            r"uptake is 1\.4 to 1\.7 molecules",
        ],
    },
    "lefebvre_2019": {
        "url": "https://aura.abdn.ac.uk/server/api/core/bitstreams/"
        "2b796f02-b577-4b8d-9f8f-659cf66f431e/content",
        "citation": "Lefebvre, D. et al. (2019). Assessing the potential of soil carbonation and "
        "enhanced weathering through Life Cycle Assessment: A case study for Sao Paulo State, "
        "Brazil. Journal of Cleaner Production 233, 468-481",
        "doi": "doi:10.1016/j.jclepro.2019.06.099",
        "locator": "§2.4: application rates 5, 20 and 50 t/ha",
        "checks": [r"three basalt application rates: 5, 50, and 20 t/ha"],
    },
    "lewis_2021": {
        "url": "https://researchonline.jcu.edu.au/68920/1/68920.pdf",
        "citation": "Lewis, A.L. et al. (2021). Effects of mineralogy, chemistry and physical "
        "properties of basalts on carbon capture potential and plant-nutrient element release "
        "via enhanced weathering. Applied Geochemistry 132, 105023",
        "doi": "doi:10.1016/j.apgeochem.2021.105023",
        "locator": "Eq. 4 (charge-based CDR); 30-year RTM horizon",
        "checks": [
            r"CDR = η⋅\s+\(mol monovalent cations\) \+ 2η⋅\s+\(mol divalent cations\)",
            r"30-year RTM simulation time",
            r"equal 0\.86",  # the value Lewis quotes; the primary source gives 0.831
        ],
    },
}

ETA = 0.831
#: 1.4-1.7 CO2 per divalent cation = 2 charges -> eta 0.70-0.85.
ETA_RANGE = [round(1.4 / 2, 2), round(1.7 / 2, 2)]
APPLICATION_RATE_T_PER_HA = {"value": 20.0, "range": [5.0, 50.0]}  # Lefebvre 2019
HORIZON_YEARS = {"value": 10.0, "range": [10.0, 30.0]}  # D-53; 30 years as in Lewis 2021


def texts() -> dict[str, str]:
    """Download (if needed) and read the sources."""
    return literature.texts(SOURCES, "capture")


def verify(source_texts: dict[str, str]) -> list[str]:
    """Every quoted number must appear in its source text."""
    return literature.verify(SOURCES, source_texts)


def registry_values() -> dict[str, dict]:
    """Expected value and range of the capture and application parameters."""
    return {
        "eta_mol_co2_per_mol_charge": {"value": ETA, "range": ETA_RANGE},
        "application_rate_t_per_ha": APPLICATION_RATE_T_PER_HA,
        "horizon_years": HORIZON_YEARS,
    }


def capture_potential_t_co2_per_t(oxides_wt_pct: dict[str, float], eta: float) -> float:
    """Theoretical maximum R_CO2 (t CO2 per t rock) from oxide wt% (rock as quarried)."""
    mol_charge_per_100_g = sum(
        CHARGE_PER_OXIDE[ox] * wt / OXIDE_MOLAR_MASS[ox] for ox, wt in oxides_wt_pct.items()
    )
    return eta * mol_charge_per_100_g * CO2_MOLAR_MASS / 100
