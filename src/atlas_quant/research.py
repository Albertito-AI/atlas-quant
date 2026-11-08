"""Deterministic evidence council and a constrained external-review boundary.

The six roles are rule-based checks, not six language models. No function in this
module accesses the network, executes model output, changes weights or trades.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math
from numbers import Real
from typing import Any, Mapping

SCHEMA_VERSION = "1.0"
ROLES = ("data_quality", "performance", "risk", "costs", "model_critique", "synthesis")
METRICS = {
    "total_return": ("Total return", "fraction"),
    "annualised_return": ("Annualised return", "fraction"),
    "annualised_volatility": ("Annualised volatility", "fraction"),
    "sharpe": ("Annualised Sharpe ratio", "ratio"),
    "max_drawdown": ("Maximum drawdown magnitude", "fraction"),
    "var_95": ("Historical value at risk at 95%", "fraction"),
    "expected_shortfall_95": ("Historical expected shortfall at 95%", "fraction"),
    "total_cost_fraction": ("Sum of per-rebalance cost fractions", "fraction"),
    "turnover": ("Sum of traded notional divided by pre-trade equity", "ratio"),
}
MAX_REVIEW_BYTES = 16_384


@dataclass(frozen=True)
class ResearchPolicy:
    """Illustrative research review thresholds, not suitability limits."""

    min_observations: int = 60
    max_drawdown: float = 0.25
    max_annualised_volatility: float = 0.40
    high_cost_fraction: float = 0.02

    def __post_init__(self) -> None:
        if type(self.min_observations) is not int or self.min_observations < 2:
            raise ValueError("min_observations must be an integer of at least two")
        for name in ("max_drawdown", "max_annualised_volatility", "high_cost_fraction"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value) or value <= 0:
                raise ValueError(f"{name} must be positive and finite")
            object.__setattr__(self, name, float(value))
        if self.max_drawdown > 1:
            raise ValueError("max_drawdown must not exceed one")


def canonical_json(value: Any) -> str:
    """Stable JSON with non-finite numbers prohibited; this is not RFC 8785."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False)


def content_sha256(value: Any) -> str:
    """Hash a JSON value. Hashes detect changes; they do not authenticate authors."""
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _metric_values(metrics: Mapping[str, float | None]) -> dict[str, float | None]:
    if not isinstance(metrics, Mapping) or len(metrics) > len(METRICS):
        raise ValueError("metrics must be a bounded mapping of supported metric names")
    if any(key not in METRICS for key in metrics):
        raise ValueError("unsupported metric name")
    clean: dict[str, float | None] = {}
    for key in sorted(metrics):
        value = metrics[key]
        if value is None:
            clean[key] = None
            continue
        if isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value):
            raise ValueError(f"{key} must be a finite number or None")
        number = float(value)
        if key == "max_drawdown":
            number = abs(number)
            if number > 1:
                raise ValueError("max_drawdown magnitude must be at most one")
        if key in ("annualised_volatility", "total_cost_fraction", "turnover") and number < 0:
            raise ValueError(f"{key} must be non-negative")
        if key in ("total_return", "annualised_return") and number < -1:
            raise ValueError(f"{key} must be at least minus one")
        clean[key] = number
    return clean


def _assessment(role: str, status: str, reasons: list[str], evidence_ids: list[str]) -> dict:
    return {"role": role, "mode": "deterministic_rule", "status": status,
            "reasons": reasons, "evidence_ids": evidence_ids}


