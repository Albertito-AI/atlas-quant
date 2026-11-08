"""Generate a reproducible, synthetic transaction-cost teaching case.

Run from an installed source checkout: python examples/workshop_case.py --output output/workshop
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from atlas_quant.data import synthetic_prices
from atlas_quant.pipeline import analyse, verify_analysis
from atlas_quant.report import generate_report


def build_case(output: Path) -> dict:
    """Write three separate cases from one labelled synthetic dataset.

    All settings except per-side cost are held constant. Output must not exist.
    """
    data = synthetic_prices(days=252, assets=4, seed=42)
    cases = []
    for cost in (0, 10, 50):
        report = analyse(data, strategy="inverse_volatility", lookback=60,
                         rebalance_every=21, transaction_cost_bps=cost, seed=42)
        if not verify_analysis(report) or report["metadata"]["synthetic"] is not True:
            raise ValueError("generated research record failed consistency checks")
        cases.append((cost, report))
    output.mkdir(parents=True, exist_ok=False)
    results = []
    for cost, report in cases:
        prefix = f"cost-{cost}bps"
        (output / f"{prefix}.html").write_text(generate_report(report), encoding="utf-8")
        (output / f"{prefix}.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        metrics = report["backtest"]["metrics"]
        results.append({"cost_bps": cost, "final_equity": metrics["final_equity"],
                        "total_return": metrics["total_return"], "total_transaction_cost": metrics["total_transaction_cost"],
                        "traded_notional_turnover": metrics["total_turnover"],
                        "report_sha256": report["integrity_sha256"]})
    summary = {"title": "Transaction-cost sensitivity: synthetic teaching case", "synthetic": True,
               "dataset_sha256": data.sha256, "seed": 42, "days": 252, "assets": 4,
               "strategy": "inverse_volatility", "lookback": 60, "rebalance_every": 21,
               "meaning": "Costs are charged on each buy and sell. This sensitivity comparison is not evidence of actual market performance.",
               "cases": results}
    (output / "summary.json").write_text(json.dumps(summary, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="New output directory")
    args = parser.parse_args()
    try:
        summary = build_case(args.output)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"workshop case: {exc}\n")
    print(json.dumps(summary, indent=2, allow_nan=False))
    print(f"Open {args.output / 'cost-10bps.html'} to begin.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
