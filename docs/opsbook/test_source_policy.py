"""Adversarial policy-gate tests; these never acquire external data."""
import copy
from datetime import date
import json
from pathlib import Path
import unittest

from verify_source_policy import check_plan


class SourcePolicyTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads((Path(__file__).parent / 'pilot-plan.json').read_text())
        self.today = date(2026, 11, 13)

    def test_reviewed_noncommercial_plan(self):
        self.assertTrue(check_plan(self.plan, today=self.today)['pass'])

    def test_each_unresolved_live_source_is_refused(self):
        for source in ('binance_live', 'kraken_live', 'coinbase_live'):
            with self.subTest(source=source):
                self.plan['sources'] = [source]
                with self.assertRaises(ValueError):
                    check_plan(self.plan, today=self.today)

    def test_commercial_vision_use_is_refused(self):
        self.plan['use'] = 'commercial_use'
        with self.assertRaises(ValueError):
            check_plan(self.plan, today=self.today)

    def test_known_open_source_can_be_separately_scoped(self):
        self.plan['sources'] = ['nea_pm25']
        self.plan['use'] = 'commercial_use'
        self.assertTrue(check_plan(self.plan, today=self.today)['pass'])

    def test_unknown_source_or_purpose_is_refused(self):
        for key, value in [('sources', ['not_reviewed']), ('use', 'unbounded-ai-training')]:
            with self.subTest(field=key):
                proposal = copy.deepcopy(self.plan)
                proposal[key] = value
                with self.assertRaises(ValueError):
                    check_plan(proposal, today=self.today)

    def test_review_expiry_and_future_review_fail(self):
        for today in (date(2026, 12, 13), date(2026, 11, 12)):
            with self.subTest(today=today):
                with self.assertRaises(ValueError):
                    check_plan(self.plan, today=today)

    def test_no_silent_extension_of_review_window(self):
        self.plan['review_due'] = '2027-12-13'
        with self.assertRaises(ValueError):
            check_plan(self.plan, today=self.today)

    def test_conditions_acknowledgement_and_nonempty_plan(self):
        for key, value in [('acknowledge_conditions', False), ('sources', []), ('sources', ['nea_pm25', 'nea_pm25'])]:
            with self.subTest(field=key, value=value):
                proposal = copy.deepcopy(self.plan)
                proposal[key] = value
                with self.assertRaises(ValueError):
                    check_plan(proposal, today=self.today)


if __name__ == '__main__':
    unittest.main()
