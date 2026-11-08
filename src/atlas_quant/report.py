"""Portable, script-free HTML research reports with escaped input and exact provenance.

This presentation layer never fetches data, interprets Markdown/HTML, makes investment
recommendations or runs models. Missing values remain visibly missing.
"""
from __future__ import annotations

import base64
from collections.abc import Mapping, Sequence
from hashlib import sha256
from html import escape
import json
import math
from numbers import Real
from typing import Any

_CSS = """
:root{color-scheme:light dark;--bg:#f3f5f2;--surface:#ffffff;--ink:#192b29;--muted:#526761;--line:#d9e3de;--green:#07695b;--mint:#ddf1e9;--blue:#3263a5;--amber:#805718;--amber-bg:#faf1dc;--rose:#a44245;--soft:#edf2ee}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}a{color:var(--green)}.skip{position:absolute;left:12px;top:-80px;padding:10px;background:var(--surface);z-index:2}.skip:focus{top:8px}main{max-width:1220px;margin:auto;padding:34px 32px 60px}.topbar{display:flex;align-items:center;justify-content:space-between;gap:20px;border-bottom:1px solid var(--line);padding-bottom:20px}.brand{white-space:nowrap;font-weight:800;font-size:20px;letter-spacing:-.8px}.brand span{color:var(--green)}.edition,.eyebrow{font:700 11px/1.5 ui-monospace,monospace;letter-spacing:1.6px;text-transform:uppercase}.edition{color:var(--muted)}.hero{display:flex;justify-content:space-between;align-items:center;gap:24px;padding:36px 0 26px}.hero h1{font-size:clamp(32px,4.5vw,54px);line-height:1.08;font-weight:650;letter-spacing:-2px;margin:12px 0}.hero p{max-width:650px;color:var(--muted);margin:14px 0 0}.eyebrow{color:var(--green)}.badge{display:inline-block;border:1px solid var(--line);border-radius:30px;padding:7px 12px;font-size:11px;font-weight:750;letter-spacing:.4px;white-space:normal}.badge.warn{color:var(--amber);background:var(--amber-bg);border-color:transparent}.badge.good{color:var(--green);background:var(--mint);border-color:transparent}.context{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 24px}.context span{font-size:12px;color:var(--muted);padding:7px 12px;border:1px solid var(--line);border-radius:6px;overflow-wrap:anywhere}.metrics{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;margin:0 0 22px}.metric{background:var(--surface);border:1px solid var(--line);border-radius:12px;padding:20px}.metric .label{font-size:12px;color:var(--muted);font-weight:600}.metric .value{font-size:29px;line-height:1.4;letter-spacing:-1px;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}.metric .note{font-size:11px;color:var(--muted);margin-top:5px}.grid{display:grid;grid-template-columns:minmax(0,1.8fr) minmax(0,1fr);gap:22px;margin-bottom:22px}.panel{min-width:0;background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:25px}.panel h2{font-size:19px;line-height:1.3;margin:0 0 5px;font-weight:650;letter-spacing:-.4px}.sub{font-size:12px;color:var(--muted);margin:0 0 20px}.legend{font-size:12px;display:flex;gap:18px;flex-wrap:wrap;color:var(--muted);margin:12px 0 0}.swatch{display:inline-block;width:18px;height:3px;vertical-align:middle;margin-right:6px;background:var(--green)}.swatch.cash{background:var(--blue)}svg.chart{display:block;width:100%;height:auto;overflow:visible}svg text{font:12px system-ui,sans-serif;fill:var(--muted)}svg .axis{stroke:var(--line);stroke-width:1}svg .series{fill:none;stroke:var(--green);stroke-width:2.5;stroke-linejoin:round;stroke-linecap:round}svg .cash-series{stroke:var(--blue);stroke-dasharray:5 4}svg .drawdown{stroke:var(--rose)}.chart-caption{font-size:11px;color:var(--muted);margin-top:10px}.empty{min-height:100px;display:flex;align-items:center;justify-content:center;border:1px dashed var(--line);border-radius:8px;color:var(--muted);font-size:13px;padding:24px;text-align:center}.table-wrap{overflow-x:auto}table{border-collapse:collapse;width:100%;font-size:13px}th{text-align:left;color:var(--muted);font-size:11px;text-transform:uppercase;letter-spacing:.8px;font-weight:650}td,th{padding:11px 9px;border-bottom:1px solid var(--line);vertical-align:top;overflow-wrap:anywhere}td:first-child,th:first-child{padding-left:0}td:last-child,th:last-child{padding-right:0}td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}caption{text-align:left;color:var(--muted);font-size:11px;padding:10px 0;caption-side:bottom}.kvs{margin:0}.kvs div{display:flex;justify-content:space-between;align-items:baseline;gap:20px;border-bottom:1px solid var(--line);padding:11px 0}.kvs dt{color:var(--muted);font-size:12px}.kvs dd{font-size:13px;text-align:right;margin:0;font-variant-numeric:tabular-nums;overflow-wrap:anywhere}.section-heading{display:flex;justify-content:space-between;align-items:start;gap:20px;margin-bottom:20px}.council{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:13px}.role{padding:18px;border:1px solid var(--line);border-radius:10px;background:var(--soft);min-width:0}.role .role-no{font:600 10px ui-monospace,monospace;color:var(--green);letter-spacing:1px}.role h3{font-size:14px;margin:7px 0}.role p{font-size:12px;color:var(--muted);margin:8px 0;overflow-wrap:anywhere}.role .stance{font-size:11px;font-weight:700;color:var(--ink);text-transform:uppercase}.refs{font:10px/1.7 ui-monospace,monospace;overflow-wrap:anywhere;color:var(--muted)}.notice{padding:14px 17px;border-left:3px solid var(--amber);background:var(--amber-bg);color:var(--amber);border-radius:0 8px 8px 0;font-size:12px;margin:18px 0 0;overflow-wrap:anywhere}.wide{margin-bottom:22px}.methods{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:24px}.methods h3{font-size:14px;margin:0 0 7px}.methods p,.methods li{font-size:12px;color:var(--muted)}.methods ul{padding-left:18px;margin:8px 0}.provenance{font:11px/1.7 ui-monospace,monospace;overflow-wrap:anywhere;white-space:pre-wrap;background:var(--soft);padding:16px;border-radius:8px;margin:14px 0 0}details{margin-top:16px}summary{cursor:pointer;color:var(--green);font-size:12px;font-weight:650}footer{border-top:1px solid var(--line);display:flex;justify-content:space-between;gap:24px;color:var(--muted);font-size:11px;padding-top:20px}footer p{max-width:760px;margin:0}.status-line{font-size:12px;color:var(--muted);margin:5px 0 0}.option-grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px}.option-grid .metric{padding:15px}.option-grid .value{font-size:23px}
@media(prefers-color-scheme:dark){:root{--bg:#101c1b;--surface:#182725;--ink:#e7eeea;--muted:#a7bbb2;--line:#344941;--green:#83dac0;--mint:#1c4237;--blue:#9dbfec;--amber:#e5c181;--amber-bg:#3b3020;--rose:#efa0a4;--soft:#20332e}}
@media(max-width:800px){main{padding:22px 18px 35px}.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.grid{grid-template-columns:1fr}.council{grid-template-columns:repeat(2,minmax(0,1fr))}.hero{align-items:start}.hero h1{letter-spacing:-1px}.panel{padding:20px}.option-grid{grid-template-columns:1fr}.methods{grid-template-columns:1fr}}
@media(max-width:450px){.topbar{align-items:start}.edition{max-width:130px;text-align:right}.hero{display:block}.hero .badge{margin-top:16px}.metric{padding:15px}.metric .value{font-size:21px}.council{grid-template-columns:1fr}.section-heading{display:block}.section-heading .badge{margin-top:10px}footer{display:block}footer p+p{margin-top:12px}}
@media print{:root{color-scheme:light;--bg:#fff;--surface:#fff;--ink:#111;--muted:#444;--line:#ccc;--green:#075b4e;--mint:#eef5f1;--blue:#32588a;--amber:#664000;--amber-bg:#faf5e8;--rose:#8d3434;--soft:#f5f5f5}main{max-width:none;padding:0}.metrics{grid-template-columns:repeat(2,minmax(0,1fr))}.metric .value{font-size:24px}.grid{display:block}.grid .panel{margin-bottom:18px}.panel,.metric,.role{break-inside:avoid}.hero{padding:24px 0}.skip{display:none}.chart{max-height:300px}details{display:block}footer{margin-top:18px}}
""".strip()


