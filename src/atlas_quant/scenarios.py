"""Bounded scenario risk and minimax empirical expected-shortfall allocation.

Rows in each named scenario are equally probable one-horizon simple-return
outcomes; columns must refer to the same assets in the same order. Named
scenarios are competing assumptions, without assigned probabilities between
them. The optimiser produces research target weights, with no execution,
transaction fees, financing, liquidity model or forecast guarantee.
"""
from __future__ import annotations

from collections.abc import Mapping
import math
from numbers import Real

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix

from .quant import historical_risk

MAX_SCENARIOS = 20
MAX_ASSETS = 64
MAX_TOTAL_ROWS = 20_000
MAX_RETURN_MAGNITUDE = 1_000_000.0


def _confidence(value) -> float:
    if (isinstance(value, (bool, np.bool_)) or not isinstance(value, Real)
            or not math.isfinite(float(value)) or not 0 < value < 1):
        raise ValueError("confidence must be a finite fraction strictly between zero and one")
    return float(value)


def _matrices(scenarios) -> dict[str, np.ndarray]:
    if not isinstance(scenarios, Mapping) or not 1 <= len(scenarios) <= MAX_SCENARIOS:
        raise ValueError(f"provide between 1 and {MAX_SCENARIOS} named scenarios")
    if any(not isinstance(name, str) or not name.strip() or len(name) > 100
           or any(ord(char) < 32 for char in name) for name in scenarios):
        raise ValueError("scenario names must be nonempty text of at most 100 characters without controls")
    result = {}
    columns = None
    total_rows = 0
    # A canonical order makes mapping insertion order irrelevant to the LP.
    for name in sorted(scenarios):
        try:
            raw = np.asarray(scenarios[name])
            if raw.ndim != 2 or not raw.shape[0] or not 1 <= raw.shape[1] <= MAX_ASSETS:
                raise ValueError("invalid dimensions")
            if raw.dtype.kind not in "iuf":
                raise ValueError("non-numeric values")
            total_rows += raw.shape[0]
            if total_rows > MAX_TOTAL_ROWS:
                raise ValueError("too many scenario rows")
            values = raw.astype(float, copy=False)
        except (TypeError, ValueError, OverflowError) as exc:
            raise ValueError(f"scenario {name!r} must be a numeric outcome-by-asset matrix; "
                             f"at most {MAX_ASSETS} assets and {MAX_TOTAL_ROWS} total rows") from exc
        if (not np.isfinite(values).all() or np.any(values < -1)
                or np.any(values > MAX_RETURN_MAGNITUDE)):
            raise ValueError("scenario simple returns must be finite and lie in [-1, 1000000]")
        if columns is not None and columns != values.shape[1]:
            raise ValueError("all scenario matrices must have the same asset columns")
        columns = values.shape[1]
        result[name] = values
    return result


def _weights(weights, assets: int) -> np.ndarray:
    try:
        raw = np.asarray(weights)
        if raw.dtype.kind not in "iuf" or raw.shape != (assets,):
            raise ValueError("invalid weights")
        values = raw.astype(float, copy=False)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("weights must be a real vector with one entry per asset") from exc
    if (not np.isfinite(values).all() or np.any(values < 0) or np.any(values > 1)
            or not math.isclose(float(values.sum()), 1.0, rel_tol=0, abs_tol=1e-10)):
        raise ValueError("long-only weights must lie in [0, 1] and sum to one")
    return values


def _evaluate(matrices, weights, confidence):
    risks = {}
    for name, values in matrices.items():
        returns = values @ weights
        # A convex combination of returns >= -1 cannot fall below -1
        # mathematically. Remove only floating-point summation roundoff here.
        if np.any(returns < -1 - 1e-12):
            raise ValueError("portfolio scenario return is below complete loss")
        risks[name] = historical_risk(np.maximum(returns, -1.0), confidence)
    cvars = {name: risk["expected_shortfall"] for name, risk in risks.items()}
    return {"per_scenario_cvar": cvars,
            "per_scenario_var": {name: risk["var"] for name, risk in risks.items()},
            "worst_cvar": max(cvars.values()),
            "scenario_observations": {name: risk["observations"] for name, risk in risks.items()},
            "confidence": confidence}


def scenario_cvar(scenarios, weights, confidence: float = .95) -> dict:
    """Evaluate supplied weights using the project's fractional empirical tail.

    Loss is minus a one-horizon simple return. CVaR here means integrated-quantile
    expected shortfall, including fractional mass at an empirical tail boundary.
    Negative CVaR is preserved when the selected tail contains gains. This is a
    conditional scenario statistic, not a market-calibrated loss bound.
    """
    matrices = _matrices(scenarios)
    confidence = _confidence(confidence)
    weights = _weights(weights, next(iter(matrices.values())).shape[1])
    return _evaluate(matrices, weights, confidence)


