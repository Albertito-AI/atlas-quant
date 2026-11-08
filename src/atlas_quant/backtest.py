"""Auditable walk-forward close-to-close portfolio research.

Signals use a trailing window ending at close t. Rebalances execute at close
 t+1 after existing holdings receive that day's return. Prices are adjusted
closes in one currency; fractions of shares and perfect closing fills are
assumed. No broker integration, leverage, shorting or final liquidation.
"""
from __future__ import annotations

from dataclasses import dataclass
from numbers import Real

import numpy as np

from .data import PriceDataset
from .quant import historical_risk, minimum_variance, performance_metrics

STRATEGIES = ("equal_weight", "inverse_volatility", "minimum_variance")


def _integer(value: int, name: str, minimum: int = 1) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or value < minimum:
        raise ValueError(f"{name} must be an integer at least {minimum}")
    return int(value)


def _capped_proportions(raw: np.ndarray, cap: float) -> np.ndarray:
    """Allocate proportionally, repeatedly fixing any cap-saturated assets."""
    n = len(raw)
    if cap * n < 1 - 1e-12:
        raise ValueError("max_weight is infeasible for a fully invested portfolio")
    if abs(cap * n - 1) <= 1e-12:
        return np.full(n, 1 / n)
    weights = np.zeros(n)
    available = np.ones(n, dtype=bool)
    remaining = 1.0
    for _ in range(n):
        scores = raw[available]
        candidate = remaining * (scores / scores.sum() if scores.sum() > 0 else np.full(len(scores), 1 / len(scores)))
        indices = np.flatnonzero(available)
        saturated = candidate > cap
        if not saturated.any():
            weights[indices] = candidate
            break
        weights[indices[saturated]] = cap
        available[indices[saturated]] = False
        remaining = 1 - float(weights.sum())
    return weights / weights.sum()


def strategy_weights(history_returns: np.ndarray, strategy: str, max_weight: float = 1.0) -> np.ndarray:
    """Compute targets using only the explicitly supplied training returns.

    Inverse volatility assigns equal score to zero-volatility assets and zero
    score elsewhere, then applies the cap. It is a simple allocation heuristic,
    not a risk-parity optimiser. Minimum variance uses 10% diagonal covariance
    shrinkage; the shrinkage fraction is fixed rather than selected in sample.
    History must contain real integer or floating-point values; complex,
    boolean, textual and object arrays are rejected before allocation.
    """
    try:
        supplied = np.asarray(history_returns)
        if supplied.dtype.kind not in "iuf":
            raise ValueError("history must contain real numbers without coercion")
        history = supplied.astype(float, copy=False)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("history_returns must be a real numeric rectangular matrix without coercion") from exc
    if history.ndim != 2 or history.shape[0] < 2 or history.shape[1] < 1:
        raise ValueError("history_returns must be a matrix with at least two observations")
    if not np.isfinite(history).all() or (history <= -1).any():
        raise ValueError("history returns must be finite and greater than -1")
    if strategy not in STRATEGIES:
        raise ValueError(f"strategy must be one of {STRATEGIES}")
    n = history.shape[1]
    if isinstance(max_weight, bool) or not isinstance(max_weight, Real) or not np.isfinite(max_weight) or not 0 < max_weight <= 1 or n * max_weight < 1 - 1e-12:
        raise ValueError("max_weight must be feasible and in (0, 1]")
    if strategy == "equal_weight":
        return np.full(n, 1 / n)
    if strategy == "inverse_volatility":
        vol = history.std(axis=0, ddof=1)
        zeros = vol <= np.finfo(float).eps
        raw = zeros.astype(float) if zeros.any() else 1 / vol
        return _capped_proportions(raw, max_weight)
    covariance = np.atleast_2d(np.cov(history, rowvar=False, ddof=1))
    covariance = 0.9 * covariance + 0.1 * np.diag(np.diag(covariance))
    return minimum_variance(covariance, max_weight=max_weight)


