# Research roadmap

This file distinguishes proposed work from implemented capability.

| Priority | Proposed extension | Acceptance evidence needed |
|---|---|---|
| 1 | Independent numerical audit | Comparisons with a separately implemented reference library, across random and boundary cases |
| 1 | Broader market-data evaluation | Licensed point-in-time datasets, delistings, explicit corporate actions, missing-data policy and calendar checks |
| 1 | Multiple-testing controls | Predeclared strategy selection, nested temporal validation, disclosure of every tested configuration |
| 2 | Confidence estimation for portfolio results | Dependence-aware bootstrap, interval calibration and sensitivity to block length |
| 2 | Better trading frictions | Liquidity constraints, spread/impact models and partial fills checked against execution data |
| 2 | Optional model providers | Explicit user budgets and network consent, bounded inference, evaluated factuality and failure modes |
| 3 | Live read-only feeds | Source licensing, timestamps, cache provenance and stale-feed rejection |

Broker execution is outside version 0.1.0. Any future execution component needs
separate scope, credentials, operational controls and human authorisation.
No roadmap entry is a promise of profitability, a certified safety claim or a
claim that the feature already exists.

