"""Independent identities, published benchmarks and adversarial domains."""
import json
import math
import unittest
from unittest.mock import patch

import numpy as np

from atlas_quant.quant import (simple_returns, drawdown, performance_metrics,
                               historical_risk, minimum_variance, black_scholes,
                               option_greeks, binomial_price, monte_carlo_price)


class ReturnTests(unittest.TestCase):
    def test_adjacent_ratios_and_matrix_axis(self):
        np.testing.assert_allclose(simple_returns([100, 110, 99]), [.1, -.1])
        np.testing.assert_allclose(simple_returns([[100, 20], [110, 10]]), [[.1, -.5]])

    def test_reject_prices(self):
        for bad in ([], [1], [1, 0], [1, -1], [1, float('nan')], [[1, 2], [3]], [[[]]]):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                simple_returns(bad)

    def test_no_numeric_coercion(self):
        for bad in ([True, False], ["1", "2"], np.array([1+2j, 2+3j])):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                simple_returns(bad)

    def test_initial_loss_is_drawdown(self):
        np.testing.assert_allclose(drawdown([-.2, .25, -.1]), [0, -.2, 0, -.1], atol=1e-14)

    def test_bankruptcy_stays_zero(self):
        np.testing.assert_allclose(drawdown([-.2, -1, 10]), [0, -.2, -1, -1])
        result = performance_metrics([-.2, -1, .1])
        self.assertEqual(result['annualised_return'], -1)
        self.assertEqual(result['max_drawdown'], 1)

    def test_impossible_simple_returns_rejected(self):
        for function in (drawdown, performance_metrics, historical_risk):
            with self.assertRaises(ValueError):
                function([-.1, -1.01])

    def test_metrics_geometric_compounding(self):
        result = performance_metrics([.1, -.1], periods_per_year=2)
        self.assertAlmostEqual(result['total_return'], -.01)
        self.assertAlmostEqual(result['annualised_return'], -.01)
        self.assertAlmostEqual(result['annualised_volatility'], .2)
        self.assertAlmostEqual(result['max_drawdown'], .1)
        self.assertAlmostEqual(result['sharpe_ratio'], 0)

    def test_risk_free_effective_rate_conversion(self):
        result = performance_metrics([.01, .03], periods_per_year=2, risk_free_rate=.0404)
        self.assertAlmostEqual(result['sharpe_ratio'], 0, places=12)

    def test_undefined_statistics_serialise(self):
        for values in ([0, 0], [.1, .1, .1], [.1]):
            result = performance_metrics(values)
            self.assertIsNone(result['sharpe_ratio'])
            json.dumps(result, allow_nan=False)

    def test_invalid_scalar_parameters(self):
        for kw in ({'periods_per_year': 0}, {'periods_per_year': True},
                   {'risk_free_rate': -1}, {'risk_free_rate': float('inf')}):
            with self.assertRaises(ValueError):
                performance_metrics([.01, .02], **kw)

    def test_fractional_tail_expected_shortfall(self):
        result = historical_risk([-.1, -.2, -.3, -.4], confidence=.625)
        self.assertAlmostEqual(result['var'], .3)
        self.assertAlmostEqual(result['expected_shortfall'], (.4 + .5 * .3) / 1.5)
        self.assertAlmostEqual(result['tail_observations'], 1.5)

    def test_empirical_tail_ties(self):
        result = historical_risk([-.4, -.4, -.1, .1], confidence=.5)
        self.assertAlmostEqual(result['expected_shortfall'], .4)
        self.assertAlmostEqual(result['var'], .1)

    def test_small_tail_and_all_gains(self):
        result = historical_risk([.1, .2], confidence=.95)
        self.assertAlmostEqual(result['var'], -.1)
        self.assertAlmostEqual(result['expected_shortfall'], -.1)

    def test_tail_average_does_not_overflow(self):
        result = historical_risk([1e308] * 20, confidence=.5)
        self.assertEqual(result['var'], -1e308)
        self.assertEqual(result['expected_shortfall'], -1e308)
        json.dumps(result, allow_nan=False)

    def test_confidence_domains(self):
        for confidence in (0, 1, -.5, float('nan'), True):
            with self.assertRaises(ValueError):
                historical_risk([.1, -.1], confidence)

    def test_extreme_growth_fails_cleanly(self):
        with self.assertRaises(ValueError):
            performance_metrics([1e100, 1e100])


