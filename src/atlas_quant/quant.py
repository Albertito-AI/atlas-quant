"""Auditable numerical finance primitives, with explicit units and finite inputs.

Rates and volatilities are decimals; option rates are continuously compounded.
Prices are per unit of underlying. None denotes an undefined sample statistic.
These models describe assumptions, not market forecasts or trading instructions.
"""
from __future__ import annotations

import math
from numbers import Integral, Real

import numpy as np
from scipy.optimize import minimize
from scipy.special import ndtr, ndtri


def _scalar(value: float, name: str) -> float:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, Real):
        raise ValueError(f"{name} must be a finite real number")
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be a finite real number")
    return value


def _array(values, name: str, dimensions: tuple[int, ...]) -> np.ndarray:
    try:
        raw = np.asarray(values)
        if raw.dtype.kind not in "iuf":
            raise ValueError(f"{name} must contain real numbers, without coercion")
        array = raw.astype(float, copy=False)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a rectangular numeric array") from exc
    if array.ndim not in dimensions or array.size == 0 or not np.isfinite(array).all():
        raise ValueError(f"{name} must be a nonempty finite array of dimension {dimensions}")
    return array


def _returns(values) -> np.ndarray:
    values = _array(values, "returns", (1,))
    if np.any(values < -1):
        raise ValueError("simple returns cannot be below -1")
    return values


def simple_returns(prices) -> np.ndarray:
    """Adjacent simple returns, with observations in rows; no missing-value filling."""
    values = _array(prices, "prices", (1, 2))
    if values.shape[0] < 2 or np.any(values <= 0):
        raise ValueError("prices need at least two observations, all strictly positive")
    with np.errstate(over="ignore", invalid="ignore"):
        result = values[1:] / values[:-1] - 1.0
    if not np.isfinite(result).all():
        raise ValueError("price ratios exceed numeric range")
    return result


def drawdown(returns) -> np.ndarray:
    """Fractional drawdown <= 0, including initial wealth and exact bankruptcy.

    Compensated log accumulation avoids losing recoverable wealth to absolute
    underflow. Only the log distance from the running peak is exponentiated,
    so a finite relative drawdown needs no representable absolute wealth.
    """
    values = _returns(returns)
    result = np.empty(len(values) + 1)
    result[0] = 0.0
    log_wealth = correction = peak = 0.0
    for index, value in enumerate(values, start=1):
        if value == -1:
            # An actual complete loss is absorbing, unlike numerical underflow.
            result[index:] = -1.0
            break
        increment = math.log1p(float(value)) - correction
        updated = log_wealth + increment
        correction = (updated - log_wealth) - increment
        log_wealth = updated
        if not math.isfinite(log_wealth):
            raise ValueError("log wealth exceeds numeric range")
        peak = max(peak, log_wealth)
        result[index] = math.expm1(log_wealth - peak)
    return result


def performance_metrics(returns, periods_per_year: float = 252,
                        risk_free_rate: float = 0.0) -> dict:
    """Geometric annual return; sample volatility; arithmetic excess-return Sharpe.

    risk_free_rate is an effective annual rate, converted geometrically to a
    per-observation rate. Sampling intervals must be equally spaced. Sharpe is
    None for fewer than two observations or zero sample volatility. Square-root
    annualisation assumes stationary, uncorrelated returns and can mislead.
    """
    values = _returns(returns)
    periods = _scalar(periods_per_year, "periods_per_year")
    risk_free = _scalar(risk_free_rate, "risk_free_rate")
    if periods <= 0 or risk_free <= -1:
        raise ValueError("periods_per_year must be positive and risk_free_rate > -1")
    dd = drawdown(values)
    if np.any(values == -1):
        total, annual = -1.0, -1.0
    else:
        log_growth = float(np.log1p(values).sum())
        try:
            total = math.expm1(log_growth)
            annual = math.expm1(log_growth * periods / len(values))
        except OverflowError as exc:
            raise ValueError("annualised growth exceeds numeric range") from exc
    with np.errstate(over="ignore", invalid="ignore"):
        std = float(np.std(values, ddof=1)) if len(values) > 1 else None
    if len(values) > 1 and np.all(values == values[0]):
        std = 0.0
    volatility = std * math.sqrt(periods) if std is not None else None
    try:
        period_rf = math.expm1(math.log1p(risk_free) / periods)
    except OverflowError as exc:
        raise ValueError("per-period risk-free rate exceeds numeric range") from exc
    sharpe = None
    if std is not None and std > 0:
        sharpe = float((np.mean(values) - period_rf) / std * math.sqrt(periods))
    result = {"observations": len(values), "total_return": total,
              "annualised_return": annual, "annualised_volatility": volatility,
              "sharpe_ratio": sharpe, "max_drawdown": float(-np.min(dd))}
    if any(v is not None and not math.isfinite(v) for v in result.values()):
        raise ValueError("performance statistics exceed numeric range")
    return result


