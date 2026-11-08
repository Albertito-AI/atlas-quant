# Mathematical conventions

The public functions in `atlas_quant.quant` use fractional returns and annual rates: `0.05` means five per cent. Time to option maturity is measured in years. Prices and strikes must use the same currency and scale. Inputs must be finite. These conventions are part of the API, not presentation choices.

## Returns, wealth and drawdown

For positive prices, the simple return is

\[
r_t=P_t/P_{t-1}-1.
\]

Given an initial wealth of one, the cumulative wealth path includes that initial observation:

\[
W_0=1,\qquad W_t=\prod_{j=1}^{t}(1+r_j),\qquad
D_t=W_t/\max_{0\le j\le t}W_j-1.
\]

`drawdown` returns signed values at or below zero, including the initial zero. `performance_metrics["max_drawdown"]` returns the nonnegative magnitude of the worst drawdown. Including initial wealth makes an immediate loss visible. A return of exactly minus one represents complete loss; values below minus one are rejected.

For `n` observations and `m` observations per year, geometric annualised return is

\[
(W_n/W_0)^{m/n}-1.
\]

Annualised volatility is the sample standard deviation, with one degree of freedom removed, multiplied by \(\sqrt m\). The effective annual risk-free rate is converted to an observation rate by \((1+R_f)^{1/m}-1\). Sharpe uses mean arithmetic excess return divided by sample volatility, then multiplies by \(\sqrt m\). It is `None` when sample volatility is zero or there are fewer than two observations. Neither compounding nor this frequency scaling corrects irregular observation intervals, serial correlation or nonstationarity.

## Empirical tail risk

`historical_risk` uses losses \(L_t=-r_t\). For confidence level \(c\), value at risk is the left inverse of the empirical distribution: the ascending observation at one-based rank \(\lceil cn\rceil\). This discrete convention is deliberately explicit because interpolation methods give different results on small samples.

Expected shortfall averages exactly the worst \(n(1-c)\) observations. A fractional final observation receives fractional weight. If sorted descending losses are \(l_1\ge\cdots\ge l_n\), set \(a=n(1-c)\), \(k=\lfloor a\rfloor\), and \(f=a-k\):

\[
ES_c=\frac{\sum_{j=1}^{k}l_j+f l_{k+1}}{a}.
\]

When `f` is zero, the final term is omitted. With losses `0.10, 0.04, 0.01, -0.02` and confidence `0.625`, tail mass is `1.5`, value at risk is `0.04`, and expected shortfall is `(0.10 + 0.5 * 0.04)/1.5 = 0.08`. Negative values are retained if even the selected worst outcomes are gains.

