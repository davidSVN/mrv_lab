# 01 — Where does ERW make sense in Colombia?

> Screening estimate from public data. Not a measured or certified removal. Spec and live status: [`docs/plans/erw_siting_colombia.md`](../../docs/plans/erw_siting_colombia.md)
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
| Geology (rock units) | Servicio Geológico Colombiano, Mapa Geológico de Colombia 2023, 1:1,500,000 (D1) | CC BY 4.0 stated in the explanatory memoir; not confirmed for the geodatabase | Gómez, J., Montes, N.E. & Marín, E. (comps.) 2023. *Mapa Geológico de Colombia 2023, 1:1 500 000*. SGC, Bogotá. Derived maps, tables and numbers are published relying on the memoir's CC BY 4.0 statement; the SGC's written confirmation for the geodatabase is pending (D-65). |
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
- **Results derived from the SGC geology** are published relying on the memoir's CC BY 4.0
  statement; the SGC's written confirmation is pending (D-65).
- No personal data is used.

## Method

Screening on a 1 km grid (EPSG:9377) over Meta, Tolima and Valle del Cauca. Full specification:
[`docs/plans/erw_siting_colombia.md`](../../docs/plans/erw_siting_colombia.md) §5; every decision
(D-xx) is explained in the [journal](../../docs/plans/erw_siting_journal.md).

1. **Candidate farmland** (D-56). A cell is a candidate when, as shares of its area, it is < 50 %
   protected (RUNAP), ≥ 50 % inside the UPRA frontier "No condicionada", ≥ 50 % in agricultural use
   (MapBiomas 2024 classes 21, 35, 74) and < 50 % steeper than 12 %. Natural grassland / savanna is
   excluded (D-59).
2. **Rock sources** (F2, F3). The 194 SGC units are classified Apta / Mixta / No apta for mafic and
   ultramafic rock; potential sources are points on truck roads within 5 km of Apta units (no
   licensed quarry data, D-09). Each cell is routed by road to its nearest Apta source (Dijkstra on
   the OpenStreetMap truck network; road km = last mile + network + access, D-47).
3. **Theoretical capture** (D-53): `R_CO2 = M_CO2/100 × 2η × Σ(wt% oxide / M oxide)` for CaO, MgO,
   Na₂O, K₂O, with η = 0.831 mol CO₂ per mole of charge (Renforth & Henderson 2017). Rock chemistry
   from Colombian samples (basalt: Kerr et al. 2002; ultramafic: García-Casco et al. 2020; gabbro uses
   basalt as a proxy).
4. **Dissolved fraction** (D-52, D-57): `f_diss = min(1, SSA(P80) × WR × M × s/yr × years ×
   Arrhenius(T))` (Strefler et al. 2018), with the cell's ERA5-Land mean temperature; ultramafic
   rate corrected for serpentinization (Palandri & Kharaka 2004). Grain classes P80 = 1000 / 100 /
   10 µm; base = medium (100 µm); horizon 10 years; application rate 20 t/ha.
5. **Soil losses** (D-54): share of released alkalinity spent on soil acidity, 0.68 where topsoil
   pH < 5.5 and 0.33 otherwise (Su et al. 2026; Bertagni & Porporato 2022).
6. **Emissions** (D-51): grinding (crushing 5.45 kWh/t + Bond's law) × Colombian grid factor
   0.220 kg CO₂/kWh (UPME); trucking 0.0204 L diesel/(t·km) × 1.42 empty return × 2.689 kg CO₂/L
   (UPME/IDB, SICE-TAC, FECOC); spreading 2.02 L diesel/t (Lefebvre et al. 2019).
7. **Net removal and break-even**: `net = R_CO2 × f_diss × (1 − f_loss) − grinding − transport −
   spreading` (t CO₂/t rock); break-even distance = road km at which net = 0.
8. **Uncertainty** (D-60): 1,000 Monte Carlo draws (seed 20261118) of every sourced range
   (triangular) and whole rock samples; per cell P5 / P50 / P95 and P(net > 0). One-at-a-time
   tornado and eight assumption scenarios (horizon 30 years, conditioned frontier, slope 8 %,
   Apta + Mixta sources, Meta without its main rock unit, no ultramafic sources, fine-grinding
   energy of Rinder & von Hagke 2021, temperature 1996–2025).

**Own reading added on top of the sources** (CLAUDE.md §6.5): the sources give rock maps, soil,
climate and literature rates; this analysis combines them into a per-cell net balance with a
probability, and shows which single assumption and which single rock unit each department's result
depends on.

## Result

<!-- results:start -->
_Generated from [`results.json`](results.json) (as of 2026-11-21); Screening estimate from public data. Not a measured or certified removal._

| | Meta | Tolima | Valle del Cauca |
|---|---|---|---|
| Candidate farmland | 14,915 km² | 3,933 km² | 3,082 km² |
| Acid topsoil (pH < 5.5) | 100% | 64% | 14% |
| Median road distance to rock | 170 km | 164 km | 10 km |
| Cells with net > 0, coarse grain | 0% | 0% | 0% |
| Cells with net > 0, medium grain | 68% | 99% | 97% |
| Cells with net > 0, fine grain | 98% | 99% | 97% |
| Median P(net > 0), medium | 47% | 100% | 66% |
| Median net removal, medium (P50) | -0.006 t CO₂/ha/yr | 0.243 t CO₂/ha/yr | 0.026 t CO₂/ha/yr |
| Median break-even distance, medium | 247 km | 1,297 km | 403 km |
<!-- results:end -->

## Limitations

- **Screening, not removal.** Lab-based weathering rates (range of three orders of magnitude) and
  one soil-loss study drive the result (tornado); neither is measured in Colombian fields.
- **Rock.** Rock sources are potential, not quarries; chemistry comes from other Colombian
  localities (G-11); gabbro uses basalt as a proxy; the 1:1.5M map misses small bodies.
- **Ultramafic rock** carries open health questions (asbestos, Ni, Cr; research pending, D-61) and
  is what makes Tolima's result; without it Tolima falls to the level of the other departments.
- **Meta** depends on a single gabbro unit (NP3ε-Pm) at its western edge.
- **Soil.** pH is modelled (SoilGrids), not measured; two pH classes create a step at 5.5; time
  dynamics of acidity are ignored; the ocean pathway is assumed (soil carbonate would halve capture).
- **Grinding.** Bond's law underestimates energy below ~70 µm; the fine class is checked with
  Rinder & von Hagke's higher value (scenario s7).
- **Roads.** Distances are not yet validated against documented routes (D-47).
- **Licence.** The SGC's written confirmation for the geodatabase is pending (D-65).
- No money costs, no yield effects, no permanence or verification modelling.

## Reproduce

```bash
uv run python analyses/01_erw_siting_colombia/analysis.py
```
