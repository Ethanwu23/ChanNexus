"""无需外部行情文件的确定性模拟行情与自测。"""

from __future__ import annotations

import math
import random

import pandas as pd

from .config import ChanConfig
from .engine import ChanEngine


def simulated_klines(size: int = 360, seed: int = 20260712) -> pd.DataFrame:
    """生成趋势、震荡、反转和少量包含关系并存的 OHLCV 数据。"""
    if size < 30:
        raise ValueError("模拟行情至少需要 30 根 K线")
    rng = random.Random(seed)
    rows = []
    previous = 100.0
    for i in range(size):
        phase = i / max(1, size - 1)
        trend = 18 * phase if phase < 0.3 else (18 - 30 * (phase - 0.3) if phase < 0.65 else 7 + 24 * (phase - 0.65))
        center = 100 + trend + 5 * math.sin(i / 7) + 2 * math.sin(i / 2.7)
        close = center + rng.uniform(-0.7, 0.7)
        open_ = previous + rng.uniform(-0.5, 0.5)
        high = max(open_, close) + rng.uniform(0.3, 1.4)
        low = min(open_, close) - rng.uniform(0.3, 1.4)
        # 定期制造位于上一根内部的小 K线，覆盖包含合并路径。
        if i and i % 37 == 0:
            last = rows[-1]
            high = last["high"] - 0.1
            low = last["low"] + 0.1
            open_ = close = (high + low) / 2
        rows.append({"date": pd.Timestamp("2020-01-01") + pd.Timedelta(days=i), "open": open_, "close": close,
                     "high": high, "low": low, "volume": 1000 + rng.randint(0, 900)})
        previous = close
    return pd.DataFrame(rows)


def run_self_test() -> dict:
    data = simulated_klines()
    engine = ChanEngine("SIM.TEST", "d", ChanConfig(bi_type="top_bottom", strict_fractal=False))
    engine.process_klines(data.iloc[:180])
    engine.process_klines(data)
    snapshot = engine.snapshot()
    assert snapshot["counts"]["src"] == len(data)
    assert snapshot["counts"]["cl"] <= snapshot["counts"]["src"]
    assert all(left.kind != right.kind for left, right in zip(engine.get_fxs(), engine.get_fxs()[1:]))
    assert all(line.direction != next_line.direction for line, next_line in zip(engine.get_bis(), engine.get_bis()[1:]))
    assert snapshot["counts"]["xd"] > 0, "模拟行情应形成线段"
    assert all(zs.zg >= zs.zd and len(zs.lines) >= 3 for zs in engine.get_bi_zss())
    before = engine.snapshot()
    engine.process_klines(data)
    assert before == engine.snapshot(), "重复输入必须幂等"
    return snapshot
