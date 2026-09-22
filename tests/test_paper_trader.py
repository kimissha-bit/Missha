import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "src"))
from paper_trader import PriceBar, TradingConfig, crossover_signal, run_backtest


class PaperTraderTests(unittest.TestCase):
    def test_needs_enough_history(self):
        config = TradingConfig(short_window=2, long_window=3)
        self.assertIsNone(crossover_signal([100, 101, 102], config))

    def test_buy_signal_on_upward_cross(self):
        config = TradingConfig(short_window=2, long_window=3)
        self.assertEqual(crossover_signal([10, 9, 8, 9, 11], config), "BUY")

    def test_backtest_never_exceeds_position_limit(self):
        config = TradingConfig(initial_cash=1_000, max_position_value=100, short_window=2, long_window=3)
        prices = [PriceBar(str(index), close) for index, close in enumerate([10, 9, 8, 9, 11, 12])]
        broker = run_backtest(prices, config)
        self.assertLessEqual(broker.shares * 12, 100)


if __name__ == "__main__":
    unittest.main()
