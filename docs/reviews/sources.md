# Source and methods review: twenty completed passes

Reviewer role: source provenance, mathematical documentation and evidence discipline. Date: 8 November 2026. These are twenty substantive work passes performed by one development agent, with findings communicated to the other agents. They are not twenty independent reviewers or twenty complete readings of the repositories.

| Pass | Evidence examined or action performed | Finding and resulting decision |
| --- | --- | --- |
| 01 | Read AI-Investment-Advisor README at `990a16c12436e83d0e977f48d6a81485deb6f251`; inspected actual source paths | Fixed the revision and bounded the study to selected code/configuration/test paths. The README itself says benchmark outperformance is unproven. |
| 02 | Read upstream LICENSE and NOTICE | Recorded Apache-2.0 and the upstream attribution. Kept implementation independent; wrote Atlas Quant's own provenance NOTICE. |
| 03 | Fetched the complete FinMathematics recursive tree at `c9bffd9b7795790e1ed23361ad393579658d6bd5` | Counted 104 blobs and 10 directories. Confirmed catalogue nature, duplicated PC/UNIX notebooks and installer. No licence file appeared. Excluded these materials from distribution and made no full-book reading claim. |
| 04 | Read `config/workflows/single_ticker_council.yaml` | Found ten debate voices plus later synthesis/challenge stages. Corrected reliance on seven-agent repository metadata in the study; informed the parent and council agent. |
| 05 | Read compositor fallback and aggregation functions | Credited its explicit insufficient-evidence fallback. Distinguished score aggregation from calibrated confidence or independently sourced facts. Sent the lesson to the council agent. |
| 06 | Read debate termination tokenisation and similarity functions | Observed token-set Dice overlap, despite broader module language. Documented the difference between lexical stability and factual correctness. |
| 07 | Read single-asset backtest signal/fill sequence | Full history reaches callbacks and same-close fills are possible. Informed the backtest agent; specified enforced time separation and future perturbation checks for Atlas Quant. |
| 08 | Read multiasset date alignment and valuation loop | Found union-of-dates alignment and an entry-price fallback for missing current marks. Required explicit common-calendar complete rows in the new design. |
| 09 | Read upstream metrics definitions | Recorded sample-volatility, growth, undefined-ratio and initial-baseline conventions. Specified exact conventions in MATHEMATICS.md. |
| 10 | Read mission configuration and security policy | Identified explicit constraints and evidence gates as useful architecture. Kept new software scope offline and documented no live-order path. |
| 11 | Read upstream backtest arithmetic tests and executor quantity invariant | Recognised positive evidence of accounting and fail-closed intent without claiming the upstream suite was run. Used identities and rejection cases in the validation guide. |
| 12 | Opened Privault's author-hosted Black-Scholes chapter and teaching index | Verified academic provenance and selected options/Greek learning routes. Wrote original model assumptions and formulas with links. |
| 13 | Verified Boyle, Broadie and Glasserman 1997 through Columbia and publisher records | Confirmed citation and variance-reduction subject. Documented independent antithetic-pair standard error and simulation-only uncertainty. |
| 14 | Opened Markowitz's publisher record and official SciPy SLSQP documentation | Verified the bibliographic anchor and solver result semantics. Required explicit feasibility and solver-success checks in the documentation. |
| 15 | Opened Privault's expected-shortfall chapter, Rockafellar/Uryasev author-hosted paper and Basel MAR33 | Separated empirical fractional-tail research risk from regulatory capital requirements. Wrote a hand-calculated discrete-tail example. |
| 16 | Located Bailey and colleagues' paper at the author's website and its institutional record | Documented strategy-selection and repeated-testing limitations. Avoided claiming that walk-forward timing eliminates overfitting. |
| 17 | Read the newly implemented quant, backtest, data and council APIs | Matched drawdown sign, effective risk-free conversion, per-unit Greeks, next-close timing and constrained external-review schema. Added fixed covariance shrinkage and inverse-volatility qualifications. |
| 18 | Checked authored Markdown local links, source paths, punctuation and distribution contents | Local `reviews/` reference resolves; all source links use the frozen revision; no bundled PDF, DJVU, Mathematica notebook/package or executable was present. Authored documents contain no em dash. External academic URLs were inspected through search/open; some publisher pages restrict automated access. |
| 19 | Ran `PYTHONPATH=src python -m unittest discover -s tests -v` on the assembled local tree | 125 tests passed in 0.493 seconds in that snapshot, using Python 3.12.14, NumPy 2.3.5 and SciPy 1.17.0. This is a point-in-time local result, not a claim about later commits or remote CI. |
| 20 | Reviewed the final SOURCE_STUDY, MATHEMATICS, VALIDATION and NOTICE claims against inspected code and sources | Preserved bounded claims: original research toolkit, catalogue study, partial upstream inspection, no proven alpha, no independent certification, and a stated external-validation agenda. |

## Deliverables

- [Source study](../SOURCE_STUDY.md) links inspected upstream files at their exact revision and maps lessons to new design decisions.
- [Mathematical conventions](../MATHEMATICS.md) specifies formulas, units, edge cases and model assumptions.
- [Validation guide](../VALIDATION.md) separates reproducible implementation evidence from empirical investment claims.
- [NOTICE](../../NOTICE) records inspiration, attribution, reuse boundaries and AI assistance.

## Remaining uncertainty

This review did not independently run the upstream application, validate its live-account behaviour, read every FinMathematics book, or establish the ownership of each catalogue item. It did not run a production reference-engine comparison or an independent security audit. The software's checks and source study provide an inspectable foundation for those later tasks.
