"""Five inspectable analytical roles over an explicitly synthetic market model.

This is an offline research demonstrator, with no language-model calls, learned
parameters, trading actions or general-intelligence claim. The generator's
parameters are deliberately known to the filter; empirical validity is untested.
"""
from __future__ import annotations

import math
from numbers import Integral, Real

import numpy as np

from .beliefs import gaussian_regime_filter, online_gaussian_experts
from .research import content_sha256
from .scenarios import robust_cvar_allocation, scenario_cvar


def _integer(value, name, minimum, maximum):
    if isinstance(value, bool) or not isinstance(value, Integral) or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer in [{minimum}, {maximum}]")
    return int(value)


def _covariance(stds, correlation):
    """Common-factor covariance: off-diagonal correlations equal correlation."""
    stds = np.asarray(stds, dtype=float)
    return correlation * np.outer(stds, stds) + (1 - correlation) * np.diag(stds ** 2)


def review_lab_evidence(worst_cvar, regime_probabilities, observations, scenario_count):
    """Preserve missing evidence and apply explicitly illustrative research gates.

    Entropy is a dispersion diagnostic for supplied model beliefs. A low value
    cannot establish calibration, model correctness or investment suitability.
    ``research_only`` permits examination; neither outcome authorises a trade.
    """
    def finite(value):
        return (not isinstance(value, bool) and isinstance(value, Real)
                and math.isfinite(value))
    entropy = None
    try:
        p = list(regime_probabilities)
        if (len(p) >= 2 and all(finite(v) and 0 <= v <= 1 for v in p)
                and math.isclose(sum(p), 1, rel_tol=0, abs_tol=1e-12)):
            entropy = -sum(v * math.log(v) for v in p if v > 0) / math.log(len(p))
    except (TypeError, ValueError):
        pass
    count = lambda value: int(value) if isinstance(value, Integral) and not isinstance(value, bool) and value >= 0 else None
    risk = float(worst_cvar) if finite(worst_cvar) else None
    policy = {"max_cvar": .02, "max_regime_entropy": .95,
              "min_observations": 120, "min_scenarios_per_set": 400,
              "confidence": .95, "horizon_observations": 1,
              "meaning": "Illustrative thresholds, not calibrated suitability or statistical sufficiency rules."}
    checks = []
    for name, value, limit, relation in (
        ("Observed sample", count(observations), policy["min_observations"], ">="),
        ("Scenarios per set", count(scenario_count), policy["min_scenarios_per_set"], ">="),
        ("Next-state entropy", entropy, policy["max_regime_entropy"], "<="),
        ("Worst scenario CVaR", risk, policy["max_cvar"], "<="),
    ):
        passed = value is not None and (value >= limit if relation == ">=" else value <= limit)
        checks.append({"name": name, "value": value, "limit": limit, "relation": relation,
                       "passed": bool(passed), "evidence_available": value is not None})
    return {"policy": policy, "checks": checks,
            "outcome": "research_only" if all(c["passed"] for c in checks) else "blocked_for_review",
            "authority": "research review only; no order or execution path",
            "risk_budget_sweep": [{"budget": b, "worst_cvar": risk,
                                   "tail_gate_passed": risk is not None and risk <= b}
                                  for b in (.01, .015, .02, .025, .03, .04, .05)],
            "sweep_meaning": "Only the tail-risk threshold changes; this does not replace the other gates."}


