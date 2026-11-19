# 01 — Where does ERW make sense in Colombia?

> Work in progress. Spec and live status: [`docs/plans/erw_siting_colombia.md`](../../docs/plans/erw_siting_colombia.md)
> (§0). Steps, decisions and results: [`docs/plans/erw_siting_journal.md`](../../docs/plans/erw_siting_journal.md).
> Sections are filled when results are final; no number is quoted before it is in `results.json`. Contract: [CLAUDE.md §6](../../CLAUDE.md).

## Question

In which agricultural areas of Colombia would spreading crushed rock remove net CO₂, and where do
transport, grinding and soil losses eat the gain?

## Data

Full registry with quoted licence text, access dates and checksums:
[`data/SOURCES.md`](../../data/SOURCES.md). No raw file is redistributed here: `analysis.py`
downloads every source into `data/raw/` (gitignored) and pins its SHA-256 in
`data/checksums.json`.

### Spatial data

| Layer | Source (ID in SOURCES.md) | Licence | Required attribution / note |
|---|---|---|---|
| Geology (rock units) | Servicio Geológico Colombiano, Mapa Geológico de Colombia 2023, 1:1,500,000 (D1) | CC BY 4.0 stated in the explanatory memoir; not confirmed for the geodatabase | Gómez, J., Montes, N.E. & Marín, E. (comps.) 2023. *Mapa Geológico de Colombia 2023, 1:1 500 000*. SGC, Bogotá. **Internal use only until the SGC confirms in writing that derived maps and figures may be published (D-08).** |
| Agricultural frontier | UPRA, Frontera Agrícola Nacional (D4) | CC BY-SA 4.0 (stricter reading of the UPRA licence) | Holder (UPRA) and version date; the service does not declare a version date (gap G-06). Transformations listed below. |
| Protected areas | Parques Nacionales Naturales, RUNAP (D18) | CC BY-SA 4.0 | "RUNAP © 2025 por Parques Nacionales Naturales licenciado bajo CC BY-SA 4.0" |
| Land cover 2024 | MapBiomas Colombia, Collection 3.0 (D6) | CC BY 4.0 | Citation format to be confirmed on the official page before publication. |
| Soil (pH, CEC, clay, SOC, bulk density) | ISRIC SoilGrids 2.0 (D8) | CC BY 4.0 | Poggio et al. 2021, *SOIL* 7, 217–240, doi:10.5194/soil-7-217-2021. Model predictions, not measurements. |
| Rainfall | CHIRPS v2.0 monthly, UCSB Climate Hazards Center (D9) | Public domain (CC0 statement) | Funk et al. 2015, *Scientific Data* 2, 150066. |
| Temperature, evaporation | ERA5-Land monthly means, Copernicus Climate Change Service (D9/D10/D19) | CC BY 4.0 | Cite C3S and ERA5-Land; exact C3S attribution text to be checked before publication. |
| Elevation / slope | Copernicus DEM GLO-30 (D11) | Copernicus DEM licence | "produced using Copernicus WorldDEM-30 © DLR e.V. 2010-2014 and © Airbus Defence and Space GmbH 2014-2018 provided under COPERNICUS by the European Union and ESA; all rights reserved". "The organisations in charge of the Copernicus programme by law or by delegation do not incur any liability for any use of the Copernicus WorldDEM-30". |
| Roads | OpenStreetMap via HOT export on HDX (D12) | ODbL 1.0 | © OpenStreetMap contributors. Derived databases are shared under ODbL. |
| Department outlines (clipping only) | geoBoundaries gbOpen COL ADM1 (D17b) | ODbL 1.0 (OSM-derived) | Not official limits; areas are not reported by department from this layer. |

### Parameters (literature and official factors)

Every parameter value lives in [`config/erw_siting/parameters/`](../../config/erw_siting/parameters/)
with its citation and locator, and is recomputed from (and checked against) the source text in every
run. Sources: rock chemistry (Kerr et al. 2002; García-Casco et al. 2020; D16), emission factors
(UPME SIN factor and FECOC, UPME/IDB freight baseline, SICE-TAC via ANDI, Lefebvre et al. 2019,
Ruan et al. 2026; D14, D15, D21–D24), weathering kinetics (Strefler et al. 2018; Palandri &
Kharaka 2004; D25, D26), capture (Renforth & Henderson 2017; Lewis et al. 2021; D27, D28), soil
losses (Su et al. 2026; Bertagni & Porporato 2022; D29, D30) and the fine-grinding scenario
(Rinder & von Hagke 2021; D31). Only aggregates of published tables are stored here.

### Transformations made to the source data

1. Clipped to Meta, Tolima and Valle del Cauca and reprojected to EPSG:9377 (MAGNA-SIRGAS Origen
   Nacional).
2. Geology: every unit classified Apta / Mixta / No apta for mafic and ultramafic rock; potential
   rock sources placed on truck roads within 5 km of suitable units.
3. Frontier, protected areas, land cover and slope: converted to the share of each 1 km cell;
   soil and climate: averaged per cell; climate: 1991–2020 (and 1996–2025 temperature) normals.
4. Roads: truck classes only; shortest road distance from every cell to the nearest rock source.
5. All layers combined in a cell database to compute net CO₂ removal per cell (method below).

### Licence of the outputs

- **Code:** MIT ([LICENSE](../../LICENSE)).
- **Figures, tables and numbers derived from the data:** CC BY-SA 4.0, because they derive from
  CC BY-SA 4.0 layers (UPRA frontier, RUNAP).
- **Derived databases that contain road data** (e.g. road distances per cell): ODbL 1.0.
- **Anything derived from the SGC geology** is not published until the SGC answers (D-08).
- No personal data is used.

## Method

_Pending._

## Result

_Pending._ Numbers will come from [`results.json`](results.json) only.

## Limitations

_Pending._

## Reproduce

```bash
uv run python analyses/01_erw_siting_colombia/analysis.py
```
