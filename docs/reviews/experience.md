# Experience and reporting: 20 review rounds

Reviewer: experience agent, one of six development agents. Date: 8 November 2026.

These are 20 scoped, substantive study, implementation and verification rounds by this agent. They are not 20 separately spawned agents and are not evidence of 20 independent external audits. Several rounds resulted in the same test suite being extended and rerun. The final report module is original work.

## Source examined

`neohsiung/AI-Investment-Advisor` at `990a16c12436e83d0e977f48d6a81485deb6f251`, specifically:

- `src/api/v1/schemas/dashboard_schemas.py`
- `src/services/reporting_service.py`
- `frontend/src/app/performance/page.tsx`
- `frontend/src/app/backtest/page.tsx`
- `frontend/src/components/dashboard/NetAlphaCard.tsx`

The source informed the selection of portfolio, cost, data-quality and review panels. No implementation, stylesheet or asset was copied. The unlicensed FinMathematics collection was not used as a source of visual assets or text.

| Round | Work and finding | Result or verification |
|---|---|---|
| 1 | Inspected upstream report and dashboard file inventory. | Identified the separation between overview metrics, historical equity, agent review and cost attribution as a useful presentation structure. |
| 2 | Read dashboard schema and performance component. | Identified a need to preserve missing-data semantics rather than displaying absent values as zero. Added explicit empty states and origin-unknown labelling. |
| 3 | Read upstream HTML reporting service. | Observed Markdown-to-HTML conversion and raw string interpolation as unsuitable boundaries for untrusted narrative text in our renderer. Chose escaped plain text throughout. |
| 4 | Read backtest view and net-alpha component. | Carried forward the useful distinction between portfolio return, costs and evidence reliability. Avoided adopting performance targets or implying that a cumulative return difference is alpha. |
| 5 | Designed a script-free report contract with root and the backtest/council agents. | Fixed the public API as `generate_report(data) -> str`, with `render_report` alias and graceful absent sections. |
| 6 | Built visual hierarchy, type scale, colour variables, cards and responsive grids. | Implemented light/dark preferences, print styles and small-screen breakpoints without external fonts, scripts or assets. Structural test checks required responsive rules. |
| 7 | Implemented safe text, number and mapping/sequence helpers. | Malicious title, dates, source, symbol, narrative, evidence and option input are escaped. The HTML parser test finds no injected script/image/event-handler elements. |
| 8 | Added a restrictive Content Security Policy and exact stylesheet hash. | Test recomputes SHA-256 from the rendered stylesheet and verifies the policy. No `unsafe-inline`, inline style attributes or remote resource elements are emitted. |
| 9 | Built equity/cash SVG plots with numeric-only coordinates, titles, descriptions and labelled axes. | Tests cover complete data, a single observation and constant data; invalid primary series are labelled rather than silently filtered. |
| 10 | Added drawdown and closing holdings with a common missing-data policy. | Summary/table drawdown shows positive loss magnitude; chart stays non-positive. Asset names are escaped and weights use decimal fractions formatted as percentages. |
| 11 | Designed bounded plot reduction for long samples. | A 10,000-point oscillating series test confirms SVG point counts are bounded while retaining endpoints and bucket extrema. Original values remain in JSON. |
| 12 | Implemented risk metrics with explicit units and confidence level. | Tests confirm ordinary fractions format correctly and nonfinite/boolean metrics are not displayed as valid numbers. No currency is inferred. |
| 13 | Integrated actual `BacktestResult.to_dict()` schema supplied by the backtest agent. | Adapted nested dataset/config, equity/cash curves, final weights, transaction cost totals and assumptions. Read the real root-generated JSON to verify fields. |
| 14 | Integrated council roles, evidence references, dissent, gates and audit trace. | Six-role test confirms all six cards, deterministic mode, evidence ledger and provenance appear. Outcomes are translated into readable labels without implying trade approval. |
| 15 | Added the separate derivative comparison panel and expandable inputs/uncertainty. | Prices use per-underlying-unit wording. Missing binomial output remains visibly unavailable; recorded status remains in expanded detail. |
| 16 | Responded to security-agent adversarial review of extreme numeric inputs. | Added a chart magnitude limit to prevent nonfinite SVG coordinates and guarded percentage overflow. Tests cover values of `1e308`. The API documents trusted in-memory callers and ingress-size responsibility. |
| 17 | Added matched benchmark and cost-sensitivity comparison. | Regression test checks percentage-point wording, 20-basis-point scenario label and explicit distinction from risk-adjusted alpha. Exact recorded costs are used. |
| 18 | Wrote and checked the user guide against current CLI, data and backtest source. | Documented executable commands, file format, cap feasibility, lag, per-side costs, drift, no liquidation, annualisation, council limits and integrity scope. |
| 19 | Attempted desktop/mobile visual verification using Playwright. | Bundled Chromium was absent; the download response was unusable. System Chromium then failed with `socket() ... Operation not permitted`. No screenshot or visual pass is claimed from this attempt. Structural accessibility checks pass, but browser visual verification was unavailable to this agent. |
| 20 | Generated HTML from the real integrated root report and reran presentation tests. | The integrated file contains six role cards, both comparison sections and no script elements. Final command: `PYTHONPATH=src python -m unittest discover -s tests -p 'test_report.py' -v`; 21 tests passed. |

## Boundaries and remaining limitations

The renderer is an offline presentation layer, not a financial validation engine. Its HTML escaping and restrictive policy reduce executable-content risk, but do not establish the truth of supplied narrative or figures. In-memory callers must enforce data-ingress limits before parsing untrusted payloads. Long plots are reduced for presentation, while exact observations remain in the accompanying JSON. Automated structural accessibility tests do not establish complete assistive-technology compatibility. Browser-level visual verification was blocked in this agent's execution environment; the integration owner may perform that check separately.
