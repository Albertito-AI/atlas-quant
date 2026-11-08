"""Escaped, offline presentation of the five-stage agent-lab evidence record.

Rendering never reruns a model, supplies missing measurements or approves a
trade. Plots describe recorded synthetic observations and declared scenarios.
"""
from __future__ import annotations

import base64
from hashlib import sha256
import math

from .report import _CSS, _fmt, _mapping, _number, _sequence, _text

_COLOURS = ("#007f80", "#4674bd", "#be581d", "#8153a2")
_EMPTY = '<div class="empty">Complete, finite numerical evidence is unavailable for this chart.</div>'


def _probability_series(record: dict, field: str) -> list[list[float]]:
    rows = _sequence(record.get(field))
    if not rows or len(rows) > 100000:
        return []
    clean = []
    for row in rows:
        values = [_number(v) for v in _sequence(row)]
        if (not 1 <= len(values) <= 4 or any(v is None or not 0 <= v <= 1 for v in values)
                or not math.isclose(sum(values), 1, abs_tol=1e-8)):
            return []
        if clean and len(values) != len(clean[0]):
            return []
        clean.append(values)
    return [list(values) for values in zip(*clean)]


def _lines(series: list[list], labels: list[str], title: str, chart_id: str) -> str:
    """Probability plot with all source observations checked before subsampling."""
    if not series or len(series) > 4 or len(series) != len(labels):
        return _EMPTY
    n = len(series[0])
    if not 1 <= n <= 100000 or any(len(s) != n for s in series):
        return _EMPTY
    if any(_number(v) is None or not 0 <= v <= 1 for s in series for v in s):
        return _EMPTY
    # Bound SVG size while retaining every local series extremum in each bucket.
    indices = set((0, n - 1))
    width = max(1, math.ceil(n / 300))
    for start in range(0, n, width):
        end = min(n, start + width)
        for values in series:
            indices.add(min(range(start, end), key=lambda i: values[i]))
            indices.add(max(range(start, end), key=lambda i: values[i]))
    indices = sorted(indices)
    pieces = []
    for tick in (0, .25, .5, .75, 1):
        y = 230 - 200 * tick
        pieces.append(f'<line x1="60" x2="700" y1="{y}" y2="{y}" stroke="#d9e3de"/>'
                      f'<text x="49" y="{y+4}" text-anchor="end">{tick:.0%}</text>')
    legend = []
    for j, values in enumerate(series):
        points = ' '.join(f'{60+640*i/max(1,n-1):.2f},{230-200*values[i]:.2f}' for i in indices)
        pieces.append(f'<polyline points="{points}" fill="none" stroke="{_COLOURS[j]}" stroke-width="2.4"/>')
        legend.append(f'<span><svg width="16" height="6" aria-hidden="true"><rect width="16" height="4" fill="{_COLOURS[j]}"/></svg> {_text(labels[j])}</span>')
    pieces.append(f'<text x="60" y="254">1</text><text x="700" y="254" text-anchor="end">{n}</text>'
                  '<text x="380" y="277" text-anchor="middle">Observation number</text>')
    return (f'<svg class="chart" viewBox="0 0 740 290" role="img" aria-labelledby="{chart_id}-title {chart_id}-desc">'
            f'<title id="{chart_id}-title">{_text(title)}</title><desc id="{chart_id}-desc">'
            f'Probability from zero to one over {n} recorded observations. {len(indices)} points displayed with local extrema retained.</desc>'
            + ''.join(pieces) + '</svg><div class="legend">' + ''.join(legend) + '</div>')


def _scenario_scatter(scenarios: dict) -> str:
    if not 1 <= len(scenarios) <= 4:
        return _EMPTY
    groups = []
    for name, matrix in scenarios.items():
        rows = _sequence(matrix)
        if not 1 <= len(rows) <= 20000:
            return _EMPTY
        clean = []
        for row in rows:
            values = [_number(v) for v in _sequence(row)]
            if len(values) < 2 or any(v is None or abs(v) > 100 for v in values):
                return _EMPTY
            clean.append(values[:2])
        groups.append((name, clean))
    xs = [p[0] for _, rows in groups for p in rows]
    ys = [p[1] for _, rows in groups for p in rows]
    lo_x, hi_x, lo_y, hi_y = min(xs), max(xs), min(ys), max(ys)
    pad_x, pad_y = max((hi_x-lo_x)*.05, 1e-6), max((hi_y-lo_y)*.05, 1e-6)
    lo_x, hi_x, lo_y, hi_y = lo_x-pad_x, hi_x+pad_x, lo_y-pad_y, hi_y+pad_y
    def x(v):
        return 75 + 620 * (v-lo_x) / (hi_x-lo_x)
    def y(v):
        return 245 - 210 * (v-lo_y) / (hi_y-lo_y)
    pieces, legend = [], []
    for i in range(5):
        xv, yv = lo_x+(hi_x-lo_x)*i/4, lo_y+(hi_y-lo_y)*i/4
        pieces.append(f'<line x1="75" x2="695" y1="{y(yv):.2f}" y2="{y(yv):.2f}" stroke="#d9e3de"/>'
                      f'<text x="64" y="{y(yv)+4:.2f}" text-anchor="end">{yv:.1%}</text>'
                      f'<text x="{x(xv):.2f}" y="268" text-anchor="middle">{xv:.1%}</text>')
    for j, (name, rows) in enumerate(groups):
        step = max(1, math.ceil(len(rows)/500))
        for a, b in rows[::step]:
            pieces.append(f'<circle cx="{x(a):.2f}" cy="{y(b):.2f}" r="2.2" fill="{_COLOURS[j]}" opacity=".45"/>')
        legend.append(f'<span><svg width="12" height="12" aria-hidden="true"><rect width="12" height="12" fill="{_COLOURS[j]}"/></svg> {_text(name)}: {len(rows):,} recorded draws</span>')
    pieces.append('<text x="385" y="298" text-anchor="middle">First asset simple return</text>'
                  '<text x="18" y="140" text-anchor="middle" transform="rotate(-90 18 140)">Second asset simple return</text>')
    return ('<svg class="chart" viewBox="0 0 740 315" role="img" aria-labelledby="scenario-title scenario-desc">'
            '<title id="scenario-title">Joint scenario returns for the first two assets</title>'
            '<desc id="scenario-desc">Points are generated conditional draws or imposed stress draws, not forecasts of all possible outcomes. At most 500 points per scenario set are displayed.</desc>'
            + ''.join(pieces) + '</svg><div class="legend">' + ''.join(legend) + '</div>')