def build_research_report(
    metrics: Mapping[str, float | None], *, observations: int, assets: int,
    data_source: str = "synthetic demo", dataset_sha256: str | None = None,
    synthetic: bool = True, policy: ResearchPolicy | None = None,
) -> dict:
    """Review computed metrics and retain all six role opinions and hard gates.

    ``observations`` counts realised portfolio return periods. Metric fractions
    use 0.10 for ten per cent. Drawdown accepts either sign and stores magnitude.
    Callers must compute metrics honestly: schema validation cannot establish the
    correctness or provenance of the caller's underlying data. A dataset digest
    identifies caller-supplied bytes; this function does not read those bytes.
    """
    for name, value, lower in (("observations", observations, 0), ("assets", assets, 1)):
        if type(value) is not int or value < lower or value > 10_000_000:
            raise ValueError(f"{name} is outside supported integer bounds")
    if type(synthetic) is not bool:
        raise ValueError("synthetic must be boolean")
    if not isinstance(data_source, str) or not data_source.strip() or len(data_source) > 500:
        raise ValueError("data_source must be a non-empty label of at most 500 characters")
    if any(ord(char) < 32 for char in data_source):
        raise ValueError("data_source must not contain control characters")
    if dataset_sha256 is not None and (
        not isinstance(dataset_sha256, str) or len(dataset_sha256) != 64
        or any(char not in "0123456789abcdef" for char in dataset_sha256)
    ):
        raise ValueError("dataset_sha256 must be a lowercase SHA-256 hex digest")
    policy = ResearchPolicy() if policy is None else policy
    if not isinstance(policy, ResearchPolicy):
        raise ValueError("policy must be ResearchPolicy")
    clean = _metric_values(metrics)
    evidence = [
        {"id": "observations", "label": "Realised return observations", "value": observations, "unit": "periods"},
        {"id": "assets", "label": "Asset count", "value": assets, "unit": "count"},
    ] + [{"id": key, "label": METRICS[key][0], "value": value, "unit": METRICS[key][1]}
         for key, value in clean.items()]
    required = ("total_return", "annualised_volatility", "max_drawdown")
    missing = [key for key in required if clean.get(key) is None]
    gates = []
    def gate(code: str, passed: bool, evidence_ids: list[str], description: str) -> None:
        gates.append({"code": code, "passed": passed, "evidence_ids": evidence_ids, "description": description})
    gate("sample_size", observations >= policy.min_observations, ["observations"], "Realised sample meets the configured minimum.")
    gate("required_metrics", not missing, [key for key in required if key in clean], "Return, volatility and drawdown are available.")
    gate("drawdown_limit", clean.get("max_drawdown") is not None and clean["max_drawdown"] <= policy.max_drawdown,
         ["max_drawdown"] if "max_drawdown" in clean else [], "Historical drawdown is within the configured review limit.")
    gate("volatility_limit", clean.get("annualised_volatility") is not None and clean["annualised_volatility"] <= policy.max_annualised_volatility,
         ["annualised_volatility"] if "annualised_volatility" in clean else [], "Historical annualised volatility is within the configured review limit.")
    data_reasons = []
    if observations < policy.min_observations:
        data_reasons.append("The realised sample is too short for the configured review policy.")
    if missing:
        data_reasons.append("Required metrics are missing: " + ", ".join(missing) + ".")
    if synthetic:
        data_reasons.append("Synthetic observations demonstrate mechanics and provide no evidence of market performance.")
    if dataset_sha256 is None:
        data_reasons.append("No dataset digest was supplied; input-byte provenance is unavailable.")
    data_status = "block" if missing or observations < policy.min_observations else ("caution" if synthetic or dataset_sha256 is None else "pass")
    roles = [_assessment("data_quality", data_status, data_reasons or ["Basic sample and provenance fields are present; data quality still requires independent verification."], ["observations", "assets"])]
    total_return = clean.get("total_return")
    if total_return is None:
        roles.append(_assessment("performance", "block", ["Total return is unavailable."], []))
    else:
        roles.append(_assessment("performance", "support" if total_return > 0 else "caution",
            ["The observed total return is positive." if total_return > 0 else "The observed total return is non-positive.",
             "Historical return does not establish expected return or statistical significance."], ["total_return"]))
    risk_failures = [item for item in gates if item["code"] in ("drawdown_limit", "volatility_limit") and not item["passed"]]
    roles.append(_assessment("risk", "block" if risk_failures else "pass",
        ["At least one configured historical risk gate failed or lacks evidence."] if risk_failures else ["Historical drawdown and volatility satisfy the configured review thresholds; future losses may be larger."],
        [key for key in ("max_drawdown", "annualised_volatility", "var_95", "expected_shortfall_95") if key in clean]))
    costs = clean.get("total_cost_fraction")
    roles.append(_assessment("costs", "caution" if costs is None or costs > policy.high_cost_fraction else "pass",
        ["Cost evidence is absent; inspect execution assumptions before interpreting results."] if costs is None else
        (["Accumulated cost fractions exceed the configured research threshold; inspect turnover and cost sensitivity."] if costs > policy.high_cost_fraction else
         ["Accumulated cost fractions are within the configured review threshold; market impact and taxes may remain unmodelled."]),
        [key for key in ("total_cost_fraction", "turnover") if key in clean]))
    roles.append(_assessment("model_critique", "caution", [
        "The council checks arithmetic outputs against explicit rules; it does not validate a predictive investment thesis.",
        "Check survivorship bias, data revisions, execution timing, parameter selection and untouched holdout results.",
        "Role agreement is not a calibrated probability, independent expert evidence or an investment recommendation.",
    ], ["observations"]))
    blocked = any(not item["passed"] for item in gates)
    dissent = [role["role"] for role in roles if role["status"] in ("block", "caution")]
    roles.append(_assessment("synthesis", "block" if blocked else "caution",
        ["Pause interpretation and resolve failed gates."] if blocked else ["Proceed only with further research and independent validation; the council does not approve an investment."],
        [item["id"] for item in evidence]))
    report = {
        "schema_version": SCHEMA_VERSION,
        "mode": "offline_deterministic_research_council",
        "source": {"label": data_source, "synthetic": synthetic, "dataset_sha256": dataset_sha256,
                   "provenance_status": "caller_supplied_unverified"},
        "policy": asdict(policy), "evidence": evidence, "roles": roles, "gates": gates,
        "dissent": dissent,
        "outcome": "blocked_for_review" if blocked else "research_only",
        "trace": [
            {"stage": "evidence", "action": "Validate bounded inputs and retain typed measurements."},
            {"stage": "independent_checks", "action": "Evaluate data, performance, risk, costs and model assumptions."},
            {"stage": "challenge", "action": "Preserve all cautions and blockers; majority support cannot override hard gates."},
            {"stage": "synthesis", "action": "Produce a research-only disposition with no trading authority."},
        ],
        "limitations": ["No live prices, model calls, broker connectivity or automated investment decisions.",
                        "Thresholds are illustrative research controls, not personalised suitability advice.",
                        "A digest detects content changes; it does not prove data truth, authorship or authenticity."],
    }
    report["report_sha256"] = content_sha256(report)
    return report