def _text(value: Any, limit: int = 10000) -> str:
    """Bound free text; escape before it enters any HTML context."""
    if value is None:
        return "Not supplied"
    text = str(value)
    if len(text) > limit:
        text = text[:limit] + " [truncated]"
    return escape(text, quote=True)


def _mapping(value: Any) -> dict:
    return dict(value) if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> list:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return list(value)
    # NumPy arrays are deliberately accepted without importing NumPy.
    if hasattr(value, "tolist"):
        result = value.tolist()
        return result if isinstance(result, list) else []
    return []


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, Real):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _fmt(value: Any, kind: str = "number") -> str:
    number = _number(value)
    if number is None:
        return "Not available"
    if kind == "percent":
        if abs(number) > 1e100:
            return 'Outside display range'
        return f"{100 * number:,.2f}%"
    if kind == "integer":
        return f"{number:,.0f}"
    if kind == "small":
        return f"{number:,.4f}"
    return f"{number:,.2f}"


def _pick(mapping: Mapping, *keys: str) -> Any:
    for key in keys:
        if key in mapping and mapping[key] is not None:
            return mapping[key]
    return None


def _metric(label: str, value: Any, note: str, kind: str = "number") -> str:
    return (f'<div class="metric"><div class="label">{_text(label)}</div>'
            f'<div class="value">{_fmt(value, kind)}</div>'
            f'<div class="note">{_text(note)}</div></div>')


