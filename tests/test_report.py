"""Presentation tests enforce safe rendering and honest missing-data semantics."""
import base64
from hashlib import sha256
from html.parser import HTMLParser
import math
import re
import unittest

from atlas_quant.report import generate_report, render_report


class StructureParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = []
        self.attributes = []
    def handle_starttag(self, tag, attrs):
        self.tags.append(tag)
        self.attributes.extend((tag, key, value) for key, value in attrs)


def example():
    roles = []
    for role in ('data_quality', 'performance', 'risk', 'costs', 'model_critique', 'synthesis'):
        roles.append({'role': role, 'mode': 'deterministic_rule', 'status': 'caution',
                      'reasons': ['The sample is synthetic.'], 'evidence_ids': ['e1']})
    return {
        'metadata': {'synthetic': True, 'seed': 42, 'dataset_sha256': 'a' * 64},
        'backtest': {
            'dataset': {'source': 'synthetic://seed/42', 'synthetic': True, 'symbols': ['SYN1', 'SYN2']},
            'config': {'strategy': 'equal_weight', 'initial_cash': 1000},
            'dates': ['2025-01-01', '2025-01-02', '2025-01-03'],
            'equity_curve': [1000, 1020, 1010], 'cash_curve': [1000, 0, 0],
            'final_weights': {'SYN1': 0.4, 'SYN2': 0.6},
            'metrics': {'total_return': 0.01, 'annualised_return': .12, 'annualised_volatility': .2,
                        'sharpe_ratio': .5, 'max_drawdown': -10/1020},
            'risk': {'var': .03, 'expected_shortfall': .04, 'confidence': .95},
            'trades': [{'transaction_cost': 1.1}],
            'assumptions': ['No final liquidation.'],
        },
        'council': {'roles': roles, 'outcome': 'research_only', 'dissent': ['model_critique'],
                    'evidence': [{'id': 'e1', 'label': 'Return', 'value': .01, 'unit': 'fraction'}],
                    'policy': {'max_drawdown': .2}, 'report_sha256': 'b' * 64},
        'options': {'input': {'spot': 100}, 'black_scholes': 10.45, 'binomial': 10.44,
                    'monte_carlo': {'price': 10.46, 'confidence_interval': [10.1, 10.8]}},
    }


