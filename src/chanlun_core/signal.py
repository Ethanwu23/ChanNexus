"""背驰和买卖点信号计算。"""

from .models import Line, Pivot, Signal


def _line_strength(line: Line) -> float:
    span = max(1, line.end.raw_end_index - line.start.raw_start_index)
    return abs(line.end.value - line.start.value) / span


def attach_signals(lines: list[Line], pivots: list[Pivot]) -> None:
    """根据中枢进入、离开和回抽线生成当前基线信号。"""
    for line in lines:
        line.signals.clear()
        line.divergences.clear()

    for pivot in pivots:
        first_index = pivot.lines[0].index
        last_index = pivot.lines[-1].index
        if first_index > 0 and last_index + 1 < len(lines):
            enter = lines[first_index - 1]
            leave = lines[last_index + 1]
            same_direction = enter.direction == leave.direction
            new_extreme = (
                leave.low < enter.low
                if leave.direction == "down"
                else leave.high > enter.high
            )
            weaker = _line_strength(leave) < _line_strength(enter)
            if same_direction and new_extreme and weaker:
                name = "1buy" if leave.direction == "down" else "1sell"
                leave.divergences.append(
                    Signal("pz", "离开段相对进入段力度减弱", pivot.index)
                )
                leave.signals.append(
                    Signal(name, "中枢离开段盘整背驰", pivot.index)
                )

        if last_index + 2 < len(lines):
            leave = lines[last_index + 1]
            pullback = lines[last_index + 2]
            if leave.direction == "up" and pullback.low > pivot.zg:
                pullback.signals.append(
                    Signal("3buy", "向上离开后回抽不进中枢", pivot.index)
                )
                pivot.done = True
            elif leave.direction == "down" and pullback.high < pivot.zd:
                pullback.signals.append(
                    Signal("3sell", "向下离开后反抽不进中枢", pivot.index)
                )
                pivot.done = True
