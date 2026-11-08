"""Forward-only Bayesian calculations for explicitly specified Gaussian models.

Inputs use one-observation fractional return units: 0.01 is one per cent and
standard deviations are per observation, not annualised. Gaussian distributions
are unbounded; callers choosing simple returns must acknowledge the resulting
model misspecification below minus one. Log returns are another possible input.
These functions do not fit parameters, fetch prices, infer causality or place
orders. Probabilities are conditional model beliefs, not calibrated assurances
of future market behaviour or a measure of general intelligence.
"""
from __future__ import annotations

import math

import numpy as np
from scipy.special import logsumexp

MAX_OBSERVATIONS = 100_000
MAX_COMPONENTS = 32
MAX_PROBABILITY_CELLS = 1_000_000


def _array(values, name: str, dimensions: int) -> np.ndarray:
    try:
        raw = np.asarray(values)
        if raw.dtype.kind not in "iuf":
            raise ValueError("real numeric input is required")
        result = raw.astype(float, copy=False)
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError(f"{name} must be a rectangular real numeric array") from exc
    if result.ndim != dimensions or result.size == 0 or not np.isfinite(result).all():
        raise ValueError(f"{name} must be a nonempty finite {dimensions}D array")
    return result


def _probabilities(values: np.ndarray, name: str, axis=None) -> np.ndarray:
    if np.any(values < 0) or np.any(values > 1):
        raise ValueError(f"{name} must contain probabilities summing to one")
    totals = values.sum(axis=axis)
    if not np.allclose(totals, 1, rtol=0, atol=1e-12):
        raise ValueError(f"{name} must contain probabilities summing to one")
    # Normalise accepted floating-point round-off only; invalid weights fail.
    return values / (totals if axis is None else totals[:, None])


def _inputs(returns, means, stds, prior):
    observed = _array(returns, "returns", 1)
    centres = _array(means, "means", 1)
    scales = _array(stds, "stds", 1)
    weights = _array(prior, "prior", 1)
    n, k = len(observed), len(centres)
    if n > MAX_OBSERVATIONS or k > MAX_COMPONENTS or n * k > MAX_PROBABILITY_CELLS:
        raise ValueError("observations or components exceed the bounded belief calculation")
    if len(scales) != k or len(weights) != k:
        raise ValueError("means, stds and prior must have the same length")
    if np.any(scales <= 0):
        raise ValueError("stds must be strictly positive")
    weights = _probabilities(weights, "prior")
    # Squared deviations and component variances must remain representable.
    with np.errstate(over="ignore", invalid="ignore", under="ignore"):
        variances = scales * scales
    if not np.isfinite(variances).all() or np.any(variances <= 0):
        raise ValueError("stds lie outside the supported numerical range")
    return observed, centres, scales, weights, variances


def _log_weights(weights):
    with np.errstate(divide="ignore"):
        return np.log(weights)


def _calculate(observed, centres, scales, weights, variances, transition=None):
    log_weights = _log_weights(weights)
    log_transition = _log_weights(transition) if transition is not None else None
    prior_rows, posterior_rows = [], []
    means, total_variances, within_variances, between_variances = [], [], [], []
    log_scores, evidence_path = [], []
    cumulative_evidence = 0.0
    normal_constant = .5 * math.log(2 * math.pi)
    for value in observed:
        # The predictive record is fixed before this observation is consumed.
        predicted_weights = np.exp(log_weights)
        predicted_weights /= predicted_weights.sum()
        mean = float(predicted_weights @ centres)
        with np.errstate(over="ignore", invalid="ignore", divide="ignore"):
            within = float(predicted_weights @ variances)
            between = float(predicted_weights @ np.square(centres - mean))
            variance = within + between
            z = (value - centres) / scales
            log_likelihood = -normal_constant - np.log(scales) - .5 * np.square(z)
        if (not all(math.isfinite(v) for v in (mean, within, between, variance))
                or not np.isfinite(log_likelihood).all()):
            raise ValueError("Gaussian likelihood or moments exceed the supported numerical range")
        log_joint = log_weights + log_likelihood
        log_density = float(logsumexp(log_joint))
        if not math.isfinite(log_density):
            raise ValueError("observation has no representable likelihood under the supplied models")
        posterior = log_joint - log_density
        posterior -= logsumexp(posterior)
        post_weights = np.exp(posterior)
        post_weights /= post_weights.sum()
        cumulative_evidence += log_density
        if not math.isfinite(cumulative_evidence):
            raise ValueError("cumulative log evidence exceeds the supported numerical range")
        prior_rows.append(predicted_weights.tolist())
        posterior_rows.append(post_weights.tolist())
        means.append(mean)
        total_variances.append(variance)
        within_variances.append(within)
        between_variances.append(between)
        log_scores.append(log_density)
        evidence_path.append(cumulative_evidence)
        log_weights = (posterior if log_transition is None else
                       logsumexp(posterior[:, None] + log_transition, axis=0))
        log_weights -= logsumexp(log_weights)
    next_weights = np.exp(log_weights)
    next_weights /= next_weights.sum()
    return {
        "prior_probabilities": prior_rows,
        "posterior_probabilities": posterior_rows,
        "predictive_mean": means,
        "predictive_variance": total_variances,
        "aleatoric_variance": within_variances,
        "disagreement_variance": between_variances,
        "log_predictive_density": log_scores,
        "log_evidence_path": evidence_path,
        "cumulative_log_evidence": cumulative_evidence,
        "next_probabilities": next_weights.tolist(),
    }


def gaussian_regime_filter(returns, means, stds, transition, prior) -> dict:
    """Filter a fixed Gaussian hidden-state model using observations so far only.

    ``transition[i][j]`` is P(next state j | current state i), with each row
    summing to one. ``prior`` describes the state of the first observation;
    no transition precedes that observation. For every t, the returned prior,
    mean and variance condition on observations strictly before t; the posterior
    includes t. ``next_probabilities`` applies the transition after the final
    posterior. There is no smoothing or retrospective parameter estimation.

    Variance is the law-of-total-variance sum of conditional within-state
    variance and between-state mean disagreement. The returned key
    ``aleatoric_variance`` names that within-state term conditional on the
    supplied model. Neither term includes uncertainty about fitted parameters.
    Log scores are natural logarithms of densities, which can exceed zero.
    """
    observed, centres, scales, weights, variances = _inputs(returns, means, stds, prior)
    matrix = _array(transition, "transition", 2)
    if matrix.shape != (len(centres), len(centres)):
        raise ValueError("transition must be square with one row per component")
    matrix = _probabilities(matrix, "transition rows", axis=1)
    return _calculate(observed, centres, scales, weights, variances, matrix)


def online_gaussian_experts(returns, means, stds, prior) -> dict:
    """Score fixed Gaussian experts sequentially, then update Bayesian weights.

    An expert supplies one fixed mean and standard deviation for every
    observation. Its weight before observation t depends only on earlier
    outcomes. The posterior multiplies those weights by the observed Gaussian
    likelihood and normalises in log space. A zero initial weight remains zero.
    No forgetting factor, parameter learning or fitted calibration is implied.

    ``predictive_variance`` includes both within-expert variance and weighted
    squared disagreement between expert means. These are conditional model
    quantities, not a complete account of market or parameter uncertainty.
    Outputs use the same contract as ``gaussian_regime_filter``; here
    ``next_probabilities`` equals the final posterior because experts do not
    transition between states.
    """
    return _calculate(*_inputs(returns, means, stds, prior))
