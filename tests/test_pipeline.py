import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest

from atlas_quant.cli import main
from atlas_quant.data import synthetic_prices
from atlas_quant.pipeline import analyse, load_analysis, option_comparison, verify_analysis
from atlas_quant.research import content_sha256


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = synthetic_prices(days=90, assets=3, seed=17)
        cls.report = analyse(cls.data, lookback=20, seed=17)

    def test_full_pipeline_is_reproducible(self):
        self.assertEqual(self.report, analyse(self.data, lookback=20, seed=17))
        self.assertTrue(verify_analysis(self.report))
        json.dumps(self.report, allow_nan=False)

    def test_baseline_has_identical_calendar(self):
        report = self.report
        self.assertEqual(report['backtest']['dates'], report['benchmark']['dates'])
        self.assertEqual(len(report['backtest']['equity_curve']), len(report['benchmark']['equity_curve']))

    def test_equal_weight_matches_own_baseline(self):
        report = analyse(self.data, lookback=20, strategy='equal_weight')
        self.assertEqual(report['benchmark']['total_return_difference'], 0)

    def test_cost_sensitivity_changes_measured_result(self):
        self.assertLess(self.report['cost_sensitivity']['metrics']['total_return'],
                        self.report['backtest']['metrics']['total_return'])

    def test_tamper_and_source_mismatch_detected(self):
        changed = copy.deepcopy(self.report)
        changed['backtest']['metrics']['total_return'] = 99
        self.assertFalse(verify_analysis(changed))
        changed = copy.deepcopy(self.report)
        changed['metadata']['dataset_sha256'] = '0' * 64
        changed.pop('integrity_sha256')
        changed['integrity_sha256'] = content_sha256(changed)
        self.assertFalse(verify_analysis(changed))

    def test_cli_demo_bundle_and_verify(self):
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()):
            output = Path(temp) / 'demo'
            self.assertEqual(main(['demo','--days','90','--lookback','20','--output',str(output)]), 0)
            self.assertTrue((output / 'report.html').is_file())
            report = load_analysis(output / 'report.json')
            self.assertTrue(report['metadata']['synthetic'])
            self.assertEqual(main(['verify',str(output/'report.json')]), 0)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(['demo','--output',str(output)]), 2)

    def test_cli_csv_real_input_flag(self):
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()):
            source = Path(temp) / 'prices.csv'
            lines = ['date,ALPHA,BETA']
            lines += [f'2026-01-{i:02d},{100+i},{100+i/2}' for i in range(1,25)]
            source.write_text('\n'.join(lines),encoding='utf-8')
            output = Path(temp) / 'report'
            self.assertEqual(main(['backtest',str(source),'--lookback','5','--output',str(output)]),0)
            self.assertFalse(load_analysis(output/'report.json')['metadata']['synthetic'])

    def test_cli_external_review_end_to_end(self):
        with tempfile.TemporaryDirectory() as temp, contextlib.redirect_stdout(io.StringIO()) as out:
            report_path = Path(temp) / 'report.json'
            review_path = Path(temp) / 'review.json'
            report_path.write_text(json.dumps(self.report))
            review = {'schema_version':'1.0','role':'data_quality',
                      'report_sha256':self.report['council']['report_sha256'],
                      'findings':[{'code':'inspect_sample','evidence_ids':['observations']}]}
            review_path.write_text(json.dumps(review))
            self.assertEqual(main(['review',str(report_path),str(review_path),'--role','data_quality']),0)
            self.assertIn('inspect_sample',out.getvalue())
            review['arbitrary_command'] = 'do something untrusted'
            review_path.write_text(json.dumps(review))
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(['review',str(report_path),str(review_path),'--role','data_quality']),2)

    def test_cli_errors_are_actionable(self):
        with contextlib.redirect_stderr(io.StringIO()) as err:
            self.assertEqual(main(['options','--volatility','-1']),2)
        self.assertIn('atlas-quant:',err.getvalue())

    def test_option_boundary_prices_remain_available(self):
        for kwargs in ({'maturity':0},{'volatility':0}):
            result = option_comparison(**kwargs)
            self.assertIn('status',result['greeks'])
            self.assertGreaterEqual(result['black_scholes'],0)

    def test_low_volatility_tree_limitation_does_not_hide_other_methods(self):
        result = option_comparison(volatility=.001)
        self.assertIsNone(result['binomial'])
        self.assertIn('Unavailable',result['binomial_status'])
        self.assertGreater(result['black_scholes'],0)

    def test_rehashed_incomplete_and_inconsistent_envelopes_fail(self):
        for key in ('options','benchmark','cost_sensitivity'):
            report = copy.deepcopy(self.report)
            report.pop(key)
            report.pop('integrity_sha256')
            report['integrity_sha256'] = content_sha256(report)
            self.assertFalse(verify_analysis(report))
        report = copy.deepcopy(self.report)
        report['backtest']['metrics']['total_return'] = .99
        report.pop('integrity_sha256')
        report['integrity_sha256'] = content_sha256(report)
        self.assertFalse(verify_analysis(report))

    def test_json_rejects_duplicate_and_nonfinite(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'bad.json'
            for raw in ('{"x":1,"x":2}', '{"x":NaN}', '[1,2]', '{}'):
                path.write_text(raw)
                with self.assertRaises(ValueError):
                    load_analysis(path)

    def test_invalid_envelopes_fail(self):
        for value in (None, [], {}, {'schema_version':'2.0'}):
            self.assertFalse(verify_analysis(value))


if __name__ == '__main__':
    unittest.main()