def _key_values(rows: list[tuple[str, str]]) -> str:
    return '<dl class="kvs">' + ''.join(
        f'<div><dt>{_text(label)}</dt><dd>{value}</dd></div>' for label, value in rows
    ) + '</dl>'


def _line_chart(values: list, dates: list, label: str, chart_id: str,
                second: list | None = None, percentage: bool = False) -> str:
    """Draw numeric values only. Invalid observations are never silently dropped."""
    clean = [_number(v) for v in values]
    if not clean or any(v is None for v in clean):
        return '<div class="empty">No complete finite series supplied for this chart.</div>'
    if len(clean) > 100000:
        return '<div class="empty">Series exceeds the report limit of 100,000 observations.</div>'
    companion = [_number(v) for v in (second or [])]
    if len(companion) != len(clean) or any(v is None for v in companion):
        companion = []
    all_values = clean + companion
    if any(abs(v) > 1e100 for v in all_values):
        return '<div class="empty">Series magnitude exceeds the supported chart range.</div>'
    lo, hi = min(all_values), max(all_values)
    if percentage:
        hi = max(0.0, hi)
    spread = hi - lo
    padding = (spread * .12) if spread else max(abs(hi) * .02, .01)
    lo -= padding
    hi += padding
    # Width of plot is fixed in SVG coordinates and scales with the container.
    left, right, top, bottom = 65, 720, 20, 245
    def x(i: int) -> float:
        return left + (right - left) * i / max(1, len(clean) - 1)
    def y(v: float) -> float:
        return bottom - (bottom - top) * (v - lo) / (hi - lo)
    # Preserve extrema through bucketed sampling. The table/JSON retain exact values.
    indices = list(range(len(clean)))
    if len(indices) > 1400:
        selected = {0, len(clean) - 1}
        width = math.ceil(len(clean) / 350)
        for start in range(0, len(clean), width):
            stop = min(start + width, len(clean))
            for series in (clean, companion):
                if series:
                    selected.add(min(range(start, stop), key=lambda i: series[i]))
                    selected.add(max(range(start, stop), key=lambda i: series[i]))
        indices = sorted(selected)
    lines = []
    for i in range(5):
        val = lo + (hi - lo) * i / 4
        ypos = y(val)
        tick = f"{val * 100:.1f}%" if percentage else f"{val:,.0f}"
        lines.append(f'<line class="axis" x1="{left}" x2="{right}" y1="{ypos:.2f}" y2="{ypos:.2f}"/>'
                     f'<text x="{left - 10}" y="{ypos + 4:.2f}" text-anchor="end">{tick}</text>')
    for values_, style in ((clean, 'series drawdown' if percentage else 'series'), (companion, 'series cash-series')):
        if values_:
            points = ' '.join(f'{x(i):.2f},{y(values_[i]):.2f}' for i in indices)
            lines.append(f'<polyline class="{style}" points="{points}"/>')
    first = dates[0] if dates else 'First observation'
    last = dates[-1] if dates else f'Observation {len(clean)}'
    lines.append(f'<text x="{left}" y="275">{_text(first, 80)}</text>')
    lines.append(f'<text x="{right}" y="275" text-anchor="end">{_text(last, 80)}</text>')
    description = (f'{len(clean):,} observations. Minimum {_fmt(min(clean), "percent" if percentage else "number")}; '
                   f'maximum {_fmt(max(clean), "percent" if percentage else "number")}.')
    return (f'<svg class="chart" viewBox="0 0 740 290" role="img" aria-labelledby="{chart_id}-title {chart_id}-desc">'
            f'<title id="{chart_id}-title">{_text(label)}</title><desc id="{chart_id}-desc">{description}</desc>'
            + ''.join(lines) + '</svg>')


