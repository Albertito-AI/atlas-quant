# Version 0.1.0 release checks

Observed on 8 November 2026. This record concerns the local release candidate.

| Check | Observed result |
|---|---|
| Runtime | CPython 3.12.14, NumPy 2.3.5, SciPy 1.17.0, Linux |
| Integrated unittest suite | 145 tests passed |
| Statement coverage | 1,156 statements, 56 unexecuted, 95% rounded coverage; coverage is not proof of correctness |
| Repository policy | Zero findings from the deliberately limited local checker |
| Dependency advisory check | pip-audit 2.10.1 reported no known vulnerabilities for NumPy 2.3.5 and SciPy 1.17.0; other tools and unknown vulnerabilities are outside this result |
| Packaging | Source distribution and wheel built with isolated setuptools 84.2.1 build environment |
| Installed package | Fresh virtual environment outside the checkout: demo, JSON verification, 145 tests and pip dependency consistency check passed |
| Reproducibility | Source and installed-wheel default demo produced the same JSON content digest |
| Review records | Six development agents, each with 20 documented work passes; 120 recorded passes in total |
| Presentation | Escaping, Content Security Policy, accessibility structure and numeric formatting tests passed; first printed page visually inspected with WeasyPrint and corrected for numeric wrapping |
| Browser visual check | Unavailable: Chromium could not launch under the runtime's socket restriction. Responsive CSS has structural checks, not a completed browser rendering review |
| GitHub publication and CI | At the time of these checks, publication and remote CI were pending. Consult GitHub Actions for current run results. |

Default demo content SHA-256:

```text
29e3e3c5a7b3d963e01e03b2e0ec5514cb018abf0175c0917560c2779d9bc61d
```

The demo uses synthetic prices and is retained even though its default portfolio
loses value. There is no selection of a favourable seed to imply profitability.
The hash identifies content under the recorded numeric environment. It is not a
cryptographic signature and does not validate the economic assumptions.

Final integration corrections included retaining analytic/Monte Carlo prices
when a 400-step tree is inadmissible, checking council consistency with the
backtest evidence, aligning the cost-fraction definition, and preventing report
output from overwriting an existing experiment directory.

## Reproduce

```bash
python -m pip install -c requirements-tested.txt .
python -m unittest discover -s tests -v
python scripts/security_check.py
atlas-quant demo --output output/release-check
atlas-quant verify output/release-check/report.json
```

Further evidence is required before claiming robust empirical performance,
complete security, browser accessibility conformance, independent validation or
production readiness. Python 3.11 and 3.13 are in the CI matrix but were not
executed locally.

