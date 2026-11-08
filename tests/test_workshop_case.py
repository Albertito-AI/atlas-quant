"""End-to-end evidence for the standalone educational example."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

from atlas_quant.pipeline import load_analysis

spec = importlib.util.spec_from_file_location('workshop_case', Path(__file__).resolve().parents[1] / 'examples' / 'workshop_case.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class WorkshopCaseTests(unittest.TestCase):
    def test_three_cases_are_synthetic_consistent_and_cost_sensitive(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'workshop'
            summary = module.build_case(root)
            self.assertTrue(summary['synthetic'])
            self.assertEqual([case['cost_bps'] for case in summary['cases']], [0, 10, 50])
            self.assertGreater(summary['cases'][0]['final_equity'], summary['cases'][1]['final_equity'])
            self.assertGreater(summary['cases'][1]['final_equity'], summary['cases'][2]['final_equity'])
            self.assertEqual(json.loads((root / 'summary.json').read_text()), summary)
            for case in summary['cases']:
                cost = case['cost_bps']
                report = load_analysis(root / f'cost-{cost}bps.json')
                self.assertTrue(report['metadata']['synthetic'])
                self.assertEqual(report['metadata']['dataset_sha256'], summary['dataset_sha256'])
                self.assertEqual(report['backtest']['config']['transaction_cost_bps'], cost)
                self.assertIn('SYNTHETIC DATA', (root / f'cost-{cost}bps.html').read_text())
            with self.assertRaises(FileExistsError):
                module.build_case(root)