def _rebalance(pretrade_holdings: np.ndarray, wealth: float, weights: np.ndarray, cost_rate: float):
    """Solve the self-financing trade equation for a proportional per-side fee."""
    if cost_rate == 0:
        post_wealth = wealth
    else:
        lower, upper = 0.0, wealth
        for _ in range(64):
            midpoint = (lower + upper) / 2
            residual = midpoint + cost_rate * np.abs(weights * midpoint - pretrade_holdings).sum() - wealth
            if residual > 0:
                upper = midpoint
            else:
                lower = midpoint
        post_wealth = (lower + upper) / 2
    holdings = weights * post_wealth
    notional = float(np.abs(holdings - pretrade_holdings).sum())
    fees = cost_rate * notional
    # Keep conservation exact at normal floating-point precision.
    cash = wealth - fees - float(holdings.sum())
    if abs(cash) < wealth * 1e-13:
        cash = 0.0
    return holdings, cash, fees, notional


@dataclass(frozen=True)
class BacktestResult:
    dataset: dict
    config: dict
    dates: list[str]
    equity_curve: list[float]
    cash_curve: list[float]
    weights_history: list[list[float]]
    net_returns: list[float]
    trades: list[dict]
    metrics: dict
    risk: dict
    assumptions: list[str]

    def to_dict(self) -> dict:
        return {
            "schema_version": "1.0", "dataset": self.dataset, "config": self.config,
            "dates": self.dates, "equity_curve": self.equity_curve, "cash_curve": self.cash_curve,
            "weights_history": self.weights_history, "net_returns": self.net_returns,
            "final_weights": dict(zip(self.dataset["symbols"], self.weights_history[-1])),
            "trades": self.trades, "metrics": self.metrics, "risk": self.risk,
            "assumptions": self.assumptions,
        }


