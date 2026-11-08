"""Hand-calculated Bayesian identities and temporal separation checks."""
import json
from itertools import product
import math
import unittest

import numpy as np

from atlas_quant.beliefs import gaussian_regime_filter, online_gaussian_experts


class BeliefTests(unittest.TestCase):
    def test_one_step_bayes_matches_independent_density_calculation(self):
        observed, means, stds, prior = [.02], [0, .03], [.01, .02], [.75, .25]
        result = online_gaussian_experts(observed, means, stds, prior)
        densities = [math.exp(-.5 * ((observed[0] - mu) / sigma) ** 2)
                     / (sigma * math.sqrt(2 * math.pi)) for mu, sigma in zip(means, stds)]
        normaliser = sum(p * d for p, d in zip(prior, densities))
        expected = [p * d / normaliser for p, d in zip(prior, densities)]
        np.testing.assert_allclose(result["posterior_probabilities"][0], expected, rtol=1e-14)
        self.assertEqual(result["prior_probabilities"][0], prior)
        self.assertAlmostEqual(result["log_predictive_density"][0], math.log(normaliser), places=12)

    def test_hmm_transition_occurs_after_first_observation(self):
        transition = [[.8, .2], [.1, .9]]
        result = gaussian_regime_filter([0, 0], [-.01, .01], [.02, .02], transition, [.25, .75])
        # Equal likelihoods at zero leave the first prior unchanged.
        np.testing.assert_allclose(result["posterior_probabilities"][0], [.25, .75])
        np.testing.assert_allclose(result["prior_probabilities"][1], [.275, .725])
        np.testing.assert_allclose(result["next_probabilities"], [.2925, .7075])

    def test_hmm_evidence_matches_enumeration_of_every_hidden_path(self):
        observations, means, stds = [.001, -.01, .02], [0, -.01], [.01, .03]
        prior, transition = [.7, .3], [[.95, .05], [.2, .8]]
        result = gaussian_regime_filter(observations, means, stds, transition, prior)
        path_mass_by_final_state = [0.0, 0.0]
        for path in product(range(2), repeat=3):
            mass = prior[path[0]]
            for t, state in enumerate(path):
                mass *= math.exp(-.5 * ((observations[t] - means[state]) / stds[state]) ** 2)
                mass /= stds[state] * math.sqrt(2 * math.pi)
                if t:
                    mass *= transition[path[t - 1]][state]
            path_mass_by_final_state[path[-1]] += mass
        evidence = sum(path_mass_by_final_state)
        self.assertAlmostEqual(result["cumulative_log_evidence"], math.log(evidence), places=12)
        np.testing.assert_allclose(result["posterior_probabilities"][-1],
                                   np.array(path_mass_by_final_state) / evidence, rtol=1e-13)

    def test_predictive_total_variance_has_between_mean_term(self):
        result = online_gaussian_experts([.05], [-.1, .1], [.02, .03], [.25, .75])
        self.assertAlmostEqual(result["predictive_mean"][0], .05)
        within = .25 * .02 ** 2 + .75 * .03 ** 2
        between = .25 * (-.1 - .05) ** 2 + .75 * (.1 - .05) ** 2
        self.assertAlmostEqual(result["aleatoric_variance"][0], within)
        self.assertAlmostEqual(result["disagreement_variance"][0], between)
        self.assertAlmostEqual(result["predictive_variance"][0], within + between)

    def test_future_observations_cannot_change_past_predictions(self):
        original, altered = [.001, -.01, .003, .012], [.001, -.01, -.5, .9]
        for function in (online_gaussian_experts, gaussian_regime_filter):
            args = dict(means=[0, -.01], stds=[.01, .04], prior=[.7, .3])
            if function is gaussian_regime_filter:
                args["transition"] = [[.95, .05], [.1, .9]]
            first, second = function(original, **args), function(altered, **args)
            # The forecast for the altered third observation is still identical.
            for key in ("prior_probabilities", "predictive_mean", "predictive_variance"):
                self.assertEqual(first[key][:3], second[key][:3])
            self.assertEqual(first["posterior_probabilities"][:2], second["posterior_probabilities"][:2])

    def test_log_space_preserves_recoverable_tiny_expert_weight(self):
        # The first datum makes one displayed posterior underflow to zero;
        # symmetric contrary evidence must still restore equal model weights.
        result = online_gaussian_experts([0, 1], [0, 1], [.01, .01], [.5, .5])
        self.assertEqual(result["posterior_probabilities"][0][1], 0)
        np.testing.assert_allclose(result["posterior_probabilities"][1], [.5, .5], atol=1e-12)
        self.assertTrue(math.isfinite(result["cumulative_log_evidence"]))

    def test_zero_prior_and_absorbing_transition_remain_zero(self):
        result = gaussian_regime_filter([0, .1, -.1], [0, .1], [.1, .1], [[1, 0], [0, 1]], [1, 0])
        self.assertEqual(result["next_probabilities"], [1, 0])
        self.assertEqual(result["posterior_probabilities"], [[1, 0]] * 3)

    def test_all_probabilities_normalise_and_outputs_are_strict_json(self):
        result = gaussian_regime_filter([.01, -.02, .03], [0, -.01], [.01, .04], [[.9, .1], [.2, .8]], [.6, .4])
        for key in ("prior_probabilities", "posterior_probabilities"):
            for row in result[key]:
                self.assertAlmostEqual(sum(row), 1)
                self.assertTrue(all(0 <= p <= 1 for p in row))
        self.assertAlmostEqual(sum(result["log_predictive_density"]), result["cumulative_log_evidence"])
        json.dumps(result, allow_nan=False)

    def test_invalid_parameters_fail_without_fabricated_results(self):
        valid = dict(returns=[0, .01], means=[0, -.01], stds=[.01, .04], prior=[.6, .4])
        cases = {"returns": ([], [math.nan], ["0.1"], [[0, 1]]),
                 "means": ([0], [0, math.inf]),
                 "stds": ([0, .01], [-.01, .01], [1e-300, .01]),
                 "prior": ([.5, .4], [-.1, 1.1], [True, False])}
        for name, values in cases.items():
            for value in values:
                with self.subTest(field=name, value=value), self.assertRaises(ValueError):
                    online_gaussian_experts(**dict(valid, **{name: value}))
        for matrix in ([[1, 0]], [[.5, .4], [.2, .8]], [[1, 0], [math.nan, 1]]):
            with self.subTest(matrix=matrix), self.assertRaises(ValueError):
                gaussian_regime_filter(**valid, transition=matrix)

    def test_bounded_shape_and_numerical_range(self):
        with self.assertRaises(ValueError):
            online_gaussian_experts([0], [0] * 33, [.01] * 33, [1 / 33] * 33)
        with self.assertRaises(ValueError):
            online_gaussian_experts([0] * 100001, [0], [.01], [1])
        with self.assertRaises(ValueError):
            online_gaussian_experts([1e308], [0], [.01], [1])

    def test_single_expert_and_identical_experts_have_no_disagreement(self):
        single = online_gaussian_experts([0, .01], [.005], [.02], [1])
        self.assertEqual(single["prior_probabilities"], [[1], [1]])
        self.assertEqual(single["predictive_variance"], [.0004, .0004])
        self.assertEqual(single["disagreement_variance"], [0, 0])
        identical = online_gaussian_experts([0, .01], [.005, .005], [.02, .02], [.3, .7])
        np.testing.assert_allclose(identical["next_probabilities"], [.3, .7])


if __name__ == "__main__":
    unittest.main()
