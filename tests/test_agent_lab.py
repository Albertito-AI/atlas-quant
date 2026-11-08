"""Cross-stage evidence, information timing and hard research-gate checks."""
from copy import deepcopy
import math
import unittest
from unittest.mock import patch

import numpy as np

from atlas_quant.agent_lab import build_agent_lab, review_lab_evidence, verify_agent_lab
from atlas_quant.scenarios import robust_cvar_allocation


class AgentLabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lab = build_agent_lab(observations=150, scenario_count=80)

    def test_digest_detects_changes(self):
        self.assertTrue(verify_agent_lab(self.lab))
        changed = deepcopy(self.lab)
        changed['governance']['outcome'] = 'invented approval'
        self.assertFalse(verify_agent_lab(changed))
        self.assertFalse(verify_agent_lab(None))

    def test_history_prefix_unchanged_when_run_extended(self):
        short = build_agent_lab(observations=149, scenario_count=80)
        self.assertEqual(short['data']['log_returns'], self.lab['data']['log_returns'][:149])
        for component in ('beliefs', 'experts'):
            for name in ('prior_probabilities', 'predictive_mean', 'posterior_probabilities'):
                self.assertEqual(short[component][name], self.lab[component][name][:149])

    def test_model_variance_and_input_units(self):
        r = self.lab
        data = np.array(r['data']['log_returns'])
        np.testing.assert_allclose(data.mean(axis=1), r['data']['observed_index_log_returns'])
        for source in ('beliefs', 'experts'):
            b = r[source]
            np.testing.assert_allclose(np.array(b['aleatoric_variance']) + b['disagreement_variance'],
                                       b['predictive_variance'], rtol=1e-13)
        for arrays in (r['scenario_sets'], r['heldout_scenario_sets']):
            self.assertTrue(all(np.isfinite(v).all() and (np.array(v) > -1).all() for v in arrays.values()))

    def test_heldout_draws_are_not_used_by_optimiser(self):
        inputs = []
        def record(scenarios, **kwargs):
            inputs.append({k: np.array(v) for k, v in scenarios.items()})
            return robust_cvar_allocation(scenarios, **kwargs)
        with patch('atlas_quant.agent_lab.robust_cvar_allocation', side_effect=record):
            r = build_agent_lab(observations=20, scenario_count=50)
        self.assertEqual(len(inputs), 2)
        for supplied in inputs:
            for name, values in supplied.items():
                np.testing.assert_array_equal(values, r['scenario_sets'][name])
                self.assertFalse(np.array_equal(values, r['heldout_scenario_sets'][name]))

    def test_tail_gate_uses_more_conservative_fit_or_validation(self):
        r = self.lab
        expected = max(r['allocations']['robust']['evaluation']['worst_cvar'],
                       r['allocations']['robust']['heldout_evaluation']['worst_cvar'])
        check = next(c for c in r['governance']['checks'] if c['name'] == 'Worst scenario CVaR')
        self.assertEqual(check['value'], expected)
        self.assertEqual(r['governance']['outcome'], 'blocked_for_review')

    def test_missing_invalid_or_concentrated_beliefs_do_not_override_risk(self):
        for risk in (None, math.nan, math.inf, True, .020001):
            with self.subTest(risk=risk):
                self.assertEqual(review_lab_evidence(risk, [.99, .01], 200, 600)['outcome'], 'blocked_for_review')
        for probabilities in (None, [], [.9, .9], [1], [.5, .5], [math.nan, .1], [True, False]):
            with self.subTest(probabilities=probabilities):
                self.assertEqual(review_lab_evidence(.01, probabilities, 200, 600)['outcome'], 'blocked_for_review')
        valid = review_lab_evidence(.02, [.99, .01], 120, 400)
        self.assertEqual(valid['outcome'], 'research_only')
        self.assertTrue(all(c['passed'] for c in valid['checks']))

    def test_trace_references_resolve_to_real_evidence(self):
        self.assertEqual(len(self.lab['trace']), 5)
        for row in self.lab['trace']:
            for ref in row['input_refs'] + row['output_refs']:
                value = self.lab
                for part in ref.split('.'):
                    self.assertIn(part, value)
                    value = value[part]

    def test_bounds_reject_malformed_configuration(self):
        for kwargs in ({'seed': True}, {'seed': -1}, {'observations': 9},
                       {'observations': 2001}, {'scenario_count': 49}, {'scenario_count': 2001}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                build_agent_lab(**kwargs)


if __name__ == '__main__':
    unittest.main()