def verify_report(report: Mapping[str, Any]) -> bool:
    """Verify the content checksum. This is integrity checking, not a signature."""
    if not isinstance(report, Mapping):
        return False
    try:
        body = dict(report)
        digest = body.pop("report_sha256")
        return isinstance(digest, str) and digest == content_sha256(body)
    except (KeyError, TypeError, ValueError, RecursionError):
        return False


# An allowlisted statement vocabulary avoids presenting arbitrary model prose as
# verified facts. Qualitative claims cannot be made safe by a numeric regex.
EXTERNAL_FINDINGS = {
    "inspect_sample": {"roles": ("data_quality", "model_critique"), "metrics": ("observations",),
                       "text": "Inspect whether the sample is representative and sufficiently long."},
    "inspect_provenance": {"roles": ("data_quality",), "metrics": ("observations", "assets"),
                           "text": "Independently verify the dataset source and adjustment conventions."},
    "inspect_return": {"roles": ("performance",), "metrics": ("total_return", "annualised_return", "sharpe"),
                       "text": "Inspect return stability and untouched holdout performance."},
    "inspect_risk": {"roles": ("risk",), "metrics": ("max_drawdown", "annualised_volatility", "var_95", "expected_shortfall_95"),
                     "text": "Stress-test losses beyond those observed in this sample."},
    "inspect_costs": {"roles": ("costs",), "metrics": ("total_cost_fraction", "turnover"),
                      "text": "Vary trading costs and inspect capacity assumptions."},
    "inspect_selection_bias": {"roles": ("model_critique",), "metrics": ("observations", "total_return"),
                               "text": "Review data leakage, survivorship and model-selection bias."},
    "request_human_review": {"roles": ROLES, "metrics": tuple(METRICS) + ("observations", "assets"),
                             "text": "Request an independent human review of the referenced evidence."},
}


