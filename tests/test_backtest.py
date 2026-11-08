"""Independent accounting, chronology and portfolio constraint checks."""
import json
import unittest
from datetime import date, timedelta

import numpy as np

from atlas_quant.backtest import run_backtest, strategy_weights
from atlas_quant.data import PriceDataset, synthetic_prices


def fixture(prices):
    values = np.asarray(prices, dtype=float)
    if values.ndim == 1:
        values = values[:, None]
    dates = tuple((date(2024, 1, 1) + timedelta(days=i)).isoformat() for i in range(len(values)))
    return PriceDataset(dates, tuple(f"A{i}" for i in range(values.shape[1])), values, "hand-calculated fixture")


class BacktestTests(unittest.TestCase):
    def test_single_asset_entry_fee_exact(self):
        result = run_backtest(fixture([100, 100, 100, 100, 110]), strategy="equal_weight",
                              lookback=2, rebalance_every=21, initial_cash=1000, transaction_cost_bps=100)
        expected_entry = 1000 / 1.01
        np.testing.assert_allclose(result.equity_curve, [1000, expected_entry, 1.1 * expected_entry])
        self.assertAlmostEqual(result.trades[0]["transaction_cost"], 1000 - expected_entry)
        self.assertEqual(result.trades[0]["decision_date"], "2024-01-03")
        self.assertEqual(result.trades[0]["date"], "2024-01-04")
        self.assertEqual(result.cash_curve[1:], [0, 0])

    def test_signal_cannot_capture_execution_interval_move(self):
        result = run_backtest(fixture([100, 100, 100, 200, 220]), strategy="equal_weight",
                              lookback=2, initial_cash=1000, transaction_cost_bps=0)
        np.testing.assert_allclose(result.equity_curve, [1000, 1000, 1100])

    def test_drifted_weights_drive_turnover(self):
        data = fixture([[100, 100], [100, 100], [100, 100], [100, 100], [200, 100], [200, 100]])
        result = run_backtest(data, strategy="equal_weight", lookback=2, rebalance_every=1,
                              initial_cash=1000, transaction_cost_bps=0)
        trade = result.trades[1]
        self.assertAlmostEqual(trade["pretrade_weights"]["A0"], 2 / 3)
        self.assertAlmostEqual(trade["traded_notional"], 500)
        self.assertAlmostEqual(trade["turnover"], 1 / 3)
        self.assertEqual(result.equity_curve[-1], 1500)

    def test_cost_equation_for_every_rebalance(self):
        result = run_backtest(synthetic_prices(80, 3, 3), lookback=10, rebalance_every=3,
                              transaction_cost_bps=75, initial_cash=12345)
        for trade in result.trades:
            self.assertAlmostEqual(trade["transaction_cost"], 0.0075 * trade["traded_notional"], places=9)
            self.assertAlmostEqual(trade["pretrade_equity"] - trade["posttrade_equity"], trade["transaction_cost"], places=8)
            self.assertAlmostEqual(sum(trade["target_weights"].values()), 1, places=12)
        self.assertTrue(all(cash >= 0 for cash in result.cash_curve))

    def test_future_perturbation_cannot_change_past(self):
        data = synthetic_prices(80, 3, 4)
        changed = data.prices.copy()
        changed[45:] *= np.array([10, 0.1, 3])
        altered = PriceDataset(data.dates, data.symbols, changed, "future perturbation")
        one = run_backtest(data, lookback=10, rebalance_every=4)
        two = run_backtest(altered, lookback=10, rebalance_every=4)
        np.testing.assert_array_equal(one.equity_curve[:35], two.equity_curve[:35])
        left = [t for t in one.trades if t["date"] < data.dates[45]]
        right = [t for t in two.trades if t["date"] < data.dates[45]]
        self.assertEqual(left, right)

    def test_first_weights_use_only_training_window(self):
        data = synthetic_prices(30, 3, 6)
        changed = data.prices.copy()
        changed[11] *= np.array([5, 0.5, 2])
        altered = PriceDataset(data.dates, data.symbols, changed, "execution surprise")
        first = run_backtest(data, lookback=10).trades[0]
        second = run_backtest(altered, lookback=10).trades[0]
        self.assertEqual(first["target_weights"], second["target_weights"])

    def test_all_strategies_caps_and_serialisation(self):
        for strategy in ("equal_weight", "inverse_volatility", "minimum_variance"):
            with self.subTest(strategy=strategy):
                result = run_backtest(synthetic_prices(50, 4), strategy=strategy, lookback=10, max_weight=0.4)
                for trade in result.trades:
                    self.assertLessEqual(max(trade["target_weights"].values()), 0.4 + 1e-8)
                    self.assertGreaterEqual(min(trade["target_weights"].values()), -1e-10)
                payload = result.to_dict()
                json.dumps(payload, allow_nan=False)
                self.assertTrue(payload["dataset"]["synthetic"])
                self.assertEqual(len(payload["dates"]), len(payload["equity_curve"]))
                self.assertEqual(len(payload["net_returns"]), len(payload["dates"]) - 1)

    def test_zero_volatility_and_caps(self):
        history = np.array([[0, .1, .2], [0, -.1, -.2], [0, .1, .2]])
        weights = strategy_weights(history, "inverse_volatility", 0.4)
        np.testing.assert_allclose(weights, [.4, .3, .3])
        for strategy in ("equal_weight", "inverse_volatility", "minimum_variance"):
            weights = strategy_weights(np.zeros((4, 3)), strategy, 1 / 3)
            np.testing.assert_allclose(weights, [1 / 3] * 3)

    def test_validation(self):
        data = synthetic_prices(30, 3)
        bad = ({"lookback": 1}, {"lookback": 28}, {"lookback": True}, {"rebalance_every": 0},
               {"transaction_cost_bps": -1}, {"transaction_cost_bps": float('nan')},
               {"transaction_cost_bps": 1001}, {"initial_cash": 0}, {"max_weight": .2},
               {"max_weight": True}, {"strategy": "all_in"}, {"periods_per_year": 0})
        for kwargs in bad:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                run_backtest(data, **kwargs)

    def test_invalid_strategy_history(self):
        for history in ([.1, .2], [[.1, .2]], [[.1], [float('nan')]], [[.1], [-1]]):
            with self.subTest(history=history), self.assertRaises(ValueError):
                strategy_weights(history, "equal_weight")
        with self.assertRaises(ValueError):
            strategy_weights(np.ones((3, 2)), "unknown")

    def test_rebalance_calendar_and_unliquidated_endpoint(self):
        data = synthetic_prices(30, 2)
        result = run_backtest(data, strategy="equal_weight", lookback=5, rebalance_every=7)
        self.assertEqual([t["decision_date"] for t in result.trades], [data.dates[i] for i in (5, 12, 19, 26)])
        self.assertEqual([t["date"] for t in result.trades], [data.dates[i] for i in (6, 13, 20, 27)])
        self.assertAlmostEqual(sum(result.to_dict()["final_weights"].values()), 1)

    def test_flat_path_fee_only_and_initial_drawdown(self):
        result = run_backtest(fixture([100] * 10), strategy="equal_weight", lookback=2,
                              transaction_cost_bps=100, initial_cash=1000, rebalance_every=1)
        self.assertAlmostEqual(result.equity_curve[-1], 1000 / 1.01)
        self.assertAlmostEqual(result.metrics["total_transaction_cost"], 1000 / 101)
        self.assertAlmostEqual(abs(result.metrics["max_drawdown"]), 1 / 101)

    def test_public_strategy_scalar_types(self):
        for cap in (True, "0.5", complex(.5, 0), float("inf"), np.array([.5])):
            with self.subTest(cap=cap), self.assertRaises(ValueError):
                strategy_weights(np.zeros((3, 2)), "equal_weight", cap)
        for parameter in ("initial_cash", "transaction_cost_bps", "max_weight"):
            with self.subTest(parameter=parameter), self.assertRaises(ValueError):
                run_backtest(synthetic_prices(30, 3), lookback=5, **{parameter: complex(1, 0)})

    def test_seed_cost_cap_stress_grid(self):
        for seed in range(6):
            for strategy in ("equal_weight", "inverse_volatility", "minimum_variance"):
                data = synthetic_prices(45, 4, seed)
                free = run_backtest(data, strategy=strategy, lookback=6, rebalance_every=2,
                                    transaction_cost_bps=0, max_weight=.3)
                costly = run_backtest(data, strategy=strategy, lookback=6, rebalance_every=2,
                                      transaction_cost_bps=100, max_weight=.3)
                with self.subTest(seed=seed, strategy=strategy):
                    self.assertLessEqual(costly.equity_curve[-1], free.equity_curve[-1] + 1e-8)
                    self.assertTrue(np.isfinite(costly.equity_curve).all())
                    self.assertAlmostEqual(costly.metrics["total_cost_fraction"],
                                           sum(t["transaction_cost"] / t["pretrade_equity"] for t in costly.trades))
                    for trade in costly.trades:
                        self.assertAlmostEqual(sum(trade["target_weights"].values()), 1, places=10)
                        self.assertLessEqual(max(trade["target_weights"].values()), .3 + 1e-8)
                    json.dumps(costly.to_dict(), allow_nan=False)

    def test_single_asset_all_strategies(self):
        data = synthetic_prices(20, 1)
        for strategy in ("equal_weight", "inverse_volatility", "minimum_variance"):
            result = run_backtest(data, strategy=strategy, lookback=5)
            self.assertAlmostEqual(result.weights_history[-1][0], 1)
            json.dumps(result.to_dict(), allow_nan=False)

    def test_extreme_price_ratio_rejected(self):
        data = fixture([1e-300, 1e-300, 1e-300, 1e300, 1e300])
        with self.assertRaisesRegex(ValueError, "price ratios"):
            run_backtest(data, lookback=2)


if __name__ == "__main__":
    unittest.main()
