# Evidence council design

Atlas Quant separates financial calculations from commentary. Its default council
is six deterministic checks over a single supplied evidence set. It does not run
six language models, simulate independent experts, estimate a probability of
success or execute an investment decision. The development team that reviewed
this release is separate from these six software roles.

## Public contract

```python
from atlas_quant.research import build_research_report, verify_report

report = build_research_report(
    {
        "total_return": 0.12,
        "annualised_volatility": 0.15,
        "max_drawdown": -0.10,
        "total_cost_fraction": 0.005,
    },
    observations=252,
    assets=4,
    data_source="illustrative example",
    synthetic=True,
)
assert verify_report(report)
```

`observations` counts realised portfolio return intervals, excluding estimation
warm-up. Financial fractions use `0.10` for ten per cent. Drawdown accepts either
sign and is stored as a non-negative magnitude. `None` means unavailable, never
zero. Supported metrics are `total_return`, `annualised_return`,
`annualised_volatility`, `sharpe`, `max_drawdown`, `var_95`,
`expected_shortfall_95`, `total_cost_fraction` and `turnover`.

`total_cost_fraction` is the **sum of each rebalance's cost divided by that
rebalance's pre-trade equity**. It is not total monetary cost divided by initial
capital. `turnover` is the sum of traded absolute notional divided by pre-trade
equity, including the initial purchase; buys and sells both count. Historical
value at risk and expected shortfall can be negative if the relevant sample
outcomes are gains. Their signs are preserved.

## Role and gate semantics

| Role | Question | Behaviour |
| --- | --- | --- |
| Data quality | Are necessary measurements and enough realised observations present? | Missing required metrics or a short sample block interpretation. Synthetic data and absent dataset digests produce cautions. |
| Performance | Is observed total return positive? | Records an observation only. A positive observation cannot override another role's blocker. |
| Risk | Do historical volatility and drawdown meet configured limits? | Missing or excessive values block interpretation. |
| Costs | Is cost evidence present and below the review threshold? | Missing or large accumulated costs produce a caution. |
| Model critique | What remains untested? | Always preserves limitations concerning selection, execution, holdouts and evidence dependence. |
| Synthesis | May further research proceed? | Emits `blocked_for_review` or `research_only`; it cannot approve a trade. |

Default policy: at least 60 realised observations, maximum drawdown magnitude
at most 0.25, annualised volatility at most 0.40, and a high-cost caution above
0.02 accumulated cost fractions. These are transparent, illustrative research
thresholds. They are not calibrated suitability rules or proof of a sufficient
statistical sample. Exact boundary values pass. A caller can supply a validated
`ResearchPolicy` and the chosen policy is included in the checksum.

The trace records evidence validation, independent rule checks, preservation of
challenges and synthesis. This is a bounded computation, with no token-consuming
simulation of repeated deliberation. Every role links its conclusions to existing
evidence identifiers. All blocker and caution roles are retained in `dissent`.
The synthesis remains cautious even when all numerical gates pass.

## Optional external-model review

The application does not contact an external model or require an API key. A caller
may independently obtain a JSON review and pass it to `validate_external_review`.
The review can select approved critique templates and reference evidence. It
cannot supply arbitrary prose, numbers, URLs, tool instructions, trading actions,
new report outcomes or new gates. An allowlist avoids the false assurance that a
regular expression can verify every numerical claim in unrestricted prose.

```python
import json
from atlas_quant.research import validate_external_review

payload = json.dumps({
    "schema_version": "1.0",
    "role": "risk",
    "report_sha256": report["report_sha256"],
    "findings": [{
        "code": "inspect_risk",
        "evidence_ids": ["max_drawdown", "annualised_volatility"],
    }],
})
annotation = validate_external_review(payload, report, expected_role="risk")
assert annotation["authority"] == "annotation_only"
```

The application supplies all rendered wording and numerical values from the
report. The caller, rather than the model, binds the expected role. Each finding
code has both a role allowlist and a related-evidence allowlist. The boundary
rejects unknown fields, duplicate JSON keys, non-finite literals, invalid UTF-8,
missing or fabricated evidence, unrelated references, duplicate findings and
payloads larger than 16,384 bytes. Between one and twelve findings are accepted.
The original report is never changed. Accepted output is an annotation, not a
verified predictive judgement or proof that an external model was actually used.

