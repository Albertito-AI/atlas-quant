#!/usr/bin/env python3
"""Render five inspectable modelling stages of the offline synthetic agent lab.

The figures are derived from ``atlas_quant.agent_lab.build_agent_lab``. They do
not represent live agents, market forecasts or measured general intelligence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import numpy as np
import scipy

from atlas_quant.agent_lab import build_agent_lab
from atlas_quant.research import content_sha256
from build_visuals import COLOURS, SERIES, SVG, csv_text, regular_ticks

OUTPUT = ROOT / "docs" / "assets" / "agent-lab"
SOURCE_PATHS = ("scripts/build_agent_lab.py", "scripts/build_visuals.py",
                "src/atlas_quant/agent_lab.py", "src/atlas_quant/beliefs.py",
                "src/atlas_quant/scenarios.py", "src/atlas_quant/quant.py",
                "src/atlas_quant/research.py")
SCENARIO_LABELS = {"regime_mixture": "Regime mixture", "correlation_stress": "Correlation stress",
                   "crash_stress": "Crash stress"}
ALLOCATION_LABELS = {"equal_weight": "Equal weight", "mixture_only": "Mixture only",
                     "robust": "Worst-case CVaR"}


def compute_evidence():
    return build_agent_lab()


def chart(title, subtitle, desc, height=750):
    svg = SVG(title, subtitle, desc, height)
    svg.parts = [s.replace("FINANCIAL VISUAL ATLAS", "PROBABILISTIC AGENT LAB") for s in svg.parts]
    return svg


def time_ticks(n):
    return [(i, str(i + 1)) for i in sorted({0, (n - 1) // 4, (n - 1) // 2, 3 * (n - 1) // 4, n - 1})]


def render_beliefs(e):
    b = e["beliefs"]
    observed = e["data"]["observed_index_log_returns"]
    n = len(observed)
    svg = chart("01  Market state is a belief", "SYNTHETIC DATA  ·  Forward filtering only  ·  Gaussian emissions  ·  Fixed model parameters", "Observed synthetic index log returns and the conditional probability of the stress state, before and after each observation. The true state strip is available only from the simulator.", 800)
    max_abs = max(.01, math.ceil(max(abs(x) for x in observed) / .01) * .01)
    x, y = svg.panel(100, 185, 850, 185, "Observed index log return", (0, n - 1), (-max_abs, max_abs), time_ticks(n), regular_ticks(-max_abs, max_abs, 5, scale=100, suffix="%", decimals=1), "Observation number", "Log return per observation")
    svg.line(x(0), y(0), x(n - 1), y(0), COLOURS["muted"])
    svg.path([(x(i), y(v)) for i, v in enumerate(observed)], SERIES[0], 1.7)
    svg.legend(100, 446, [("Stress probability before observation", SERIES[1], "6 4"), ("Stress probability after observation", SERIES[2], None)], step=420)
    x, y = svg.panel(100, 490, 850, 135, "Update beliefs as evidence arrives", (0, n - 1), (0, 1), time_ticks(n), regular_ticks(0, 1, 5, scale=100, suffix="%"), "Observation number", "Conditional probability")
    for field, colour, dash in (("prior_probabilities", SERIES[1], "6 4"), ("posterior_probabilities", SERIES[2], None)):
        svg.path([(x(i), y(v[1])) for i, v in enumerate(b[field])], colour, 2, dash)
    svg.text(100, 704, "Simulator state: teal = calm; orange = stress. This strip is not supplied to the filter.", 11)
    states = e["data"]["generator_states"]
    for i, state in enumerate(states):
        svg.rect(100 + i * 850 / n, 682, 850 / n + .1, 8, SERIES[0 if state == 0 else 2])
    svg.footer(["Prior probabilities precede the observation; posterior probabilities include it. No backward smoothing or future observations.", "The emissions and transition model are supplied assumptions. Belief concentration does not prove the model describes a real market."])
    return svg.finish()


def render_experts(e):
    a = e["experts"]
    n = len(a["predictive_mean"])
    k = len(a["prior_probabilities"][0])
    svg = chart("02  Carry uncertainty through the calculation", "SYNTHETIC DATA  ·  Sequential Bayesian expert mixture  ·  Weights shown before each observation", "Before-observation probabilities of fixed Gaussian candidate models and the decomposition of the resulting predictive variance into within-model variance and between-model mean disagreement.", 800)
    svg.legend(100, 142, [(f"Expert {i + 1}", SERIES[i % 4], None) for i in range(k)], step=260)
    x, y = svg.panel(100, 190, 850, 180, "Model weights used for the next predictive calculation", (0, n - 1), (0, 1), time_ticks(n), regular_ticks(0, 1, 5, scale=100, suffix="%"), "Observation number", "Conditional model weight")
    for j in range(k):
        svg.path([(x(i), y(row[j])) for i, row in enumerate(a["prior_probabilities"])], SERIES[j % 4], 2)
    svg.legend(100, 450, [("Within-model variance", SERIES[0], None), ("Between-model mean disagreement", SERIES[2], None)], step=420)
    within = np.asarray(a["aleatoric_variance"]) * 1e4
    between = np.asarray(a["disagreement_variance"]) * 1e4
    maximum = max(.01, float(np.max(within + between)) * 1.12)
    x, y = svg.panel(100, 490, 850, 150, "Predictive variance is the sum of both components", (0, n - 1), (0, maximum), time_ticks(n), regular_ticks(0, maximum, 5, decimals=2), "Observation number", "Variance (percentage points squared)")
    for values, colour in ((within, SERIES[0]), (between, SERIES[2])):
        svg.path([(x(i), y(float(v))) for i, v in enumerate(values)], colour, 2.5)
    svg.footer(["Variance = weighted within-model variance + weighted squared distance of model means from the mixture mean.", "Candidate models are fixed. A near-certain weight or small disagreement can coexist with common misspecification and poor forecasts."])
    return svg.finish()


def render_scenarios(e):
    scenarios = e["scenario_sets"]
    arrays = [np.asarray(v) for v in scenarios.values()]
    xmin = math.floor(min(float(a[:, 0].min()) for a in arrays) / .05) * .05
    xmax = math.ceil(max(float(a[:, 0].max()) for a in arrays) / .05) * .05
    ymin = math.floor(min(float(a[:, 1].min()) for a in arrays) / .02) * .02
    ymax = math.ceil(max(float(a[:, 1].max()) for a in arrays) / .02) * .02
    svg = chart("03  Examine joint outcomes and imposed shocks", "MODELLED SCENARIOS  ·  Fitting draws  ·  Same axis scales  ·  One-observation simple returns", "Three panels show every fitting draw of simultaneous returns of the first two synthetic assets. The probabilistic regime mixture is separate from imposed correlation and crash stress sets; the stress sets are not assigned occurrence probabilities.", 730)
    for j, (name, values) in enumerate(scenarios.items()):
        a = np.asarray(values)
        left = 90 + j * 320
        x, y = svg.panel(left, 200, 250, 300, SCENARIO_LABELS[name], (xmin, xmax), (ymin, ymax), regular_ticks(xmin, xmax, 4, scale=100, suffix="%"), regular_ticks(ymin, ymax, 5, scale=100, suffix="%"), "SYNTH_1 simple return", "SYNTH_2 simple return")
        for r in a:
            svg.parts.append(f'<circle cx="{x(r[0]):.3f}" cy="{y(r[1]):.3f}" r="1.6" fill="{SERIES[j]}" fill-opacity="0.46"/>')
        if xmin <= 0 <= xmax:
            svg.line(x(0), y(ymin), x(0), y(ymax), COLOURS["muted"], .7, "3 3")
        if ymin <= 0 <= ymax:
            svg.line(x(xmin), y(0), x(xmax), y(0), COLOURS["muted"], .7, "3 3")
        svg.text(left + 125, 583, f"{len(a):,} joint draws; 4 assets per draw", 12, anchor="middle")
    svg.footer(["The mixture uses the next-state probabilities after the observed history. Stress distributions are deliberately imposed assumptions.", "Only two asset dimensions are displayed; optimisation uses all four. These finite scenarios cannot exhaust possible market outcomes."])
    return svg.finish()


def render_allocation(e):
    allocations = e["allocations"]
    keys = list(allocations)
    scenarios = list(e["scenario_sets"])
    svg = chart("04  Optimise against several possible worlds", "MODEL OUTPUT  ·  Long-only targets  ·  60% cap  ·  Empirical CVaR at 95%  ·  No execution or fees", "Target allocations for equal weight, optimisation of the probabilistic mixture alone, and minimisation of the worst CVaR across all scenario sets. Bars compare fitted tail loss; outlined points show separate held-out draws under the same models.", 850)
    svg.legend(100, 142, [(symbol, SERIES[i], None) for i, symbol in enumerate(e["data"]["symbols"])], step=220)
    x, y = svg.panel(100, 190, 850, 180, "Research target weights", (-.5, len(keys) - .5), (0, 1), [(i, ALLOCATION_LABELS[k]) for i, k in enumerate(keys)], regular_ticks(0, 1, 5, scale=100, suffix="%"), "Allocation rule", "Target portfolio weight")
    for i, key in enumerate(keys):
        bottom = 0.0
        for j, weight in enumerate(allocations[key]["weights"]):
            svg.rect(x(i) - 60, y(bottom + weight), 120, 180 * weight, SERIES[j])
            if weight >= .08:
                svg.text(x(i), y(bottom + weight / 2) + 4, f"{weight:.1%}", 12, colour="#ffffff", anchor="middle", weight=700)
            bottom += weight
    values = [allocations[k][field]["per_scenario_cvar"][s]
              for k in keys for s in scenarios for field in ("evaluation", "heldout_evaluation")]
    lo, hi = min(0, min(values)), max(.01, max(values) * 1.15)
    svg.legend(100, 446, [(ALLOCATION_LABELS[k], SERIES[i], None) for i, k in enumerate(keys)], step=280)
    x, y = svg.panel(100, 495, 850, 165, "Same candidate, different tail-loss assumptions", (-.5, len(scenarios) - .5), (lo, hi), [(i, SCENARIO_LABELS[s]) for i, s in enumerate(scenarios)], regular_ticks(lo, hi, 5, scale=100, suffix="%", decimals=1), "Scenario set", "CVaR of one-observation loss")
    for j, scenario in enumerate(scenarios):
        for i, key in enumerate(keys):
            value = allocations[key]["evaluation"]["per_scenario_cvar"][scenario]
            left = x(j) + (i - 1) * 44 - 19
            svg.rect(left, min(y(value), y(0)), 38, abs(y(value) - y(0)), SERIES[i], 2)
            heldout = allocations[key]["heldout_evaluation"]["per_scenario_cvar"][scenario]
            svg.parts.append(f'<circle cx="{left + 19:.3f}" cy="{y(heldout):.3f}" r="4" fill="#ffffff" stroke="{COLOURS["ink"]}" stroke-width="1.3"/>')
    svg.text(100, 736, "Bars: fitting scenarios. Outlined points: separate held-out draws; weights remain fixed.", 12)
    svg.footer(["Worst-case optimisation minimises the largest supplied tail loss. Its trade-off depends on the deliberately constructed stress sets.", "Targets omit fees and liquidity and have no expected-return target. Held-out draws test these models only; they offer no market guarantee."])
    return svg.finish()


def render_governance(e):
    g = e["governance"]
    sweep = g["risk_budget_sweep"]
    svg = chart("05  A calculation can still require abstention", "MODEL OUTPUT  ·  Deterministic governance  ·  Explicit thresholds and preserved evidence", "Risk-budget sensitivity shows whether the tail-risk gate passes for the same robust allocation. The complete outcome also depends on the other recorded gates and never authorises a trade.", 750)
    blocked = g["outcome"] == "blocked_for_review"
    svg.rect(100, 138, 850, 64, "#fff0ec" if blocked else "#e0f1ee", 8)
    svg.text(124, 166, "RECORDED OUTCOME", 11, colour=COLOURS["muted"], weight=700)
    svg.text(124, 190, g["outcome"], 20, colour=SERIES[2] if blocked else SERIES[0], weight=700)
    maximum = max([row["budget"] for row in sweep] + [row["worst_cvar"] for row in sweep]) * 1.12
    x, y = svg.panel(100, 270, 850, 215, "Change the risk budget; keep the proposed weights fixed", (-.5, len(sweep) - .5), (0, maximum), [(i, f'{row["budget"]:.1%}') for i, row in enumerate(sweep)], regular_ticks(0, maximum, 5, scale=100, suffix="%", decimals=1), "Illustrative CVaR budget", "One-observation loss fraction")
    for i, row in enumerate(sweep):
        svg.rect(x(i) - 32, y(row["budget"]), 64, y(0) - y(row["budget"]), "#badbd6" if row["tail_gate_passed"] else "#efc7b3", 3)
        svg.dot(x(i), y(row["worst_cvar"]), COLOURS["ink"], 4)
        svg.text(x(i), 562, "Tail pass" if row["tail_gate_passed"] else "Tail block", 11, anchor="middle", colour=SERIES[0] if row["tail_gate_passed"] else SERIES[2], weight=700)
    svg.line(x(0), y(sweep[0]["worst_cvar"]), x(len(sweep) - 1), y(sweep[-1]["worst_cvar"]), COLOURS["ink"], 2, "5 4")
    svg.text(100, 607, f'Current CVaR budget: {g["policy"]["max_cvar"]:.1%}. Current normalised regime-entropy limit: {g["policy"]["max_regime_entropy"]:.2f}.', 13)
    svg.footer(["Bars are candidate budgets; the line is max(fitted, held-out) worst-scenario CVaR for fixed weights. This sweep isolates one gate.", "The full outcome also applies evidence and uncertainty checks. Passing a gate permits research review only; it cannot approve a trade."])
    return svg.finish()


def derived_files(e):
    files = {name + ".svg": render(e) for name, render in (
        ("regime-beliefs", render_beliefs), ("expert-uncertainty", render_experts),
        ("scenario-clouds", render_scenarios), ("robust-allocation", render_allocation),
        ("governance-gates", render_governance))}
    b, a = e["beliefs"], e["experts"]
    files["data/regime-beliefs.csv"] = csv_text(
        ["observation", "index_log_return", "simulator_state", "prior_stress_probability", "posterior_stress_probability"],
        ([i + 1, r, e["data"]["generator_states"][i], b["prior_probabilities"][i][1], b["posterior_probabilities"][i][1]] for i, r in enumerate(e["data"]["observed_index_log_returns"])))
    k = len(a["prior_probabilities"][0])
    files["data/expert-uncertainty.csv"] = csv_text(
        ["observation"] + [f"prior_expert_{i+1}" for i in range(k)] + ["predictive_mean", "predictive_variance", "within_model_variance", "mean_disagreement_variance", "log_predictive_density"],
        ([i + 1] + row + [a[key][i] for key in ("predictive_mean", "predictive_variance", "aleatoric_variance", "disagreement_variance", "log_predictive_density")] for i, row in enumerate(a["prior_probabilities"])))
    files["data/scenarios.csv"] = csv_text(["sample", "scenario", "draw"] + e["data"]["symbols"],
        ([sample, name, i + 1] + row for sample, sets in (("fitting", e["scenario_sets"]), ("held_out", e["heldout_scenario_sets"]))
         for name, values in sets.items() for i, row in enumerate(values)))
    scenarios = list(e["scenario_sets"])
    files["data/allocations.csv"] = csv_text(["allocation", "sample"] + e["data"]["symbols"] + [name + "_cvar" for name in scenarios] + ["worst_cvar"],
        ([name, sample] + record["weights"] + [record[field]["per_scenario_cvar"][s] for s in scenarios] + [record[field]["worst_cvar"]]
         for name, record in e["allocations"].items() for sample, field in (("fitting", "evaluation"), ("held_out", "heldout_evaluation"))))
    files["data/governance.csv"] = csv_text(["budget", "worst_cvar", "tail_gate_passed"],
        ([row["budget"], row["worst_cvar"], row["tail_gate_passed"]] for row in e["governance"]["risk_budget_sweep"]))
    return files


def verify_saved_integrity(e):
    body = dict(e)
    recorded = body.pop("integrity_sha256", None)
    if not isinstance(recorded, str) or recorded != content_sha256(body):
        raise ValueError("Saved lab evidence integrity digest does not match its content")


def compare_evidence(actual, expected, path="evidence"):
    """Allow rounding differences, never missing values or changed decision gates."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise ValueError(f"{path}: keys changed")
        for key in expected:
            if key != "integrity_sha256":
                compare_evidence(actual[key], expected[key], f"{path}.{key}")
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise ValueError(f"{path}: array length changed")
        for i, (a, b) in enumerate(zip(actual, expected)):
            compare_evidence(a, b, f"{path}[{i}]")
    elif isinstance(expected, (float, int)) and not isinstance(expected, bool):
        if (isinstance(actual, bool) or not isinstance(actual, (float, int))
                or not math.isclose(actual, expected, rel_tol=2e-6, abs_tol=2e-8)):
            raise ValueError(f"{path}: numerical evidence changed")
    elif actual != expected or type(actual) is not type(expected):
        raise ValueError(f"{path}: value changed")


