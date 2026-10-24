from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RiskPolicy:
    """与形态计算解耦的仓位和风控策略。"""

    max_position_fraction: float = 0.2
    stop_loss_fraction: float = 0.05
    take_profit_fraction: float | None = None
    min_cash_reserve_fraction: float = 0.1

    def __post_init__(self) -> None:
        for name in ("max_position_fraction", "stop_loss_fraction", "min_cash_reserve_fraction"):
            value = getattr(self, name)
            if not 0 < value < 1:
                raise ValueError(f"{name} 必须在 (0, 1) 内")

    def order_size(self, equity: float, cash: float, price: float, lot_size: int = 1) -> int:
        if min(equity, cash, price, lot_size) <= 0:
            return 0
        budget = min(equity * self.max_position_fraction, cash - equity * self.min_cash_reserve_fraction)
        return max(0, int(budget / price / lot_size) * lot_size)

    def should_exit_long(self, entry: float, current: float) -> str | None:
        if current <= entry * (1 - self.stop_loss_fraction):
            return "stop_loss"
        if self.take_profit_fraction is not None and current >= entry * (1 + self.take_profit_fraction):
            return "take_profit"
        return None
