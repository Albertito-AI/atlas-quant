"""Rebuild the reviewed project procedure using the actual vendored Opsbook CLI."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
CLI = ROOT / ".opsbook/bin/opsbook.py"
INSTRUCTION = ("Before activating a source or materially changing its intended use, run the reviewed source-permission gate for the exact source plan. Check AI use, publication, attribution and commercial restrictions against current primary terms. Public access and a passed routing test confer no permission. Stop an unresolved or disallowed source; record the evidence and a permitted alternative.")


def replay(db: Path) -> dict:
    pin = json.loads((ROOT / ".opsbook/upstream.json").read_text(encoding="utf-8"))
    if hashlib.sha256(CLI.read_bytes()).hexdigest() != pin["sha256"]:
        raise ValueError("Vendored Opsbook differs from its reviewed source pin")
    transcript = []
    def run(*args: str, expect: int = 0):
        proc = subprocess.run([sys.executable, str(CLI), "--db", str(db), *args], cwd=ROOT,
                              capture_output=True, text=True, timeout=60, check=False)
        transcript.append({"command": list(args), "exit": proc.returncode,
                           "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip()})
        if proc.returncode != expect:
            raise ValueError(f"Unexpected Opsbook result for {args[0]}: {proc.returncode}")
        return json.loads(proc.stdout) if proc.stdout.startswith(("{", "[")) else proc.stdout
    current = run("init")
    if current["revision"] != 0:
        active = run("revision", str(current["revision"]))
        expected = json.loads((HERE / "accepted-rule.json").read_text(encoding="utf-8"))
        if active["rules"] != [expected]:
            raise ValueError("Existing manual differs; inspect it before any explicit migration")
        return {"state": "already_installed", "revision": current["revision"], "transcript": transcript}
    before = run("brief", '{"task":"activate-source","source_kind":"public"}')
    run("record", str(HERE / "practice-cases.json"))
    run("record", str(HERE / "exam-cases.json"))
    wide = run("propose", str(HERE / "overbroad-rule.json"))["proposal"]
    rejected = run("evaluate", wide)
    if rejected["eligible"]:
        raise ValueError("The deliberate counterexample failed to reject the broad rule")
    run("promote", wide, expect=2)
    candidate = run("learn", "public-feed-rights-near-miss", "review-source-permissions", INSTRUCTION)
    expected_path = HERE / "accepted-rule.json"
    if expected_path.exists() and candidate["rule"] != json.loads(expected_path.read_text(encoding="utf-8")):
        raise ValueError("Practice-derived rule differs from reviewed portable rule")
    accepted = run("evaluate", candidate["proposal"])
    if not accepted["eligible"]:
        raise ValueError("The bounded rule did not pass replay")
    promoted = run("promote", candidate["proposal"])
    after = run("brief", '{"task":"activate-source","source_kind":"public"}')
    control = run("brief", '{"task":"inspect","source_kind":"public"}')
    missing = run("gate", '{"task":"activate-source","source_kind":"public"}', expect=1)
    return {"state": "installed", "baseline": before, "rejected": rejected, "accepted": accepted,
            "rule": candidate["rule"], "revision": promoted["number"], "readback": after,
            "unaffected_control": control, "missing_check": missing, "transcript": transcript}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Use a fresh temporary manual; do not mutate local state")
    args = parser.parse_args()
    try:
        if args.check:
            with tempfile.TemporaryDirectory(prefix="atlas-opsbook-replay-") as temp:
                result = replay(Path(temp) / "manual.db")
        else:
            result = replay(ROOT / ".opsbook/manual.db")
        print(json.dumps(result, indent=2))
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