def historical_risk(returns, confidence: float = 0.95) -> dict:
    """Empirical loss VaR and integrated-quantile expected shortfall.

    Loss = -simple return. VaR uses the left inverse empirical CDF (ceil(c*n)).
    ES averages exactly the worst n*(1-c) observations with fractional weight
    at the tail boundary, including ties consistently. Negative risk values
    are retained when even the worst outcomes are gains. No distributional or
    out-of-sample guarantees are implied by these historical statistics.
    """
    values = _returns(returns)
    confidence = _scalar(confidence, "confidence")
    if not 0 < confidence < 1:
        raise ValueError("confidence must lie strictly between zero and one")
    losses = np.sort(-values)
    count = len(losses)
    quantile = float(losses[max(0, math.ceil(confidence * count) - 1)])
    tail_mass = (1.0 - confidence) * count
    whole = int(math.floor(tail_mass))
    fraction = tail_mass - whole
    descending = losses[::-1]
    scale = float(np.max(np.abs(descending)))
    normal = descending / scale if scale else descending
    total = float(normal[:whole].sum())
    if fraction > 0:
        total += fraction * float(normal[whole])
    expected_shortfall = (total / tail_mass) * scale
    if not math.isfinite(expected_shortfall):
        raise ValueError("tail risk exceeds numeric range")
    return {"var": quantile, "expected_shortfall": expected_shortfall,
            "confidence": confidence, "observations": count,
            "tail_observations": tail_mass}


def minimum_variance(covariance, max_weight: float = 1.0) -> np.ndarray:
    """Minimise w.T @ covariance @ w subject to sum(w)=1 and 0<=w<=cap.

    Rejects materially indefinite/non-symmetric covariance rather than silently
    repairing it. Scales the objective to avoid tiny variances masking gradients.
    Singular positive-semidefinite covariance is allowed; weights may be nonunique.
    """
    cov = _array(covariance, "covariance", (2,))
    n = cov.shape[0]
    cap = _scalar(max_weight, "max_weight")
    if cov.shape != (n, n) or n > 256:
        raise ValueError("covariance must be square with at most 256 assets")
    if not 0 < cap <= 1 or n * cap < 1 - 1e-12:
        raise ValueError("weight cap is invalid or infeasible")
    scale = float(np.max(np.abs(cov)))
    if scale == 0:
        return np.full(n, 1.0 / n)
    normal = cov / scale
    if not np.allclose(normal, normal.T, rtol=0, atol=1e-10):
        raise ValueError("covariance must be symmetric")
    normal = (normal + normal.T) / 2
    if np.linalg.eigvalsh(normal)[0] < -1e-10:
        raise ValueError("covariance must be positive semidefinite")
    initial = np.full(n, 1.0 / n)
    if abs(n * cap - 1.0) < 1e-12:
        return initial
    solved = minimize(lambda w: float(w @ normal @ w), initial,
                      jac=lambda w: 2 * normal @ w, method="SLSQP",
                      bounds=[(0.0, cap)] * n,
                      constraints={"type": "eq", "fun": lambda w: w.sum() - 1,
                                   "jac": lambda w: np.ones(n)},
                      options={"maxiter": 1000, "ftol": 1e-12})
    weights = solved.x
    if (not solved.success or not np.isfinite(weights).all()
            or abs(weights.sum() - 1) > 1e-8
            or weights.min() < -1e-8 or weights.max() > cap + 1e-8):
        raise ValueError("minimum-variance optimisation failed feasibility checks")
    return weights


