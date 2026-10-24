"""HTTP接口输入输出模型。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class KlineInput(BaseModel):
    """标准OHLCV输入。"""

    model_config = ConfigDict(extra="forbid")

    date: datetime
    open: float
    close: float
    high: float
    low: float
    volume: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_price_range(self) -> "KlineInput":
        if self.high < self.low:
            raise ValueError("K线high不能小于low")
        if not self.low <= self.open <= self.high:
            raise ValueError("K线open必须位于high与low之间")
        if not self.low <= self.close <= self.high:
            raise ValueError("K线close必须位于high与low之间")
        return self


class ChanConfigInput(BaseModel):
    """缠论计算参数。"""

    model_config = ConfigDict(extra="forbid")

    bi_type: Literal["old", "new", "simple", "top_bottom"] = "new"
    min_bi_raw_bars: int = Field(default=5, ge=1)
    strict_fractal: bool = True
    allow_sub_extreme_fractal: bool = False
    pivot_overlap: Literal["first_three", "all"] = "first_three"
    pivot_relation: Literal["zg_zd", "zg_dd", "gg_dd"] = "zg_zd"
    macd_fast: int = Field(default=12, ge=1)
    macd_slow: int = Field(default=26, ge=2)
    macd_signal: int = Field(default=9, ge=1)

    @model_validator(mode="after")
    def validate_macd_periods(self) -> "ChanConfigInput":
        if self.macd_fast >= self.macd_slow:
            raise ValueError("MACD周期必须满足fast小于slow")
        return self


class AnalysisRequest(BaseModel):
    """缠论分析请求。"""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1)
    frequency: str = Field(min_length=1)
    config: ChanConfigInput = Field(default_factory=ChanConfigInput)
    klines: list[KlineInput] = Field(min_length=1)


class CountSnapshot(BaseModel):
    src: int
    cl: int
    fx: int
    bi: int
    xd: int
    bi_zs: int
    xd_zs: int


class SourceBarSnapshot(BaseModel):
    index: int
    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class ChanBarSnapshot(SourceBarSnapshot):
    source_indexes: list[int]


class FractalSnapshot(BaseModel):
    index: int
    kind: Literal["top", "bottom"]
    k_index: int
    date: datetime
    value: float
    raw_start_index: int
    raw_end_index: int
    done: bool


class EndpointSnapshot(BaseModel):
    index: int
    date: datetime
    value: float


class SignalSnapshot(BaseModel):
    name: str
    message: str
    pivot_index: int | None


class LineSnapshot(BaseModel):
    index: int
    direction: Literal["up", "down"]
    start: EndpointSnapshot
    end: EndpointSnapshot
    high: float
    low: float
    done: bool
    signals: list[SignalSnapshot]
    divergences: list[SignalSnapshot]


class PivotSnapshot(BaseModel):
    index: int
    line_type: Literal["bi", "xd"]
    line_indexes: list[int]
    zg: float
    zd: float
    gg: float
    dd: float
    direction: Literal["up", "down", "range"]
    done: bool
    level: int


class AnalysisResponse(BaseModel):
    """稳定的缠论分析响应。"""

    schema_version: int
    code: str
    frequency: str
    counts: CountSnapshot
    source_bars: list[SourceBarSnapshot]
    chan_bars: list[ChanBarSnapshot]
    fractals: list[FractalSnapshot]
    bis: list[LineSnapshot]
    segments: list[LineSnapshot]
    bi_pivots: list[PivotSnapshot]
    segment_pivots: list[PivotSnapshot]


class HealthResponse(BaseModel):
    status: Literal["ok"]
    service: Literal["ChanNexus"]


class ExchangeSnapshot(BaseModel):
    value: str
    name: str
    desc: str


class TradingViewConfigResponse(BaseModel):
    supports_search: bool
    supports_group_request: bool
    supported_resolutions: list[str]
    supports_marks: bool
    supports_timescale_marks: bool
    supports_time: bool
    exchanges: list[ExchangeSnapshot]
