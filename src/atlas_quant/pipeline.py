"""Compose deterministic calculations, independent baselines and evidence."""
from __future__ import annotations

import json
from pathlib import Path

from . import __version__
from .backtest import run_backtest
from .data import PriceDataset
from .quant import black_scholes, binomial_price, monte_carlo_price, option_greeks
from .research import ResearchPolicy, build_research_report, content_sha256, verify_report

MAX_REPORT_BYTES = 50_000_000


def option_comparison(*, spot=100.0, strike=100.0, maturity=1.0, rate=.05,
                      volatility=.2, dividend=0.0, option="call", seed=42) -> dict:
    """Three numerical methods for the same European payoff and assumptions."""
    inputs = dict(spot=spot, strike=strike, maturity=maturity, rate=rate,
                  volatility=volatility, dividend=dividend, option=option)
    analytical = black_scholes(**inputs)
    try:
        tree = binomial_price(**inputs, steps=400)
        tree_status = "Computed with 400 CRR steps."
    except ValueError as exc:
        tree = None
        tree_status = "Unavailable at 400 CRR steps: " + str(exc)
    return {"input": inputs, "black_scholes": analytical,
            "binomial": tree, "binomial_status": tree_status,
            "monte_carlo": monte_carlo_price(**inputs, seed=seed),
            "greeks": (option_greeks(**inputs) if maturity > 0 and volatility > 0
                       else {"status": "Undefined at expiry or zero volatility in this implementation"}),
            "assumptions": "European exercise, constant volatility and continuous dividend yield. Risk-neutral pricing is not a return forecast."}


def analyse(data: PriceDataset, *, strategy="inverse_volatility", lookback=60,
            rebalance_every=21, transaction_cost_bps=10.0, initial_cash=100000.0,
            max_weight=1.0, periods_per_year=252, seed=42) -> dict:
    settings = dict(lookback=lookback, rebalance_every=rebalance_every,
                    transaction_cost_bps=transaction_cost_bps, initial_cash=initial_cash,
                    max_weight=max_weight, periods_per_year=periods_per_year)
    result = run_backtest(data, strategy=strategy, **settings).to_dict()
    baseline = run_backtest(data, strategy="equal_weight", **settings).to_dict()
    higher_cost = dict(settings, transaction_cost_bps=min(transaction_cost_bps * 2, 1000))
    stress = run_backtest(data, strategy=strategy, **higher_cost).to_dict()
    m = result["metrics"]
    metrics = {k: m[k] for k in ("total_return", "annualised_return", "annualised_volatility", "max_drawdown")}
    metrics.update(sharpe=m["sharpe_ratio"], var_95=result["risk"]["var"],
                   expected_shortfall_95=result["risk"]["expected_shortfall"],
                   total_cost_fraction=m["total_cost_fraction"],
                   turnover=m["total_turnover"])
    council = build_research_report(metrics, observations=len(result["net_returns"]),
                                    assets=len(data.symbols), data_source=data.source,
                                    dataset_sha256=data.sha256, synthetic=data.synthetic)
    report = {
        "schema_version": "1.0",
        "metadata": {"title": "Atlas Quant Research", "version": __version__,
                     "synthetic": data.synthetic, "dataset_sha256": data.sha256,
                     "seed": seed, "generated_by": "atlas-quant deterministic offline pipeline",
                     "limitations": ["No live data retrieval or broker execution.",
                                      "The six-role council uses documented rules, not model inference.",
                                      "Historical simulations cannot establish future profitability."]},
        "backtest": result, "council": council,
        "benchmark": {"name": "Equal weight with matching calendar, lag and costs",
                      "metrics": baseline["metrics"], "equity_curve": baseline["equity_curve"],
                      "dates": baseline["dates"],
                      "total_return_difference": m["total_return"] - baseline["metrics"]["total_return"]},
        "cost_sensitivity": {"base_bps": transaction_cost_bps,
                             "comparison_bps": higher_cost["transaction_cost_bps"],
                             "metrics": stress["metrics"],
                             "meaning": "One cost scenario; does not model liquidity or market impact."},
        "options": option_comparison(seed=seed),
    }
    report["integrity_sha256"] = content_sha256(report)
    return report


def verify_analysis(report: dict) -> bool:
    """Detect content changes, not authorship. A hash can be recomputed by anyone."""
    if not isinstance(report, dict) or report.get("schema_version") != "1.0":
        return False
    try:
        body = dict(report)
        digest = body.pop("integrity_sha256", None)
        if not isinstance(digest, str) or digest != content_sha256(body):
            return False
        for name in ("metadata", "backtest", "council", "benchmark", "cost_sensitivity", "options"):
            if not isinstance(body.get(name), dict):
                return False
        b, c, meta = body["backtest"], body["council"], body["metadata"]
        source = b["dataset"]
        if not verify_report(c) or not (meta["dataset_sha256"] == source["sha256"] == c["source"]["dataset_sha256"]):
            return False
        if type(meta["synthetic"]) is not bool or type(source["synthetic"]) is not bool:
            return False
        if not (meta["synthetic"] == source["synthetic"] == c["source"]["synthetic"]):
            return False
        n = len(b["net_returns"])
        if not n or len(b["dates"]) != n + 1 or len(b["equity_curve"]) != n + 1:
            return False
        if body["benchmark"]["dates"] != b["dates"]:
            return False
        m = b["metrics"]
        if m["observations"] != n:
            return False
        metrics = {k: m[k] for k in ("total_return", "annualised_return", "annualised_volatility", "max_drawdown")}
        metrics.update(sharpe=m["sharpe_ratio"], var_95=b["risk"]["var"],
                       expected_shortfall_95=b["risk"]["expected_shortfall"],
                       total_cost_fraction=m["total_cost_fraction"], turnover=m["total_turnover"])
        expected = build_research_report(metrics, observations=n, assets=len(source["symbols"]),
                                          data_source=source["source"], synthetic=source["synthetic"],
                                          dataset_sha256=source["sha256"], policy=ResearchPolicy(**c["policy"]))
        return c == expected
    except (ValueError, TypeError, KeyError, OverflowError, RecursionError):
        return False


def _unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object keys are not permitted")
        result[key] = value
    return result


def load_analysis(path: str | Path) -> dict:
    path = Path(path)
    if not path.is_file() or path.stat().st_size > MAX_REPORT_BYTES:
        raise ValueError("report must be a regular JSON file of at most 50 MB")
    with path.open("rb") as handle:
        raw = handle.read(MAX_REPORT_BYTES + 1)
    if len(raw) > MAX_REPORT_BYTES:
        raise ValueError("report exceeds 50 MB")
    def reject_constant(value):
        raise ValueError(f"nonfinite JSON constant {value} is not permitted")
    try:
        report = json.loads(raw, object_pairs_hook=_unique, parse_constant=reject_constant)
    except (json.JSONDecodeError, UnicodeError, RecursionError) as exc:
        raise ValueError("invalid report JSON") from exc
    if not verify_analysis(report):
        raise ValueError("report integrity or schema verification failed")
    return report

