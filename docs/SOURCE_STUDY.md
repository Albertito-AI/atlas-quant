# Source study and design decisions

Reviewed on 8 November 2026. This is a bounded source-code and methods review, with an independently written implementation. It is not an audit of every upstream file, a reading of every textbook, or evidence of investment performance.

## Frozen references

| Reference | Inspected revision | Nature and reuse decision |
| --- | --- | --- |
| [neohsiung/AI-Investment-Advisor](https://github.com/neohsiung/AI-Investment-Advisor/tree/990a16c12436e83d0e977f48d6a81485deb6f251) | `990a16c12436e83d0e977f48d6a81485deb6f251` | Application with Apache-2.0 licence and an upstream NOTICE crediting Litov and contributors. Selected source files, configuration and tests informed architecture. Atlas Quant code was independently written. |
| [PlamenStilyianov/FinMathematics](https://github.com/PlamenStilyianov/FinMathematics/tree/c9bffd9b7795790e1ed23361ad393579658d6bd5) | `c9bffd9b7795790e1ed23361ad393579658d6bd5` | Catalogue of books, Mathematica notebooks/packages and an installer. The recursive tree contains 104 blobs and 10 directory entries. No repository licence file was found. Catalogue topics informed the learning plan; its books, notebooks, code and binaries are not redistributed. |

The absence of a repository licence does not establish who owns each work or whether every upload was authorised. It gives this project no basis to apply its own licence to those materials. Follow the author and publisher links below for study material.

## What the application taught us

Links in this table resolve to the reviewed revision, so later upstream changes do not change the evidence.

| Observation from inspected source | Design consequence in Atlas Quant |
| --- | --- |
| The [README](https://github.com/neohsiung/AI-Investment-Advisor/blob/990a16c12436e83d0e977f48d6a81485deb6f251/README.md) distinguishes LLM proposals from deterministic decisions and expressly states that benchmark outperformance has not been shown. | Separate calculations, interpretation and research gates. Make no profit, alpha or suitability claim. |
| The actual [council configuration](https://github.com/neohsiung/AI-Investment-Advisor/blob/990a16c12436e83d0e977f48d6a81485deb6f251/config/workflows/single_ticker_council.yaml) has ten debate voices followed by CIO drafting, risk challenge, finalisation and verification. Repository metadata describing seven agents is insufficient to establish the active roster. | Specify the actual six research roles in code and reports. Role count does not establish independence or predictive accuracy. |
| [`CompositorService._fallback_score` and `_aggregate_scores`](https://github.com/neohsiung/AI-Investment-Advisor/blob/990a16c12436e83d0e977f48d6a81485deb6f251/src/services/confidence_compositor_service.py) exclude an explicit insufficient-data fallback and block execution when too little base weight remains. | Preserve missing evidence as missing. An unavailable result must never become a plausible invented observation. |
| The same compositor combines LLM scores and asks for some estimated financial fields. Those scores alone do not establish calibration or source accuracy. | Numeric evidence comes from the calculation layer. External reviews refer to existing evidence identifiers and cannot supply authoritative replacement numbers. |
| [`DynamicDebateTerminationService.compute_text_similarity`](https://github.com/neohsiung/AI-Investment-Advisor/blob/990a16c12436e83d0e977f48d6a81485deb6f251/src/services/dynamic_debate_termination_service.py) uses token-set Dice overlap. Its broader module description mentions other similarity measures. | Describe implemented behaviour precisely. Textual repetition or agreement does not verify a financial claim. Preserve objections and limitations. |
| [`PortfolioBacktestEngine.run`](https://github.com/neohsiung/AI-Investment-Advisor/blob/990a16c12436e83d0e977f48d6a81485deb6f251/src/services/portfolio_backtest_engine.py) gives the callback the whole OHLCV object, explicitly making callers responsible for avoiding future-data leakage. Signals can fill at that bar's close. | Restrict estimation to observed history and enforce a subsequent-close execution convention. Add future-perturbation and hand-calculated timing tests. |
| [`MultiAssetPortfolioBacktestEngine.run`](https://github.com/neohsiung/AI-Investment-Advisor/blob/990a16c12436e83d0e977f48d6a81485deb6f251/src/services/multi_asset_backtest_engine.py) unions dates; in the inspected mark-to-market loop, a missing held-asset price falls back to its entry price. | Require complete price rows on a shared calendar. Do not silently fill a missing valuation. |
| The upstream [metrics module](https://github.com/neohsiung/AI-Investment-Advisor/blob/990a16c12436e83d0e977f48d6a81485deb6f251/src/services/metrics_service.py) documents metric conventions and represents some undefined ratios with `None`. | State units, return frequency, risk-free conversion and undefined-ratio behaviour. Include initial wealth in drawdown and growth accounting. |
| The upstream [mission configuration](https://github.com/neohsiung/AI-Investment-Advisor/blob/990a16c12436e83d0e977f48d6a81485deb6f251/config/mission.yaml) centralises constraints and evidence gates. | Keep research policy explicit, serialisable and inspectable. Avoid burying policy in narrative prompts. |
| The upstream [backtest tests](https://github.com/neohsiung/AI-Investment-Advisor/blob/990a16c12436e83d0e977f48d6a81485deb6f251/tests/unit/services/test_portfolio_backtest_engine.py) check cash/fee arithmetic, and its [quantity invariant](https://github.com/neohsiung/AI-Investment-Advisor/blob/990a16c12436e83d0e977f48d6a81485deb6f251/tests/invariants/test_executor_quantity_fail_closed.py) prevents a silent order-size fallback. | Test conservation identities and rejected input, alongside expected output. A test inventory is useful evidence of intent; it is not proof that all paths are correct. |
| The upstream README describes real broker connectivity and a paper setting that does not provide a functioning simulation for its eToro token. | Provide an explicit, self-contained simulator. Atlas Quant contains no broker integration and cannot submit an order. |

These observations concern the named functions and revision. The upstream repository is much broader: market feeds, databases, portfolio operations, routing, monitoring and live execution are outside this project's implemented scope. Atlas Quant is an enhancement in reproducibility, bounded inputs and inspectable educational calculations; comprehensive superiority has not been established.

## Financial mathematics learning map

FinMathematics groups material on arbitrage, stochastic calculus, derivatives, numerical methods, Monte Carlo, volatility, dependence, optimisation and quantitative trading. That breadth is valuable as a topic map. A book title in a catalogue is not evidence that its contents were reviewed or a permission to republish them.

| Topic | Authoritative study route | Practical exercise here |
| --- | --- | --- |
| Self-financing portfolios and no-arbitrage | Nicolas Privault, [Discrete-Time Market Model](https://personal.ntu.edu.sg/nprivault/MA5182/discrete-time-model.pdf), especially sections 2.2 and 2.6 | Reconcile the cash/holdings ledger and inspect the lag between signal and execution. |
| Binomial replication and exercise | Privault, [Pricing and Hedging in Discrete Time](https://personal.ntu.edu.sg/nprivault/MA5182/pricing-hedging-discrete-time.pdf) | Compare a European binomial value with the analytic price, then inspect the American exercise premium. |
| Continuous-time valuation | Privault, [Black-Scholes Pricing and Hedging](https://personal.ntu.edu.sg/nprivault/MA5182/black-scholes-pde.pdf) | Verify put-call parity, zero-volatility limits and finite-difference Greeks. |
| Monte Carlo and variance reduction | Boyle, Broadie and Glasserman, [Monte Carlo Methods for Security Pricing](https://business.columbia.edu/faculty/research/monte-carlo-methods-security-pricing), *Journal of Economic Dynamics and Control* 21 (1997), 1267–1321 | Reproduce an antithetic estimate and compute its standard error from independent pair averages. |
| Portfolio variance | Harry Markowitz, [Portfolio Selection](https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.1952.tb01525.x), *Journal of Finance* 7(1) (1952), 77–91 | Solve a capped long-only variance problem and check the analytic two-asset case. |
| Tail risk | Privault, [Expected Shortfall](https://personal.ntu.edu.sg/nprivault/MH8331/expected_shortfall.pdf); Rockafellar and Uryasev, [Optimization of Conditional Value-at-Risk](https://sites.math.washington.edu/~rtr/papers/rtr179-CVaR1.pdf) | Compute an empirical quantile and a fractional tail average by hand. |
| Research selection bias | Bailey, Borwein, López de Prado and Zhu, [The Probability of Backtest Overfitting](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf) | Freeze a strategy specification before evaluation; keep a record of unsuccessful trials as well as successes. |

The linked teaching chapters are hosted by their author at Nanyang Technological University. Bibliographic links and relevant sections were checked during development. The project does not bundle the linked works. Some linked resources may be revised or subject to access restrictions.

## Evidence limits and next research work

Current calculations assume a shared observation frequency, adjusted closes supplied by the user, one currency, fractional positions and proportional transaction costs. They do not establish the correctness of vendor adjustments, absence of survivorship bias, actual tradability at a close, tax treatment, liquidity or market impact. A reproducible synthetic example demonstrates mechanics only.

Further development should prioritise independent reference-engine comparisons, dated real-data provenance, corporate-action fixtures, explicit benchmark alignment, multiple-testing controls, stress scenarios and external review. Regime models, stochastic volatility, extreme-value extrapolation and automatic strategy search need separate validation before being added. More model names or more debate rounds are not a substitute for that work.