def _equity_series(backtest: Mapping) -> tuple[list, list, list]:
    raw = _sequence(_pick(backtest, 'equity', 'equity_curve', 'wealth', 'nav'))
    dates = _sequence(backtest.get('dates'))
    cash = _sequence(_pick(backtest, 'cash', 'cash_curve'))
    if raw and isinstance(raw[0], Mapping):
        dates = [_pick(item, 'date', 'timestamp', 'seq') for item in raw]
        cash = [item.get('cash') for item in raw]
        raw = [_pick(item, 'equity', 'wealth', 'nav') for item in raw]
    return raw, dates, cash


def _drawdowns(equity: list) -> list:
    clean = [_number(v) for v in equity]
    if not clean or any(v is None or v <= 0 for v in clean):
        return []
    peak = clean[0]
    result = []
    for value in clean:
        peak = max(peak, value)
        result.append(value / peak - 1)
    return result


def _holdings(backtest: Mapping) -> str:
    symbols = _sequence(backtest.get('symbols'))
    weights = _pick(backtest, 'final_weights', 'weights')
    if isinstance(weights, Mapping):
        pairs = list(weights.items())
    else:
        values = _sequence(weights)
        if values and isinstance(values[-1], (list, tuple)):
            values = values[-1]
        pairs = list(zip(symbols, values)) if len(symbols) == len(values) else []
    if not pairs:
        positions = _sequence(backtest.get('holdings'))
        pairs = [(p.get('symbol', 'Unknown'), p.get('weight')) for p in positions if isinstance(p, Mapping)]
    if not pairs:
        return '<div class="empty">Final portfolio weights were not supplied.</div>'
    rows = ''.join(f'<tr><td>{_text(symbol, 100)}</td><td class="num">{_fmt(weight, "percent")}</td></tr>'
                   for symbol, weight in pairs[:100])
    return ('<div class="table-wrap"><table><caption>Weights are fractions of final portfolio equity. '
            'Uninvested cash may remain.</caption><thead><tr><th scope="col">Asset</th><th scope="col" class="num">Weight</th>'
            f'</tr></thead><tbody>{rows}</tbody></table></div>')


