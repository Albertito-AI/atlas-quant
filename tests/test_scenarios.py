"""Independent small convex problems and fail-closed scenario checks."""
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

from atlas_quant.scenarios import robust_cvar_allocation, scenario_cvar


class ScenarioTests(unittest.TestCase):
    def test_single_asset_fractional_tail_matches_hand_calculation(self):
        scenarios = {"example": [[-.10], [-.04], [-.01], [.02]]}
        risk = scenario_cvar(scenarios, [1.0], confidence=.625)
        self.assertAlmostEqual(risk["per_scenario_var"]["example"], .04)
        self.assertAlmostEqual(risk["worst_cvar"], (.10 + .5 * .04) / 1.5)
        solved = robust_cvar_allocation(scenarios, confidence=.625)
        self.assertAlmostEqual(solved["objective"], .08)
        self.assertAlmostEqual(solved["worst_cvar"], .08)

    def test_minimax_intersection_has_analytic_solution(self):
        # Losses are .4w-.1 and .1-.2w; their intersection is w=1/3,
        # worst loss=1/30. Neither scenario gets a probability weight.
        scenarios = {"a": [[-.3, .1]], "b": [[.1, -.1]]}
        solved = robust_cvar_allocation(scenarios)
        np.testing.assert_allclose(solved["weights"], [1 / 3, 2 / 3], rtol=0, atol=1e-10)
        self.assertAlmostEqual(solved["objective"], 1 / 30)
        self.assertAlmostEqual(solved["worst_cvar"], 1 / 30)
        self.assertEqual(solved["solver_status"], "optimal")
        json.dumps(solved, allow_nan=False)

    def test_cap_binds_without_inventing_return_target(self):
        solved = robust_cvar_allocation({"loss": [[-.01, -.1]]}, max_weight=.6)
        np.testing.assert_allclose(solved["weights"], [.6, .4], atol=1e-10)
        self.assertAlmostEqual(solved["worst_cvar"], .6 * .01 + .4 * .1)

    def test_negative_risk_is_preserved(self):
        solved = robust_cvar_allocation({"gains": [[.04, .02], [.05, .03]]}, confidence=.5)
        np.testing.assert_allclose(solved["weights"], [1, 0], atol=1e-10)
        self.assertAlmostEqual(solved["objective"], -.04)
        self.assertAlmostEqual(solved["worst_cvar"], -.04)

    def test_extreme_confidence_is_empirical_maximum(self):
        solved = robust_cvar_allocation({"tiny_tail": [[-.1], [.2]]}, confidence=1 - 1e-15)
        self.assertAlmostEqual(solved["worst_cvar"], .1)
        self.assertAlmostEqual(solved["objective"], .1)

    def test_zero_returns_and_complete_loss_are_supported(self):
        zero = robust_cvar_allocation({"zero": np.zeros((3, 2))}, max_weight=.5)
        self.assertEqual(zero["weights"], [.5, .5])
        self.assertEqual(zero["worst_cvar"], 0)
        loss = robust_cvar_allocation({"loss": [[-1, -1]]}, max_weight=.5)
        self.assertAlmostEqual(loss["worst_cvar"], 1)

    def test_scenario_order_and_replication_leave_solution_unchanged(self):
        a, b = [[-.3, .1]], [[.1, -.1]]
        first = robust_cvar_allocation({"a": a, "b": b})
        second = robust_cvar_allocation({"b": b * 4, "a": a * 7})
        np.testing.assert_allclose(first["weights"], second["weights"], atol=1e-10)
        self.assertAlmostEqual(first["worst_cvar"], second["worst_cvar"])

    def test_multiple_asset_distribution_agrees_with_brute_force_grid(self):
        scenarios = {"calm": [[-.01, -.02], [.03, .01], [-.02, .03], [.01, .02]],
                     "stress": [[-.06, .02], [.01, -.04], [-.03, .01]]}
        solved = robust_cvar_allocation(scenarios, confidence=.6, max_weight=.8)
        # A dense independent enumeration bounds the convex LP optimum from above.
        worst = []
        for w in np.linspace(.2, .8, 1201):
            candidates = []
            for observations in scenarios.values():
                losses = sorted((-r[0] * w - r[1] * (1 - w) for r in observations), reverse=True)
                mass = len(losses) * .4
                whole = int(mass)
                candidates.append((sum(losses[:whole]) + (mass - whole) * losses[whole]) / mass)
            worst.append(max(candidates))
        self.assertLessEqual(solved["worst_cvar"], min(worst) + 1e-10)
        self.assertLess(min(worst) - solved["worst_cvar"], .00005)

    def test_invalid_evidence_and_constraints_are_rejected(self):
        for scenarios in ({}, {"": [[.1]]}, {"x": []}, {"x": [.1]},
                          {"x": [[True]]}, {"x": [[".1"]]}, {"x": [[complex(1)]]},
                          {"x": [[np.nan]]}, {"x": [[np.inf]]}, {"x": [[-1.01]]},
                          {"x": [[1e7]]}, {"x": [[.1]], "y": [[.1, .2]]},
                          {"x": np.zeros((20001, 1))}):
            with self.subTest(scenarios=str(scenarios)[:80]):
                with self.assertRaises(ValueError):
                    robust_cvar_allocation(scenarios)
        for confidence in (True, 0, 1, -.1, np.nan, "0.95"):
            with self.subTest(confidence=confidence), self.assertRaises(ValueError):
                robust_cvar_allocation({"x": [[.1, .2]]}, confidence=confidence)
        for cap in (True, 0, .49, 1.1, np.inf, "0.5"):
            with self.subTest(cap=cap), self.assertRaises(ValueError):
                robust_cvar_allocation({"x": [[.1, .2]]}, max_weight=cap)
        for weights in ([.4, .4], [-.1, 1.1], [np.nan, 1], [.2], [True, False]):
            with self.subTest(weights=weights), self.assertRaises(ValueError):
                scenario_cvar({"x": [[.1, .2]]}, weights)

    def test_solver_failure_never_becomes_equal_weights(self):
        failed = SimpleNamespace(success=False, status=2, x=None, fun=None)
        with patch("atlas_quant.scenarios.linprog", return_value=failed):
            with self.assertRaisesRegex(ValueError, "optimal solution"):
                robust_cvar_allocation({"x": [[.1, .2]]})

    def test_false_solver_success_is_independently_rejected(self):
        # Two weights, t, eta, one slack. The claimed objective ignores the loss.
        false = SimpleNamespace(success=True, status=0, x=np.array([.5, .5, 0, 0, 0]), fun=0)
        with patch("atlas_quant.scenarios.linprog", return_value=false):
            with self.assertRaisesRegex(ValueError, "feasibility"):
                robust_cvar_allocation({"x": [[-.1, -.2]]})

    def test_scaled_solver_tolerance_cannot_hide_material_tail_loss(self):
        # A huge gain scales the 0.001 loss to 1e-9. The objective must still
        # reconcile in original fractional-return units, not only scaled units.
        false = SimpleNamespace(success=True, status=0, x=np.array([1, 0, 0, 0, 0]), fun=0)
        with patch("atlas_quant.scenarios.linprog", return_value=false):
            with self.assertRaisesRegex(ValueError, "tail risk"):
                robust_cvar_allocation({"ill_conditioned": [[1e6], [-.001]]}, confidence=.5)


if __name__ == "__main__":
    unittest.main()
