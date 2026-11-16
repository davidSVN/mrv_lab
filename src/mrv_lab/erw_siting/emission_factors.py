"""Emission factors and energy use of the rock supply chain (plan F4, group lca; decision D-51).

Each number taken from a source is written here with its locator and checked against the source
text (downloaded and SHA-256 pinned): if a source changes or a value was mistyped, :func:`verify`
fails. Derived parameters are computed here, so the registry values are reproducible:

- grid factor: UPME inventory factor of the national grid (SIN), latest year; range = 2022-2024;
- diesel: FECOC kg CO2/gal (fossil diesel) / litres per US gallon;
- truck: median SFC* of heavy diesel fleets measured on loaded trips only (UPME/IDB Table 2.8);
- empty return: 1 + empty/loaded fuel use per km (SICE-TAC C3S3, March 2024);
- grinding: crushing to 5 mm (Lefebvre 2019, Table 2) + Bond's law from 5 mm to the grain
  class P80; work index 20.41 kWh/t (value) and 17.10 kWh/t (range low end);
- spreading: Lefebvre 2019 diesel per tonne of rock / FECOC diesel density.
"""

import html
import math
import re
from pathlib import Path

import pandas as pd

from mrv_lab import io

US_GALLON_L = 3.785411784  # NIST definition of the US liquid gallon
CRUSHED_FEED_UM = 5_000  # F80 after crushing (Lefebvre 2019: comminution to 5 mm)

SOURCES: dict[str, dict] = {
    "upme_085_2026": {
        "url": "https://docs.upme.gov.co/Normatividad/085_2026.pdf",
        "citation": "UPME (2026). Resolución 000085 de 2026 (23-02-2026): factor de emisión del "
        "Sistema Interconectado Nacional del año 2024",
        "locator": "Artículo 1, literal B (factor para inventarios de GEI)",
        "checks": [r"inventarios de GEI:\s+0\.220 tonCO2eq/MWh"],
    },
    "upme_1198_2024": {
        # Copy of the UPME resolution hosted by ANDI (the UPME link was not reachable).
        "url": "https://www.andi.com.co/Uploads/1198_2024.pdf",
        "citation": "UPME (2024). Resolución 1198 de 2024: factor de emisión del SIN del año 2023",
        "locator": "Artículo 1, literal B",
        "checks": [r"inventarios de GEI:\s+0\.177 tonCO2eq/MWh"],
    },
    "upme_705_2024": {
        "url": "https://gestornormativo.creg.gov.co/gestor/entorno/docs/resolucion_upme_0705_2024.htm",
        "citation": "UPME (2024). Resolución 000705 de 2024: corrige el factor de emisión del SIN "
        "del año 2022",
        "locator": "Artículo 1, factor para inventarios de GEI",
        "checks": [r"inventarios de GEI:\s+0\.112 tonCO\s*2\s*eq/MWh"],
    },
    "fecoc_2016": {
        "url": "https://app.upme.gov.co/Calculadora_Emisiones1/new/"
        "Informe_Final_FECOC_Correcciones_UPME_FunNatura.pdf",
        "citation": "UPME, Incombustion & Fundación Natura (2016). Consultoría técnica para el "
        "fortalecimiento y mejora de la base de datos de factores de emisión de los combustibles "
        "colombianos (FECOC). Informe final",
        "locator": "Tabla 5 (Diesel: kg CO2/gal); composition table (Diésel: density kg/L)",
        "checks": [r"Diesel\s+74233,4\s+0,205\s+10,180", r"Diésel\s+85,75\s+13,80[^\n]*0,856"],
    },
    "upme_freight_baseline": {
        "url": "https://docs.upme.gov.co/DemandayEficiencia/Documents/1_Reporte_linea_base_EE_carga.pdf",
        "citation": "UPME & IDB (RELIEVE). Estándares de eficiencia energética y etiquetado para "
        "vehículos de carga en Colombia. Informe II: Línea base de consumo de combustible de "
        "vehículos de carga en Colombia",
        "locator": "Tabla 2.8, SFC* (DEL/100 t-km), heavy diesel fleets with all trips loaded",
        "checks": [],  # filled from TRUCK_ROWS below
    },
    "sicetac_andi_2024": {
        "url": "https://www.andi.com.co/Uploads/SICETAC%20CAMBIOS%20E%20IMPACTOS.pdf",
        "citation": "ANDI (2024). SICE-TAC: cambios e impactos (presentation of Ministerio de "
        "Transporte SICE-TAC fuel yields, C3S3, March 2024)",
        "locator": "Slide 'C3S3 2024': CARGADO 6.48 km/gal vs VACIO 15.55 km/gal (flat road)",
        "checks": [r"C3S3 Marzo\s+6\.48 Km / Gl", r"C3S3 Marzo\s+15\.55 Km / Gl"],
    },
    "lefebvre_2019": {
        "url": "https://aura.abdn.ac.uk/server/api/core/bitstreams/"
        "2b796f02-b577-4b8d-9f8f-659cf66f431e/content",
        "citation": "Lefebvre, D., Goglio, P., Williams, A., Manning, D.A.C., de Azevedo, A.C., "
        "Bergmann, M., Meersmans, J. & Smith, P. (2019). Assessing the potential of soil "
        "carbonation and enhanced weathering through Life Cycle Assessment: A case study for "
        "Sao Paulo State, Brazil. Journal of Cleaner Production 233, 468-481",
        "doi": "doi:10.1016/j.jclepro.2019.06.099",
        "locator": "Table 1 (spreading diesel kg/Mg rock), Table 2 (crushing kWh/t), §2.8 (Wi)",
        "checks": [
            r"Total\s+18\s+5\.450",
            r"Diesel in Agri Spreader[^\n]*kg\s+1\.73",
            r"work index of basalt for grinding\s+of 17\.10",
        ],
    },
    "ruan_2026": {
        "url": "https://link.springer.com/content/pdf/10.1007/s44246-026-00282-4.pdf",
        "citation": "Ruan, L., Li, J., Song, Z. et al. (2026). Enhanced weathering for CO2 "
        "removal from a global perspective. Carbon Research 5, 66",
        "doi": "doi:10.1007/s44246-026-00282-4",
        "locator": "§2.3.1 (particle sizes 10, 37, 100, 1000 µm), §2.3.2 Eq. 6 (Bond, Wi basalt "
        "20.41 kWh/t citing Green & Southard 2019)",
        "checks": [r"empirical work index is 20\.41\s+kWh", r"10, 37, 100, 1000 μm"],
    },
}

