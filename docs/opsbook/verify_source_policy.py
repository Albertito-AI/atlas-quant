"""Reviewed executable gate for the bounded pilot plan; makes no network requests."""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from observatory.pilot import EvidenceError, policy_check


def check_plan(plan: dict, *, today: date | None = None) -> dict:
    today = today or datetime.now(timezone.utc).date()
    if not isinstance(plan, dict) or set(plan) != {"schema", "use", "sources", "acknowledge_conditions", "review_due"}:
        raise ValueError("Unexpected source plan schema")
    if plan["schema"] != 1 or plan["acknowledge_conditions"] is not True:
        raise ValueError("Source conditions must be explicitly acknowledged")
    if not isinstance(plan["sources"], list) or not plan["sources"] or len(plan["sources"]) != len(set(plan["sources"])):
        raise ValueError("Plan needs a nonempty, distinct source list")
    due = date.fromisoformat(plan["review_due"])
    if today >= due:
        raise ValueError("Source review is due; recheck actual terms before renewing this plan")
    results = [policy_check(source, plan["use"]) for source in plan["sources"]]
    for result in results:
        if not result["allowed"] or not result["licence_url"] or not result["conditions"]:
            raise ValueError("Proposed source or use is outside the reviewed pilot scope")
        reviewed = date.fromisoformat(result["reviewed_on"])
        if reviewed > today or (due - reviewed).days > 31:
            raise ValueError("Review dates are invalid or permission review window exceeds 31 days")
    return {"pass": True, "use": plan["use"], "sources": results, "review_due": due.isoformat(),
            "scope": "Recorded source-policy check only; no new licence or authority is created."}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    args = parser.parse_args()
    try:
        result = check_plan(json.loads(args.plan.read_text(encoding="utf-8")))
    except (EvidenceError, ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({"pass": False, "reason": str(exc)}))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
