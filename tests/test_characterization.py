import hashlib
import json
import unittest
from pathlib import Path

import pandas as pd

from chanlun_core import ChanConfig, ChanEngine


FIXTURE_DIR = Path(__file__).parent / "fixtures"


def load_json(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def case_frame(case: dict) -> pd.DataFrame:
    """将紧凑的人工行情案例转换为标准OHLCV输入。"""
    highs = case["highs"]
    lows = case["lows"]
    return pd.DataFrame(
        {
            "date": pd.date_range(
                case["start_date"], periods=len(highs), freq="D"
            ),
            "open": [
                (high + low) / 2 for high, low in zip(highs, lows)
            ],
            "close": [
                (high + low) / 2 for high, low in zip(highs, lows)
            ],
            "high": highs,
            "low": lows,
            "volume": [100 + index for index in range(len(highs))],
        }
    )


def build_engine(case: dict, frame: pd.DataFrame | None = None) -> ChanEngine:
    return ChanEngine(
        case["code"],
        case["frequency"],
        ChanConfig(**case["config"]),
    ).process_klines(frame if frame is not None else case_frame(case))


def snapshot_sha256(snapshot: dict) -> str:
    canonical = json.dumps(
        snapshot,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class CharacterizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = load_json("characterization_cases.json")["cases"]
        cls.baseline = load_json("baseline_v1.json")["cases"]

    def test_complete_snapshots_match_baseline_v1(self):
        """锁定包含、分型、笔、线段、中枢及信号的完整公开输出。"""
        for case in self.cases:
            with self.subTest(case=case["name"]):
                snapshot = build_engine(case).snapshot()
                expected = self.baseline[case["name"]]
                self.assertEqual(snapshot["counts"], expected["counts"])
                self.assertEqual(snapshot_sha256(snapshot), expected["sha256"])

    def test_batch_and_incremental_results_are_identical(self):
        """实时逐根输入和批量回测必须得到完全相同的结果。"""
        for case in self.cases:
            with self.subTest(case=case["name"]):
                frame = case_frame(case)
                batch = build_engine(case, frame)
                incremental = ChanEngine(
                    case["code"],
                    case["frequency"],
                    ChanConfig(**case["config"]),
                )
                for index in range(len(frame)):
                    incremental.process_klines(frame.iloc[[index]])
                self.assertEqual(incremental.snapshot(), batch.snapshot())

    def test_domain_invariants(self):
        """验证快照之外必须始终成立的缠论结构约束。"""
        for case in self.cases:
            with self.subTest(case=case["name"]):
                engine = build_engine(case)
                source = engine.get_src_klines()
                dates = [bar.date for bar in source]
                self.assertEqual(dates, sorted(set(dates)))

                source_indexes = [
                    source.index
                    for chan_bar in engine.get_cl_klines()
                    for source in chan_bar.bars
                ]
                self.assertEqual(source_indexes, list(range(len(source))))

                fractals = engine.get_fxs()
                self.assertTrue(
                    all(
                        left.kind != right.kind
                        for left, right in zip(fractals, fractals[1:])
                    )
                )

                for lines in (engine.get_bis(), engine.get_xds()):
                    self.assertTrue(
                        all(line.start.value != line.end.value for line in lines)
                    )
                    self.assertTrue(
                        all(line.high >= line.low for line in lines)
                    )

                for pivots in (engine.get_bi_zss(), engine.get_xd_zss()):
                    self.assertTrue(
                        all(
                            pivot.zg >= pivot.zd and len(pivot.lines) >= 3
                            for pivot in pivots
                        )
                    )


if __name__ == "__main__":
    unittest.main()
