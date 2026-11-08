# Atlas Quant

**Financial research you can inspect, reproduce and challenge.**

For educators and research teams: [explore the workshop and team pilot](docs/WORKSHOP_OFFERS.md) or [email Albert](mailto:travelingbert@gmail.com?subject=Atlas%20Quant%20enquiry).

Atlas Quant combines financial mathematics, portfolio experiments and a structured
research council in a small, offline Python package. A single command produces
an accessible HTML report and a machine-readable evidence record. The demo needs
no API key, cloud account, database or paid service.

Version **0.1.0** is a research release. It has no broker adapter and makes no claim
of investment suitability, predictive accuracy or excess returns. The council's
six roles are deterministic analytical rules. Optional external reviews select
validated critique templates; this release does not call language models.

## Run it

Requires Python 3.11 or newer. Install from this source checkout:

```bash
python -m venv .venv
# Linux/macOS:
source .venv/bin/activate
# Windows PowerShell instead: .venv\Scripts\Activate.ps1
python -m pip install .
atlas-quant demo --output output/demo
atlas-quant verify output/demo/report.json
```

Open `output/demo/report.html` in your browser. The report is self-contained and
uses no remote assets or JavaScript. `--output` must name a new directory so
earlier experiments are preserved. Installation downloads NumPy and SciPy;
analysis runs locally after installation.
To reproduce the locally tested runtime versions, install with
`python -m pip install -c requirements-tested.txt .`.

### Bring your own prices

```csv
date,EQUITY,BONDS
2025-01-02,100.0,100.0
2025-01-03,101.0,99.8
2025-01-06,100.5,100.1
```

Use at least `lookback + 3` rows of adjusted closing prices in one currency.
The tiny example above shows the format only. Supply your own properly licensed
data with a shared calendar and no missing cells.

```bash
atlas-quant backtest prices.csv --strategy minimum_variance \
  --lookback 60 --rebalance-every 21 --cost-bps 10 \
  --max-weight 0.50 --periods-per-year 252 --output output/experiment-01
```

The weight cap must be feasible for the number of assets. Dates must increase
strictly; duplicates, nonpositive prices, nonfinite values and malformed rows
are rejected. The software cannot verify whether an input is correctly adjusted,
survivorship-free or denominated in a common currency. Set the annualisation
frequency to match your observations. CSV loading never silently fills gaps.

### Compare pricing methods

```bash
atlas-quant options --spot 100 --strike 100 --maturity 1 \
  --rate 0.05 --volatility 0.20 --option call
```

This compares Black–Scholes, a binomial tree and seeded antithetic Monte Carlo
for the same European payoff. Rates and yields are continuously compounded;
volatility is annualised; maturity is in years. The Python API also supports
American exercise in the tree. Model assumptions and edge cases are documented
in [Mathematics](docs/MATHEMATICS.md).

## What is included

| Component | Implemented behaviour |
|---|---|
| Price ingestion | Bounded CSV parsing, strict validation, date/asset ordering and a dataset content hash |
| Portfolio research | Equal weight, capped inverse volatility, and capped minimum variance with fixed diagonal shrinkage |
| Execution accounting | Signals at close t execute at close t+1; held assets receive returns before rebalance; fees solve a self-financing equation |
| Comparison | Equal-weight baseline on the same dates with the same lag and costs, plus a doubled-cost sensitivity scenario |
| Risk | Initial-wealth-aware drawdown, sample volatility, Sharpe, empirical value at risk and fractional-tail expected shortfall |
| Derivatives | Dividend-aware Black–Scholes, analytic Greeks, European/American trees, Monte Carlo and sampling intervals |
| Research council | Six transparent roles, traceable numeric evidence, dissent and non-overridable data/risk gates |
| External reviews | Size-bounded JSON, fixed critique codes, role and citation validation; no arbitrary prose, tools or execution |
| Reports | Responsive offline HTML with charts, holdings, risk, costs, assumptions and evidence; JSON content-integrity checks |
| Engineering | Numerical identity tests, hand-calculated accounting, future-data perturbation tests, adversarial input tests and clean-wheel checks |

The content hash detects accidental or uncoordinated edits. Anyone with the
content can recompute it; it is neither an author signature nor proof that the
underlying data are true.

## How the source projects informed this work

The requested study covered
[AI-Investment-Advisor](https://github.com/neohsiung/AI-Investment-Advisor) and
[FinMathematics](https://github.com/PlamenStilyianov/FinMathematics).

| Lesson | Atlas Quant design |
|---|---|
| Separate agent proposals from deterministic decisions | Calculations create the evidence; council roles and external reviews cannot place trades or change values |
| Make missing evidence visible | Undefined statistics remain missing; missing evidence and risk breaches trigger explicit gates |
| Prevent research shortcuts | Built-in strategies receive past returns only; execution lag and fee accounting are enforced in the simulator |
| Connect theory to executable checks | Pricing identities, finite-difference Greeks, tree convergence and an independent cash ledger anchor the test suite |
| Keep deployment understandable | Offline package and report, without broker keys, database services or a scheduler |
| Respect source provenance | Original implementation; no books, solution manuals or Mathematica code redistributed |

These are targeted design improvements for reproducible research. Atlas Quant
does not match the upstream platform's live trading, live market feeds, news
retrieval, distributed operations or provider integrations. It has not been
independently audited or benchmarked as superior to those systems.

See the [pinned source study](docs/SOURCE_STUDY.md) for inspected paths, findings,
licence observations and limits of the study. [NOTICE](NOTICE) records attribution.

## Development and evidence

```bash
python -m pip install .
python -m unittest discover -s tests -v
python scripts/security_check.py
python -m pip install build
python -m build
```

The six development agents each recorded 20 numbered study, construction and
review passes, including challenges and corrections, in
[the review directory](docs/reviews). These are development records from six
concurrent agents, not 120 independently deployed agents or 120 external audits.
The development agents are separate from the product's six rule-based council roles.

The repository includes a Python 3.11–3.13 GitHub Actions workflow and dependency
audit. A committed workflow is not evidence that a remote CI run passed. Consult
[Validation](docs/VALIDATION.md) and [the release verification record](docs/RELEASE_CHECKS.md)
for the observed checks and limitations.

## Training and implementation

[Explore the workshop and research-workflow pilot](docs/WORKSHOP_OFFERS.md).
The workshop includes a [reproducible synthetic case](docs/WORKSHOP_CASE.md).

## Further reading

- [User guide](docs/USER_GUIDE.md)
- [Reproducible workshop case](docs/WORKSHOP_CASE.md)
- [Mathematical conventions and sources](docs/MATHEMATICS.md)
- [Council architecture and external review schema](docs/AGENT_DESIGN.md)
- [Threat model and reporting vulnerabilities](SECURITY.md)
- [Contributing](CONTRIBUTING.md)
- [Roadmap](docs/ROADMAP.md)

MIT licensed original code, copyright 2026 Albert Tan Sin Hon.