class AllocationTests(unittest.TestCase):
    def test_diagonal_inverse_variance_solution(self):
        np.testing.assert_allclose(minimum_variance(np.diag([1., 4.])), [.8, .2], atol=1e-6)

    def test_small_scale_same_solution(self):
        np.testing.assert_allclose(minimum_variance(np.diag([1e-12, 4e-12])), [.8, .2], atol=1e-6)

    def test_cap_binds(self):
        weights = minimum_variance(np.diag([1., 4.]), .6)
        np.testing.assert_allclose(weights, [.6, .4], atol=1e-6)

    def test_tight_cap_and_zero_covariance(self):
        np.testing.assert_allclose(minimum_variance(np.eye(4), .25), [.25] * 4)
        np.testing.assert_allclose(minimum_variance(np.zeros((2, 2))), [.5, .5])
        np.testing.assert_allclose(minimum_variance([[.1]]), [1.])

    def test_invalid_covariances(self):
        for covariance in ([[1, 2], [2, 1]], [[1, .1], [.2, 1]], [[1, 2, 3]], [[float('nan')]]):
            with self.subTest(covariance=covariance), self.assertRaises(ValueError):
                minimum_variance(covariance)
        with self.assertRaises(ValueError):
            minimum_variance(np.eye(2), .4)

    def test_singular_psd_allowed(self):
        weights = minimum_variance(np.ones((3, 3)))
        self.assertAlmostEqual(weights.sum(), 1)
        self.assertTrue(np.all(weights >= 0))

    def test_solver_failure_is_not_advice(self):
        class Failed:
            x = np.array([.5, .5])
            success = False
        with patch('atlas_quant.quant.minimize', return_value=Failed()):
            with self.assertRaises(ValueError):
                minimum_variance(np.eye(2))