def run_backtest(
    data: PriceDataset, *, strategy: str = "inverse_volatility", lookback: int = 60,
    rebalance_every: int = 21, transaction_cost_bps: float = 10.0,
    initial_cash: float = 100_000.0, max_weight: float = 1.0,
    periods_per_year: int = 252,
) -> BacktestResult:
    """Run an expanding calendar with fixed trailing estimation windows.

    Requires lookback + 3 price rows so a first execution and one invested
    interval exist. The first result date is the first signal date; the initial
    cash baseline is included in the equity path. Rebalance dates are determined
    by observation counts, independent of realised performance. Costs apply to
    each absolute buy/sell notional, not half-turnover. Ending wealth is marked
    to market and does not include liquidation costs.
    """
    if not isinstance(data, PriceDataset):
        raise ValueError("data must be a validated PriceDataset")
    lookback = _integer(lookback, "lookback", 2)
    rebalance_every = _integer(rebalance_every, "rebalance_every")
    periods_per_year = _integer(periods_per_year, "periods_per_year")
    if len(data.dates) < lookback + 3:
        raise ValueError("at least lookback + 3 price observations are required")
    for value, name in ((transaction_cost_bps, "transaction_cost_bps"), (initial_cash, "initial_cash"), (max_weight, "max_weight")):
        if isinstance(value, bool) or not isinstance(value, Real) or not np.isfinite(value):
            raise ValueError(f"{name} must be a finite number")
    if not 0 <= transaction_cost_bps <= 1000:
        raise ValueError("transaction_cost_bps must be in [0, 1000]")
    if not 0 < initial_cash <= 1e15:
        raise ValueError("initial_cash must be in (0, 1e15]")
    n_assets = len(data.symbols)
    if not 0 < max_weight <= 1 or max_weight * n_assets < 1 - 1e-12:
        raise ValueError("max_weight is infeasible or outside (0, 1]")
    if strategy not in STRATEGIES:
        raise ValueError(f"strategy must be one of {STRATEGIES}")
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        relatives = data.prices[1:] / data.prices[:-1]
    if not np.isfinite(relatives).all() or (relatives <= 0).any():
        raise ValueError("price ratios overflow or underflow the supported numerical range")
    returns = relatives - 1
    holdings = np.zeros(n_assets)
    cash = float(initial_cash)
    equity = [cash]
    cash_curve = [cash]
    weights_history = [np.zeros(n_assets).tolist()]
    trades = []
    cost_rate = float(transaction_cost_bps) / 10_000
    pending = strategy_weights(returns[:lookback], strategy, max_weight)
    decision_index = lookback
    for index in range(lookback + 1, len(data.dates)):
        with np.errstate(over="ignore", invalid="ignore"):
            holdings = holdings * relatives[index - 1]
        wealth = float(holdings.sum() + cash)
        if not np.isfinite(wealth) or wealth <= 0:
            raise ValueError("portfolio wealth overflowed or became nonpositive")
        if pending is not None:
            prior_weights = holdings / wealth
            holdings, cash, fee, notional = _rebalance(holdings, wealth, pending, cost_rate)
            posttrade = float(holdings.sum() + cash)
            trades.append({
                "date": data.dates[index], "decision_date": data.dates[decision_index],
                "pretrade_equity": wealth, "posttrade_equity": posttrade,
                "traded_notional": notional, "transaction_cost": fee,
                "turnover": notional / wealth,
                "target_weights": dict(zip(data.symbols, pending.tolist())),
                "pretrade_weights": dict(zip(data.symbols, prior_weights.tolist())),
            })
            pending = None
        wealth = float(holdings.sum() + cash)
        equity.append(wealth)
        cash_curve.append(float(cash))
        weights_history.append((holdings / wealth).tolist())
        # Never compute a decision for an execution beyond the final bar.
        if (index - lookback) % rebalance_every == 0 and index < len(data.dates) - 1:
            pending = strategy_weights(returns[index - lookback:index], strategy, max_weight)
            decision_index = index
    net_returns = np.asarray(equity[1:]) / np.asarray(equity[:-1]) - 1
    metrics = performance_metrics(net_returns, periods_per_year=periods_per_year)
    metrics.update({"total_transaction_cost": sum(t["transaction_cost"] for t in trades),
                    "total_turnover": sum(t["turnover"] for t in trades),
                    "total_cost_fraction": sum(t["transaction_cost"] / t["pretrade_equity"] for t in trades),
                    "rebalance_count": len(trades),
                    "final_equity": equity[-1]})
    assumptions = [
        "Research simulation; no trade execution or personalised advice.",
        "Decisions at close t execute at close t+1; newly bought holdings earn returns after that close.",
        "Input prices are caller-supplied adjusted closes in one common currency; no missing-price fill.",
        "Fractional shares, complete liquidity and closing-price fills; tax, market impact and financing omitted.",
        "Cost in basis points is charged per side on every absolute traded notional; cash earns zero.",
        "Final holdings are marked to market without liquidation fees; weight caps apply at rebalances only.",
        "Metrics start on the first signal date, include first-entry costs and use the selected periods-per-year convention.",
        "Historical tail estimates and backtests do not predict future losses; asset selection may contain survivorship bias.",
    ]
    if data.synthetic:
        assumptions.insert(0, "SYNTHETIC DATA: illustrative generated paths, not observed market performance.")
    return BacktestResult(data.metadata(), {
        "strategy": strategy, "lookback": lookback, "rebalance_every": rebalance_every,
        "transaction_cost_bps": float(transaction_cost_bps), "initial_cash": float(initial_cash),
        "max_weight": float(max_weight), "periods_per_year": periods_per_year,
        "execution_lag_bars": 1, "minimum_variance_diagonal_shrinkage": 0.1,
    }, list(data.dates[lookback:]), equity, cash_curve, weights_history,
        net_returns.tolist(), trades, metrics, historical_risk(net_returns), assumptions)