These are historical one-observation statistics. They do not give a guaranteed maximum loss or estimate events absent from the sample. The report's default confidence level is a research convention. It does not implement the Basel market-risk capital framework. See Privault's [expected shortfall chapter](https://personal.ntu.edu.sg/nprivault/MH8331/expected_shortfall.pdf) for the quantile formulation; [Basel MAR33](https://www.bis.org/committees/bcbs/basel-framework/standard/mar/33/inforce/2023-01-01/published/2020-06-05) has additional confidence, horizon and modelling requirements.

## Capped minimum variance

For a symmetric positive-semidefinite covariance matrix \(\Sigma\), the portfolio routine solves

\[
\min_w w^\top\Sigma w
\quad\text{subject to}\quad
\mathbf 1^\top w=1,\quad 0\le w_i\le u.
\]

With `d` assets, feasibility requires `d * u >= 1`. The implementation uses SciPy's sequential least-squares programming solver, supplies the analytic objective gradient, scales the objective for numerical stability, and checks solver success and constraint feasibility. A singular covariance matrix is permitted; it can produce nonunique optimal portfolios. A zero matrix returns equal weights. Material asymmetry or negative eigenvalues are rejected rather than concealed by an automatic repair.

For independent assets with variances `0.04` and `0.09`, the uncapped solution is `(9/13, 4/13)`. A cap of `0.60` changes it to `(0.60, 0.40)`. Estimated minimum variance is conditional on the input covariance and constraints; it is not a forecast of superior return. Bibliographic foundation: [Markowitz (1952)](https://onlinelibrary.wiley.com/doi/10.1111/j.1540-6261.1952.tb01525.x). Solver semantics: [SciPy SLSQP documentation](https://docs.scipy.org/doc/scipy/reference/optimize.minimize-slsqp.html).

The backtest's `minimum_variance` strategy estimates covariance from its trailing training window and applies a fixed ten per cent diagonal shrinkage before calling this solver. That is an explicit stabilisation choice, without a claim that the chosen fraction is statistically optimal. `inverse_volatility` is a simpler allocation heuristic: it is not a full risk-parity optimisation.

## European option valuation

For spot `S`, strike `K`, time `T`, continuously compounded rate `r`, continuous dividend yield `q` and volatility `sigma`, define

\[
d_1=\frac{\log(S/K)+(r-q+\sigma^2/2)T}{\sigma\sqrt T},
\qquad d_2=d_1-\sigma\sqrt T.
\]

With standard normal distribution function \(\Phi\), the call and put values are

\[
C=Se^{-qT}\Phi(d_1)-Ke^{-rT}\Phi(d_2),
\qquad P=Ke^{-rT}\Phi(-d_2)-Se^{-qT}\Phi(-d_1).
\]

The implementation evaluates exact expiry and zero-volatility limits separately. Put-call parity is \(C-P=Se^{-qT}-Ke^{-rT}\). Constant volatility/rates, continuous yield and European exercise are model assumptions. A market implied volatility surface, discrete dividends, transaction costs and jumps are absent. See [Privault, Black-Scholes Pricing and Hedging](https://personal.ntu.edu.sg/nprivault/MA5182/black-scholes-pde.pdf).

| Greek | Returned derivative | Practical conversion |
| --- | --- | --- |
| Delta | Price change per unit spot change | Already per currency unit of spot |
| Gamma | Second derivative with respect to spot | Already per squared spot unit |
| Vega | Price change per `1.0` volatility change | Divide by `100` for one percentage point |
| Rho | Price change per `1.0` rate change | Divide by `100` for one percentage point |
| Theta | Calendar-time derivative per year | Divide by a chosen day-count basis for a daily approximation |

Greeks require positive maturity and volatility. The routine rejects boundary cases with discontinuous or convention-dependent derivatives. Theta is the negative derivative with respect to remaining time, which matters when constructing a finite-difference check.

## Binomial valuation

The Cox-Ross-Rubinstein tree uses \(\Delta t=T/N\), \(u=e^{\sigma\sqrt{\Delta t}}\), \(d=1/u\), and risk-neutral probability

\[
p=\frac{e^{(r-q)\Delta t}-d}{u-d}.
\]

Backward induction discounts the probability-weighted continuation values. American mode takes the greater of continuation and exercise value at every grid point. A probability outside `[0, 1]` is rejected; increasing `steps` may resolve a coarse-grid problem. American exercise is restricted to this finite grid and is an approximation to continuous exercise. The zero-volatility American path is evaluated on the same grid. See Privault's [discrete-time chapter](https://personal.ntu.edu.sg/nprivault/MA5182/discrete-time-model.pdf) and [pricing chapter](https://personal.ntu.edu.sg/nprivault/MA5182/pricing-hedging-discrete-time.pdf).

## Monte Carlo valuation and uncertainty

Terminal prices follow the risk-neutral geometric Brownian model:

\[
S_T=S\exp((r-q-\sigma^2/2)T+\sigma\sqrt T Z),\qquad Z\sim N(0,1).
\]

For each independent draw, the routine evaluates `Z` and `-Z`, discounts the two payoffs and averages the pair. With `M = paths/2` independent pair averages \(A_i\), the estimate is their mean and its standard error is \(s_A/\sqrt M\). Individual payoffs in a pair are dependent and must not be counted as independent observations.

The reported interval is a normal approximation using that standard error. It describes simulation uncertainty conditional on the model and inputs. It excludes model misspecification, parameter estimation and market risk, and can be unreliable with very small samples or rare payoffs. A fixed seed permits repeatability within the numerical environment. See [Boyle, Broadie and Glasserman (1997)](https://business.columbia.edu/faculty/research/monte-carlo-methods-security-pricing).

## Backtest interpretation

An allocation estimated after close `t` executes at close `t+1`. The old holdings earn the return into that execution close. Newly executed holdings earn returns from the following interval. Rebalancing charges proportional cost on gross traded notional, including both sales and purchases. The ledger solves for the post-cost investable wealth, so costs are funded from the portfolio. Final holdings remain marked to market; terminal liquidation costs are not assumed.

The implementation is a walk-forward estimation experiment with fixed strategy choices. Repeatedly selecting the best result on the same history still introduces selection bias. It does not implement nested cross-validation or estimate the probability of overfitting. [Bailey and colleagues](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf) explain why a good historical score can survive inadequate evaluation controls.