class OptionTests(unittest.TestCase):
    def test_standard_benchmark(self):
        self.assertAlmostEqual(black_scholes(100, 100, 1, .05, .2), 10.450583572185565, places=10)
        self.assertAlmostEqual(black_scholes(100, 100, 1, .05, .2, 'put'), 5.573526022256971, places=10)

    def test_dividend_put_call_parity(self):
        args = (97, 103, 1.7, -.01, .31)
        call = black_scholes(*args, dividend=.035)
        put = black_scholes(*args, option='put', dividend=.035)
        expected = 97 * math.exp(-.035 * 1.7) - 103 * math.exp(.01 * 1.7)
        self.assertAlmostEqual(call - put, expected, places=11)

    def test_expiry_and_zero_volatility(self):
        self.assertEqual(black_scholes(120, 100, 0, .05, .2), 20)
        self.assertEqual(black_scholes(120, 100, 0, .05, .2, 'put'), 0)
        self.assertAlmostEqual(black_scholes(100, 100, 1, .05, 0), 100 - 100 * math.exp(-.05))

    def test_prices_respect_bounds(self):
        for spot in (1, 50, 100, 1000):
            for vol in (.01, .2, 2.):
                call = black_scholes(spot, 100, 2, .03, vol, dividend=.02)
                put = black_scholes(spot, 100, 2, .03, vol, 'put', .02)
                sd, kd = spot * math.exp(-.04), 100 * math.exp(-.06)
                self.assertTrue(max(sd-kd, 0)-1e-10 <= call <= sd+1e-10)
                self.assertTrue(max(kd-sd, 0)-1e-10 <= put <= kd+1e-10)

    def test_greeks_against_finite_difference(self):
        for option in ('call', 'put'):
            s, k, t, r, v, q = 105, 100, 1.3, .03, .27, .02
            g = option_greeks(s, k, t, r, v, option, q)
            price = lambda ss=s, tt=t, rr=r, vv=v: black_scholes(ss, k, tt, rr, vv, option, q)
            eps = 1e-4
            self.assertAlmostEqual(g['delta'], (price(ss=s+eps)-price(ss=s-eps))/(2*eps), places=7)
            self.assertAlmostEqual(g['gamma'], (price(ss=s+.01)-2*price()+price(ss=s-.01))/.0001, places=6)
            self.assertAlmostEqual(g['vega'], (price(vv=v+eps)-price(vv=v-eps))/(2*eps), places=5)
            self.assertAlmostEqual(g['rho'], (price(rr=r+eps)-price(rr=r-eps))/(2*eps), places=5)
            self.assertAlmostEqual(g['theta'], -(price(tt=t+eps)-price(tt=t-eps))/(2*eps), places=6)

    def test_greeks_boundary_rejected(self):
        for maturity, volatility in ((0, .2), (1, 0)):
            with self.assertRaises(ValueError):
                option_greeks(100, 100, maturity, .03, volatility)

    def test_domain_rejections(self):
        for args in ((0, 100, 1, .05, .2), (100, -1, 1, .05, .2),
                     (100, 100, -1, .05, .2), (100, 100, 1, .05, -.2),
                     (True, 100, 1, .05, .2), (100, 100, 1, float('nan'), .2)):
            with self.assertRaises(ValueError):
                black_scholes(*args)
        with self.assertRaises(ValueError):
            black_scholes(100, 100, 1, .05, .2, option='CALL')
        with self.assertRaises(ValueError):
            black_scholes(100, 100, 100, -100, .2)

    def test_tree_converges_to_european(self):
        for option in ('call', 'put'):
            target = black_scholes(100, 100, 1, .05, .2, option, .02)
            tree = binomial_price(100, 100, 1, .05, .2, option, .02, steps=1200)
            self.assertAlmostEqual(tree, target, delta=.002)

    def test_american_put_exercise_premium(self):
        euro = binomial_price(90, 100, 1, .05, .2, 'put')
        american = binomial_price(90, 100, 1, .05, .2, 'put', american=True)
        self.assertGreater(american, euro)
        self.assertGreaterEqual(american, 10)

    def test_non_dividend_call_never_exercises_early(self):
        euro = binomial_price(100, 100, 1, .05, .2)
        american = binomial_price(100, 100, 1, .05, .2, american=True)
        self.assertAlmostEqual(euro, american, places=10)

    def test_tree_deterministic_american(self):
        self.assertAlmostEqual(binomial_price(50, 100, 1, .05, 0, 'put', american=True), 50)
        self.assertEqual(binomial_price(120, 100, 0, .05, .2), 20)

    def test_deterministic_tree_overflow_rejected(self):
        with self.assertRaises(ValueError):
            binomial_price(1e300, 100, 1, 0, 0, dividend=-100, american=True)

    def test_tree_invalid_probability_rejected(self):
        with self.assertRaises(ValueError):
            binomial_price(100, 100, 1, 1, .01, steps=1)
        for steps in (0, 5001, 1.5, True):
            with self.assertRaises(ValueError):
                binomial_price(100, 100, 1, .05, .2, steps=steps)

    def test_seeded_mc_matches_price_and_repeats(self):
        first = monte_carlo_price(100, 100, 1, .05, .2, paths=100000, seed=17)
        second = monte_carlo_price(100, 100, 1, .05, .2, paths=100000, seed=17)
        self.assertEqual(first, second)
        self.assertLess(abs(first['price']-black_scholes(100, 100, 1, .05, .2)), 4*first['standard_error'])
        self.assertEqual(first['independent_pairs'], 50000)

    def test_mc_standard_error_uses_pair_averages(self):
        result = monte_carlo_price(100, 100, 1, .05, .2, paths=1000, seed=7)
        z = np.random.default_rng(7).standard_normal(500)
        positive = np.maximum(100*np.exp(.03+.2*z)-100, 0)
        negative = np.maximum(100*np.exp(.03-.2*z)-100, 0)
        pairs = math.exp(-.05)*(positive+negative)/2
        self.assertAlmostEqual(result['standard_error'], np.std(pairs, ddof=1)/math.sqrt(500), places=12)

    def test_mc_zero_volatility_has_no_sampling_error(self):
        result = monte_carlo_price(100, 100, 1, .05, 0)
        self.assertEqual(result['standard_error'], 0)
        self.assertEqual(result['ci_low'], result['ci_high'])

    def test_mc_extreme_variance_cannot_report_false_zero(self):
        with self.assertRaises(ValueError):
            monte_carlo_price(100, 100, 1, 1e300, 1e300)
        with self.assertRaises(ValueError):
            monte_carlo_price(100, 100, 1, 0, 1e-300)

    def test_mc_invalid_work_or_seed(self):
        for kwargs in ({'paths': 3}, {'paths': 7}, {'paths': 1000002},
                       {'paths': True}, {'seed': -1}, {'seed': True}, {'confidence': 1}):
            with self.assertRaises(ValueError):
                monte_carlo_price(100, 100, 1, .05, .2, **kwargs)


if __name__ == '__main__':
    unittest.main()
