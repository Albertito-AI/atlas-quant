"""The lab CLI preserves evidence and its renderer keeps untrusted text inert."""
import contextlib
import copy
import io
import json
import math
from pathlib import Path
import tempfile
import unittest

from atlas_quant.agent_lab import build_agent_lab, verify_agent_lab
from atlas_quant.cli import main
from atlas_quant.lab_report import generate_lab_report


class LabReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = build_agent_lab(observations=30, scenario_count=80)

    def test_cli_writes_verifiable_evidence_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.redirect_stdout(io.StringIO()):
            output = Path(directory) / 'lab'
            args = ['agent-lab', '--observations', '30', '--scenario-count', '80', '--output', str(output)]
            self.assertEqual(main(args), 0)
            record = json.loads((output / 'lab.json').read_text(encoding='utf-8'))
            self.assertTrue(verify_agent_lab(record))
            self.assertTrue(record['metadata']['synthetic'])
            html = (output / 'report.html').read_text(encoding='utf-8')
            self.assertIn('id="regime-title"', html)
            self.assertIn('id="experts-title"', html)
            self.assertIn('id="scenario-title"', html)
            before = (output / 'lab.json').read_bytes()
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(args), 2)
            self.assertEqual((output / 'lab.json').read_bytes(), before)

    def test_script_free_escaped_output_has_explicit_scope(self):
        record = copy.deepcopy(self.record)
        hostile = '<script>alert("x")</script><img src="https://example.test/">'
        record['trace'][0]['role'] = hostile
        record['data']['symbols'][0] = hostile
        html = generate_lab_report(record)
        self.assertNotIn('<script>', html)
        self.assertNotIn('<img ', html)
        self.assertIn('&lt;script&gt;', html)
        self.assertIn("script-src 'none'", html)
        self.assertIn("style-src 'sha256-", html)
        self.assertIn('SYNTHETIC DATA', html)
        self.assertIn('does not deploy language-model agents or AGI', html)
        self.assertIn('Held-out expected shortfall', html)
        self.assertIn('shared model', html.lower())

    def test_invalid_probabilities_and_missing_scenarios_are_not_plotted(self):
        record = copy.deepcopy(self.record)
        record['beliefs']['posterior_probabilities'][0] = [.6, .6]
        record['experts']['prior_probabilities'][0][0] = math.nan
        record['scenario_sets']['regime_mixture'][0][0] = math.inf
        html = generate_lab_report(record)
        for marker in ('regime-title', 'experts-title', 'scenario-title'):
            self.assertNotIn(f'id="{marker}"', html)
        self.assertEqual(html.count('Complete, finite numerical evidence is unavailable'), 3)
        self.assertNotIn('nan,', html)

    def test_incomplete_record_never_acquires_a_research_outcome(self):
        html = generate_lab_report({})
        self.assertIn('Recorded outcome: Unavailable', html)
        self.assertNotIn('Outcome: research_only', html)

    def test_gate_relations_and_heldout_losses_remain_explicit(self):
        html = generate_lab_report(self.record)
        self.assertIn('&gt;=', html)
        self.assertIn('&lt;=', html)
        self.assertIn('Maximum of fitted and separately drawn held-out', html)
        self.assertIn('separate random stream', html)
        self.assertIn('blocked_for_review', html)


if __name__ == '__main__':
    unittest.main()