def make_bundle(e):
    verify_saved_integrity(e)
    files = derived_files(e)
    files["data/evidence.json"] = json.dumps(e, indent=2, allow_nan=False) + "\n"
    manifest = {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__,
                "evidence_sha256": e["integrity_sha256"],
                "sources": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCE_PATHS},
                "files": {name: hashlib.sha256(value.encode()).hexdigest() for name, value in files.items()},
                "meaning": "Reproducible synthetic/model evidence and local build environment; not a signature, external audit or intelligence benchmark."}
    files["data/manifest.json"] = json.dumps(manifest, indent=2, allow_nan=False) + "\n"
    return files


def verify_bundle(output, generated=None):
    e = json.loads((output / "data/evidence.json").read_text(encoding="utf-8"))
    manifest = json.loads((output / "data/manifest.json").read_text(encoding="utf-8"))
    verify_saved_integrity(e)
    if manifest["evidence_sha256"] != e["integrity_sha256"]:
        raise ValueError("Manifest evidence digest does not match saved evidence")
    compare_evidence(compute_evidence() if generated is None else generated, e)
    derived = derived_files(e)
    expected = set(derived) | {"data/evidence.json"}
    if set(manifest["files"]) != expected or set(manifest["sources"]) != set(SOURCE_PATHS):
        raise ValueError("Manifest inventory is incomplete or unexpected")
    for name in SOURCE_PATHS:
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != manifest["sources"][name]:
            raise ValueError(f"{name}: source changed; regenerate agent lab visuals")
    for name in expected:
        path = output / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != manifest["files"][name]:
            raise ValueError(f"{name}: missing asset or hash mismatch")
        if name in derived and path.read_text(encoding="utf-8") != derived[name]:
            raise ValueError(f"{name}: rendering does not match numerical evidence")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    evidence = compute_evidence()
    if args.check:
        verify_bundle(args.output, evidence)
        print("Agent lab verified: five SVGs, five CSVs and the saved evidence agree.")
    else:
        files = make_bundle(evidence)
        for name, value in files.items():
            path = args.output / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(value, encoding="utf-8", newline="\n")
        print(f"Wrote {len(files)} agent-lab files to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