def robust_cvar_allocation(scenarios, confidence: float = .95,
                           max_weight: float = 1.0) -> dict:
    """Minimise the largest empirical CVaR across the supplied scenario sets.

    For each scenario j with n_j equally probable rows and losses L_ji=-R_ji w,
    the LP requires t >= eta_j + sum_i u_ji/[n_j(1-c)], with
    u_ji >= L_ji-eta_j and u_ji >= 0. Target weights satisfy sum(w)=1 and
    0 <= w_i <= max_weight. Both t and eta_j are free, so all-gain scenarios
    retain negative risk rather than being clipped to zero. For tail mass below
    one observation, replacing it by one is exactly equivalent to the empirical
    maximum loss and avoids an unnecessarily ill-conditioned coefficient.

    Returns an independently reevaluated tail risk alongside the LP objective.
    Unsupported inputs, solver failure or failed feasibility checks raise
    ValueError. Equal objectives may have multiple optimal portfolios. No
    realised trading performance, fee accounting or prediction is implied.
    """
    matrices = _matrices(scenarios)
    confidence = _confidence(confidence)
    assets = next(iter(matrices.values())).shape[1]
    if (isinstance(max_weight, (bool, np.bool_)) or not isinstance(max_weight, Real)
            or not math.isfinite(float(max_weight)) or not 0 < max_weight <= 1
            or assets * max_weight < 1 - 1e-12):
        raise ValueError("max_weight must be a finite feasible cap in (0, 1]")
    cap = float(max_weight)
    groups, observations = len(matrices), sum(len(values) for values in matrices.values())
    t_index = assets
    eta_offset = assets + 1
    slack_offset = eta_offset + groups
    variables = slack_offset + observations
    scale = max(float(np.max(np.abs(values))) for values in matrices.values()) or 1.0
    # Sparse constraints avoid a quadratic allocation in the number of samples.
    row_parts, col_parts, coefficient_parts = [], [], []
    offset = 0
    for j, values in enumerate(matrices.values()):
        n = len(values)
        row_indices = np.arange(offset, offset + n)
        row_parts += [np.repeat(row_indices, assets), row_indices, row_indices,
                      np.full(n, observations + j), np.array([observations + j] * 2)]
        col_parts += [np.tile(np.arange(assets), n), np.full(n, eta_offset + j),
                      slack_offset + row_indices, slack_offset + row_indices,
                      np.array([t_index, eta_offset + j])]
        coefficient_parts += [(-values / scale).ravel(), -np.ones(n), -np.ones(n),
                              np.full(n, 1.0 / max(1.0, n * (1 - confidence))),
                              np.array([-1.0, 1.0])]
        offset += n
    inequalities = coo_matrix((np.concatenate(coefficient_parts),
                               (np.concatenate(row_parts), np.concatenate(col_parts))),
                              shape=(observations + groups, variables)).tocsr()
    equality = coo_matrix((np.ones(assets), (np.zeros(assets, dtype=int), np.arange(assets))),
                          shape=(1, variables)).tocsr()
    objective = np.zeros(variables)
    objective[t_index] = 1.0
    bounds = [(0.0, cap)] * assets + [(None, None)] * (1 + groups) + [(0.0, None)] * observations
    solved = linprog(objective, A_ub=inequalities, b_ub=np.zeros(observations + groups),
                     A_eq=equality, b_eq=np.ones(1), bounds=bounds, method="highs",
                     options={"primal_feasibility_tolerance": 1e-9,
                              "dual_feasibility_tolerance": 1e-9,
                              "ipm_optimality_tolerance": 1e-10,
                              "time_limit": 30.0})
    solution = getattr(solved, "x", None)
    if (not solved.success or solved.status != 0 or solution is None
            or np.shape(solution) != (variables,) or not np.isfinite(solution).all()
            or not math.isfinite(float(solved.fun))):
        raise ValueError("robust CVaR optimisation did not return a finite optimal solution")
    if (np.max(inequalities @ solution) > 1e-7
            or abs(float((equality @ solution)[0]) - 1.0) > 1e-10
            or np.min(solution[:assets]) < 0 or np.max(solution[:assets]) > cap + 1e-10
            or np.min(solution[slack_offset:]) < -1e-9):
        raise ValueError("robust CVaR solution failed feasibility checks")
    weights = _weights(solution[:assets], assets)
    risk = _evaluate(matrices, weights, confidence)
    return_objective = float(solved.fun * scale)
    if (not math.isclose(float(solved.fun), float(solution[t_index]), rel_tol=1e-8, abs_tol=1e-8)
            or not math.isclose(risk["worst_cvar"], return_objective, rel_tol=1e-7, abs_tol=1e-9)):
        raise ValueError("robust CVaR objective disagrees with independently evaluated tail risk")
    return {"weights": weights.tolist(), **risk,
            "objective": return_objective, "max_weight": cap,
            "solver": "scipy.optimize.linprog/highs", "solver_status": "optimal",
            "solver_status_code": int(solved.status),
            "assumptions": ["Equal probability for rows within each scenario set.",
                            "Worst-case CVaR across supplied scenario sets, without probabilities between sets.",
                            "Long-only fully invested research target; no fees, execution, financing or liquidity model.",
                            "Risk is conditional on supplied scenarios and does not bound unseen market losses."]}
