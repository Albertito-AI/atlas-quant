#!/usr/bin/env python3
"""Rebuild the financial visual atlas using only Atlas Quant and its dependencies.

Run ``python scripts/build_visuals.py`` from a source checkout. ``--check``
recomputes the numerical evidence with a small floating-point tolerance, then
checks that the committed SVG and CSV files exactly render that evidence.
No network requests, JavaScript, external fonts or plotting packages are used.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
from html import escape
import io
import json
import math
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import numpy as np
import scipy

from atlas_quant.backtest import run_backtest, strategy_weights
from atlas_quant.data import PriceDataset, synthetic_prices
from atlas_quant.quant import (binomial_price, black_scholes, drawdown,
                               historical_risk, monte_carlo_price, option_greeks)

OUTPUT = ROOT / "docs" / "assets"
COLOURS = {"ink": "#162c42", "muted": "#52677a", "teal": "#007f80",
           "blue": "#4674bd", "orange": "#be581d", "purple": "#8153a2",
           "grid": "#dce4e9", "bg": "#f7f9fb", "red": "#a53b4a"}
SERIES = [COLOURS[c] for c in ("teal", "blue", "orange", "purple")]
SETTINGS = dict(lookback=60, rebalance_every=21, initial_cash=100000.0,
                max_weight=0.5, periods_per_year=252)
MODEL = dict(spot=100.0, strike=100.0, maturity=1.0, rate=.05,
             volatility=.2, dividend=0.0, option="call")


def compute_evidence() -> dict:
    """Collect actual public API results; no financial formula is reimplemented."""
    data = synthetic_prices(days=504, assets=4, seed=42)
    selected = run_backtest(data, strategy="minimum_variance", transaction_cost_bps=10, **SETTINGS)
    baseline = run_backtest(data, strategy="equal_weight", transaction_cost_bps=10, **SETTINGS)
    returns = data.prices[1:] / data.prices[:-1] - 1
    training = returns[:SETTINGS["lookback"]]
    costs = []
    for bps in (0, 10, 25, 50):
        case = run_backtest(data, strategy="minimum_variance", transaction_cost_bps=bps, **SETTINGS)
        costs.append({"cost_bps": bps, "final_equity": case.equity_curve[-1],
                      "total_cost": case.metrics["total_transaction_cost"],
                      "total_return": case.metrics["total_return"]})
    option_curve = []
    for spot in np.linspace(60, 140, 81):
        inputs = dict(MODEL, spot=float(spot))
        call = black_scholes(**inputs)
        put = black_scholes(**dict(inputs, option="put"))
        option_curve.append({"spot": float(spot), "call": call, "put": put,
                             "intrinsic_call": max(float(spot) - MODEL["strike"], 0),
                             "call_delta": option_greeks(**inputs)["delta"],
                             "put_delta": option_greeks(**dict(inputs, option="put"))["delta"]})
    analytical = black_scholes(**MODEL)
    trees = [{"steps": steps, "price": binomial_price(**MODEL, steps=steps)}
             for steps in (10, 20, 40, 80, 160, 320, 640)]
    simulations = [monte_carlo_price(**MODEL, paths=n, seed=42)
                   for n in (200, 1000, 5000, 20000, 100000)]
    losses = -np.asarray(selected.net_returns)
    counts, edges = np.histogram(losses, bins=30)
    return {
        "schema_version": "1.0",
        "provenance": {"synthetic": True, "generator": "atlas_quant.data.synthetic_prices",
                       "seed": 42, "price_rows": 504, "assets": 4,
                       "dataset_sha256": data.sha256, "symbols": list(data.symbols),
                       "dates": list(data.dates), "prices": data.prices.tolist()},
        "settings": dict(SETTINGS, strategy="minimum_variance", transaction_cost_bps=10),
        "performance": {"dates": selected.dates, "selected_equity": selected.equity_curve,
                        "baseline_equity": baseline.equity_curve,
                        "selected_drawdown": drawdown(selected.net_returns).tolist(),
                        "baseline_drawdown": drawdown(baseline.net_returns).tolist(),
                        "net_returns": selected.net_returns},
        "cost_scenarios": costs,
        "allocation": {"signal_date": data.dates[60], "execution_date": data.dates[61],
                       "training_return_count": 60,
                       "weights": {strategy: strategy_weights(training, strategy, .5).tolist()
                                   for strategy in ("equal_weight", "inverse_volatility", "minimum_variance")},
                       "correlation": np.corrcoef(training, rowvar=False).tolist()},
        "options": {"inputs": MODEL, "curve": option_curve, "analytical": analytical,
                    "trees": trees, "monte_carlo": simulations},
        "tail_risk": {"risk": historical_risk(selected.net_returns),
                      "bin_edges": edges.tolist(), "counts": counts.tolist()},
    }


class SVG:
    """Small deterministic SVG renderer. Every textual field is escaped."""
    def __init__(self, title: str, subtitle: str, description: str, height=680):
        self.height = height
        self.parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1040" height="{height}" viewBox="0 0 1040 {height}" role="img" aria-labelledby="title desc">',
                      f'<title id="title">{escape(title)}</title><desc id="desc">{escape(description)}</desc>',
                      '<style>text{font-family:Arial,Helvetica,sans-serif} .muted{fill:#52677a}</style>',
                      f'<rect width="1040" height="{height}" rx="18" fill="#f7f9fb"/>',
                      '<rect x="0" y="0" width="1040" height="8" fill="#007f80"/>']
        self.text(36, 39, "ATLAS QUANT  /  FINANCIAL VISUAL ATLAS", 12, colour=COLOURS["teal"], weight=700)
        self.text(36, 76, title, 27, weight=700)
        self.text(36, 103, subtitle, 13, colour=COLOURS["muted"])

    def text(self, x, y, value, size=12, colour=None, anchor="start", weight=400, rotate=None):
        transform = f' transform="rotate({rotate} {x} {y})"' if rotate is not None else ""
        self.parts.append(f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" fill="{colour or COLOURS["ink"]}" text-anchor="{anchor}" font-weight="{weight}"{transform}>{escape(str(value))}</text>')

    def line(self, x1, y1, x2, y2, colour=None, width=1, dash=None):
        dashed = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(f'<line x1="{x1:.3f}" y1="{y1:.3f}" x2="{x2:.3f}" y2="{y2:.3f}" stroke="{colour or COLOURS["grid"]}" stroke-width="{width}"{dashed}/>')

    def rect(self, x, y, w, h, fill, radius=0):
        self.parts.append(f'<rect x="{x:.3f}" y="{y:.3f}" width="{w:.3f}" height="{h:.3f}" fill="{fill}" rx="{radius}"/>')

    def path(self, points, colour, width=2.5, dash=None):
        value = " ".join(f'{"M" if i == 0 else "L"}{x:.3f},{y:.3f}' for i, (x, y) in enumerate(points))
        dashed = f' stroke-dasharray="{dash}"' if dash else ""
        self.parts.append(f'<path d="{value}" fill="none" stroke="{colour}" stroke-width="{width}" stroke-linejoin="round"{dashed}/>')

    def dot(self, x, y, colour, r=4):
        self.parts.append(f'<circle cx="{x:.3f}" cy="{y:.3f}" r="{r}" fill="{colour}"/>')

    def legend(self, x, y, entries, step=220):
        for i, (label, colour, dash) in enumerate(entries):
            left = x + i * step
            self.line(left, y - 4, left + 25, y - 4, colour, 3, dash)
            self.text(left + 34, y, label, 12)

    def panel(self, x, y, w, h, title, xlim, ylim, xticks, yticks, xlabel, ylabel):
        self.text(x, y - 18, title, 16, weight=700)
        self.rect(x, y, w, h, "#ffffff", 5)
        def tx(v):
            return x + (v - xlim[0]) / (xlim[1] - xlim[0]) * w
        def ty(v):
            return y + h - (v - ylim[0]) / (ylim[1] - ylim[0]) * h
        for value, label in yticks:
            self.line(x, ty(value), x + w, ty(value))
            self.text(x - 12, ty(value) + 4, label, 11, anchor="end", colour=COLOURS["muted"])
        for value, label in xticks:
            self.line(tx(value), y + h, tx(value), y + h + 5)
            self.text(tx(value), y + h + 23, label, 11, anchor="middle", colour=COLOURS["muted"])
        self.text(x + w / 2, y + h + 48, xlabel, 12, anchor="middle")
        self.text(x - 55, y + h / 2, ylabel, 12, anchor="middle", rotate=-90)
        return tx, ty

    def footer(self, lines):
        self.line(36, self.height - 75, 1004, self.height - 75)
        for i, line in enumerate(lines):
            self.text(36, self.height - 51 + i * 19, line, 11, colour=COLOURS["muted"])

    def finish(self):
        return "\n".join(self.parts + ["</svg>", ""])


def regular_ticks(lower, upper, count=5, scale=1, suffix="", decimals=0):
    return [(v, f"{v * scale:,.{decimals}f}{suffix}") for v in np.linspace(lower, upper, count)]


def render_performance(e):
    p = e["performance"]
    n = len(p["dates"])
    svg = SVG("Wealth and the path of losses", "SYNTHETIC DATA  ·  Four generated assets  ·  Seed 42  ·  Same dates, execution lag and fees", "Minimum-variance and equal-weight simulated wealth with signed drawdown including initial cash. These are generated paths, not observed returns.", 800)
    svg.legend(100, 140, [("Minimum variance", SERIES[0], None), ("Equal-weight baseline", SERIES[1], "7 4")])
    xticks = [(i, p["dates"][i][:7]) for i in (0, 110, 220, 330, n - 1)]
    curves = [p["selected_equity"], p["baseline_equity"]]
    lo = math.floor(min(min(x) for x in curves) / 10000) * 10000
    hi = math.ceil(max(max(x) for x in curves) / 10000) * 10000
    x, y = svg.panel(100, 185, 850, 205, "01  Net wealth, including entry costs", (0, n - 1), (lo, hi), xticks, regular_ticks(lo, hi, scale=.001, suffix="k"), "Synthetic calendar date", "Wealth (currency units)")
    for values, colour, dash in zip(curves, SERIES, (None, "7 4")):
        svg.path([(x(i), y(v)) for i, v in enumerate(values)], colour, dash=dash)
    dds = [p["selected_drawdown"], p["baseline_drawdown"]]
    low = min(-.05, math.floor(min(min(v) for v in dds) / .05) * .05)
    x, y = svg.panel(100, 495, 850, 150, "02  Drawdown from each path's running peak", (0, n - 1), (low, 0), xticks, regular_ticks(low, 0, round(abs(low) / .05) + 1, scale=100, suffix="%"), "Synthetic calendar date", "Signed drawdown")
    for values, colour, dash in zip(dds, SERIES, (None, "7 4")):
        svg.path([(x(i), y(v)) for i, v in enumerate(values)], colour, dash=dash)
    svg.footer(["Initial wealth 100,000; 60-return lookback; rebalance every 21 observations; target weight cap 50%; 10 bps per side.", "Signals at close t execute at close t+1. Fractional shares and full liquidity assumed; no terminal liquidation fee."])
    return svg.finish()


def render_costs(e):
    cases = e["cost_scenarios"]
    svg = SVG("Costs change the result", "SYNTHETIC DATA  ·  One fixed path and strategy  ·  Only the per-side fee changes", "Two bar charts show final wealth and total fees for zero, ten, twenty-five and fifty basis points per side. Fee sums differ from the final-wealth difference because cash flows compound differently.")
    xticks = [(i, str(row["cost_bps"])) for i, row in enumerate(cases)]
    for left, key, title, ylabel in [(100, "final_equity", "Final portfolio wealth", "Currency units"), (595, "total_cost", "Sum of transaction fees", "Currency units")]:
        maximum = math.ceil(max(row[key] for row in cases) / (20000 if key == "final_equity" else 500)) * (20000 if key == "final_equity" else 500)
        x, y = svg.panel(left, 190, 345, 310, title, (-.6, 3.6), (0, maximum), xticks, regular_ticks(0, maximum, 5, scale=.001, suffix="k", decimals=1), "Per-side cost (basis points)", ylabel)
        for i, row in enumerate(cases):
            svg.rect(x(i) - 24, y(row[key]), 48, y(0) - y(row[key]), SERIES[0 if key == "final_equity" else 2], 3)
            svg.text(x(i), y(row[key]) - 12, f'{row[key]:,.0f}', 12, anchor="middle", weight=700)
    svg.footer(["Both purchases and sales incur fees on gross traded notional. Each scenario reruns the self-financing ledger.", "The wealth difference includes compounding effects; it is not identical to the sum of fees. No liquidity or market-impact model."])
    return svg.finish()


def render_allocation(e):
    a = e["allocation"]
    svg = SVG("From observed variation to weights", f'SYNTHETIC DATA  ·  First signal: {a["signal_date"]}  ·  Execution: {a["execution_date"]}  ·  60 training returns', "First-signal target weights for three implemented strategies alongside the corresponding training-return correlation matrix. The optimiser uses ten per cent diagonal covariance shrinkage and a fifty per cent weight cap.")
    labels = ("Equal weight", "Inverse volatility", "Minimum variance")
    svg.legend(100, 145, [(f"SYNTH_{i + 1}", c, None) for i, c in enumerate(SERIES)], step=220)
    x, y = svg.panel(100, 215, 390, 270, "Target allocation at the first signal", (-.6, 2.6), (0, 1), list(enumerate(labels)), regular_ticks(0, 1, 5, scale=100, suffix="%"), "Allocation method", "Portfolio weight")
    for i, values in enumerate(a["weights"].values()):
        bottom = 0.0
        for weight, colour in zip(values, SERIES):
            svg.rect(x(i) - 29, y(bottom + weight), 58, weight * 270, colour)
            if weight >= .08:
                svg.text(x(i), y(bottom + weight / 2) + 4, f"{weight:.0%}", 11, colour="#ffffff", anchor="middle", weight=700)
            bottom += weight
    svg.text(610, 197, "Training-return correlation", 16, weight=700)
    matrix = a["correlation"]
    for row in range(4):
        svg.text(604, 252 + row * 64, str(row + 1), 12, anchor="end")
        svg.text(646 + row * 64, 502, str(row + 1), 12, anchor="middle")
        for col in range(4):
            value = matrix[row][col]
            rgb = tuple(round(244 + (target - 244) * abs(value)) for target in ((0, 127, 128) if value >= 0 else (190, 88, 29)))
            colour = "#" + "".join(f"{v:02x}" for v in rgb)
            svg.rect(614 + col * 64, 215 + row * 64, 62, 62, colour, 4)
            svg.text(645 + col * 64, 252 + row * 64, f"{value:.2f}", 13, colour="#ffffff" if abs(value) > .65 else COLOURS["ink"], anchor="middle", weight=700)
    svg.text(740, 532, "Rows and columns: SYNTH_1 to SYNTH_4", 12, anchor="middle")
    svg.text(740, 555, "Scale: −1 (orange), 0 (pale), +1 (teal)", 11, anchor="middle")
    svg.footer(["Minimum variance minimises estimated wᵀΣw with weights summing to one, no shorts and a 50% target cap.", "Correlation uses the raw training returns. The optimiser uses covariance with 10% diagonal shrinkage; realised weights can drift."])
    return svg.finish()


def render_options(e):
    curve = e["options"]["curve"]
    svg = SVG("Option value and sensitivity", "MODEL OUTPUT  ·  European exercise  ·  Strike 100  ·  1 year  ·  Rate 5%  ·  Volatility 20%  ·  Dividend yield 0%", "Black-Scholes call and put prices over spot levels sixty to one hundred and forty, call intrinsic value, and analytic call and put deltas. Monetary values use the same arbitrary currency unit as spot and strike.")
    svg.legend(100, 148, [("Call", SERIES[0], None), ("Put", SERIES[1], "7 4"), ("Call intrinsic value", SERIES[2], "3 4")], step=280)
    x, y = svg.panel(100, 210, 350, 280, "Black–Scholes valuation", (60, 140), (0, 50), regular_ticks(60, 140), regular_ticks(0, 50, 6), "Spot (currency units)", "Option price (currency units)")
    for key, colour, dash in (("call", SERIES[0], None), ("put", SERIES[1], "7 4"), ("intrinsic_call", SERIES[2], "3 4")):
        svg.path([(x(row["spot"]), y(row[key])) for row in curve], colour, dash=dash)
    x, y = svg.panel(595, 210, 350, 280, "Analytic delta", (60, 140), (-1, 1), regular_ticks(60, 140), regular_ticks(-1, 1, 5, decimals=1), "Spot (currency units)", "Price change per unit spot")
    svg.line(x(60), y(0), x(140), y(0), COLOURS["muted"], 1)
    for key, colour, dash in (("call_delta", SERIES[0], None), ("put_delta", SERIES[1], "7 4")):
        svg.path([(x(row["spot"]), y(row[key])) for row in curve], colour, dash=dash)
    svg.footer(["Rates and dividend yield are continuously compounded; volatility is annualised. Values are conditional on these inputs.", "The model assumes constant volatility and rates, European exercise and continuous yield; these curves are not market quotes."])
    return svg.finish()


def render_convergence(e):
    o = e["options"]
    svg = SVG("Different methods, one pricing model", "MODEL OUTPUT  ·  European call  ·  Spot = strike = 100  ·  T = 1 year  ·  r = 5%  ·  σ = 20%  ·  q = 0%", "Even-step Cox-Ross-Rubinstein tree errors approach the Black-Scholes reference. Monte Carlo estimates show approximate ninety-five per cent intervals based on independent antithetic pair averages.", 720)
    svg.text(100, 145, f'Black–Scholes reference: {o["analytical"]:.8f} currency units', 15, weight=700, colour=SERIES[0])
    trees, simulations = o["trees"], o["monte_carlo"]
    errors = [row["price"] - o["analytical"] for row in trees]
    low = math.floor(min(errors) / .05) * .05
    x, y = svg.panel(100, 210, 350, 280, "Binomial discretisation error", (-.3, 6.3), (low, .01), [(i, str(r["steps"])) for i, r in enumerate(trees)], regular_ticks(low, 0, 5, decimals=2), "Tree steps (categorical, all even)", "Tree price minus reference")
    svg.line(x(-.3), y(0), x(6.3), y(0), COLOURS["muted"], 1, "5 4")
    svg.path([(x(i), y(error)) for i, error in enumerate(errors)], SERIES[0])
    for i, error in enumerate(errors):
        svg.dot(x(i), y(error), SERIES[0])
    lo = math.floor(min(r["ci_low"] for r in simulations) * 2) / 2
    hi = math.ceil(max(r["ci_high"] for r in simulations) * 2) / 2
    x, y = svg.panel(595, 210, 350, 280, "Monte Carlo sampling uncertainty", (-.4, 4.4), (lo, hi), [(i, f'{r["paths"] // 1000}k' if r["paths"] >= 1000 else str(r["paths"])) for i, r in enumerate(simulations)], regular_ticks(lo, hi, 5, decimals=1), "Terminal paths (categorical)", "Option price (currency units)")
    svg.line(x(-.4), y(o["analytical"]), x(4.4), y(o["analytical"]), SERIES[0], 2, "5 4")
    for i, row in enumerate(simulations):
        svg.line(x(i), y(row["ci_low"]), x(i), y(row["ci_high"]), SERIES[1], 2)
        for bound in ("ci_low", "ci_high"):
            svg.line(x(i) - 7, y(row[bound]), x(i) + 7, y(row[bound]), SERIES[1], 2)
        svg.dot(x(i), y(row["price"]), SERIES[1], 5)
    svg.legend(100, 583, [("Model reference", SERIES[0], "5 4"), ("Estimate and 95% interval", SERIES[1], None)], step=440)
    svg.footer(["Monte Carlo uses antithetic pairs; independent observations = terminal paths / 2. Seed 42 is reused, so estimates are correlated.", "Intervals describe sampling uncertainty under the chosen model. They exclude parameter uncertainty and model misspecification."])
    return svg.finish()


def render_tail(e):
    tail = e["tail_risk"]
    risk = tail["risk"]
    edges, counts = tail["bin_edges"], tail["counts"]
    n = len(e["performance"]["net_returns"])
    svg = SVG("Inspect the observed loss tail", f'SYNTHETIC DATA  ·  Minimum-variance simulation  ·  {n} one-observation net returns  ·  Loss = −return', "Histogram of simulated single-period losses with empirical ninety-five per cent value at risk and expected shortfall. Expected shortfall uses fractional weighting of the worst five per cent of observations.")
    svg.legend(100, 145, [(f'VaR 95%: {risk["var"]:.2%}', SERIES[2], "6 4"), (f'Expected shortfall 95%: {risk["expected_shortfall"]:.2%}', COLOURS["red"], "3 3")], step=420)
    max_count = math.ceil(max(counts) / 10) * 10
    low = math.floor(edges[0] / .005) * .005
    high = math.ceil(edges[-1] / .005) * .005
    x, y = svg.panel(100, 210, 850, 280, "Distribution of net one-observation losses", (low, high), (0, max_count), regular_ticks(low, high, round((high - low) / .005) + 1, scale=100, suffix="%", decimals=1), regular_ticks(0, max_count, 5), "Loss as a fraction of previous wealth (negative = gain)", "Observation count")
    for left, right, count in zip(edges[:-1], edges[1:], counts):
        svg.rect(x(left) + .8, y(count), x(right) - x(left) - 1.6, y(0) - y(count), "#83bec0", 1)
    for value, colour, dash in ((risk["var"], SERIES[2], "6 4"), (risk["expected_shortfall"], COLOURS["red"], "3 3")):
        svg.line(x(value), y(0), x(value), y(max_count), colour, 2.5, dash)
    svg.text(100, 562, f'Tail mass: {n} × 5% = {n * .05:.2f} observations; the boundary observation receives fractional weight.', 13)
    svg.footer(["VaR uses empirical rank ceil(0.95 × n); expected shortfall averages exactly the worst 5% tail mass.", "Binning is visual only: both measures use the unbinned returns. This sample does not bound future losses or unseen shocks."])
    return svg.finish()


def csv_text(headers, rows):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(headers)
    writer.writerows(rows)
    return stream.getvalue()


def derived_files(e):
    p, o, a = e["performance"], e["options"], e["allocation"]
    files = {name + ".svg": render(e) for name, render in (
        ("research-performance", render_performance), ("cost-sensitivity", render_costs),
        ("allocation-risk", render_allocation), ("option-sensitivities", render_options),
        ("pricing-convergence", render_convergence), ("tail-risk", render_tail))}
    files["data/synthetic-prices.csv"] = csv_text(["date"] + e["provenance"]["symbols"],
        ([date] + row for date, row in zip(e["provenance"]["dates"], e["provenance"]["prices"])))
    files["data/performance.csv"] = csv_text(["date", "minimum_variance_equity", "equal_weight_equity", "minimum_variance_drawdown", "equal_weight_drawdown"],
        zip(p["dates"], p["selected_equity"], p["baseline_equity"], p["selected_drawdown"], p["baseline_drawdown"]))
    files["data/cost-scenarios.csv"] = csv_text(list(e["cost_scenarios"][0]), (r.values() for r in e["cost_scenarios"]))
    files["data/option-sensitivities.csv"] = csv_text(list(o["curve"][0]), (r.values() for r in o["curve"]))
    files["data/pricing-convergence.csv"] = csv_text(["method", "steps_or_terminal_paths", "price", "ci_low", "ci_high", "independent_pairs"],
        [["Black-Scholes", "", o["analytical"], "", "", ""]] +
        [["CRR", r["steps"], r["price"], "", "", ""] for r in o["trees"]] +
        [["Monte Carlo", r["paths"], r["price"], r["ci_low"], r["ci_high"], r["independent_pairs"]] for r in o["monte_carlo"]])
    files["data/allocation.csv"] = csv_text(["strategy"] + e["provenance"]["symbols"], ([key] + value for key, value in a["weights"].items()))
    files["data/correlation.csv"] = csv_text(["symbol"] + e["provenance"]["symbols"], ([symbol] + values for symbol, values in zip(e["provenance"]["symbols"], a["correlation"])))
    files["data/tail-risk.csv"] = csv_text(["date", "net_return", "loss"], ([date, value, -value] for date, value in zip(p["dates"][1:], p["net_returns"])))
    return files


def compare_evidence(actual, expected, path="evidence"):
    """Check recomputation without requiring platform-identical BLAS output."""
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or set(actual) != set(expected):
            raise ValueError(f"{path}: keys changed")
        for key in expected:
            # Canonical byte hashes can vary with last-bit libm differences;
            # price arrays are independently compared below.
            if key != "dataset_sha256":
                compare_evidence(actual[key], expected[key], f"{path}.{key}")
    elif isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise ValueError(f"{path}: array length changed")
        for i, (a, b) in enumerate(zip(actual, expected)):
            compare_evidence(a, b, f"{path}[{i}]")
    elif isinstance(expected, (float, int)) and not isinstance(expected, bool):
        if not isinstance(actual, (float, int)) or not math.isclose(actual, expected, rel_tol=2e-6, abs_tol=2e-8):
            raise ValueError(f"{path}: numerical evidence changed")
    elif actual != expected:
        raise ValueError(f"{path}: value changed")


def make_bundle(evidence):
    """Build assets and their provenance manifest entirely in memory."""
    files = derived_files(evidence)
    files["data/visual-evidence.json"] = json.dumps(evidence, indent=2, allow_nan=False) + "\n"
    manifest = {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__,
                "dataset_sha256": evidence["provenance"]["dataset_sha256"],
                "sources": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in
                            ("scripts/build_visuals.py", "src/atlas_quant/data.py", "src/atlas_quant/backtest.py", "src/atlas_quant/quant.py")},
                "meaning": "Environment and source hashes for this generated bundle, not an audit or a signature.",
                "files": {name: hashlib.sha256(content.encode()).hexdigest() for name, content in files.items()}}
    files["data/manifest.json"] = json.dumps(manifest, indent=2, allow_nan=False) + "\n"
    return files


def verify_bundle(output, generated=None):
    """Verify source hashes, internal data hashes, reproduction and rendering.

    A hash is an integrity check, not a signature. The recorded build environment
    is retained; it need not equal the current environment. Recomputed price
    arrays are compared numerically rather than by a platform-sensitive hash.
    """
    existing = json.loads((output / "data/visual-evidence.json").read_text(encoding="utf-8"))
    manifest = json.loads((output / "data/manifest.json").read_text(encoding="utf-8"))
    p = existing["provenance"]
    recorded = PriceDataset(tuple(p["dates"]), tuple(p["symbols"]), np.array(p["prices"]),
                            f'synthetic-lognormal-v1:seed={p["seed"]}', True)
    if recorded.sha256 != p["dataset_sha256"] or manifest["dataset_sha256"] != recorded.sha256:
        raise ValueError("Recorded dataset hash does not match the saved price observations")
    compare_evidence(compute_evidence() if generated is None else generated, existing)
    expected_files = derived_files(existing)
    required_files = set(expected_files) | {"data/visual-evidence.json"}
    if set(manifest["files"]) != required_files:
        raise ValueError("Manifest file inventory is incomplete or unexpected")
    source_paths = {"scripts/build_visuals.py", "src/atlas_quant/data.py",
                    "src/atlas_quant/backtest.py", "src/atlas_quant/quant.py"}
    if set(manifest["sources"]) != source_paths:
        raise ValueError("Manifest source inventory is incomplete or unexpected")
    for name in source_paths:
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != manifest["sources"][name]:
            raise ValueError(f"{name}: source changed; regenerate the visual atlas")
    for name in required_files:
        path = output / name
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != manifest["files"][name]:
            raise ValueError(f"{path}: asset hash mismatch or missing file")
        if name in expected_files and path.read_text(encoding="utf-8") != expected_files[name]:
            raise ValueError(f"{path}: stale derived asset; run scripts/build_visuals.py")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify committed evidence and rendered assets without writing")
    parser.add_argument("--output", type=Path, default=OUTPUT, help="Asset directory (default: docs/assets)")
    args = parser.parse_args()
    generated = compute_evidence()
    if args.check:
        verify_bundle(args.output, generated)
        print("Visual atlas verified: six SVG charts and eight CSV exports agree with recomputed evidence.")
    else:
        files = make_bundle(generated)
        for name, content in files.items():
            path = args.output / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
        print(f"Wrote {len(files)} files to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