class ReportTests(unittest.TestCase):
    def test_complete_report_has_all_panels(self):
        html = generate_report(example())
        for heading in ['Capital through time', 'Drawdown', 'Closing allocation', 'Research council',
                        'Derivative laboratory', 'Interpretation and reproducibility']:
            self.assertIn(heading, html)
        self.assertIn('1,010.00', html)
        self.assertIn('1.00%', html)
        self.assertIn('40.00%', html)
        self.assertIn('95.00%', html)
        self.assertIn('equal_weight', html)

    def test_missing_data_remains_missing(self):
        html = generate_report({})
        self.assertIn('Not available', html)
        self.assertIn('DATA ORIGIN NOT SPECIFIED', html)
        self.assertIn('No council review was supplied', html)
        self.assertNotIn('0.00%', html)
        self.assertNotIn('>0.00<', html)

    def test_false_synthetic_is_user_data(self):
        data = example()
        data['metadata']['synthetic'] = False
        self.assertIn('USER-SUPPLIED DATA', generate_report(data))

    def test_dataset_origin_fallback(self):
        data = example()
        data['metadata'] = {}
        html = generate_report(data)
        self.assertIn('SYNTHETIC DATA', html)
        self.assertIn('synthetic://seed/42', html)

    def test_malicious_strings_are_only_text(self):
        data = example()
        payload = '<script>alert("owned")</script><img src=x onerror=alert(1)>'
        data['metadata']['title'] = payload
        data['backtest']['dataset']['source'] = payload
        data['backtest']['dates'][0] = payload
        data['backtest']['final_weights'] = {payload: .5}
        data['council']['roles'][0]['reasons'] = [payload]
        data['council']['evidence'][0]['value'] = payload
        data['options']['input']['comment'] = payload
        data['metadata']['limitations'] = [payload]
        html = generate_report(data)
        parsed = StructureParser()
        parsed.feed(html)
        self.assertNotIn('script', parsed.tags)
        self.assertNotIn('img', parsed.tags)
        self.assertFalse(any(key.lower().startswith('on') for _, key, _ in parsed.attributes))
        self.assertIn('&lt;script&gt;', html)

    def test_no_executable_or_remote_resource_elements(self):
        parsed = StructureParser()
        parsed.feed(generate_report(example()))
        for tag in ['script', 'iframe', 'object', 'embed', 'form', 'link', 'img']:
            self.assertNotIn(tag, parsed.tags)
        for _, key, value in parsed.attributes:
            if key in ('src', 'href', 'action'):
                self.assertTrue(value.startswith('#'))
        self.assertFalse(any(key == 'style' for _, key, _ in parsed.attributes))

    def test_content_security_policy_hash_matches_exact_stylesheet(self):
        html = generate_report(example())
        css = re.search(r'<style>(.*?)</style>', html, re.S).group(1)
        digest = base64.b64encode(sha256(css.encode()).digest()).decode()
        self.assertIn('sha256-' + digest, html)
        self.assertIn('default-src &#x27;none&#x27;', html)
        self.assertNotIn('unsafe-inline', html)

    def test_nonfinite_metrics_not_reported_as_numbers(self):
        data = example()
        data['backtest']['metrics'] = {'total_return': math.nan, 'sharpe_ratio': math.inf, 'annualised_return': 1e308}
        html = generate_report(data)
        self.assertNotIn('>nan<', html)
        self.assertNotIn('>inf<', html)
        self.assertNotIn('inf%', html)
        self.assertIn('Not available', html)

    def test_boolean_not_numeric(self):
        data = example()
        data['backtest']['metrics']['total_return'] = True
        html = generate_report(data)
        self.assertIn('Total return</div><div class="value">Not available', html)

    def test_invalid_chart_is_not_silently_filtered(self):
        data = example()
        data['backtest']['equity_curve'][1] = math.nan
        html = generate_report(data)
        self.assertIn('No complete finite series supplied', html)
        self.assertNotIn('points="nan', html)

    def test_single_point_chart_supported(self):
        data = example()
        data['backtest']['equity_curve'] = [100]
        data['backtest']['dates'] = ['2025-01-01']
        html = generate_report(data)
        self.assertIn('1 observations.', html)
        self.assertNotIn('NaN', html)

    def test_constant_series_supported(self):
        data = example()
        data['backtest']['equity_curve'] = [100, 100, 100]
        data['backtest']['cash_curve'] = [0, 0, 0]
        html = generate_report(data)
        self.assertIn('polyline', html)
        self.assertNotIn('NaN', html)

    def test_extreme_finite_chart_fails_explicitly(self):
        data = example()
        data['backtest']['equity_curve'] = [1e308, 1e307, 1e308]
        html = generate_report(data)
        self.assertIn('exceeds the supported chart range', html)
        self.assertNotIn('points="nan', html)

    def test_long_series_is_bounded_for_svg(self):
        data = example()
        data['backtest']['equity_curve'] = [100 + math.sin(i) for i in range(10000)]
        data['backtest']['cash_curve'] = []
        html = generate_report(data)
        points = re.findall(r'points="([^"]*)"', html)
        self.assertLessEqual(max(len(p.split()) for p in points), 1402)
        self.assertIn('10,000 observations.', html)

    def test_bad_secondary_series_does_not_break_equity(self):
        data = example()
        data['backtest']['cash_curve'] = [1, 2]
        html = generate_report(data)
        self.assertIn('polyline class="series"', html)
        self.assertNotIn('polyline class="series cash-series"', html)

    def test_council_roles_evidence_and_mode(self):
        html = generate_report(example())
        self.assertEqual(html.count('<article class="role">'), 6)
        self.assertIn('Deterministic rules, 6-role review', html)
        self.assertIn('Model Critique', html)
        self.assertIn('The sample is synthetic.', html)
        self.assertIn('Inspect the council evidence ledger', html)
        self.assertIn('Research only', html)
        self.assertIn('Dissent and qualifications', html)

    def test_comparisons_use_percentage_points_and_recorded_costs(self):
        data = example()
        data['backtest']['metrics']['total_transaction_cost'] = 1.1
        data['benchmark'] = {'name': 'Matched equal weight', 'total_return_difference': .0123,
                             'metrics': {'total_return': -.0023, 'max_drawdown': .02}}
        data['cost_sensitivity'] = {'base_bps': 10, 'comparison_bps': 20,
                                    'metrics': {'total_return': .008}, 'meaning': 'One scenario.'}
        html = generate_report(data)
        self.assertIn('1.23 percentage points', html)
        self.assertIn('Cost scenario: 20 bps', html)
        self.assertIn('This difference is not risk-adjusted alpha', html)

    def test_provenance_preserved(self):
        html = generate_report(example())
        self.assertIn('a' * 64, html)
        self.assertIn('b' * 64, html)
        self.assertIn('council_policy', html)
        self.assertIn('No final liquidation.', html)

    def test_chart_accessibility(self):
        html = generate_report(example())
        self.assertIn('lang="en"', html)
        self.assertIn('Skip to research report', html)
        self.assertEqual(html.count('role="img"'), 2)
        self.assertEqual(html.count('<title id='), 2)
        self.assertEqual(html.count('<desc id='), 2)
        self.assertIn('scope="col"', html)
        self.assertIn('@media(max-width:450px)', html)
        self.assertIn('@media print', html)

    def test_text_limits_and_no_currency_assumption(self):
        data = example()
        data['metadata']['title'] = 'x' * 100000
        html = generate_report(data)
        self.assertIn('[truncated]', html)
        self.assertLess(len(html), 50000)
        self.assertNotIn('USD', html)
        self.assertNotIn('$1,010', html)

    def test_determinism_and_alias(self):
        data = example()
        self.assertEqual(generate_report(data), generate_report(data))
        self.assertEqual(generate_report(data), render_report(data))
        with self.assertRaises(TypeError):
            generate_report(None)


if __name__ == '__main__':
    unittest.main()
