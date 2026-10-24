"""笔的有效性判断与构造。"""

from .config import ChanConfig
from .models import Fractal, Line


def _is_valid(start: Fractal, end: Fractal, config: ChanConfig) -> bool:
    if start.kind == end.kind:
        return False

    raw_count = end.middle.bars[-1].index - start.middle.bars[0].index + 1
    if config.bi_type == "top_bottom":
        distance_ok = True
    elif config.bi_type == "old":
        distance_ok = end.k_index - start.k_index >= 3
    else:
        distance_ok = raw_count >= config.min_bi_raw_bars
    if not distance_ok:
        return False

    if config.strict_fractal:
        if start.kind == "bottom" and start.value >= end.value:
            return False
        if start.kind == "top" and start.value <= end.value:
            return False
    return True


def build_strokes(fractals: list[Fractal], config: ChanConfig) -> list[Line]:
    """根据交替分型、间距和严格性配置生成笔。"""
    lines: list[Line] = []
    if not fractals:
        return lines

    start = fractals[0]
    for end in fractals[1:]:
        if not _is_valid(start, end, config):
            if start.kind == end.kind:
                more_extreme = (
                    end.value >= start.value
                    if end.kind == "top"
                    else end.value <= start.value
                )
                if more_extreme:
                    start = end
            continue
        direction = "up" if start.kind == "bottom" else "down"
        lines.append(
            Line(
                len(lines),
                direction,
                start,
                end,
                max(start.value, end.value),
                min(start.value, end.value),
            )
        )
        start = end
    return lines
