from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from defi_manager.trading.market import Candle

@dataclass(frozen=True)
class Signal:
    action: str
    reason: str

    @classmethod
    def hold(cls, reason: str = "no action") -> "Signal":
        return cls("hold", reason)

class Strategy(Protocol):
    name: str
    def evaluate(self, candles: list[Candle]) -> Signal: ...

class StrategyRegistry:
    def __init__(self) -> None:
        self._strategies: dict[str, Strategy] = {}

    def register(self, strategy: Strategy) -> None:
        if strategy.name in self._strategies:
            raise ValueError(f"strategy already registered: {strategy.name}")
        self._strategies[strategy.name] = strategy

    def get(self, name: str) -> Strategy:
        return self._strategies[name]

@dataclass(frozen=True)
class MovingAverageCrossStrategy:
    fast_period: int
    slow_period: int
    name: str = "ma-crossover"

    def __post_init__(self) -> None:
        if not 0 < self.fast_period < self.slow_period:
            raise ValueError("fast_period must be positive and smaller than slow_period")

    def evaluate(self, candles: list[Candle]) -> Signal:
        if len(candles) < self.slow_period + 1:
            return Signal.hold("insufficient history")
        previous = candles[:-1]
        previous_fast = _average(previous[-self.fast_period:])
        previous_slow = _average(previous[-self.slow_period:])
        current_fast = _average(candles[-self.fast_period:])
        current_slow = _average(candles[-self.slow_period:])
        if previous_fast <= previous_slow and current_fast > current_slow:
            return Signal("buy", "fast moving average crossed above slow moving average")
        if previous_fast >= previous_slow and current_fast < current_slow:
            return Signal("sell", "fast moving average crossed below slow moving average")
        return Signal.hold()

def _average(candles: list[Candle]) -> Decimal:
    return sum(candle.close_usd for candle in candles) / Decimal(len(candles))


@dataclass(frozen=True)
class RsiStrategy:
    period: int = 14
    oversold: Decimal = Decimal("30")
    overbought: Decimal = Decimal("70")
    name: str = "rsi"

    def __post_init__(self) -> None:
        if self.period <= 0:
            raise ValueError("period must be positive")
        if not Decimal("0") < self.oversold < self.overbought < Decimal("100"):
            raise ValueError("RSI thresholds must satisfy 0 < oversold < overbought < 100")

    def evaluate(self, candles: list[Candle]) -> Signal:
        if len(candles) < self.period + 1:
            return Signal.hold("insufficient history")
        rsi = _rsi(candles[-(self.period + 1) :])
        if rsi <= self.oversold:
            return Signal("buy", f"RSI oversold at {rsi:.2f}")
        if rsi >= self.overbought:
            return Signal("sell", f"RSI overbought at {rsi:.2f}")
        return Signal.hold(f"RSI neutral at {rsi:.2f}")


def _rsi(candles: list[Candle]) -> Decimal:
    changes = [right.close_usd - left.close_usd for left, right in zip(candles, candles[1:])]
    gains = sum((change for change in changes if change > 0), Decimal("0"))
    losses = -sum((change for change in changes if change < 0), Decimal("0"))
    if losses == 0:
        return Decimal("100") if gains > 0 else Decimal("50")
    relative_strength = (gains / Decimal(len(changes))) / (losses / Decimal(len(changes)))
    return Decimal("100") - Decimal("100") / (Decimal("1") + relative_strength)
