# Using Atlas Quant

Atlas Quant is an offline research toolkit for financial mathematics, portfolio experiments and evidence-led review. Its default experiment uses labelled synthetic data. It requires no account, trading credentials, paid model subscription or market-data API.

## Install and run

From a local clone of this repository, use Python 3.11 or later:

```sh
python -m venv .venv
# macOS/Linux:
. .venv/bin/activate
# Windows PowerShell instead: .venv\Scripts\Activate.ps1
python -m pip install .
atlas-quant demo --output output-demo
```

Open `output-demo/report.html` in a browser. The accompanying `report.json` contains the exact numeric results, input digest, configuration, trade ledger, council evidence and content-integrity digest. Choose a new output directory for every run; an existing directory is deliberately not overwritten.

A complete demo runs portfolio research, a matched equal-weight benchmark, one higher-cost scenario, a separate European option-pricing experiment and the six-role deterministic council. This is a reproducible demonstration of mechanics. Synthetic performance does not provide evidence of profitability in markets.

## Analyse your own prices

Supply a local UTF-8 CSV with an exact `date` column followed by unique asset symbols:

```csv
date,ASSET_A,ASSET_B
2025-01-02,100.00,80.00
2025-01-03,101.00,79.50
2025-01-06,100.50,80.25
```

The three-row fragment illustrates the format only. A backtest needs enough observations for its lookback and subsequent executions. Use a sufficiently long series of adjusted closing prices, expressed in one common currency on a shared calendar:

```sh
atlas-quant backtest prices.csv --strategy inverse_volatility --lookback 60 --rebalance-every 21 --cost-bps 10 --max-weight 0.40 --output output-prices
```

A 40% maximum weight requires at least three assets for a fully invested portfolio. The engine rejects infeasible caps. Dates must be canonical `YYYY-MM-DD`, unique and strictly increasing. Prices must be finite, positive and complete. No missing prices are filled automatically. Files are limited to 20 MB, 100,000 rows and 100 assets. Asset identifiers contain letters, digits, full stops, underscores or hyphens, with a maximum of 32 characters.

CSV structure cannot prove that prices are correctly adjusted, currency-consistent or free of survivorship bias. The data provider and researcher remain responsible for those properties. Select the universe and test design before interpreting results. The toolkit does not download price histories or incorporate delisted securities for you.

## Choose a strategy and conventions

| Setting | Meaning |
|---|---|
| `--strategy equal_weight` | Equal target weights across assets. |
| `--strategy inverse_volatility` | Allocate proportionally to inverse trailing sample volatility, subject to the cap. This is a heuristic, not a general risk-parity optimiser. |
| `--strategy minimum_variance` | Long-only constrained minimum-variance allocation using a fixed 10% diagonal covariance shrinkage. |
| `--lookback 60` | Number of trailing return observations used at each decision. |
| `--rebalance-every 21` | Number of observation intervals between decisions. |
| `--cost-bps 10` | Proportional cost on gross traded notional. Ten basis points equals 0.1%; purchases and sales both contribute. |
| `--initial-cash 100000` | Starting capital in the currency units of the supplied data. |
| `--max-weight 0.40` | Maximum target allocation per asset. Prices may subsequently cause weights to drift. |
| `--periods-per-year 252` | Observation frequency used for annualisation. Choose a value consistent with the data frequency. |
| `--seed 42` | Reproducibility seed for synthetic prices and the option simulation. |

A signal uses data through close *t* and executes at close *t + 1*. Existing positions receive the intervening return before the rebalance. Costs are charged using a self-financing equation against drifted holdings. The ledger records decision and execution dates, before/after equity, target and pre-trade weights, notional, fees and turnover. There is no assumed final liquidation. Uninvested cash earns zero.

The matched equal-weight benchmark uses the same calendar, lag, rebalance schedule and costs. Its cumulative return difference is measured in percentage points and is not risk-adjusted alpha. The separate cost scenario is a sensitivity check; it does not model liquidity or market impact.

## Read the report

The HTML file works offline, includes no scripts or external resources, and adapts to light/dark system preferences and printing. Values use supplied portfolio units; Atlas Quant does not assume a currency symbol. Missing data is labelled, rather than replaced with a zero.