def _table(headers: list[str], rows: list[list[str]]) -> str:
    return ('<div class="table-wrap"><table><thead><tr>'
            + ''.join(f'<th scope="col">{_text(h)}</th>' for h in headers)
            + '</tr></thead><tbody>'
            + ''.join('<tr>' + ''.join(f'<td>{cell}</td>' for cell in row) + '</tr>' for row in rows)
            + '</tbody></table></div>')


def generate_lab_report(record: dict) -> str:
    """Render the supplied lab record. Missing values never acquire an approval."""
    record = _mapping(record)
    metadata, data = _mapping(record.get('metadata')), _mapping(record.get('data'))
    beliefs, experts = _mapping(record.get('beliefs')), _mapping(record.get('experts'))
    expert_model = _mapping(_mapping(record.get('model')).get('experts'))
    governance = _mapping(record.get('governance'))
    prior = _probability_series(beliefs, 'prior_probabilities')
    posterior = _probability_series(beliefs, 'posterior_probabilities')
    regime = (_lines([prior[1], posterior[1]], ['Before observation', 'After observation'],
                     'Conditional stress-regime probability', 'regime')
              if len(prior) == len(posterior) == 2 else _EMPTY)
    expert_series = _probability_series(experts, 'prior_probabilities')
    expert_names = _sequence(expert_model.get('names'))
    if len(expert_names) != len(expert_series):
        expert_names = [f'Expert {i+1}' for i in range(len(expert_series))]
    expert_chart = _lines(expert_series, expert_names,
                          'Expert weights fixed before each observation', 'experts')
    expert_rows = [[_text(name), _fmt(mean, 'small'), _fmt(std, 'small')]
                   for name, mean, std in zip(expert_names, _sequence(expert_model.get('means')),
                                              _sequence(expert_model.get('stds')))]
    diagnostic = _mapping(record.get('diagnostics'))
    allocation_rows, risk_rows = [], []
    symbols = _sequence(data.get('symbols'))
    for name, raw in list(_mapping(record.get('allocations')).items())[:8]:
        allocation = _mapping(raw)
        weights = [_number(v) for v in _sequence(allocation.get('weights'))]
        valid = (weights and len(weights) == len(symbols) and all(v is not None and 0 <= v <= 1 for v in weights)
                 and math.isclose(sum(weights), 1, abs_tol=1e-8))
        allocation_rows.append([_text(name), ', '.join(f'{_text(s)}: {_fmt(w,"percent")}' for s,w in zip(symbols,weights)) if valid else 'Not available'])
        evaluation = _mapping(allocation.get('evaluation'))
        heldout = _mapping(_mapping(allocation.get('heldout_evaluation')).get('per_scenario_cvar'))
        for scenario, value in list(_mapping(evaluation.get('per_scenario_cvar')).items())[:20]:
            risk_rows.append([_text(name), _text(scenario), _fmt(value, 'percent'),
                              _fmt(heldout.get(scenario), 'percent')])
    gate_rows = []
    for raw in _sequence(governance.get('checks'))[:30]:
        gate = _mapping(raw)
        state = 'Pass' if gate.get('passed') is True else 'Blocked' if gate.get('passed') is False else 'Unavailable'
        gate_rows.append([_text(gate.get('name')), _fmt(gate.get('value'), 'small'),
                          _text(gate.get('relation')), _fmt(gate.get('limit'), 'small'), state])
    outcome = governance.get('outcome')
    outcome = outcome if outcome in ('blocked_for_review', 'research_only') else 'Unavailable'
    trace_rows = []
    for raw in _sequence(record.get('trace'))[:20]:
        item = _mapping(raw)
        trace_rows.append([_text(item.get('role')), _text(item.get('method')),
                           _text(item.get('input_refs')), _text(item.get('output_refs')), _text(item.get('authority'))])
    css = _CSS + '\n.lab-number{font:700 12px ui-monospace,monospace;color:var(--green);letter-spacing:1px}.lab-panel{margin-bottom:22px}.lab-panel h2{margin-top:5px}.lab-panel>p{color:var(--muted);font-size:13px}@media print{.lab-panel{padding:18px}.lab-panel td,.lab-panel th{padding:7px 6px;font-size:11px}.lab-panel>p{font-size:11px}.lab-panel tr{break-inside:avoid}}'
    css_hash = base64.b64encode(sha256(css.encode()).digest()).decode()
    return f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'none'; style-src 'sha256-{css_hash}'; img-src 'none'; base-uri 'none'; form-action 'none'">
