# Validation guide and evidence boundaries

Atlas Quant's tests are designed to challenge arithmetic, timing and rejected input. Passing them does not establish investment performance, complete security or regulatory compliance. The evidence applies to the tested revision and environment.

## Reproduce the checks

From the repository root, after installing the package dependencies:

```bash
python -m unittest discover -s tests -v
python scripts/security_check.py
python scripts/build_visuals.py --check
```

See the repository's CI configuration for the supported Python matrix and packaging checks. A committed workflow describes intended checks. Only a completed successful run establishes that they ran on GitHub.

## Acceptance arguments

| Property | Independent check to inspect | What it establishes |
| --- | --- | --- |
| Option prices | Known Black-Scholes value; put-call parity; expiry/zero-volatility limits | Agreement with a standard model and its identities for the fixtures |
| Sensitivities | Central finite differences with explicit rate/volatility units | Local consistency of analytic Greeks |
| Tree convergence | Binomial European prices approach the analytic model; American value is at least its European counterpart | Expected numerical behaviour on the selected cases |
| Monte Carlo error | Independently reconstruct antithetic pair averages and their standard error | Correct treatment of dependence in the estimator |
| Portfolio optimisation | Analytic independent two-asset solution; cap feasibility; invalid covariance rejection | Correct constrained solution and error handling for the fixtures |
| Tail loss | Small manually ordered sample with fractional tail mass and ties | Correct declared quantile/expected-shortfall convention |
| Wealth accounting | Hand-calculated one- and two-asset paths including fees | Cost funding and self-financing identities |
| Information timing | Perturb future prices while comparing earlier allocations and outcomes | No future effect in the tested strategy path before its information becomes available |
| Data ingestion | Unsorted/duplicate dates, missing cells, non-finite/non-positive prices and bounded input | Enforcement of the local data contract |
| Research evidence | Unknown citation, fabricated numeric input, altered hash and missing metric cases | Enforcement of structural evidence restrictions |
| Report output | Hostile text and markup fixtures; content security policy inspection | Escaping and browser restrictions exercised by those fixtures |
| Visual comparisons | Mismatched calendar/capital fixtures and reconciled cash/holdings | Prevents drawing a falsely aligned benchmark or fabricated allocation |
| Pricing intervals | Missing/non-finite estimates, reversed intervals and invalid confidence levels | Unsupported numerical evidence remains visibly unavailable |
| Committed gallery | Recomputed numerical evidence, saved-price digest, source/asset hashes and exact rendering checks | The checked figures correspond to recorded inputs and executable calculations within declared tolerances |

Tests should be read alongside their implementation. Numerical tolerances are part of the specification. Broad tolerances can conceal an error; excessively narrow tolerances can become platform-dependent. Randomised tests use fixed seeds, while algebraic and hand-calculated cases provide nonrandom anchors.

## Research controls still needed for empirical claims

The included synthetic series demonstrates a reproducible pipeline. It cannot support a claim that a strategy earns money. A real-data experiment should record vendor/licence, retrieval time, adjustment convention, currency, universe construction, delistings, missing sessions and the exact evaluation period. Validate benchmark alignment and cost sensitivity before comparison. Preserve failed strategies and all attempted parameter variants; selecting a winner after many trials changes the evidential meaning of its score.

No reference production engine, independent financial audit, penetration test, market-impact calibration or broker reconciliation has been completed as part of this first version. The package deliberately offers no live order path. Performance and security claims must remain within the evidence actually obtained.

## Review record

The six files in [reviews](reviews/) record the development agents' work. Each agent was asked to conduct twenty substantive passes across study, implementation, testing and revision. A pass is an evidenced work item, not a separate model process, a statistically independent vote or certification. The records describe completed work and findings; they must not be used to infer measured predictive accuracy.
