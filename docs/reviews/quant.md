# Quantitative methods: twenty development and review rounds

Agent: `quant`. Date: 8 November 2026. Scope: original numerical primitives in
`src/atlas_quant/quant.py` and independent checks in `tests/test_quant.py`.
These are twenty substantive work rounds by one agent, not twenty independently
spawned agents. They record inspection and implementation actually performed.

| Round | Work performed | Evidence and resulting decision |
|---|---|---|
| 01 | Inspected upstream numerical-risk design | Read `src/services/risk_parity_cvar_service.py` in the pinned AI-Investment-Advisor checkout, including covariance construction and risk definitions. Preserve explicit risk metrics; reject missing values rather than filling them with zero. |
| 02 | Inspected upstream derivative calculations | Read `src/services/option_gamma_exposure_gex_service.py`, including gamma conventions and missing-chain signalling. Implement a general dividend-aware pricing kernel rather than inferring dealer positions from open interest. |
| 03 | Established mathematical sources | Consulted the NTU Black–Scholes and expected-shortfall chapters, the derivative-securities Monte Carlo/tree chapters, the Geweke variance-reduction paper and official SciPy SLSQP documentation listed below. No source code or book files were copied. |
| 04 | Agreed interfaces with backtest agent | Sent exact signatures, dictionary keys, sign conventions and `None` conventions. Backtest agent confirmed compatibility and JSON `allow_nan=False` requirements. |
| 05 | Implemented strict price/return input handling | Adjacent ratios on observation axis; missing, ragged, nonpositive and nonfinite prices rejected. `test_adjacent_ratios_and_matrix_axis`, `test_reject_prices`. |
| 06 | Reworked drawdown initial condition | Include initial wealth of one before any realised return. A first-period loss is captured. Bankruptcy remains zero wealth. `test_initial_loss_is_drawdown`, `test_bankruptcy_stays_zero`. |
| 07 | Implemented explicit performance conventions | Geometric annual return; sample volatility; effective annual risk-free rate converted to observation interval; undefined statistics use `None`. Hand-calculated two-period example and risk-free conversion tests pass. |
| 08 | Implemented empirical fractional-tail risk | Empirical inverse-CDF VaR and exactly weighted worst-tail ES, retaining negative loss estimates. Fractional-tail, tie and tiny-tail examples verify distinct conventions. |
| 09 | Implemented constrained minimum variance | PSD and symmetry checks, feasibility checks and bounded SLSQP. Scale the covariance objective so small variance magnitudes do not hide the gradient. Diagonal analytical solution, cap binding, singular covariance and failed-solver tests pass. |
| 10 | Implemented dividend Black–Scholes | Explicit expiry/zero-volatility limits, continuous rates and dividend yield. Published standard benchmark and independent put–call parity tests pass. |
| 11 | Independently checked Greeks | Analytic delta, gamma, vega, rho and calendar theta compared with central finite differences for both calls and puts. Units are documented; discontinuous boundary derivatives are rejected. |
| 12 | Implemented the CRR tree | Recombining risk-neutral tree, finite-grid early exercise and no-arbitrage probability validation. European convergence, American put premium and no-dividend American call equality pass. |
| 13 | Implemented antithetic Monte Carlo | Seeded GBM terminal sampling with independent pair averages. Standard error uses the pair count, not the count of correlated paths. Independent SE reconstruction, reproducibility and analytic-price proximity pass. |
| 14 | Ran first complete quant suite | Initial 37 tests passed. Tests include independent identities and hand-computed values; they do not merely duplicate function outputs. |
| 15 | Performed randomised numerical challenge | Two hundred fixed-seed parameter combinations gave maximum dividend put–call-parity discrepancy `5.684341886080802e-14`. Random PSD optimisation examples satisfied caps/sum constraints and did no worse than equal weights. |
| 16 | Attacked extreme numerical domains | Found Monte Carlo could report zero when variance overflowed; added shared analytic-domain validation and regression tests. Rejected nonnumeric array coercion. Suite increased to 39 passing tests. |
| 17 | Cross-reviewed backtest integration | Read signal timing, shifted execution, drifted weights, self-financing transaction costs and metrics integration. Communicated a direct-API boolean/coercion hardening opportunity to the backtest agent. |
| 18 | Incorporated independent peer challenge | Research-agent review reproduced ES overflow for twenty `1e308` gains. Replaced unscaled tail sums with a scaled weighted mean and added finite-output regression. |
| 19 | Rechecked remaining boundary artefacts | Fixed decimal-constant return roundoff generating a spurious Sharpe ratio, and zero-volatility American-tree discounted-price overflow. The quant suite now has 41 passing tests. |
| 20 | Validated combined integration state | `PYTHONPATH=src python -m unittest discover -s tests -v` passed all 104 tests present at this checkpoint, including quant, backtest, data, research and security. Root performs final release verification after other agents finish. |

## Reproduction

```bash
PYTHONPATH=src python -m unittest discover -s tests -p test_quant.py -v
```

Forty-one quant tests passed at the final checkpoint recorded above. Subsequent
release checks may add more tests. A passing suite establishes behaviour on
these cases, not universal financial correctness or production certification.

## Source verification

- [AI-Investment-Advisor, commit 990a16c12436e83d0e977f48d6a81485deb6f251](https://github.com/neohsiung/AI-Investment-Advisor/tree/990a16c12436e83d0e977f48d6a81485deb6f251).
- Nicolas Privault, [Black–Scholes Pricing and Hedging](https://personal.ntu.edu.sg/nprivault/MA5182/black-scholes-pde.pdf), chapter 6, author-hosted NTU notes.
- Nicolas Privault, [Expected Shortfall](https://personal.ntu.edu.sg/nprivault/MH8331/expected_shortfall.pdf), chapter 7, especially the integrated-quantile definition (7.1). The implementation uses that integrated-tail convention; naming conventions for conditional tail expectation vary.
- [Pricing and Hedging Derivative Securities, Monte Carlo Methods](https://book.derivative-securities.org/Chapter_MonteCarlo.html), chapter 13, GBM terminal simulation and antithetic sampling.
- [Pricing and Hedging Derivative Securities, Binomial Trees](https://book.derivative-securities.org/Chapter_Trees.html), chapter 4, no-arbitrage probabilities and backward induction.
- John Geweke, [Monte Carlo Simulation and Numerical Integration](https://www.minneapolisfed.org/economic-research/conferences/~/media/files/research/events/1994_03-18/Geweke_MonteCarlo.pdf), section 5.1, antithetic correlated pairs and variance reduction.
- SciPy, [SLSQP reference](https://docs.scipy.org/doc/scipy/reference/optimize.minimize-slsqp.html), solver configuration and constraints.

## Deliberate limits

Options assume constant parameters and the stated diffusion or discrete tree;
prices are model values. The tree approximates continuous American exercise on
a finite grid. Monte Carlo intervals describe simulation error only, use an
asymptotic normal approximation and can be unreliable with very few pairs or
rare payoffs. They do not measure model error. Tail statistics are historical
sample summaries, especially unstable with tiny tails. Square-root volatility
annualisation assumes uncorrelated stationary returns. Optimisation is a
long-only minimum-variance allocation under the supplied covariance, with no
return forecast. No empirical outperformance claim is made.
