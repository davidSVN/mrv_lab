# 01 — Where does ERW make sense in Colombia?

> Work in progress. Spec and live status: [`docs/plans/erw_siting_colombia.md`](../../docs/plans/erw_siting_colombia.md)
> (§0). Steps, decisions and results: [`docs/plans/erw_siting_journal.md`](../../docs/plans/erw_siting_journal.md).
> Sections are filled when results are final; no number is quoted before it is in `results.json`. Contract: [CLAUDE.md §6](../../CLAUDE.md).

## Question

In which agricultural areas of Colombia would spreading crushed rock remove net CO₂, and where do
transport, grinding and soil losses eat the gain?

## Data

Sources registered with licence text in [`data/SOURCES.md`](../../data/SOURCES.md): RUNAP (D18),
UPRA agricultural frontier (D4), ISRIC SoilGrids 2.0 (D8), MapBiomas Colombia 2024 (D6), Copernicus
DEM GLO-30 (D11), CHIRPS v2.0 (D9), ERA5-Land (D10, D19), SGC Mapa Geológico 2023 (D1, internal use
until SGC confirms publication), OpenStreetMap roads via HOT/HDX (D12), geoBoundaries (D17b), rock chemistry from Kerr et al. 2002 and García-Casco et al. 2020 (D16; only
aggregates in `config/erw_siting/parameters/rock.yaml`), emission factors from UPME (SIN factor,
FECOC, freight baseline), SICE-TAC via ANDI, Lefebvre et al. 2019 and Ruan et al. 2026 (D14, D15,
D21–D24; values quoted in `lca.yaml`).
Nothing raw is redistributed here.

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