def _option(spot, strike, maturity, rate, volatility, option, dividend):
    values = tuple(_scalar(v, k) for v, k in zip(
        (spot, strike, maturity, rate, volatility, dividend),
        ("spot", "strike", "maturity", "rate", "volatility", "dividend")))
    s, k, t, r, v, q = values
    if s <= 0 or k <= 0 or t < 0 or v < 0:
        raise ValueError("spot/strike must be positive; maturity/volatility nonnegative")
    if option not in ("call", "put"):
        raise ValueError("option must be 'call' or 'put'")
    return s, k, t, r, v, q


def _exp(value: float) -> float:
    try:
        result = math.exp(value)
    except OverflowError as exc:
        raise ValueError("option parameters exceed numeric range") from exc
    if not math.isfinite(result):
        raise ValueError("option parameters exceed numeric range")
    return result


def _discounted(s, k, t, r, q):
    sd, kd = s * _exp(-q * t), k * _exp(-r * t)
    if not math.isfinite(sd) or not math.isfinite(kd):
        raise ValueError("discounted prices exceed numeric range")
    return sd, kd


def black_scholes(spot, strike, maturity, rate, volatility,
                  option: str = "call", dividend: float = 0.0) -> float:
    """European option with continuous dividend yield; exact zero-time/vol limits."""
    s, k, t, r, v, q = _option(spot, strike, maturity, rate, volatility, option, dividend)
    sd, kd = _discounted(s, k, t, r, q)
    sign = 1 if option == "call" else -1
    if t == 0 or v == 0:
        return max(sign * (sd - kd), 0.0)
    variance = v * v * t
    if not math.isfinite(variance) or variance == 0:
        raise ValueError("option variance exceeds numeric range")
    d1 = (math.log(s) - math.log(k) + (r - q) * t + variance / 2) / math.sqrt(variance)
    d2 = d1 - math.sqrt(variance)
    if not math.isfinite(d1) or not math.isfinite(d2):
        raise ValueError("option parameters exceed numeric range")
    price = sign * (sd * ndtr(sign * d1) - kd * ndtr(sign * d2))
    return float(max(0.0, price))


def option_greeks(spot, strike, maturity, rate, volatility,
                  option: str = "call", dividend: float = 0.0) -> dict:
    """Analytic delta/gamma/vega/rho/theta, per unit input (theta per year).

    Requires strictly positive maturity and volatility; boundary derivatives
    can be discontinuous or convention-dependent and are deliberately rejected.
    Vega and rho are per 1.0 change, not per percentage point; divide by 100 for
    sensitivity to one percentage point. Theta is calendar-time decay (dV/dt).
    """
    s, k, t, r, v, q = _option(spot, strike, maturity, rate, volatility, option, dividend)
    if t == 0 or v == 0:
        raise ValueError("Greeks require positive maturity and volatility")
    black_scholes(s, k, t, r, v, option, q)  # shared numeric-domain validation
    sd, kd = _discounted(s, k, t, r, q)
    root = math.sqrt(t)
    d1 = (math.log(s) - math.log(k) + (r - q + v * v / 2) * t) / (v * root)
    d2 = d1 - v * root
    density = _exp(-0.5 * d1 * d1) / math.sqrt(2 * math.pi)
    sign = 1 if option == "call" else -1
    delta = sign * _exp(-q * t) * ndtr(sign * d1)
    gamma = _exp(-q * t) * density / (s * v * root)
    vega = sd * density * root
    rho = sign * kd * t * ndtr(sign * d2)
    theta = (-sd * density * v / (2 * root)
             - sign * r * kd * ndtr(sign * d2)
             + sign * q * sd * ndtr(sign * d1))
    result = dict(delta=float(delta), gamma=float(gamma), vega=float(vega),
                  rho=float(rho), theta=float(theta))
    if not all(math.isfinite(x) for x in result.values()):
        raise ValueError("Greeks exceed numeric range")
    return result


