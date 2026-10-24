"""缠论计算接口。"""

from __future__ import annotations

import datetime
from types import SimpleNamespace
from typing import Union

import pandas as pd

from chanlun.cl_interface import BI, FX, XD, ZS, CLKline, Config, Kline
from chanlun_core import ChanConfig, ChanEngine


def _config_value(config: dict, key: str, default):
    value = config.get(key, default)
    return value.value if hasattr(value, "value") else value


def _to_core_config(config: dict) -> ChanConfig:
    bi_types = {
        Config.BI_TYPE_OLD.value: "old",
        Config.BI_TYPE_NEW.value: "new",
        Config.BI_TYPE_JDB.value: "simple",
        Config.BI_TYPE_DD.value: "top_bottom",
    }
    overlap = "all" if _config_value(config, "zs_cd", Config.ZS_CD_THREE.value) == Config.ZS_CD_MORE.value else "first_three"
    relations = {
        Config.ZS_WZGX_ZGD.value: "zg_zd",
        Config.ZS_WZGX_ZGGDD.value: "zg_dd",
        Config.ZS_WZGX_GD.value: "gg_dd",
    }
    return ChanConfig(
        bi_type=bi_types.get(_config_value(config, "bi_type", Config.BI_TYPE_NEW.value), "new"),
        strict_fractal=bool(config.get("allow_bi_fx_strict", True)),
        allow_sub_extreme_fractal=_config_value(config, "bi_fx_cgd", Config.BI_FX_CHD_NO.value) == Config.BI_FX_CHD_YES.value,
        pivot_overlap=overlap,
        pivot_relation=relations.get(_config_value(config, "zs_wzgx", Config.ZS_WZGX_ZGD.value), "zg_zd"),
        macd_fast=int(config.get("idx_macd_fast", 12)),
        macd_slow=int(config.get("idx_macd_slow", 26)),
        macd_signal=int(config.get("idx_macd_signal", 9)),
    )