| Code | Permitted role | Purpose |
| --- | --- | --- |
| `inspect_sample` | Data quality, model critique | Review sample length and representativeness. |
| `inspect_provenance` | Data quality | Review input provenance and adjustment conventions. |
| `inspect_return` | Performance | Review stability and untouched holdout performance. |
| `inspect_risk` | Risk | Stress-test beyond observed sample losses. |
| `inspect_costs` | Costs | Vary cost and capacity assumptions. |
| `inspect_selection_bias` | Model critique | Review leakage, survivorship and model selection. |
| `request_human_review` | Any registered role | Request independent examination of referenced evidence. |

This design limits what model output can do. It does not claim to solve prompt
injection generally. A malicious source label is inert data; the HTML renderer
must still escape all source labels. No label or model text enters a shell,
Python evaluator, network request or broker.

## Provenance and checksums

`report_sha256` hashes the report with that field removed, serialised with Python
JSON's `sort_keys=True`, `separators=(',', ':')`, `ensure_ascii=True` and
`allow_nan=False`, encoded as UTF-8. This deterministic encoding is not a claim of
RFC 8785 compliance. `verify_report` checks content integrity; it is not a schema
validator, digital signature or authentication mechanism. The external-review
boundary additionally validates the evidence structure before using it.

A party able to change a report can also calculate a new digest. A digest cannot
prove truthful prices, legitimate adjustments, authorship or historical
performance. `dataset_sha256` is caller supplied, explicitly marked unverified;
the council does not open the underlying dataset. The application should retain
the original input and model configuration with exported reports.

## Lessons from the reference project

Inspected source snapshot:
[`neohsiung/AI-Investment-Advisor` at `990a16c12436e83d0e977f48d6a81485deb6f251`](https://github.com/neohsiung/AI-Investment-Advisor/tree/990a16c12436e83d0e977f48d6a81485deb6f251).
The files below were read; Atlas Quant's implementation is original.

- [`swarm_orchestrator.py`](https://github.com/neohsiung/AI-Investment-Advisor/blob/990a16c12436e83d0e977f48d6a81485deb6f251/src/agents/orchestration/swarm_orchestrator.py)
  provides tiered dispatch, timeouts and result aggregation. Separating execution,
  aggregation and evidence makes failure behaviour easier to review. Atlas Quant
  takes that separation as a design lesson while using no external calls.
- [`strategies.py`](https://github.com/neohsiung/AI-Investment-Advisor/blob/990a16c12436e83d0e977f48d6a81485deb6f251/src/agents/swarm/strategies.py)
  classifies bullish and bearish terms and reports the winning weighted share as
  confidence. Such agreement is not a calibrated probability of an investment
  outcome. Atlas Quant reports explicit checks and dissent without confidence
  scores. This observation concerns the inspected aggregation implementation,
  rather than a claim about every upstream execution path.
- [`verifier_agent.txt`](https://github.com/neohsiung/AI-Investment-Advisor/blob/990a16c12436e83d0e977f48d6a81485deb6f251/prompts/verifier_agent.txt)
  asks a verifier to check numerical claims against fetched data. Atlas Quant
  moves its limited external-review boundary further upstream: model output
  cannot introduce numbers, and rendering draws figures directly from evidence.
- [`dynamic_debate_termination_service.py`](https://github.com/neohsiung/AI-Investment-Advisor/blob/990a16c12436e83d0e977f48d6a81485deb6f251/src/services/dynamic_debate_termination_service.py)
  provides bounded debate and stopping logic. Its implemented text comparison is
  token-set Dice overlap. Lexical stability does not establish factual truth or
  epistemic independence. Atlas Quant therefore makes no quality claim based on
  repeated agreement or number of reasoning rounds.
- [`confidence_compositor_service.py`](https://github.com/neohsiung/AI-Investment-Advisor/blob/990a16c12436e83d0e977f48d6a81485deb6f251/src/services/confidence_compositor_service.py)
  explicitly marks a scoring fallback as insufficient data and excludes it from
  usable evidence. This is a useful fail-closed lesson. Atlas Quant rejects
  unavailable required measurements rather than replacing them with plausible
  scores. Other upstream paths need their own review; this is not a whole-system
  security assessment.

The security boundary also draws on the primary
[OWASP prompt-injection guidance](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)
and [OWASP prevention cheat sheet](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html),
accessed 8 November 2026. External content is untrusted, and restricting
capabilities is necessary beyond text filters. No upstream code or book text was
copied into this module.
