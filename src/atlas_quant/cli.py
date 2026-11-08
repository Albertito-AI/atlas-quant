"""Local command-line interface. No network, account or credential required."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .backtest import STRATEGIES
from .data import load_prices_csv, synthetic_prices
from .pipeline import analyse, load_analysis, option_comparison
from .report import generate_report
from .research import validate_external_review


def _settings(parser):
    parser.add_argument("--strategy", choices=STRATEGIES, default="inverse_volatility")
    parser.add_argument("--lookback", type=int, default=60)
    parser.add_argument("--rebalance-every", type=int, default=21)
    parser.add_argument("--cost-bps", type=float, default=10)
    parser.add_argument("--initial-cash", type=float, default=100000)
    parser.add_argument("--max-weight", type=float, default=1)
    parser.add_argument("--periods-per-year", type=int, default=252)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, default=Path("output"))


def _write_bundle(report, output: Path):
    # Require a fresh directory to protect previous reports and user files.
    output.mkdir(parents=True, exist_ok=False)
    (output / "report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False) + "\n", encoding="utf-8")
    (output / "report.html").write_text(generate_report(report), encoding="utf-8")
    print(f"Research report: {output / 'report.html'}")
    print(f"Evidence record: {output / 'report.json'}")
    print(f"SHA-256: {report['integrity_sha256']}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="atlas-quant", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo", help="Generate labelled synthetic research and a report")
    _settings(demo)
    demo.add_argument("--days", type=int, default=504)
    demo.add_argument("--assets", type=int, default=4)
    backtest = commands.add_parser("backtest", help="Analyse a local adjusted-close CSV")
    backtest.add_argument("csv", type=Path)
    _settings(backtest)
    option = commands.add_parser("options", help="Compare European option pricing methods")
    for name, default in (("spot",100), ("strike",100), ("maturity",1), ("rate",.05), ("volatility",.2), ("dividend",0)):
        option.add_argument("--" + name, type=float, default=default)
    option.add_argument("--option", choices=("call", "put"), default="call")
    option.add_argument("--seed", type=int, default=42)
    verify = commands.add_parser("verify", help="Verify report content hashes, not authorship")
    verify.add_argument("report", type=Path)
    review = commands.add_parser("review", help="Validate an inert external review against a report")
    review.add_argument("report", type=Path)
    review.add_argument("review", type=Path)
    review.add_argument("--role", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command in ("demo", "backtest"):
            if args.output.exists():
                raise ValueError("output directory already exists; choose a new --output path")
            data = (synthetic_prices(days=args.days, assets=args.assets, seed=args.seed)
                    if args.command == "demo" else load_prices_csv(args.csv))
            result = analyse(data, strategy=args.strategy, lookback=args.lookback,
                             rebalance_every=args.rebalance_every, transaction_cost_bps=args.cost_bps,
                             initial_cash=args.initial_cash, max_weight=args.max_weight,
                             periods_per_year=args.periods_per_year, seed=args.seed)
            _write_bundle(result, args.output)
        elif args.command == "options":
            inputs = {key: value for key, value in vars(args).items() if key != "command"}
            print(json.dumps(option_comparison(**inputs), indent=2, allow_nan=False))
        elif args.command == "verify":
            load_analysis(args.report)
            print("Content integrity verified. This is not an author signature or financial validation.")
        elif args.command == "review":
            report = load_analysis(args.report)
            if not args.review.is_file() or args.review.stat().st_size > 16384:
                raise ValueError("external review must be a regular file of at most 16 KB")
            with args.review.open("rb") as handle:
                raw = handle.read(16385)
            result = validate_external_review(raw, report["council"], args.role)
            print(json.dumps(result, indent=2, allow_nan=False))
    except (ValueError, OSError, TypeError, OverflowError) as exc:
        print(f"atlas-quant: {exc}", file=sys.stderr)
        return 2
    return 0