def _unique_object(pairs: list[tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _review_evidence(report: Mapping[str, Any]) -> dict[str, dict]:
    """Check the report boundary before indexing caller-supplied structures."""
    if report.get("schema_version") != SCHEMA_VERSION or report.get("mode") != "offline_deterministic_research_council":
        raise ValueError("unsupported report schema or mode")
    rows = report.get("evidence")
    if not isinstance(rows, list) or not 2 <= len(rows) <= len(METRICS) + 2:
        raise ValueError("report evidence has an invalid shape")
    expected = dict(METRICS, observations=("Realised return observations", "periods"),
                    assets=("Asset count", "count"))
    evidence = {}
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"id", "label", "value", "unit"}:
            raise ValueError("invalid report evidence record")
        key = row["id"]
        if not isinstance(key, str) or key not in expected or key in evidence:
            raise ValueError("unknown or duplicate report evidence identifier")
        if (row["label"], row["unit"]) != expected[key]:
            raise ValueError("report evidence label or unit mismatch")
        value = row["value"]
        if value is not None and (isinstance(value, bool) or not isinstance(value, Real) or not math.isfinite(value)):
            raise ValueError("report evidence must be numeric or unavailable")
        evidence[key] = row
    if not {"observations", "assets"}.issubset(evidence):
        raise ValueError("report lacks sample evidence")
    return evidence


def validate_external_review(payload: str | bytes, report: Mapping[str, Any], expected_role: str) -> dict:
    """Accept a constrained external-model critique as inert, non-authoritative data.

    Schema: {schema_version, role, report_sha256, findings:[{code,evidence_ids}]}.
    No arbitrary prose, numeric values, URLs, actions or extra fields are accepted.
    A model selects approved critique codes and references existing evidence; the
    application supplies all displayed wording and measurements. Caller binds the
    expected role; a model cannot nominate its own authority. The report is never
    mutated, its gates/outcome never overridden, and no model/API call is made.
    """
    if expected_role not in ROLES:
        raise ValueError("unsupported expected_role")
    if not verify_report(report):
        raise ValueError("report checksum mismatch")
    if not isinstance(payload, (str, bytes)):
        raise ValueError("payload must be JSON text or UTF-8 bytes")
    if len(payload) > MAX_REVIEW_BYTES:
        raise ValueError("review payload is too large")
    try:
        text = payload.decode("utf-8") if isinstance(payload, bytes) else payload
        if len(text.encode("utf-8")) > MAX_REVIEW_BYTES:
            raise ValueError("review payload is too large")
        parsed = json.loads(text, object_pairs_hook=_unique_object,
                            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("non-finite JSON number")))
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("invalid review JSON") from exc
    keys = {"schema_version", "role", "report_sha256", "findings"}
    if not isinstance(parsed, dict) or set(parsed) != keys:
        raise ValueError("review fields must exactly match the schema")
    if parsed["schema_version"] != SCHEMA_VERSION or parsed["role"] != expected_role:
        raise ValueError("review schema or role mismatch")
    if parsed["report_sha256"] != report["report_sha256"]:
        raise ValueError("review references a different report")
    findings = parsed["findings"]
    if not isinstance(findings, list) or not 1 <= len(findings) <= 12:
        raise ValueError("review must contain between one and twelve findings")
    evidence = _review_evidence(report)
    rendered = []
    seen = set()
    for finding in findings:
        if not isinstance(finding, dict) or set(finding) != {"code", "evidence_ids"}:
            raise ValueError("finding fields must exactly match the schema")
        code = finding["code"]
        if not isinstance(code, str) or code not in EXTERNAL_FINDINGS:
            raise ValueError("unsupported finding code")
        specification = EXTERNAL_FINDINGS[code]
        if expected_role not in specification["roles"]:
            raise ValueError("finding is not allowed for this role")
        ids = finding["evidence_ids"]
        if not isinstance(ids, list) or not 1 <= len(ids) <= len(METRICS) + 2:
            raise ValueError("finding needs a bounded non-empty evidence list")
        if any(not isinstance(item, str) for item in ids) or len(set(ids)) != len(ids):
            raise ValueError("evidence references must be unique strings")
        if any(item not in evidence or item not in specification["metrics"] or evidence[item]["value"] is None for item in ids):
            raise ValueError("unknown, missing or unrelated evidence reference")
        key = (code, tuple(sorted(ids)))
        if key in seen:
            raise ValueError("duplicate finding")
        seen.add(key)
        rendered.append({"code": code, "text": specification["text"], "evidence_ids": ids,
                         "measurements": [dict(evidence[item]) for item in ids]})
    result = {"schema_version": SCHEMA_VERSION, "role": expected_role,
              "report_sha256": report["report_sha256"], "mode": "external_selection_of_fixed_critique_templates",
              "authority": "annotation_only", "findings": rendered}
    result["review_sha256"] = content_sha256(result)
    return result
