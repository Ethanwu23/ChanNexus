import unittest

import pandas as pd

from chanlun_core import ChanConfig, ChanEngine
from chanlun_core.risk import RiskPolicy


def frame(highs, lows=None):
    lows = lows or [value - 2 for value in highs]
    return pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=len(highs), freq="D"),
            "open": [(high + low) / 2 for high, low in zip(highs, lows)],
            "close": [(high + low) / 2 for high, low in zip(highs, lows)],
            "high": highs,
            "low": lows,
            "volume": [100] * len(highs),
        }
    )


class ChanEngineTests(unittest.TestCase):
    def test_inclusion_merges_bars_and_preserves_raw_bars(self):
        data = frame([10, 9, 12], [5, 6, 7])
        engine = ChanEngine("T", "d").process_klines(data)
        self.assertEqual(len(engine.get_src_klines()), 3)
        self.assertEqual(len(engine.get_cl_klines()), 2)
        self.assertEqual(len(engine.get_cl_klines()[0].bars), 2)

    def test_three_bars_create_top_fractal(self):
        data = frame([10, 13, 11], [7, 9, 8])
        engine = ChanEngine("T", "d").process_klines(data)
        self.assertEqual([(fx.kind, fx.value) for fx in engine.get_fxs()], [("top", 13)])

    def test_incremental_input_is_idempotent_and_updates_same_date(self):
        data = frame([10, 13, 11, 14, 9])
        engine = ChanEngine("T", "d").process_klines(data.iloc[:3])
        engine.process_klines(data)
        first = engine.snapshot()
        engine.process_klines(data)
        self.assertEqual(engine.snapshot(), first)

    def test_pivot_uses_three_line_overlap(self):
        # 宽松笔口径让人工波峰波谷形成足够的笔。
        highs = [10, 14, 11, 15, 12, 16, 13, 17, 14, 18, 15]
        lows = [8, 12, 7, 13, 8, 14, 9, 15, 10, 16, 11]
        engine = ChanEngine("T", "d", ChanConfig(bi_type="top_bottom", strict_fractal=False))
        engine.process_klines(frame(highs, lows))
        for pivot in engine.get_bi_zss():
            self.assertGreaterEqual(pivot.zg, pivot.zd)
            self.assertGreaterEqual(len(pivot.lines), 3)

    def test_risk_policy_rounds_to_lot_and_stops_loss(self):
        policy = RiskPolicy(max_position_fraction=0.2, stop_loss_fraction=0.05)
        self.assertEqual(policy.order_size(100_000, 100_000, 10, 100), 2_000)
        self.assertEqual(policy.should_exit_long(10, 9.49), "stop_loss")

    def test_simulated_swing_data_creates_segments(self):
        highs = [10, 14, 11, 15, 12, 16, 13, 17, 14]
        lows = [8, 12, 7, 13, 8, 14, 9, 15, 10]
        engine = ChanEngine("T", "d", ChanConfig(bi_type="top_bottom", strict_fractal=False))
        engine.process_klines(frame(highs, lows))
        self.assertGreater(len(engine.get_xds()), 0)


if __name__ == "__main__":
    unittest.main()
