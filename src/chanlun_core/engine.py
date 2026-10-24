from __future__ import annotations

import pandas as pd

from .config import ChanConfig
from .fractal import find_fractals
from .inclusion import merge_inclusions
from .models import Bar, ChanBar, Fractal, Line, Pivot
from .pivot import build_pivots
from .segment import build_segments
from .signal import attach_signals
from .stroke import build_strokes


class ChanEngine:
    """确定性增量缠论计算器。

    新数据到来时重建派生结构，输入按日期去重，因此行为可重复且不会累计重复K线。
    """

    REQUIRED_COLUMNS = {"date", "open", "close", "high", "low", "volume"}

    def __init__(self, code: str, frequency: str, config: ChanConfig | None = None):
        self.code = code
        self.frequency = frequency
        self.config = config or ChanConfig()
        self._bars: list[Bar] = []
        self._chan_bars: list[ChanBar] = []
        self._fractals: list[Fractal] = []
        self._bis: list[Line] = []
        self._segments: list[Line] = []
        self._bi_pivots: list[Pivot] = []
        self._segment_pivots: list[Pivot] = []

    def process_klines(self, klines: pd.DataFrame) -> "ChanEngine":
        missing = self.REQUIRED_COLUMNS.difference(klines.columns)
        if missing:
            raise ValueError(f"K线缺少字段: {sorted(missing)}")
        frame = klines.copy()
        frame["date"] = pd.to_datetime(frame["date"])
        frame = frame.sort_values("date").drop_duplicates("date", keep="last")
        incoming = [
            Bar(
                index=i,
                date=row.date.to_pydatetime() if hasattr(row.date, "to_pydatetime") else row.date,
                high=float(row.high), low=float(row.low), open=float(row.open),
                close=float(row.close), volume=float(row.volume),
            )
            for i, row in enumerate(frame.itertuples(index=False))
        ]
        merged = {bar.date: bar for bar in self._bars}
        merged.update({bar.date: bar for bar in incoming})
        self._bars = [
            Bar(i, bar.date, bar.high, bar.low, bar.open, bar.close, bar.volume)
            for i, bar in enumerate(sorted(merged.values(), key=lambda item: item.date))
        ]
        self._recalculate()
        return self

    def _recalculate(self) -> None:
        self._chan_bars = merge_inclusions(self._bars)
        self._fractals = find_fractals(self._chan_bars)
        self._bis = build_strokes(self._fractals, self.config)
        self._segments = build_segments(self._bis)
        self._bi_pivots = build_pivots(self._bis, "bi", self.config)
        self._segment_pivots = build_pivots(
            self._segments, "xd", self.config
        )
        attach_signals(self._bis, self._bi_pivots)
        attach_signals(self._segments, self._segment_pivots)


    def get_src_klines(self) -> list[Bar]: return list(self._bars)
    def get_cl_klines(self) -> list[ChanBar]: return list(self._chan_bars)
    def get_fxs(self) -> list[Fractal]: return list(self._fractals)
    def get_bis(self) -> list[Line]: return list(self._bis)
    def get_xds(self) -> list[Line]: return list(self._segments)
    def get_bi_zss(self) -> list[Pivot]: return list(self._bi_pivots)
    def get_xd_zss(self) -> list[Pivot]: return list(self._segment_pivots)

    def snapshot(self) -> dict:
        """返回可长期保存并用于特征测试的完整业务快照。

        快照只包含公开、确定性的业务字段，不包含对象地址和运行时间。所有
        浮点数统一保留八位小数，避免不同平台的浮点表示差异干扰回归测试。
        """

        def number(value: float) -> float:
            return round(float(value), 8)

        def line_snapshot(line: Line) -> dict:
            return {
                "index": line.index,
                "direction": line.direction,
                "start": {
                    "index": line.start.index,
                    "date": line.start.middle.date.isoformat(),
                    "value": number(line.start.value),
                },
                "end": {
                    "index": line.end.index,
                    "date": line.end.middle.date.isoformat(),
                    "value": number(line.end.value),
                },
                "high": number(line.high),
                "low": number(line.low),
                "done": bool(line.done),
                "signals": [
                    {
                        "name": signal.name,
                        "message": signal.message,
                        "pivot_index": signal.pivot_index,
                    }
                    for signal in line.signals
                ],
                "divergences": [
                    {
                        "name": signal.name,
                        "message": signal.message,
                        "pivot_index": signal.pivot_index,
                    }
                    for signal in line.divergences
                ],
            }

        def pivot_snapshot(pivot: Pivot) -> dict:
            return {
                "index": pivot.index,
                "line_type": pivot.line_type,
                "line_indexes": [line.index for line in pivot.lines],
                "zg": number(pivot.zg),
                "zd": number(pivot.zd),
                "gg": number(pivot.gg),
                "dd": number(pivot.dd),
                "direction": pivot.direction,
                "done": bool(pivot.done),
                "level": pivot.level,
            }

        return {
            "schema_version": 1,
            "code": self.code,
            "frequency": self.frequency,
            "counts": {
                "src": len(self._bars),
                "cl": len(self._chan_bars),
                "fx": len(self._fractals),
                "bi": len(self._bis),
                "xd": len(self._segments),
                "bi_zs": len(self._bi_pivots),
                "xd_zs": len(self._segment_pivots),
            },
            "source_bars": [
                {
                    "index": bar.index,
                    "date": bar.date.isoformat(),
                    "open": number(bar.open),
                    "high": number(bar.high),
                    "low": number(bar.low),
                    "close": number(bar.close),
                    "volume": number(bar.volume),
                }
                for bar in self._bars
            ],
            "chan_bars": [
                {
                    "index": bar.index,
                    "date": bar.date.isoformat(),
                    "open": number(bar.open),
                    "high": number(bar.high),
                    "low": number(bar.low),
                    "close": number(bar.close),
                    "volume": number(bar.volume),
                    "source_indexes": [source.index for source in bar.bars],
                }
                for bar in self._chan_bars
            ],
            "fractals": [
                {
                    "index": fractal.index,
                    "kind": fractal.kind,
                    "k_index": fractal.k_index,
                    "date": fractal.middle.date.isoformat(),
                    "value": number(fractal.value),
                    "raw_start_index": fractal.raw_start_index,
                    "raw_end_index": fractal.raw_end_index,
                    "done": bool(fractal.done),
                }
                for fractal in self._fractals
            ],
            "bis": [line_snapshot(line) for line in self._bis],
            "segments": [line_snapshot(line) for line in self._segments],
            "bi_pivots": [pivot_snapshot(pivot) for pivot in self._bi_pivots],
            "segment_pivots": [
                pivot_snapshot(pivot) for pivot in self._segment_pivots
            ],
        }