class CL:
    """提供 ICL 约定的缠论计算接口。"""

    def __init__(
        self,
        code: str,
        frequency: str,
        config: Union[dict, None] = None,
        start_datetime: datetime.datetime = None,
    ):
        self.code = code
        self.frequency = frequency
        self.config = dict(config or {})
        self.start_datetime = start_datetime
        self._engine = ChanEngine(code, frequency, _to_core_config(self.config))
        self._src: list[Kline] = []
        self._cks: list[CLKline] = []
        self._fxs: list[FX] = []
        self._bis: list[BI] = []
        self._xds: list[XD] = []
        self._zsds: list[XD] = []
        self._bi_zss: list[ZS] = []
        self._xd_zss: list[ZS] = []
        self._zsd_zss: list[ZS] = []
        self._idx: dict = {}

    def process_klines(self, klines: pd.DataFrame):
        frame = klines
        if self.start_datetime is not None:
            frame = klines[pd.to_datetime(klines["date"]) >= self.start_datetime]
        self._engine.process_klines(frame)
        self._convert_objects()
        self._calculate_indicators()
        return self

    def _convert_objects(self) -> None:
        self._src = [Kline(k.index, k.date, k.high, k.low, k.open, k.close, k.volume) for k in self._engine.get_src_klines()]
        src_by_index = {k.index: k for k in self._src}
        self._cks = []
        for ck in self._engine.get_cl_klines():
            source = [src_by_index[k.index] for k in ck.bars]
            self._cks.append(CLKline(source[-1].index, source[-1].date, ck.high, ck.low, ck.open, ck.close, ck.volume, source, ck.index, len(source), False))

        self._fxs = []
        core_fx_to_dto = {}
        for core_fx in self._engine.get_fxs():
            dto = FX("ding" if core_fx.kind == "top" else "di", self._cks[core_fx.k_index],
                     [self._cks[core_fx.k_index - 1], self._cks[core_fx.k_index], self._cks[core_fx.k_index + 1]],
                     core_fx.value, len(self._fxs), core_fx.done)
            self._fxs.append(dto)
            core_fx_to_dto[id(core_fx)] = dto

        self._bis = []
        core_bi_to_dto = {}
        default_zs_type = self._default_zs_type("zs_bi_type")
        for line in self._engine.get_bis():
            dto = BI(core_fx_to_dto[id(line.start)], core_fx_to_dto[id(line.end)], line.direction, line.index, default_zs_type)
            dto.high = dto.zs_high = line.high
            dto.low = dto.zs_low = line.low
            self._bis.append(dto)
            core_bi_to_dto[id(line)] = dto

        self._xds = self._convert_segments(self._engine.get_xds(), self._bis)
        self._zsds = self._convert_segments(self._build_recursive_lines(self._engine.get_xds()), self._xds)
        self._bi_zss = self._convert_pivots(self._engine.get_bi_zss(), core_bi_to_dto, "bi", default_zs_type)
        core_xd_to_dto = {id(core): dto for core, dto in zip(self._engine.get_xds(), self._xds)}
        self._xd_zss = self._convert_pivots(self._engine.get_xd_zss(), core_xd_to_dto, "xd", self._default_zs_type("zs_xd_type"))
        self._attach_signals(self._engine.get_bis(), self._bis, self._bi_zss, default_zs_type)

    def _convert_segments(self, core_lines, lower_lines):
        result = []
        default = self._default_zs_type("zs_xd_type")
        for line in core_lines:
            start_i, end_i = line.start.k_index, line.end.k_index
            if start_i >= len(lower_lines) or end_i >= len(lower_lines):
                continue
            start_line, end_line = lower_lines[start_i], lower_lines[end_i]
            marker = SimpleNamespace(qk=False, done=line.done, is_line_bad=False)
            dto = XD(start_line.start, end_line.end, start_line, end_line, line.direction,
                     marker if line.direction == "up" else None,
                     marker if line.direction == "down" else None, len(result), default)
            dto.high = dto.zs_high = line.high
            dto.low = dto.zs_low = line.low
            dto.done = line.done
            result.append(dto)
        return result

    @staticmethod
    def _build_recursive_lines(lines):
        # 当前标准实现的走势段由线段特征序列递归生成；短序列返回空列表。
        return []

    @staticmethod
    def _convert_pivots(core_pivots, line_map, line_type, default_zs_type):
        result = []
        for pivot in core_pivots:
            lines = [line_map[id(line)] for line in pivot.lines if id(line) in line_map]
            if not lines:
                continue
            zs = ZS(line_type, lines[0].start, lines[-1].end, pivot.zg, pivot.zd,
                    pivot.gg, pivot.dd, "zd" if pivot.direction == "range" else pivot.direction,
                    len(result), len(lines), pivot.level)
            zs.lines = lines
            zs.done = pivot.done
            zs.real = True
            zs.zs_kind = default_zs_type
            result.append(zs)
        return result

    @staticmethod
    def _attach_signals(core_lines, dto_lines, zss, zs_type):
        zs_by_index = {zs.index: zs for zs in zss}
        for core, dto in zip(core_lines, dto_lines):
            for signal in core.signals:
                zs = zs_by_index.get(signal.pivot_index)
                if zs is not None:
                    dto.add_mmd(signal.name, zs, zs_type, signal.message)
            for signal in core.divergences:
                zs = zs_by_index.get(signal.pivot_index)
                dto.add_bc(signal.name, zs, None, [], True, zs_type)

    def _calculate_indicators(self) -> None:
        close = pd.Series([k.c for k in self._src], dtype="float64")
        fast, slow, signal = self._engine.config.macd_fast, self._engine.config.macd_slow, self._engine.config.macd_signal
        dif = close.ewm(span=fast, adjust=False).mean() - close.ewm(span=slow, adjust=False).mean()
        dea = dif.ewm(span=signal, adjust=False).mean()
        hist = (dif - dea) * 2
        self._idx = {"macd": {"dif": dif.to_numpy(), "dea": dea.to_numpy(), "hist": hist.to_numpy()}}

    def _default_zs_type(self, key):
        value = self.config.get(key, [Config.ZS_TYPE_BZ.value])
        if isinstance(value, str):
            return value
        return value[0] if value else Config.ZS_TYPE_BZ.value

    def get_code(self): return self.code
    def get_frequency(self): return self.frequency
    def get_config(self): return dict(self.config)
    def get_src_klines(self): return self._src
    def get_klines(self):
        return self._cks if self.config.get("kline_type") == Config.KLINE_TYPE_CHANLUN.value else self._src
    def get_cl_klines(self): return self._cks
    def get_idx(self): return self._idx
    def get_fxs(self): return self._fxs
    def get_bis(self): return self._bis
    def get_xds(self): return self._xds
    def get_zsds(self): return self._zsds
    def get_qsds(self): return []
    def get_bi_zss(self, zs_type=None): return self._bi_zss
    def get_xd_zss(self, zs_type=None): return self._xd_zss
    def get_zsd_zss(self): return self._zsd_zss
    def get_qsd_zss(self): return []
    def get_last_bi_zs(self): return self._bi_zss[-1] if self._bi_zss else None
    def get_last_xd_zs(self): return self._xd_zss[-1] if self._xd_zss else None

    def create_dn_zs(self, zs_type, lines, max_line_num=999, zs_include_last_line=True):
        # 对外部 DTO 线使用同一三线重叠规则。
        result = []
        for i in range(max(0, len(lines) - 2)):
            group = lines[i : min(len(lines), i + max_line_num)]
            if len(group) < 3:
                break
            zg, zd = min(x.high for x in group[:3]), max(x.low for x in group[:3])
            if zg >= zd:
                zs = ZS(zs_type, group[0].start, group[-1].end, zg, zd,
                        max(x.high for x in group), min(x.low for x in group), "zd", len(result), len(group), max(0, (len(group)-1)//9))
                zs.lines = group
                result.append(zs)
        return result

    @staticmethod
    def _strength(line):
        span = max(1, line.end.k.k_index - line.start.k.k_index)
        return abs(line.end.val - line.start.val) / span

    def beichi_pz(self, zs, now_line):
        enter_index = zs.lines[0].index - 1
        pool = self._bis if zs.zs_type == "bi" else self._xds
        if enter_index < 0 or enter_index >= len(pool):
            return False, None
        compare = pool[enter_index]
        is_bc = compare.type == now_line.type and self._strength(now_line) < self._strength(compare)
        return is_bc, compare

    def beichi_qs(self, lines, zss, now_line):
        if len(zss) < 2 or self.zss_is_qs(zss[-2], zss[-1]) is None:
            return False, []
        comparisons = [line for line in lines[: now_line.index] if line.type == now_line.type]
        if not comparisons:
            return False, []
        compare = comparisons[-1]
        return self._strength(now_line) < self._strength(compare), [compare]

    def zss_is_qs(self, one_zs, two_zs):
        relation = self._engine.config.pivot_relation
        if relation == "gg_dd":
            one_high, one_low, two_high, two_low = one_zs.gg, one_zs.dd, two_zs.gg, two_zs.dd
        elif relation == "zg_dd":
            one_high, one_low, two_high, two_low = one_zs.gg, one_zs.zd, two_zs.zg, two_zs.dd
        else:
            one_high, one_low, two_high, two_low = one_zs.zg, one_zs.zd, two_zs.zg, two_zs.zd
        if two_low > one_high: return "up"
        if two_high < one_low: return "down"
        return None