def _council(council: Mapping) -> str:
    findings = _sequence(_pick(council, 'roles', 'findings', 'reviews', 'agents', 'assessments', 'opinions'))
    panels = []
    for i, finding in enumerate(findings[:12], 1):
        item = _mapping(finding)
        role = _pick(item, 'role', 'agent', 'name') or f'Reviewer {i}'
        role = str(role).replace('_', ' ').title()
        stance = _pick(item, 'stance', 'status', 'verdict') or 'Recorded finding'
        summary = _pick(item, 'summary', 'finding', 'rationale', 'message', 'conclusion')
        if summary is None:
            summary = _pick(item, 'observations', 'reasons', 'notes')
        if isinstance(summary, (list, tuple)):
            summary = ' '.join(str(s) for s in summary)
        refs = _sequence(_pick(item, 'evidence_ids', 'evidence', 'references'))
        panels.append(f'<article class="role"><div class="role-no">REVIEW {i:02d}</div><h3>{_text(role, 200)}</h3>'
                      f'<div class="stance">{_text(stance, 200)}</div><p>{_text(summary)}</p>'
                      f'<div class="refs">Evidence: {_text(", ".join(str(r) for r in refs) or "No references supplied", 2000)}</div></article>')
    if not panels:
        return '<div class="empty">No council review was supplied. No review outcome is inferred.</div>'
    return '<div class="council">' + ''.join(panels) + '</div>'



def _evidence_table(council: Mapping) -> str:
    evidence = _sequence(council.get('evidence'))
    if not evidence:
        return ''
    rows = []
    for entry in evidence[:200]:
        item = _mapping(entry)
        value = item.get('value')
        rendered = _text(value, 500) if not isinstance(value, (dict, list)) else _text(json.dumps(value, sort_keys=True, default=str), 2000)
        rows.append(f'<tr><td class="refs">{_text(item.get("id"), 150)}</td><td>{_text(item.get("label"), 500)}</td><td>{rendered}</td><td>{_text(item.get("unit", ""), 100)}</td></tr>')
    return ('<details><summary>Inspect the council evidence ledger</summary><div class="table-wrap"><table>'
            '<caption>Values appear exactly as supplied to the council, in the indicated units.</caption>'
            '<thead><tr><th scope="col">Reference</th><th scope="col">Measure</th><th scope="col">Value</th><th scope="col">Unit</th></tr></thead><tbody>'
            + ''.join(rows) + '</tbody></table></div></details>')

