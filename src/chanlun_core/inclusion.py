"""K线包含关系处理。"""

from collections.abc import Iterable

from .models import Bar, ChanBar


def _contains(one: ChanBar, two: ChanBar) -> bool:
    return (one.high >= two.high and one.low <= two.low) or (
        two.high >= one.high and two.low <= one.low
    )


def merge_inclusions(bars: Iterable[Bar]) -> list[ChanBar]:
    """按当前趋势方向合并存在包含关系的相邻K线。"""
    result: list[ChanBar] = []
    for bar in bars:
        current = ChanBar(
            len(result),
            bar.high,
            bar.low,
            bar.open,
            bar.close,
            bar.volume,
            [bar],
        )
        if not result or not _contains(result[-1], current):
            result.append(current)
            continue

        previous = result[-1]
        if len(result) >= 2:
            upward = previous.high >= result[-2].high
        else:
            upward = bar.close >= previous.close
        previous.high = (
            max(previous.high, bar.high)
            if upward
            else min(previous.high, bar.high)
        )
        previous.low = (
            max(previous.low, bar.low)
            if upward
            else min(previous.low, bar.low)
        )
        previous.close = bar.close
        previous.volume += bar.volume
        previous.bars.append(bar)

    for index, bar in enumerate(result):
        bar.index = index
    return result
