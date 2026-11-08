# Backtest and data engineering: 20-round work record

This record describes twenty development and review rounds performed by the backtest agent. A round is a substantive investigation, implementation or check, not a claim that a new agent process was launched. Original implementation; no upstream source was copied.

## Round 1: inspect the upstream data and execution boundary
Read `AI-Investment-Advisor/src/services/portfolio_backtest_engine.py` and `multi_asset_backtest_engine.py` at upstream revision `990a16c12436e83d0e977f48d6a81485deb6f251`. The former gives the signal callback the whole history and relies on callers to avoid look-ahead; signals execute at that bar's close. Its position sizing first removes the fee then charges another fee against the resulting quantity. These observations motivate explicit temporal separation and a self-financing fee equation. This is a local code-path assessment, not an assessment of every upstream strategy.

## Round 2: inspect upstream safeguards and benchmarking
Read `src/domain/portfolio_guard.py` and `scripts/backtest_forecast.py`. Report-text percentage rewriting cannot enforce a numerical portfolio constraint. The forecast script's comparison with a random-walk baseline is a useful methodological lesson. Our weights are constrained in numerical space, and our research strategies remain simple, inspectable baselines.

## Round 3: agree module contracts
Coordinated with the quantitative agent on `minimum_variance`, `performance_metrics` and `historical_risk`; sent the root agent the `PriceDataset`, CSV, synthetic-data and `run_backtest` signatures. Chose NumPy/SciPy plus the standard library. The data layer will reject partial calendars instead of filling missing prices.

## Round 4: define the event clock and cash equation
A decision formed at close t executes at close t+1. Existing holdings earn that interval's return; new holdings earn only later returns. Execution costs solve U + c sum(abs(w U - H)) = V, with post-cost wealth U, pre-trade marked holdings H, pre-trade wealth V and per-side proportional cost c. This charges actual buy and sell notionals and leaves a fully funded portfolio. Evaluation begins at the first decision date and includes the first cost interval. No final liquidation is assumed.

## Round 5: implement strict shared-calendar input
Implemented canonical ISO dates, strict chronological uniqueness, safe unique asset identifiers, a positive finite rectangular price matrix, no missing fill, and caller-visible currency/adjustment assumptions. Data is copied on construction and marked read-only. File input is bounded before parsing.

## Round 6: implement deterministic research fixtures
Added labelled correlated lognormal synthetic prices with a fixed calendar, explicit seed and content SHA-256. Synthetic tickers begin `SYNTH_`. The generator contains no historical-market claims and no external requests.

## Round 7: adversarial CSV test pass
Ran `PYTHONPATH=atlas-quant/src python -m unittest discover -s atlas-quant/tests -p test_data.py -v`: 12 tests passed. Cases include missing/extra cells, NaN/infinity/zero/negative prices, formula strings, duplicate/reversed/noncanonical dates, duplicate symbols, blank rows, row/asset limits and copying/read-only behaviour.

## Round 8: audit reproducibility and input bounds
The data suite confirms identical seeds produce identical arrays and digests; seed, dates and symbol changes affect the digest. Empty/header-only files fail. `max_rows` and `max_assets` allow only tighter bounds. A source label records only the filename rather than exposing an absolute local path.

## Round 9: implement the execution and cost engine
Implemented three numerical strategies, decision and execution dates in every trade row, trailing-window-only strategy inputs, drifted holdings, explicit cash, transaction costs, portfolio paths and serialisable results. Numerical position caps act at rebalances; holdings can drift between them.

## Round 10: verify self-financing against independent arithmetic
The one-asset fixture begins with 1,000 currency units and a 1% cost. Invested value is exactly 1,000 / 1.01, then grows by 10%. A separate two-asset fixture doubles one price and expects pre-rebalance weights 2/3 and 1/3, traded notional 500 and gross turnover 1/3. These checks passed.

## Round 11: attack temporal leakage
A doubling during the execution interval does not earn a return on the pending first purchase. Changing all prices after a cutoff leaves earlier equity and trade records identical. Changing the execution-day prices leaves the earlier chosen target weights identical. All three chronology checks passed.

## Round 12: review degenerate covariance and volatility
Zero-volatility assets receive an explicitly defined inverse-volatility policy. Capped redistribution is tested with a zero-volatility asset, and all-zero matrices are exercised across all three strategies. Equal cap 1/n gives equal weights. Infeasible caps fail.

## Round 13: integrate the independent quantitative module
Ran all strategies against the quantitative agent's minimum-variance optimiser and metric functions. Cap, nonnegative weight, strict JSON and dimension checks passed. The initial-entry loss is included in drawdown; an unchanged-price fixture with 1% entry cost has maximum drawdown 1/101.

## Round 14: check calendars and endpoint conventions
A seven-observation rebalance schedule produces exactly the expected decision/execution date pairs. The final equity remains invested and marked to market, with no implicit free liquidation. Result dates begin at the first decision; warm-up observations are excluded from performance metrics.

## Round 15: reject invalid operational parameters
The first full backtest run passed 13 tests, covering malformed histories, unknown strategies, negative or nonfinite costs, nonpositive capital, infeasible weights and oversized price ratios. Combined with the data tests, the initial component suite passed 25 tests.

## Round 16: stress the interaction of fees, seeds and weight caps
Added a 36-run grid: six seeds, three strategies and two cost rates. It verifies finite paths, valid capped targets, strict JSON, cost-fraction accounting and that higher proportional costs reduce final wealth for otherwise identical signals. The expanded 15-test backtest suite passed.

## Round 17: incorporate independent agent review
The research agent found that the public `strategy_weights` helper accepted a boolean cap and raised a TypeError for a string cap; both now fail with a controlled ValueError. Complex scalars are rejected. The security agent identified that a wrong-shaped ndarray could be copied before dimension rejection; shape is now checked before the numeric copy. The quant agent independently reviewed lagged execution and self-financing costs without finding an accounting defect.

## Round 18: align reporting and provenance contracts
Added `total_cost_fraction = sum(transaction_cost / pretrade_equity)` with an unambiguous meaning for the research council. Communicated the monetary cost and gross-turnover units to the report agent. Reviewed council source-label validation and aligned control-character rejection in `PriceDataset`. Data and council both permit 500-character source labels. Added byte-limit, UTF-8, provenance and invalid-symbol-type regressions.

## Round 19: examine edge dimensions and declared omissions
Added the single-asset case for all three strategies, including scalar covariance. Reviewed and retained explicit assumptions for fractional shares, common-currency adjusted closes, unverified adjustment quality, perfect liquidity, omitted tax/impact/financing, no final liquidation, potential survivorship bias and weight drift. These are operational limitations, not purportedly solved features. Synthetic weekdays are a teaching calendar, not an exchange calendar.

## Round 20: final integrated regression check
Ran `PYTHONPATH=atlas-quant/src python -m unittest discover -s atlas-quant/tests -v` after the review fixes: **141 tests passed** at this checkpoint, including **30 owned data/backtest tests** (14 data, 16 backtest). The integrated suite also exercised command-line CSV ingestion, reproducible research bundles, baseline calendars, cost sensitivity, strict serialisation and rendering. This count is a dated development checkpoint and may increase as other agents finish. No performance superiority or live-trading readiness is inferred from these checks.