def build_agent_lab(*, seed=2026, observations=320, scenario_count=600) -> dict:
    """Compute the complete seeded lab, retaining observations and scenario draws.

    Time is one hypothetical observation, with no annualisation. HMM and expert
    calculations consume the mean of four log returns. Portfolio scenarios use
    simple returns, exp(log return)-1. Each scenario set has equiprobable rows;
    the two imposed stress sets have no assigned occurrence probabilities.
    """
    seed = _integer(seed, "seed", 0, 2 ** 32 - 1)
    observations = _integer(observations, "observations", 10, 2000)
    scenario_count = _integer(scenario_count, "scenario_count", 50, 2000)
    streams = np.random.SeedSequence(seed).spawn(3)
    history_rng, scenario_rng, holdout_rng = (np.random.default_rng(s) for s in streams)
    symbols = [f"SYNTH_{i + 1}" for i in range(4)]
    means = np.array([[.0003, .0001, .00015, .00008], [-.0025, -.0002, -.0012, .00025]])
    stds = np.array([[.008, .003, .006, .002], [.026, .009, .021, .005]])
    correlations = [.25, .65]
    covariances = np.array([_covariance(s, rho) for s, rho in zip(stds, correlations)])
    cholesky = np.linalg.cholesky(covariances)
    transition = np.array([[.97, .03], [.10, .90]])
    prior = np.array([.8, .2])
    states, log_returns = [], []
    state = int(history_rng.choice(2, p=prior))
    for t in range(observations):
        if t:
            state = int(history_rng.choice(2, p=transition[state]))
        states.append(state)
        log_returns.append((means[state] + cholesky[state] @ history_rng.normal(size=4)).tolist())
    log_returns = np.asarray(log_returns)
    observed = log_returns.mean(axis=1)
    index_weights = np.full(4, .25)
    index_means = means @ index_weights
    index_stds = np.sqrt([index_weights @ c @ index_weights for c in covariances])
    beliefs = gaussian_regime_filter(observed, index_means, index_stds, transition, prior)
    expert_means, expert_stds = [.0005, 0.0, -.002], [.004, .009, .02]
    experts = online_gaussian_experts(observed, expert_means, expert_stds, [1 / 3] * 3)
    next_probabilities = beliefs["next_probabilities"]

    def draw_scenarios(rng):
        labels = rng.choice(2, size=scenario_count, p=next_probabilities)
        mixture = np.empty((scenario_count, 4))
        for k in range(2):
            selected = labels == k
            mixture[selected] = means[k] + rng.normal(size=(int(selected.sum()), 4)) @ cholesky[k].T
        # Deliberately challenge the fourth asset's calm-regime low volatility:
        # the imposed shock reverses its apparent protection without assigning
        # this event an empirically estimated probability.
        correlated = rng.normal(size=(scenario_count, 4)) @ np.linalg.cholesky(
            _covariance([.030, .012, .025, .020], .90)).T + [-.010, -.003, -.007, -.035]
        crash = rng.normal(size=(scenario_count, 4)) @ cholesky[1].T + [-.055, -.018, -.040, -.010]
        return {"regime_mixture": np.expm1(mixture),
                "correlation_stress": np.expm1(correlated),
                "crash_stress": np.expm1(crash)}

    scenarios = draw_scenarios(scenario_rng)
    # Separate draws challenge fitted scenario weights; they are never passed to the optimiser.
    heldout = draw_scenarios(holdout_rng)
    robust = robust_cvar_allocation(scenarios, confidence=.95, max_weight=.60)
    single = robust_cvar_allocation({"regime_mixture": scenarios["regime_mixture"]},
                                    confidence=.95, max_weight=.60)
    allocations = {}
    for name, result in (("equal_weight", {"weights": [.25] * 4}),
                         ("mixture_only", single), ("robust", robust)):
        allocations[name] = dict(result,
                                 evaluation=scenario_cvar(scenarios, result["weights"], .95),
                                 heldout_evaluation=scenario_cvar(heldout, result["weights"], .95))
    # The critic conservatively checks the greater fitted/held-out scenario loss.
    fitted_risk = allocations["robust"]["evaluation"]["worst_cvar"]
    heldout_risk = allocations["robust"]["heldout_evaluation"]["worst_cvar"]
    governance = review_lab_evidence(max(fitted_risk, heldout_risk), next_probabilities,
                                     observations, scenario_count)
    governance["risk_evidence"] = "Maximum of fitted and separately drawn held-out worst-scenario CVaR."
    governance["fitted_worst_cvar"] = fitted_risk
    governance["heldout_worst_cvar"] = heldout_risk
    entropy = next(c["value"] for c in governance["checks"] if c["name"] == "Next-state entropy")
    trace = [
        {"step": 1, "role": "Regime observer", "input_refs": ["data.observed_index_log_returns", "model.regimes"],
         "output_refs": ["beliefs"], "method": "Gaussian forward filtering; no smoothing", "authority": "conditional model beliefs"},
        {"step": 2, "role": "Forecast challengers", "input_refs": ["data.observed_index_log_returns", "model.experts"],
         "output_refs": ["experts"], "method": "Pre-observation predictions, likelihood update and variance decomposition", "authority": "competing fixed hypotheses"},
        {"step": 3, "role": "Scenario analyst", "input_refs": ["beliefs.next_probabilities", "model.regimes", "model.stresses", "model.random_streams", "metadata.seed", "metadata.scenario_count"],
         "output_refs": ["scenario_sets", "heldout_scenario_sets"], "method": "Joint conditional draws plus imposed shocks; independent validation stream", "authority": "specified simulated possibilities"},
        {"step": 4, "role": "Allocation proposer", "input_refs": ["scenario_sets", "model.max_weight", "model.confidence"],
         "output_refs": ["allocations"], "method": "Minimise worst supplied scenario CVaR with long-only weight cap", "authority": "hypothetical target weights; no execution"},
        {"step": 5, "role": "Critic and governor", "input_refs": ["allocations", "heldout_scenario_sets", "beliefs.next_probabilities", "governance.policy", "experts.disagreement_variance", "experts.predictive_variance", "metadata.observations", "metadata.scenario_count"],
         "output_refs": ["governance", "diagnostics"], "method": "Held-out scenario challenge, uncertainty diagnostic and non-overridable research gates", "authority": "research_only or blocked_for_review"},
    ]
    result = {
        "schema_version": "agent-lab-1.0",
        "metadata": {"synthetic": True, "seed": seed, "observations": observations,
                     "scenario_count": scenario_count, "mode": "offline deterministic agent-workflow demonstrator",
                     "scope": "Five analytical roles; no external AI model, AGI, market feed or trade execution.",
                     "assumptions": ["Known generator parameters are supplied to the regime filter; no empirical fitting.",
                                     "Three Gaussian experts are fixed; weights update without forgetting or parameter learning.",
                                     "Scenario horizon is one hypothetical observation; shocks have no occurrence probabilities.",
                                     "Simple portfolio returns exclude fees, market impact, leverage and execution.",
                                     "Held-out draws share the specified model; they do not validate real-market behaviour."]},
        "model": {"regimes": {"names": ["calm", "stress"], "log_return_means": means.tolist(),
                               "log_return_stds": stds.tolist(), "correlations": correlations,
                               "transition": transition.tolist(), "prior": prior.tolist(),
                               "observed_index_means": index_means.tolist(), "observed_index_stds": index_stds.tolist()},
                  "experts": {"names": ["narrow positive", "broad neutral", "wide negative"],
                              "means": expert_means, "stds": expert_stds, "prior": [1 / 3] * 3},
                  "stresses": {"correlation_stress": {"log_return_means": [-.010, -.003, -.007, -.035],
                                                        "log_return_stds": [.030, .012, .025, .020], "correlation": .90,
                                                        "purpose": "Joint-dependence shock with a loss in the normally low-volatility fourth asset."},
                               "crash_stress": {"log_return_means": [-.055, -.018, -.040, -.010],
                                                "log_return_stds": stds[1].tolist(), "correlation": correlations[1]}},
                  "max_weight": .60, "confidence": .95,
                  "random_streams": "NumPy SeedSequence(seed).spawn(3): history, optimisation scenarios, held-out scenarios."},
        "data": {"symbols": symbols, "observed_index_log_returns": observed.tolist(),
                 "generator_states": states, "log_returns": log_returns.tolist(),
                 "state_label_meaning": "Known simulation labels, displayed for diagnosis only and never supplied as filter observations."},
        "beliefs": beliefs, "experts": experts,
        "scenario_sets": {k: v.tolist() for k, v in scenarios.items()},
        "heldout_scenario_sets": {k: v.tolist() for k, v in heldout.items()},
        "allocations": allocations, "governance": governance, "trace": trace,
        "diagnostics": {"next_regime_entropy": entropy,
                        "final_expert_disagreement_fraction": experts["disagreement_variance"][-1] / experts["predictive_variance"][-1],
                        "disagreement_meaning": "Between fixed expert means only; shared model error and parameter uncertainty are absent."},
    }
    result["integrity_sha256"] = content_sha256(result)
    return result


def verify_agent_lab(record) -> bool:
    """Check the saved content digest, not truth, provenance or schema validity."""
    if not isinstance(record, dict) or record.get("schema_version") != "agent-lab-1.0":
        return False
    try:
        body = dict(record)
        digest = body.pop("integrity_sha256", None)
        return isinstance(digest, str) and digest == content_sha256(body)
    except (TypeError, ValueError, OverflowError, RecursionError):
        return False