def binomial_price(spot, strike, maturity, rate, volatility,
                   option: str = "call", dividend: float = 0.0,
                   steps: int = 400, american: bool = False) -> float:
    """Cox-Ross-Rubinstein tree; American exercise is tested on the finite grid.

    Rejects step sizes giving invalid risk-neutral probabilities rather than
    clipping them. Increase steps when drift overwhelms a small volatility.
    """
    s, k, t, r, v, q = _option(spot, strike, maturity, rate, volatility, option, dividend)
    if isinstance(steps, bool) or not isinstance(steps, Integral) or not 1 <= steps <= 5000:
        raise ValueError("steps must be an integer between 1 and 5000")
    if not isinstance(american, (bool, np.bool_)):
        raise ValueError("american must be boolean")
    sign = 1 if option == "call" else -1
    if t == 0:
        return max(sign * (s - k), 0.0)
    if v == 0:
        if not american:
            return black_scholes(s, k, t, r, v, option, q)
        exercise = []
        for tau in np.linspace(0, t, steps + 1):
            sd, kd = _discounted(s, k, float(tau), r, q)
            exercise.append(max(sign * (sd - kd), 0.0))
        return max(exercise)
    dt = t / steps
    jump = v * math.sqrt(dt)
    up, down = _exp(jump), _exp(-jump)
    if up == down:
        raise ValueError("tree jump is below numeric resolution")
    probability = (_exp((r - q) * dt) - down) / (up - down)
    if not 0 <= probability <= 1:
        raise ValueError("tree violates no-arbitrage bounds; increase steps")
    discount = _exp(-r * dt)
    with np.errstate(over="ignore", invalid="ignore"):
        terminal = s * np.exp(jump * (2 * np.arange(steps + 1) - steps))
    if not np.isfinite(terminal).all():
        raise ValueError("tree prices exceed numeric range")
    values = np.maximum(sign * (terminal - k), 0.0)
    for level in range(steps - 1, -1, -1):
        values = discount * ((1 - probability) * values[:-1] + probability * values[1:])
        if american:
            nodes = s * np.exp(jump * (2 * np.arange(level + 1) - level))
            values = np.maximum(values, np.maximum(sign * (nodes - k), 0.0))
    if not math.isfinite(float(values[0])):
        raise ValueError("tree valuation exceeds numeric range")
    return float(values[0])


def monte_carlo_price(spot, strike, maturity, rate, volatility,
                      option: str = "call", dividend: float = 0.0,
                      paths: int = 20000, seed: int = 0,
                      confidence: float = 0.95) -> dict:
    """European GBM pricing with antithetic pairs and an approximate normal CI.

    paths is the even number of terminal paths. Independent observations are
    pair averages, so the standard error uses paths/2 independent pairs, not
    the dependent individual payoffs. The CI measures simulation error only.
    """
    s, k, t, r, v, q = _option(spot, strike, maturity, rate, volatility, option, dividend)
    if isinstance(paths, bool) or not isinstance(paths, Integral) or not 4 <= paths <= 1000000 or paths % 2:
        raise ValueError("paths must be an even integer between 4 and 1000000")
    if isinstance(seed, bool) or not isinstance(seed, Integral) or seed < 0:
        raise ValueError("seed must be a nonnegative integer")
    confidence = _scalar(confidence, "confidence")
    if not 0 < confidence < 1:
        raise ValueError("confidence must lie strictly between zero and one")
    analytic = black_scholes(s, k, t, r, v, option, q)
    pairs = paths // 2
    if t == 0 or v == 0:
        price = analytic
        standard_error = 0.0
    else:
        z = np.random.default_rng(seed).standard_normal(pairs)
        drift = (r - q - v * v / 2) * t
        diffusion = v * math.sqrt(t)
        with np.errstate(over="ignore", invalid="ignore"):
            a = s * np.exp(drift + diffusion * z)
            b = s * np.exp(drift - diffusion * z)
            sign = 1 if option == "call" else -1
            averages = _exp(-r * t) * (np.maximum(sign * (a - k), 0)
                                      + np.maximum(sign * (b - k), 0)) / 2
        if not np.isfinite(averages).all():
            raise ValueError("simulation payoffs exceed numeric range")
        price = float(np.mean(averages))
        with np.errstate(over="ignore", invalid="ignore"):
            standard_error = float(np.std(averages, ddof=1) / math.sqrt(pairs))
    radius = float(-ndtri((1 - confidence) / 2)) * standard_error
    result = {"price": price, "standard_error": standard_error,
              "ci_low": price - radius, "ci_high": price + radius,
              "paths": int(paths), "independent_pairs": int(pairs),
              "seed": int(seed), "confidence": confidence}
    if not all(math.isfinite(x) for x in result.values()):
        raise ValueError("simulation statistics exceed numeric range")
    return result