GRID_INVENTORY_T_PER_MWH = {2022: 0.112, 2023: 0.177, 2024: 0.220}
GRID_SOURCE_BY_YEAR = {2022: "upme_705_2024", 2023: "upme_1198_2024", 2024: "upme_085_2026"}
DIESEL_KGCO2_PER_GAL = 10.180  # FECOC Tabla 5, Diesel
DIESEL_DENSITY_KG_PER_L = 0.856  # FECOC, Diésel
#: UPME/IDB Table 2.8, heavy diesel fleets (C3, 2SX, 3SX) whose trips were all loaded:
#: (company, configuration, vehicles, trips, loaded trips, SFC L/100 km, SFC* L/100 t-km).
TRUCK_ROWS = [
    (1, "C3", 4, "119", "119", "46,31", "3,64"),
    (2, "2SX", 3, "45", "45", "34,65", "2,04"),
    (4, "2SX", 14, "240", "240", "61,92", "2,26"),
    (4, "3SX", 3, "54", "54", "67,59", "2,26"),
    (4, "2SX", 3, "5", "5", "55,29", "1,60"),
    (5, "3SX", 92, "179", "179", "54,74", "1,59"),
    (6, "3SX", 39, "669", "669", "66,86", "1,95"),
]
SFC_LOADED_KM_PER_GAL = 6.48  # SICE-TAC C3S3, March 2024, flat road, loaded
SFC_EMPTY_KM_PER_GAL = 15.55  # same, empty
CRUSHING_KWH_PER_T = 5.45  # Lefebvre 2019 Table 2 (crushing to 5 mm, metered electricity)
BOND_WI_KWH_PER_T = {"value": 20.41, "low": 17.10}  # Ruan 2026 / Lefebvre 2019
SPREADING_KG_DIESEL_PER_T = 1.73  # Lefebvre 2019 Table 1 (per Mg of rock)

