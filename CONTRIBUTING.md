# Contributing

Atlas Quant welcomes reproducible numerical corrections, clearer explanations and targeted improvements to research workflows. Start with a small change that can be checked against an independent example. Use British English in prose.

## Development

Use Python 3.11 or newer in a virtual environment, install the project, then run:

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
python scripts/security_check.py
```

A pull request should identify the concrete problem, resulting behaviour, test evidence and remaining limitations. Numerical work should include an independent reference value, identity, convergence test or hand-calculated accounting example. State units and timing conventions. A test that merely reproduces the implementation is insufficient evidence.

## Research discipline

- Identify synthetic data prominently; never present a tutorial simulation as historical performance.
- Record data provenance, dates, transformations, seeds, transaction-cost assumptions and strategy settings.
- Preserve temporal separation between training, signal observation and execution. Test future-data perturbations when changing backtests.
- Keep unavailable results explicit. Do not substitute a plausible score or claim an optimisation succeeded when it did not.
- Separate empirical findings, model assumptions and forecasts. Never promise investment returns.
- Cite primary sources and inspect their actual contents. Do not copy textbooks, third-party datasets or code without verifying redistribution rights.

## Security and maintenance

No credentials, personal financial data, generated executable code or broker connectivity belong in ordinary contributions. Treat narratives and CSV files as untrusted. Preserve the offline boundary and HTML escaping. Follow [SECURITY.md](SECURITY.md) for private vulnerability reporting.

Changes to GitHub Actions must pin external actions to verified full commit SHAs, retain read-only permissions and avoid privileged pull-request triggers. The existing Atlas monitoring caller is a narrow exception: its exact path and pinned content are recognised by the policy checker for Actions retry access; it also carries issue-reporting permission. This exception does not extend to application or pull-request test workflows. Review dependency update proposals and rerun numerical tests. A green CI run is evidence for those checks at that commit, not a certification of security or predictive value.

## Visual evidence

Regenerate the committed figures with `python scripts/build_visuals.py` and check
them with `python scripts/build_visuals.py --check`. Use the documented fixed
synthetic seed and settings. Keep numerical data beside the SVGs, declare units
and sample windows, and retain unfavourable outcomes. Distinguish model sampling
uncertainty from future investment risk. Changes to a plot must preserve the
underlying financial meaning and accessible descriptions. See the
[visual guide](docs/VISUAL_GUIDE.md).
