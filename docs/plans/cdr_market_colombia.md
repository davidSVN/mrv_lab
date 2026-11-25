# Plan — Analysis 02: economics of enhanced rock weathering (ERW) in Colombia

Status: v0.1 (2026-11-25) · Owner: David · Code targets (proposed): `src/mrv_lab/market/`,
`analyses/02_erw_economics_colombia/`, `config/market/` · Depends on analysis 01 (cell results).

Hard rules (as in analysis 01): never invent values, URLs or licences; every number carries a
source and is recomputed / checked by code; a value without a verified source stays `missing`;
licence of every market data source checked before download (R-04). Prices are volatile: every
value carries its date, currency and year of the currency.

## 0. Status

| Step | What | Status |
|---|---|---|
| M0 | This plan; research prompts R11–R16 written (kept in `private/`, not in git) | ✅ |
| M1 | Research modules R11–R16 run by David (separate research chat) | ⏳ |
| M2 | Market parameter registry (`config/market/*.yaml`), same rules as the F4 registry | ⏳ |
| M3 | Cost per tonne of CO₂ removed per cell (from analysis 01) | ⏳ |
| M4 | Margin and break-even credit price per cell; scenarios and Monte Carlo | ⏳ |
| M5 | README, `results.json`, figures | ⏳ |

## 1. Question

**At which credit price does ERW pay for itself in each candidate area of Meta, Tolima and Valle
del Cauca, and what does the market currently pay for it?**

Sub-questions:
1. What does one tonne of rock cost delivered and spread on a field (quarry fines, grinding, truck,
   spreading), in COP and USD?
2. What is the cost per tonne of CO₂ removed per cell, combining that cost with the net removal of
   analysis 01 (cost ÷ net t CO₂ per t rock)?
3. What prices do buyers pay for ERW removals (offtakes, spot, registries), and how have they moved?
4. Which Colombian policies change the economics (carbon tax and its offset mechanism, voluntary
   market rules, Article 6, ICA rules for soil amendments)?
5. Who invests in carbon removal and ERW, how much, and is Latin America / Colombia in their scope?
6. What co-benefit value exists (agricultural lime replaced on acid soils) and who would pay it?

## 2. Method (to confirm after M1)

- `cost_rock_usd_per_t` = quarry fines price + grinding (kWh/t × industrial electricity tariff)
  + transport (road km × freight cost per t·km, SICE-TAC) + spreading (cost per t).
- `cost_per_t_co2` (per cell) = `cost_rock_usd_per_t` ÷ `net_tco2_per_t` (only where net > 0),
  plus MRV cost per tonne and registry fees.
- `breakeven_credit_price` = `cost_per_t_co2`; `margin` = market price − break-even price.
- Optional co-benefit: avoided lime purchase (t lime equivalent × lime price) on acid soils,
  reported on a separate axis, never netted against carbon (as in analysis 01, plan v0.2).
- Uncertainty: price ranges drawn in the Monte Carlo of analysis 01 (same seed policy).
- Currency: values converted with a documented exchange rate and date (Banco de la República TRM).

## 3. Research modules (David's research chat; prompts in `private/research_prompts/`)

| ID | Topic | Feeds |
|---|---|---|
| R11 | Global and ERW carbon-removal market: volumes, prices by pathway, buyers, offtakes, registries | Price per t CO₂ (sub-question 3) |
| R12 | ERW project economics and MRV: cost structure of ERW projects, MRV and verification costs, registry fees | MRV / registry cost |
| R13 | Colombian cost inputs: quarry fines and aggregate prices, industrial electricity tariffs, freight cost per t·km, spreading cost, agricultural lime prices | Cost per t rock, co-benefit |
| R14 | Colombian policy and carbon market: carbon tax and offset mechanism, voluntary market rules, RENARE, Article 6, ICA amendments | Policy scenarios |
| R15 | Investment landscape: CDR and ERW funding (VC, grants, prizes, climate funds), Latin America focus | Context, investor map |
| R16 | Demand in Colombia: corporate net-zero commitments and potential buyers of removals | Demand context |

Already available: R01 (ERW trials, actors and rock-flour market in Colombia, cut 2026-11-06,
David's research; not in git): one ERW developer listed on Isometric without verified issued
credits; rock flour sold as a coarse soil amendment (ICA Res. 150/2003, "acondicionador
inorgánico"); no remineralizer category; the only public field figure is an AGU 2024 abstract.

## 4. Limitations to declare from the start

- Market prices are thin, mostly undisclosed and volatile; registries and buyers report differently.
- Colombian freight, electricity and quarry prices vary by region and contract; public tariffs are
  references, not quotes.
- Costs are not offers: no supplier was contacted.
- Analysis 01 limitations carry over (weathering rate and soil losses unmeasured in Colombia).
