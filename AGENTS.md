# Project instructions

Use British English. Preserve explicit units and model assumptions.

1. Read the source study and numerical conventions before changing financial logic.
2. Never introduce future observations into a strategy's information set.
3. Preserve self-financing accounting and the documented per-side cost convention.
4. Keep product runtime offline unless an explicit feature request changes that boundary.
5. Missing or invalid evidence must never become fabricated zero, confidence or approval.
6. Do not add books, unlicensed code, secrets, personal datasets or generated performance claims.
7. Include independent numerical identities or accounting evidence for material financial changes.
8. Run the relevant tests, the full unittest suite and security_check.py before release.
9. Report actual validation and its environment. Never describe configured CI as passed CI.
10. Update documentation when behaviour, schema or assumptions change.



For a fresh observatory checkout, run `python docs/opsbook/bootstrap.py` before
the first manual briefing. Preserve any existing local revision; do not reset it
to make a check pass. Apply the executable source-plan gate before collection.

<!-- atlas-opsbook:start -->
## Project operations manual

At task intake, identify the project facts (such as task and artefact). Run
`python .opsbook/bin/opsbook.py brief '<context JSON>'` from the repository root.
Read the matching procedures and follow them within the owner's existing authority.
If pstack is installed, use its usual router and playbook for the engineering work.

After a significant failure, correction or repeated success, retain a sanitised
case with observable evidence, the expected checks and a nearby counterexample.
Use `record` for cases, then write a conditional rule with `propose`, or use
`learn CASE CHECK "instruction"` to infer its conditions from practice cases.
Use independently labelled exam cases. Run `evaluate ID` and inspect every
new error. Use `promote ID` only within project policy. Read `manual` for the
current text. At task completion use `verify CONTEXT --checks TRUSTED_FILE`
for executable checks. Use `gate` only for externally verified check names.
Never infer permission from an observation or a learned rule. If the manual
causes harm, use `history` then `rollback REVISION "reason"` and retain the case.
<!-- atlas-opsbook:end -->

## Observatory manual bootstrap

For a fresh checkout, run `python docs/opsbook/bootstrap.py` before the Opsbook
brief. Read `docs/opsbook/README.md` for the reviewed source plan and executable
gate. Represent a new source or a material change of purpose as
`{"task":"activate-source","source_kind":"public"}`. A past successful check
may not be reused for a different source, purpose or changed plan. The portable
manual and replay evidence do not confer data rights or additional authority.