SOURCES["upme_freight_baseline"]["checks"] = [
    rf"D – {cfg}\s+{veh}\s+{trips}\s+{loaded}\s+{sfc} ± [\d,]+\s+{sfc_star} ±"
    for _, cfg, veh, trips, loaded, sfc, sfc_star in TRUCK_ROWS
]


def download() -> dict[str, Path]:
    """Download every source to ``data/raw/emission_factors/`` (SHA-256 pinned)."""
    folder = io.raw_dir() / "emission_factors"
    paths = {}
    for key, src in SOURCES.items():
        suffix = ".htm" if src["url"].endswith(".htm") else ".pdf"
        paths[key] = io.download_file(src["url"], folder / f"{key}{suffix}", timeout_s=300)
    return paths


def source_text(path: Path) -> str:
    """Plain text of a downloaded source (PDF layout text, or HTML without tags)."""
    if path.suffix == ".htm":
        raw = path.read_bytes().decode("utf-8", errors="replace")
        return html.unescape(re.sub(r"<[^>]+>", " ", raw))
    return io.pdf_text(path, layout=True) + "\n" + io.pdf_text(path, layout=False)


def verify(texts: dict[str, str]) -> list[str]:
    """Every transcribed number must appear in its source text."""
    return [
        f"{key}: pattern not found: {pattern}"
        for key, src in SOURCES.items()
        for pattern in src["checks"]
        if not re.search(pattern, texts[key])
    ]


def bond_kwh_per_t(work_index_kwh_per_t: float, p80_um: float, f80_um: float) -> float:
    """Bond's law: ``W = 10 Wi (1/sqrt(P80) - 1/sqrt(F80))``, sizes in µm, W in kWh/t."""
    return 10 * work_index_kwh_per_t * (1 / math.sqrt(p80_um) - 1 / math.sqrt(f80_um))


def comminution_kwh_per_t(p80_um: float, work_index_kwh_per_t: float) -> float:
    """Crushing to 5 mm (metered) + grinding from 5 mm to ``p80_um`` (Bond)."""
    return CRUSHING_KWH_PER_T + bond_kwh_per_t(work_index_kwh_per_t, p80_um, CRUSHED_FEED_UM)


def truck_sfc_l_per_t_km() -> pd.Series:
    """SFC* of the loaded-trip heavy fleets, L/(t*km)."""
    return pd.Series([float(r[6].replace(",", ".")) / 100 for r in TRUCK_ROWS])


def registry_values(p80_um: dict[str, float]) -> dict[str, dict]:
    """Expected value and range of every lca parameter; ``p80_um`` by grain class (grain.yaml)."""
    years = sorted(GRID_INVENTORY_T_PER_MWH)
    grid = [GRID_INVENTORY_T_PER_MWH[y] for y in years]  # t/MWh == kg/kWh
    truck = truck_sfc_l_per_t_km()
    empty = round(1 + SFC_LOADED_KM_PER_GAL / SFC_EMPTY_KM_PER_GAL, 2)
    out = {
        "grid_ef_kgco2_per_kwh": {"value": grid[-1], "range": [min(grid), max(grid)]},
        "diesel_ef_kgco2_per_l": {
            "value": round(DIESEL_KGCO2_PER_GAL / US_GALLON_L, 3),
            "range": None,
        },
        "truck_l_diesel_per_t_km": {
            "value": round(float(truck.median()), 4),
            "range": [round(float(truck.min()), 4), round(float(truck.max()), 4)],
        },
        "empty_return_factor": {"value": empty, "range": [1.0, empty]},
        "spreading_l_diesel_per_t": {
            "value": round(SPREADING_KG_DIESEL_PER_T / DIESEL_DENSITY_KG_PER_L, 2),
            "range": None,
        },
    }
    for grain, p80 in p80_um.items():
        hi = round(comminution_kwh_per_t(p80, BOND_WI_KWH_PER_T["value"]), 2)
        lo = round(comminution_kwh_per_t(p80, BOND_WI_KWH_PER_T["low"]), 2)
        out[f"grinding_kwh_per_t_{grain}"] = {"value": hi, "range": [lo, hi]}
    return out
