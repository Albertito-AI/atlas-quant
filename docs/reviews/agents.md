# Research council: 20 development and review rounds

Reviewer: research-council development agent. Date: 8 November 2026.

These are twenty substantive work rounds by one member of the six-agent
**development team**, not twenty independent expert votes or twenty external
model calls. Inspection, implementation and tests occurred within this build
session. The six deterministic software roles are a separate product feature.

| Round | Work and evidence | Result or revision |
| --- | --- | --- |
| 01 | Located upstream swarm, orchestration, role, verifier and risk files using the repository inventory. | Distinguished the compatibility shim from the canonical orchestration implementation. |
| 02 | Read `src/agents/orchestration/swarm_orchestrator.py`, including tier fan-out, timeouts, weights and dependency scheduling. | Chose a bounded offline implementation with separate evidence, checks and synthesis. |
| 03 | Read `src/agents/swarm/strategies.py` signal regexes, weighted vote share and error treatment. | Avoided presenting agreement as a probability; added explicit statuses instead. |
| 04 | Read the risk agent and numerical-verifier prompt. | Separated computed measurements from optional external critique; chose evidence identifiers. |
| 05 | Read dynamic debate termination and its implemented token Dice comparison. | Declined to equate lexical convergence with truth; made challenge retention explicit. |
| 06 | Retrieved primary OWASP prompt-injection guidance and prevention material. | Used capability restriction and exact schemas instead of claiming text-filter immunity. |
| 07 | Sent a public API proposal to the coordinating agent. | Stabilised `build_research_report` and metric naming before integrating presentation. |
| 08 | Designed six roles, required metrics, minimum sample and historical risk thresholds. | `ResearchPolicy` validates domains; thresholds are retained as data in the report. |
| 09 | Implemented bounded metric and provenance validation. | Non-finite values, booleans, unknown metrics and invalid domains fail; missing values remain `None`. |
| 10 | Implemented hard gates, dissent retention and research-only synthesis. | A positive-return role cannot outvote a failed risk gate. |
| 11 | Implemented canonical JSON and SHA-256 report integrity. | Identical input ordering produces the same digest; mutation invalidates it. Authentication is explicitly excluded. |
| 12 | Implemented fixed-template external-review selection and role binding. | Model output cannot supply free prose, numerical claims, URLs, actions or new outcomes. |
| 13 | Built and ran the first 22 research tests. | All passed, including sample/risk gates, deterministic roles and numerical-domain cases. |
| 14 | Exercised external-review adversarial cases. | Fabricated citations, role spoofing, extra fields, duplicate keys, non-finite literals, invalid UTF-8 and oversized input were rejected by passing tests. |
| 15 | Tested evidence linkage, unavailable citations and policy object handling. | Added three tests; fixed falsey invalid policy objects being replaced by defaults and normalised numeric policy scalars. |
| 16 | Reviewed the HTML report integration contract with the presentation agent. | Sent exact role/evidence/gate schema and aligned source-label length with the data module's 500-character bound. |
| 17 | Independently reviewed quantitative metrics and ran an extreme-tail reproducer. | Found historical ES summation overflow for finite large gains; sent the owner a reproducer. Owner implemented a scaled tail mean and confirmed regression tests. |
| 18 | Independently reviewed backtest timing and the self-financing fee equation. | Confirmed next-close execution logic; identified inconsistent public weight-cap type validation and coordinated an explicit accumulated cost-fraction metric with the owner. |
| 19 | Responded to the security agent's malformed self-hashed report finding. | Added evidence-shape validation before external-review indexing and a regression test; 26 research tests passed. Read the upstream insufficient-data fallback to accurately credit its fail-closed path. |
| 20 | Wrote API, threat-boundary, provenance and upstream lesson documentation; ran the final research suite after revisions. | All 26 research tests passed. Limitations remain explicit: deterministic checks, caller-supplied data, illustrative thresholds, no predictive validation and no trading authority. |

Final domain verification command:

```sh
PYTHONPATH=src python -m unittest discover -s tests -p test_research.py -v
```

Result: **26 tests passed**. This count concerns the research module at this
review checkpoint; the coordinating agent reports the final whole-project count.
