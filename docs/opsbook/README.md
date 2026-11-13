# Atlas Quant's project operations manual

This pilot uses the actual [Atlas Opsbook](https://github.com/Albertito-AI/atlas-opsbook)
CLI. It records a source-permission near miss, tests an overbroad instruction
against a counterexample, derives a narrower condition, and makes the resulting
check available to the next agent session.

The original runtime is copied unchanged at the source revision recorded in
[`.opsbook/upstream.json`](../../.opsbook/upstream.json). Its MIT licence is
retained at [`.opsbook/bin/LICENSE`](../../.opsbook/bin/LICENSE). The financial
package remains offline; the manual and collector are separate checkout tools.

## Fresh checkout and task intake

Run from the repository root:

```sh
python docs/opsbook/bootstrap.py
python .opsbook/bin/opsbook.py brief '{"task":"activate-source","source_kind":"public"}'
python .opsbook/bin/opsbook.py manual
```

The bootstrap reconstructs the reviewed rule using the actual CLI. It checks
the pinned runtime, records the cases, observes the overbroad draft's refusal,
learns and evaluates the bounded rule, and promotes it. Repeating the command
preserves the existing matching manual. A different active manual requires
inspection and an explicit migration; the bootstrap does not overwrite it.
SQLite state stays local and is excluded from Git. The cases, accepted rule,
source pin and portable [manual](MANUAL.md) remain in the repository.

Use `task = activate-source` whenever a source is enabled **or its intended use
materially changes**. Context is supplied by the operator, not inferred by
Opsbook. Use `task = inspect` or `task = document` only for work that performs no
source activation or change of purpose.

## Before collection

Inspect [the exact source plan](pilot-plan.json), then run:

```sh
python .opsbook/bin/opsbook.py verify '{"task":"activate-source","source_kind":"public"}' --checks docs/opsbook/checks.json
```

The trusted command map invokes the observatory's actual `policy_check` for
every planned source and intended use. The pilot plan covers non-commercial
research using NEA observations and Binance Vision archives. It requires
acceptance of attribution and applicable derivative-licence conditions. The
plan is due for a fresh source review on **13 December 2026**; the gate fails
on or after that date. Renew only after checking actual current terms and
recording the new evidence, not merely to make a job pass.

Do not reuse a successful gate for a different source, purpose or changed
plan. A changed plan must be reviewed and verified again. Source dates and
allowance flags record reviewed decisions; software cannot itself decide that
a provider has granted a new licence. The collector also checks its registry,
and unresolved live exchange adapters remain disabled.

## Reproduce the evidence

```sh
python docs/opsbook/bootstrap.py --check
python -m unittest discover -s docs/opsbook -p 'test_*.py' -v
```

`--check` uses a fresh temporary database and leaves the active manual intact.
The eight policy tests cover allowed scope, disallowed live feeds, commercial
Vision use, unknown source/purpose, expired or future-dated reviews, duplicate
sources and missing conditions. See [the incident and limits](INCIDENT.md),
[actual replay](evidence.json) and [the executable gate result](verification.json). A separate agent also
[read the procedure and exercised a fresh disallowed-source case](independent-readback.json):
the reviewed plan passed, and a Coinbase activation plan was refused.

## Evolution procedure

1. Read the active brief before work. Retain the exact source revision and run
   manifest for any material result.
2. Record a sanitised observed failure or near miss, its expected check and a
   nearby unaffected control. Distinguish observed events from authored tests.
3. Ask a separate reviewer to label fresh cases before showing the candidate
   rule. Once exposed, retain them as regression fixtures.
4. Propose or learn a scoped instruction, evaluate it, inspect every new error,
   and promote only when the applicable project procedure permits it.
5. Have another agent read the manual and apply the check to a fresh scoped
   task. Preserve both the result and any failure; route counterexamples into
   a revised rule or an explicit rollback.

A manual rule supplies no new authority, data rights, spending allowance,
learner status or permission to trade. Claims of learning or improved research
quality require separate prospective evidence.

## An observed verifier failure and repair

The pilot's independent reviewer found a real software defect using a synthetic
adversarial bundle: after removing every source from a report and recomputing
its manifest hash, the initial verifier still returned `verified` and `ok`.
Byte consistency had been mistaken for sufficient evidence of completeness.

The repaired verifier derives the required source set from the declared run,
requires those sources to be present, and replays the retained observations.
The same empty-source attack now raises an explicit error. An unchanged valid
bundle still passes without network access, while a changed observation with a
recomputed hash is rejected. The
[observed before/after receipt](observed-verifier-repair.json) preserves the
reviewer's function results, precise regression names and a separately captured
working-tree validation snapshot. Historical pre-fix hashes were not captured;
none have been reconstructed or presented as known.

This incident produces a **candidate** instruction: require semantic replay,
required-source checks and adversarial controls before publishing an evidence
bundle. It has not been promoted into the active manual. Fresh independent
routing cases and scope review are required before a second procedure is
accepted. The current manual remains at revision 1, and these checks establish
software behaviour rather than an agent learning gain.
