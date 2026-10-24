from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class ChanConfig:
    """独立计算器配置；默认值对应文档中的标准/新笔口径。"""

    bi_type: Literal["old", "new", "simple", "top_bottom"] = "new"
    min_bi_raw_bars: int = 5
    strict_fractal: bool = True
    allow_sub_extreme_fractal: bool = False
    pivot_overlap: Literal["first_three", "all"] = "first_three"
    pivot_relation: Literal["zg_zd", "zg_dd", "gg_dd"] = "zg_zd"
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9

    def __post_init__(self) -> None:
        if self.min_bi_raw_bars < 1:
            raise ValueError("min_bi_raw_bars 必须大于 0")
        if not (0 < self.macd_fast < self.macd_slow):
            raise ValueError("MACD 周期必须满足 0 < fast < slow")
        if self.macd_signal < 1:
            raise ValueError("macd_signal 必须大于 0")