<title>Atlas Quant: probabilistic agent lab</title><style>{css}</style></head>
<body><a class="skip" href="#main">Skip to evidence</a><main id="main">
<header class="topbar"><div class="brand">ATLAS <span>QUANT</span></div><div class="edition">Probabilistic agent lab</div></header>
<div class="hero"><div><div class="eyebrow">SYNTHETIC DATA · FIXED MODELS</div><h1>Inspect the calculation.<br>Challenge the decision.</h1><p>Five mathematical stages connect conditional beliefs, competing models, generated scenarios and constrained allocation. This offline demonstrator does not deploy language-model agents or AGI.</p></div></div>
<div class="context"><span>Seed: {_text(metadata.get('seed'))}</span><span>Observations: {_text(metadata.get('observations'))}</span><span>Draws per scenario set: {_text(metadata.get('scenario_count'))}</span><span>Outcome: {_text(outcome)}</span></div>
<section class="panel lab-panel"><div class="lab-number">01 / INFER A HIDDEN STATE</div><h2>Beliefs change as observations arrive</h2><p>The prior uses earlier observations. The posterior includes the current observation. Probabilities are conditional on the declared Gaussian state model; low entropy does not establish accuracy or profit.</p>{regime}</section>
<section class="panel lab-panel"><div class="lab-number">02 / COMPARE FIXED EXPERTS</div><h2>Score first, then update the weights</h2><p>These are fixed Gaussian hypotheses. A weight is a Bayesian model weight, not a vote by an independent expert. Shared model errors can remain invisible to agreement.</p>{expert_chart}{_table(['Fixed hypothesis','Mean log return','Log-return standard deviation'],expert_rows)}<p>Inputs are fractions per hypothetical observation. Predictive variance combines within-model variance and disagreement between candidate means. The between-mean share at the last pre-observation prediction is {_fmt(diagnostic.get('final_expert_disagreement_fraction'),'percent')}. This conditional diagnostic excludes shared model error and parameter uncertainty.</p></section>
<section class="panel lab-panel"><div class="lab-number">03 / CHALLENGE JOINT OUTCOMES</div><h2>Dependence matters in a stress scenario</h2><p>Each point is a joint simulated return vector. The view shows the first two assets; the calculation uses every recorded asset. Scenario sets have explicit assumptions and are not an exhaustive set of future markets.</p>{_scenario_scatter(_mapping(record.get('scenario_sets')))}</section>
<section class="panel lab-panel"><div class="lab-number">04 / OPTIMISE THE DECLARED LOSS</div><h2>Minimise the worst scenario tail loss</h2><p>Long-only allocation targets are constrained to sum to one. Robustness applies to the supplied scenario sets. These targets are research proposals; fees, execution and market impact are absent from this optimisation.</p>{_table(['Proposal','Target asset weights'],allocation_rows)}{_table(['Proposal','Scenario set','Fitted expected shortfall','Held-out expected shortfall'],risk_rows)}<p>Losses are one-observation fractions of wealth at the recorded confidence level. Held-out draws use a separate random stream under the same specified models. They challenge sample fitting without validating real-market behaviour.</p></section>
<section class="panel lab-panel"><div class="lab-number">05 / APPLY THE REVIEW POLICY</div><h2>Recorded outcome: {_text(outcome)}</h2><p>Optimisation success cannot override a failed review gate. Risk evidence: {_text(governance.get('risk_evidence'))} Values and limits below use the record's numerical units: observation counts, loss fractions and normalised entropy. A research-only outcome is not a trade approval.</p>{_table(['Check','Recorded value','Relation','Limit','Result'],gate_rows)}</section>
<section class="panel lab-panel"><h2>Evidence trace</h2>{_table(['Role','Method','Inputs','Outputs','Authority'],trace_rows)}<p>Full inputs, model parameters, scenarios and outputs remain in the accompanying <code>lab.json</code>.</p><div class="provenance">SHA-256: {_text(record.get('integrity_sha256'))}</div><p>The digest detects changes relative to the recorded digest. It does not prove authorship, data truth or predictive validity.</p></section>
<footer><p>Offline research demonstrator. Generated data and fixed hypotheses illustrate implemented mathematics. No live feed, broker connection, autonomous language-model inference or claim of general intelligence.</p></footer>
</main></body></html>'''