- **Capital through time:** equity after modelled costs and the supplied cash series. Charts retain local extrema when reducing long series for display. The JSON preserves exact observations.
- **Risk in context:** annualised return and sample volatility, Sharpe ratio, historical value at risk and expected shortfall. The tail statistics are measured over the observed return sample at the displayed confidence level.
- **Drawdown:** the curves are non-positive and measure distance below each path's own running peak. A matched benchmark appears as a dashed line. The summary tile and comparison table display the maximum loss as a positive magnitude.
- **Closing allocation:** final asset weights. A target cap applies at rebalancing; final drifted weights can differ.
- **Allocation through time:** stacked observed asset and cash weights, reconciled against equity. The chart supports up to 12 assets and displays at most 700 evenly spaced observations; the JSON retains every observation. Missing or inconsistent holdings produce an explicit unavailable state.
- **Matched capital paths:** the strategy and benchmark share a scale. The chart requires complete positive equity, identical dates and matching initial capital. It does not silently align different samples.
- **Research council:** six deterministic role assessments, dissent, evidence references and review outcome. Expand the evidence ledger to inspect exact values and units.
- **Derivative laboratory:** a separate option-pricing comparison with input parameters, Greeks, Monte Carlo standard error and confidence interval. The plot uses a zoomed axis to make method differences visible. The interval describes simulation sampling uncertainty, conditional on the model and inputs.
- **Provenance:** dataset digest, configuration, council policy, gates, trace and hashes. These support reproducibility and detection of changes; they do not establish authorship or data truth.

Short samples can produce unstable annualised statistics. An attractive historical result may reflect chance, parameter tuning, asset selection or omitted costs. Keep an untouched evaluation period and examine whether the conclusion survives reasonable changes in assumptions.

The repository's [visual guide](VISUAL_GUIDE.md) provides six additional,
reproducible financial figures with CSV observations and a source manifest.
Regenerate them with `python scripts/build_visuals.py`, or check the committed
evidence with `python scripts/build_visuals.py --check`. These gallery figures
use a fixed minimum-variance experiment; the default CLI demo uses inverse
volatility. Both settings are explicit, so their numerical results need not match.

## Understand the council

The roles are data quality, performance, risk, costs, model critique and synthesis. They inspect explicit metrics using documented rules. A `research_only` outcome means the record can be considered for further research. It does not approve a trade. A `blocked_for_review` outcome identifies a failed or unsupported research gate.

External review text can be validated against the evidence record using the `review` command described in [AGENT_DESIGN.md](AGENT_DESIGN.md). It remains inert text. The toolkit does not give an external model permission to execute code, retrieve secrets, place orders or invent numeric evidence.

## Price a European option

```sh
atlas-quant options --spot 100 --strike 100 --maturity 1 --rate 0.05 --volatility 0.20 --dividend 0 --option call --seed 42
```

Time is measured in years. Rates and volatility use decimal fractions. The CLI compares Black–Scholes, a binomial tree and a seeded Monte Carlo estimator for a European option. The Python kernel also offers American exercise through its binomial function. See [MATHEMATICS.md](MATHEMATICS.md) for formula assumptions, boundary cases and Greek units. Monte Carlo intervals describe simulation sampling uncertainty conditional on the model, not uncertainty about whether the model describes markets.

## Check integrity and inspect exact outputs

```sh
atlas-quant verify output-demo/report.json
python -m unittest discover -s tests -v
```

`verify` checks the recorded content hashes. A person able to change the file can also recompute a hash. Integrity verification is not an author signature, an independent audit or financial validation. The HTML is a presentation of the accompanying JSON and is not cryptographically signed.

For Python integration:

```python
from atlas_quant.data import synthetic_prices
from atlas_quant.pipeline import analyse
from atlas_quant.report import generate_report

result = analyse(synthetic_prices(days=504, assets=4, seed=42))
html = generate_report(result)
```

`generate_report` accepts an in-memory mapping from trusted application code. Bound file or request sizes before parsing untrusted data. Rendering escapes narrative text and does not treat Markdown or HTML from a model as executable markup. Plotting supports at most 100,000 observations and absolute numeric magnitudes up to `1e100`; unsupported series are labelled instead of drawn.

## Troubleshooting

| Message or symptom | Next step |
|---|---|
| Output directory already exists | Choose a new `--output` directory to preserve the previous run. |
| Missing, duplicate or unsorted data | Correct the source CSV. The importer does not guess how to fill or reorder observations. |
| Infeasible `max_weight` | Use a cap of at least `1 / asset_count` or increase the eligible asset set. |
| Insufficient observations | Supply more history or choose a shorter, justified lookback. |
| Missing metric | Inspect the sample and JSON; a zero-volatility Sharpe ratio may be undefined. |
| Council blocked for review | Inspect gate explanations and evidence. A blocked result should not be interpreted as an approved strategy. |
| Integrity check fails | Recover the original report or rerun from known inputs; do not silently accept a changed evidence record. |

The current release is an alpha research toolkit. It contains no live brokerage connection and does not claim production trading readiness or demonstrated outperformance.
