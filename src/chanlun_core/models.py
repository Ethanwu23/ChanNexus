from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

Direction = Literal["up", "down"]
FractalKind = Literal["top", "bottom"]


@dataclass(frozen=True, slots=True)
class Bar:
    index: int
    date: datetime
    high: float
    low: float
    open: float
    close: float
    volume: float

    def __post_init__(self) -> None:
        if self.high < self.low:
            raise ValueError(f"K线 high < low: {self.date}")
        if not self.low <= self.open <= self.high or not self.low <= self.close <= self.high:
            raise ValueError(f"开收盘价超出高低区间: {self.date}")


@dataclass(slots=True)
class ChanBar:
    index: int
    high: float
    low: float
    open: float
    close: float
    volume: float
    bars: list[Bar] = field(default_factory=list)

    @property
    def date(self) -> datetime:
        return self.bars[-1].date


@dataclass(slots=True)
class Fractal:
    index: int
    kind: FractalKind
    k_index: int
    value: float
    left: ChanBar
    middle: ChanBar
    right: ChanBar
    done: bool = True

    @property
    def raw_start_index(self) -> int:
        return self.left.bars[0].index

    @property
    def raw_end_index(self) -> int:
        return self.right.bars[-1].index


@dataclass(slots=True)
class Signal:
    name: str
    message: str
    pivot_index: int | None = None


@dataclass(slots=True)
class Line:
    index: int
    direction: Direction
    start: Fractal
    end: Fractal
    high: float
    low: float
    done: bool = True
    signals: list[Signal] = field(default_factory=list)
    divergences: list[Signal] = field(default_factory=list)


@dataclass(slots=True)
class Pivot:
    index: int
    line_type: Literal["bi", "xd"]
    lines: list[Line]
    zg: float
    zd: float
    gg: float
    dd: float
    direction: Literal["up", "down", "range"] = "range"
    done: bool = False

    @property
    def level(self) -> int:
        return max(0, (len(self.lines) - 1) // 9)

    def overlaps(self, line: Line) -> bool:
        return min(self.zg, line.high) >= max(self.zd, line.low)
