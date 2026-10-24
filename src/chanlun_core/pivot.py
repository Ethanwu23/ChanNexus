"""中枢构造。"""

from typing import Literal

from .config import ChanConfig
from .models import Line, Pivot


def build_pivots(
    lines: list[Line],
    line_type: Literal["bi", "xd"],
    config: ChanConfig,
) -> list[Pivot]:
    """从连续三条存在重叠的线开始构造中枢。"""
    pivots: list[Pivot] = []
    index = 0
    while index + 2 < len(lines):
        seed = lines[index : index + 3]
        zg = min(line.high for line in seed)
        zd = max(line.low for line in seed)
        if zg < zd:
            index += 1
            continue

        members = list(seed)
        probe = index + 3
        while probe < len(lines) and min(zg, lines[probe].high) >= max(
            zd, lines[probe].low
        ):
            members.append(lines[probe])
            if config.pivot_overlap == "all":
                zg = min(zg, lines[probe].high)
                zd = max(zd, lines[probe].low)
            probe += 1

        pivot = Pivot(
            len(pivots),
            line_type,
            members,
            zg,
            zd,
            max(line.high for line in members),
            min(line.low for line in members),
        )
        if index > 0 and probe < len(lines):
            enter = lines[index - 1]
            leave = lines[probe]
            pivot.direction = (
                "up"
                if enter.direction == leave.direction == "up"
                else (
                    "down"
                    if enter.direction == leave.direction == "down"
                    else "range"
                )
            )
        pivots.append(pivot)
        index = max(index + 1, probe - 1)
    return pivots
