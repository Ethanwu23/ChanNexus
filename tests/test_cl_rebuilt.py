import unittest
import sys
import types

# 此测试不调用 ZS.r2，仅注册最小 scipy 模块以加载公开 DTO。
# 完整项目环境使用真实 scipy。
if "scipy" not in sys.modules:
    scipy_stub = types.ModuleType("scipy")
    scipy_stub.stats = types.SimpleNamespace(linregress=lambda *_args, **_kwargs: (0, 0, 0, 0, 0))
    sys.modules["scipy"] = scipy_stub

from chanlun import cl_rebuilt
from chanlun.cl_interface import BI, CLKline, FX, Kline
from chanlun_core.selftest import simulated_klines


class CompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.data = simulated_klines(180)
        self.cd = cl_rebuilt.CL("SIM.TEST", "d", {"bi_type": "bi_type_dd"}).process_klines(self.data)

    def test_public_getters_and_dto_types(self):
        self.assertIsInstance(self.cd.get_src_klines()[0], Kline)
        self.assertIsInstance(self.cd.get_cl_klines()[0], CLKline)
        self.assertTrue(all(isinstance(item, FX) for item in self.cd.get_fxs()))
        self.assertTrue(all(isinstance(item, BI) for item in self.cd.get_bis()))
        self.assertEqual(self.cd.get_code(), "SIM.TEST")
        self.assertEqual(self.cd.get_frequency(), "d")

    def test_field_chains_used_by_strategies(self):
        if self.cd.get_bis():
            bi = self.cd.get_bis()[-1]
            self.assertIsInstance(bi.start.k.k_index, int)
            self.assertIsInstance(bi.line_mmds("|"), list)
            self.assertIn(bi.type, ("up", "down"))

    def test_macd_lengths_match_source_bars(self):
        macd = self.cd.get_idx()["macd"]
        self.assertEqual(len(macd["dif"]), len(self.data))
        self.assertEqual(len(macd["dea"]), len(self.data))
        self.assertEqual(len(macd["hist"]), len(self.data))

    def test_incremental_input_is_idempotent(self):
        before = [(bi.type, bi.start.val, bi.end.val) for bi in self.cd.get_bis()]
        self.cd.process_klines(self.data)
        after = [(bi.type, bi.start.val, bi.end.val) for bi in self.cd.get_bis()]
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
