"""顶底分型识别。"""

from .models import ChanBar, Fractal


def find_fractals(bars: list[ChanBar]) -> list[Fractal]:
    """识别严格顶底分型，并保证最终序列顶底交替。"""
    candidates: list[Fractal] = []
    for index in range(1, len(bars) - 1):
        left, middle, right = bars[index - 1 : index + 2]
        is_top = middle.high > left.high and middle.high > right.high
        is_bottom = middle.low < left.low and middle.low < right.low
        if is_top:
            candidates.append(
                Fractal(
                    len(candidates),
                    "top",
                    index,
                    middle.high,
                    left,
                    middle,
                    right,
                )
            )
        elif is_bottom:
            candidates.append(
                Fractal(
                    len(candidates),
                    "bottom",
                    index,
                    middle.low,
                    left,
                    middle,
                    right,
                )
            )

    result: list[Fractal] = []
    for fractal in candidates:
        if result and result[-1].kind == fractal.kind:
            better = (
                fractal.value >= result[-1].value
                if fractal.kind == "top"
                else fractal.value <= result[-1].value
            )
            if better:
                result[-1] = fractal
            continue
        result.append(fractal)

    for index, fractal in enumerate(result):
        fractal.index = index
    return result