def generate_report(data: dict) -> str:
    """Render a portable research report. All input strings are escaped as plain text.

    Expected top-level keys: ``metadata``, ``backtest``, ``council``, ``options``.
    Missing sections are explicitly labelled. Financial ratios use decimal fractions,
    and currency values use portfolio units because the renderer does not assume USD.
    This API accepts in-memory data from trusted callers; enforce request/file byte
    limits before parsing untrusted JSON. Charts cap at 100,000 observations and
    absolute magnitudes of 1e100. Free text and displayed table lengths are bounded.
    """
    if not isinstance(data, Mapping):
        raise TypeError('report data must be a mapping')
    metadata = _mapping(data.get('metadata'))
    backtest = _mapping(data.get('backtest'))
    council = _mapping(data.get('council'))
    options = _mapping(data.get('options'))
    dataset = _mapping(backtest.get('dataset'))
    metrics = _mapping(backtest.get('metrics'))
    risk = _mapping(_pick(backtest, 'risk', 'historical_risk'))
    if not risk:
        risk = _mapping(data.get('risk'))
    equity, dates, cash = _equity_series(backtest)
    drawdown = _sequence(backtest.get('drawdown')) or _drawdowns(equity)
    synthetic = metadata.get('synthetic', backtest.get('synthetic', dataset.get('synthetic')))
    classification = ('SYNTHETIC DATA · RESEARCH DEMO' if synthetic is True else
                      'USER-SUPPLIED DATA · RESEARCH' if synthetic is False else
                      'DATA ORIGIN NOT SPECIFIED')
    title = metadata.get('title', 'Evidence before conviction.')
    source = _pick(metadata, 'source', 'data_source') or backtest.get('source') or dataset.get('source') or 'Source not supplied'
    config = _mapping(backtest.get('config'))
    strategy = _pick(backtest, 'strategy', 'strategy_name') or config.get('strategy') or 'Strategy not supplied'
    initial = _pick(backtest, 'initial_cash', 'initial_equity')
    if initial is None:
        initial = config.get('initial_cash')
    final = _pick(backtest, 'final_equity', 'final_wealth')
    if final is None and equity:
        final = equity[-1]
    total_return = _pick(metrics, 'total_return', 'cumulative_return')
    max_drawdown = _pick(metrics, 'max_drawdown', 'maximum_drawdown')
    if _number(max_drawdown) is not None:
        max_drawdown = abs(float(max_drawdown))
    if max_drawdown is None and drawdown:
        finite_drawdowns = [_number(v) for v in drawdown]
        if all(v is not None for v in finite_drawdowns):
            max_drawdown = abs(min(finite_drawdowns))
    costs = _pick(backtest, 'total_cost', 'total_costs', 'transaction_costs')
    if costs is None:
        costs = metrics.get('total_transaction_cost')
    trades = _sequence(backtest.get('trades'))
    if costs is None and 'trades' in backtest:
        cost_values = [_number(_mapping(t).get('transaction_cost')) for t in trades]
        if all(v is not None for v in cost_values):
            costs = sum(cost_values)
    gate = _pick(council, 'outcome', 'decision', 'gate', 'status', 'verdict') or 'No review supplied'
    if isinstance(gate, Mapping):
        gate = _pick(gate, 'status', 'decision', 'verdict') or 'See review detail'
    mode = council.get('mode')
    roles = _sequence(council.get('roles'))
    if mode is None and roles and all(_mapping(r).get('mode') == 'deterministic_rule' for r in roles):
        mode = f'Deterministic rules, {len(roles)}-role review'
    mode = mode or 'Mode not supplied'
    if mode == 'offline_deterministic_research_council':
        mode = 'Deterministic rules, six-role review'
    gate = {'research_only': 'Research only', 'blocked_for_review': 'Blocked for review'}.get(str(gate), gate)
    dissent = _pick(council, 'dissent', 'dissenting_views', 'warnings')
    if isinstance(dissent, (list, tuple)):
        dissent = '; '.join(str(item) for item in dissent)
    risk_rows = [
        ('Annualised return', _fmt(_pick(metrics, 'annualised_return', 'annualized_return', 'cagr'), 'percent')),
        ('Annualised volatility', _fmt(_pick(metrics, 'annualised_volatility', 'annualized_volatility', 'volatility'), 'percent')),
        ('Sharpe ratio', _fmt(_pick(metrics, 'sharpe_ratio', 'sharpe'))),
        ('Historical value at risk', _fmt(_pick(risk, 'var', 'value_at_risk'), 'percent')),
        ('Historical expected shortfall', _fmt(_pick(risk, 'expected_shortfall', 'es', 'cvar'), 'percent')),
        ('Risk confidence level', _fmt(risk.get('confidence'), 'percent')),
        ('Total transaction costs', _fmt(costs)),
    ]
    option_html = '<div class="empty">No option valuation experiment was included.</div>'
    if options:
        option_html = '<div class="option-grid">' + ''.join([
            _metric('Black–Scholes value', _pick(options, 'black_scholes', 'analytical', 'analytic_price'), 'European option · per underlying unit', 'small'),
            _metric('Binomial value', _pick(options, 'binomial', 'binomial_price', 'crr'), 'Discrete tree · see recorded inputs', 'small'),
            _metric('Monte Carlo estimate', _pick(_mapping(options.get('monte_carlo')), 'price', 'estimate') if isinstance(options.get('monte_carlo'), Mapping) else options.get('monte_carlo'), 'Risk-neutral simulation · see interval below', 'small'),
        ]) + '</div>'
        option_html += '<details><summary>Inspect option inputs and uncertainty</summary><pre class="provenance">' + _text(json.dumps(options, indent=2, sort_keys=True, default=str), 30000) + '</pre></details>'
    provenance = {key: metadata[key] for key in sorted(metadata) if key != 'title'}
    if 'integrity_sha256' in data:
        provenance['artifact_integrity_sha256'] = data['integrity_sha256']
    for key in ('report_hash', 'report_sha256', 'limitations', 'evidence_hash', 'digest', 'evidence_digest', 'audit_hash', 'policy', 'source', 'gates', 'trace'):
        if key in council:
            provenance[f'council_{key}'] = council[key]
    if 'config' in backtest:
        provenance['backtest_config'] = backtest['config']
    provenance_text = json.dumps(provenance, indent=2, sort_keys=True, default=str)
    style_hash = base64.b64encode(sha256(_CSS.encode('utf-8')).digest()).decode('ascii')
    csp = f"default-src 'none'; style-src 'sha256-{style_hash}'; base-uri 'none'; form-action 'none'; object-src 'none'"
    warnings = (_sequence(backtest.get('warnings')) + _sequence(backtest.get('assumptions'))
                + _sequence(metadata.get('warnings')) + _sequence(metadata.get('limitations')))
    warning_html = ''.join(f'<li>{_text(w)}</li>' for w in warnings[:30])
    benchmark = _mapping(data.get('benchmark'))
    comparison = _mapping(data.get('cost_sensitivity'))
    comparison_html = ''
    if benchmark or comparison:
        benchmark_metrics = _mapping(benchmark.get('metrics'))
        cost_metrics = _mapping(comparison.get('metrics'))
        columns = [('Base strategy', metrics)]
        if benchmark:
            columns.append(('Equal-weight benchmark', benchmark_metrics))
        if comparison:
            columns.append((f'Cost scenario: {comparison.get("comparison_bps", "unspecified")} bps', cost_metrics))
        headers = ''.join(f'<th scope="col" class="num">{_text(name, 100)}</th>' for name, _ in columns)
        rows = []
        for label, key, kind in [('Total return', 'total_return', 'percent'), ('Annualised volatility', 'annualised_volatility', 'percent'), ('Maximum drawdown (loss)', 'max_drawdown', 'percent'), ('Transaction costs', 'total_transaction_cost', 'number')]:
            cells = ''.join(f'<td class="num">{_fmt(abs(value[key]) if key == "max_drawdown" and _number(value.get(key)) is not None else value.get(key), kind)}</td>' for _, value in columns)
            rows.append(f'<tr><th scope="row">{label}</th>{cells}</tr>')
        comparison_html = ('<section class="panel wide"><h2>Comparison and cost sensitivity</h2><p class="sub">A matched benchmark and one explicit cost scenario help test the interpretation.</p><div class="table-wrap"><table><thead><tr><th scope="col">Measure</th>' + headers + '</tr></thead><tbody>' + ''.join(rows) + '</tbody></table></div>')
        if benchmark:
            comparison_html += '<p class="chart-caption">Benchmark: ' + _text(benchmark.get('name', 'Name not supplied'), 500) + '. Cumulative return difference: ' + (_fmt(100 * benchmark['total_return_difference']) if _number(benchmark.get('total_return_difference')) is not None else 'Not available') + ' percentage points. This difference is not risk-adjusted alpha.</p>'
        if comparison:
            comparison_html += '<p class="chart-caption">Base cost: ' + _text(comparison.get('base_bps'), 50) + ' basis points; comparison: ' + _text(comparison.get('comparison_bps'), 50) + ' basis points. ' + _text(comparison.get('meaning', ''), 500) + '</p>'
        comparison_html += '</section>'
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="{escape(csp, quote=True)}"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="color-scheme" content="light dark"><title>Atlas Quant | {_text(title, 200)}</title><style>{_CSS}</style></head>
<body><a class="skip" href="#main">Skip to research report</a><main id="main">
<div class="topbar"><div class="brand">ATLAS<span> / QUANT</span></div><div class="edition">Independent research<br>Reproducible by design</div></div>
<header class="hero"><div><div class="eyebrow">Portfolio research notebook</div><h1>{_text(title, 300)}</h1><p>A transparent account of the data, portfolio mechanics, uncertainty and review behind one research run.</p></div><span class="badge warn">{classification}</span></header>
<div class="context"><span>Strategy: {_text(strategy, 100)}</span><span>Source: {_text(source, 200)}</span><span>Window: {_text(dates[0] if dates else 'Not supplied', 100)} to {_text(dates[-1] if dates else 'Not supplied', 100)}</span></div>
<section class="metrics" aria-label="Portfolio summary">
{_metric('Final portfolio equity', final, 'Net of modelled transaction costs')}
{_metric('Total return', total_return, 'Full reported observation window', 'percent')}
{_metric('Maximum drawdown', max_drawdown, 'Loss from the running equity peak', 'percent')}
{_metric('Starting capital', initial, 'Values in supplied portfolio units')}
</section>
<div class="grid"><section class="panel"><h2>Capital through time</h2><p class="sub">Net equity and uninvested cash across the reported window.</p>{_line_chart(equity, dates, 'Portfolio equity and cash', 'equity', cash)}<div class="legend"><span><i class="swatch"></i>Net equity</span><span><i class="swatch cash"></i>Cash, if supplied</span></div><p class="chart-caption">Charts retain endpoints and local extrema when long series are reduced for display. Exact values remain in the JSON output.</p></section>
<section class="panel"><h2>Risk in context</h2><p class="sub">Observed sample statistics, with no predictive guarantee.</p>{_key_values(risk_rows)}<p class="chart-caption">Value at risk and expected shortfall use the supplied return sample and confidence level. Values express losses as fractions of equity.</p></section></div>
<div class="grid"><section class="panel"><h2>Drawdown</h2><p class="sub">Distance below the running peak, including the initial reported capital.</p>{_line_chart(drawdown, dates, 'Portfolio drawdown', 'drawdown', percentage=True)}</section><section class="panel"><h2>Closing allocation</h2><p class="sub">Portfolio weights at the final observation.</p>{_holdings(backtest)}</section></div>
{comparison_html}
<section class="panel wide"><div class="section-heading"><div><h2>Research council</h2><p class="status-line">Mode: {_text(mode, 200)}. Findings reflect the recorded evidence.</p></div><span class="badge">{_text(gate, 200)}</span></div>{_council(council)}{f'<div class="notice"><strong>Dissent and qualifications:</strong> {_text(dissent)}</div>' if dissent else ''}{_evidence_table(council)}</section>
<section class="panel wide"><h2>Derivative laboratory</h2><p class="sub">A separate pricing experiment. Model values are conditional on the stated assumptions.</p>{option_html}</section>
<section class="panel wide"><h2>Interpretation and reproducibility</h2><p class="sub">Read the conventions before comparing results or changing parameters.</p><div class="methods"><div><h3>Portfolio mechanics</h3><p>Signals are formed from information available at their decision time. Consult the recorded backtest configuration and ledger for execution timing, lookback, rebalancing and transaction costs. Capital and cash are shown in the units supplied to the calculation.</p><h3>Limits of the experiment</h3><p>Historical and synthetic results do not establish future profitability. Costs, slippage, liquidity, taxes, corporate actions and data selection affect real outcomes. A deterministic review is a reproducible rules assessment, not independent model intelligence.</p></div><div><h3>Reading the measures</h3><p>Returns compound through time. Drawdown compares equity with its previous high. Annualisation assumes the reported observation frequency; a short sample can make annualised figures unstable. Expected shortfall summarises the estimated loss in the selected tail of the sample.</p><h3>Evidence record</h3><p>Missing values stay visible. This report does not infer an asset currency, replace missing observations with zero, execute trades, or fetch external data.</p>{f'<ul>{warning_html}</ul>' if warning_html else ''}</div></div><details><summary>Inspect provenance and run configuration</summary><pre class="provenance">{_text(provenance_text, 50000)}</pre></details></section>
<footer><p>Atlas Quant · Research and education. Results require independent judgement and are not personalised investment advice. This file contains no scripts, trackers or external resources.</p><p>Static research report</p></footer>
</main></body></html>'''


render_report = generate_report
