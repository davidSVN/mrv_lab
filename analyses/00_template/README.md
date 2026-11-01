# NN — <Title = the finding>

> Template. Copy this folder to `analyses/NN_slug/` and replace every `<...>`.
> Contract: [CLAUDE.md §6](../../CLAUDE.md). Keep exactly these six sections.

## Question

<One sentence.>

## Data

- **Source:** <name> — <URL>
- **Access date:** <YYYY-MM-DD>
- **License / terms:** <license, link to terms> (registered in [`data/SOURCES.md`](../../data/SOURCES.md))
- **Redistributed here:** <nothing / aggregates only / raw files> — <why the license allows it>

## Method

1. <Step.>
2. <Step.>

- **Assumptions:** <...>
- **Formulas:** <...>
- **Own reading added on top of the source:** <the cut, ratio, comparison or chart that is new here>
- **Random seed:** <value, also recorded in `results.json`, or "not applicable">

## Result

Numbers below come from [`results.json`](results.json); posts quote these keys only.

| Key | Value | Unit | As of |
|---|---|---|---|
| `<key>` | <value> | <unit> | <YYYY-MM-DD> |

![<Alt text describing the finding>](figures/<name>.png)

## Limitations

- <What this does NOT show.>
- <Biases or coverage gaps of the source.>

## Reproduce

```bash
uv run python analyses/NN_slug/analysis.py
```
