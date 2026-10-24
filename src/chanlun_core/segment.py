"""线段构造。"""

from .models import Bar, ChanBar, Fractal, Line


def build_segments(strokes: list[Line]) -> list[Line]:
    """以至少三笔、奇数笔构造当前基线定义的线段。"""
    if len(strokes) < 3:
        return []

    pseudo_bars = [
        ChanBar(
            index,
            line.high,
            line.low,
            line.start.value,
            line.end.value,
            0.0,
            [
                Bar(
                    index,
                    line.end.middle.date,
                    line.high,
                    line.low,
                    line.start.value,
                    line.end.value,
                    0.0,
                )
            ],
        )
        for index, line in enumerate(strokes)
    ]

    segments: list[Line] = []
    start_index = 0
    while start_index + 2 < len(strokes):
        direction = strokes[start_index].direction
        end_index = start_index + 2
        probe = end_index + 2
        while probe < len(strokes):
            extends = (
                strokes[probe].high >= strokes[end_index].high
                if direction == "up"
                else strokes[probe].low <= strokes[end_index].low
            )
            if not extends:
                break
            end_index = probe
            probe += 2

        start_bar = pseudo_bars[start_index]
        end_bar = pseudo_bars[end_index]
        start_kind = "bottom" if direction == "up" else "top"
        end_kind = "top" if direction == "up" else "bottom"
        start_value = strokes[start_index].start.value
        end_value = strokes[end_index].end.value
        start_fractal = Fractal(
            start_index,
            start_kind,
            start_index,
            start_value,
            start_bar,
            start_bar,
            start_bar,
        )
        end_fractal = Fractal(
            end_index,
            end_kind,
            end_index,
            end_value,
            end_bar,
            end_bar,
            end_bar,
            probe < len(strokes),
        )
        members = strokes[start_index : end_index + 1]
        segments.append(
            Line(
                len(segments),
                direction,
                start_fractal,
                end_fractal,
                max(item.high for item in members),
                min(item.low for item in members),
                probe < len(strokes),
            )
        )
        start_index = end_index
    return segments
