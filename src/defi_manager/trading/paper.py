from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from defi_manager.domain.models import ExecutionIntent
from defi_manager.domain.risk import RiskDecision
from defi_manager.simulation.environment import SimulationEnvironment
from defi_manager.trading.market import Candle
from defi_manager.trading.strategy import Signal, Strategy


@dataclass(frozen=True)
class PaperExecutionConfig:
    """Deterministic execution parameters for paper trading only."""

    fee_bps: int = 0
    slippage_bps: int = 0
    position_size_fraction: Decimal = Decimal("1")

    def __post_init__(self) -> None:
        if self.fee_bps < 0 or self.slippage_bps < 0:
            raise ValueError("fees and slippage cannot be negative")
        if not Decimal("0") < self.position_size_fraction <= Decimal("1"):
            raise ValueError("position_size_fraction must be in (0, 1]")


@dataclass(frozen=True)
class PaperStepResult:
    signal: Signal
    intent: ExecutionIntent | None
    decision: RiskDecision | None


class PaperTradingEngine:
    """Connects a strategy to the existing safety/risk-gated simulation.

    This engine never signs or broadcasts a blockchain transaction.
    """

    def __init__(self, simulation: SimulationEnvironment, config: PaperExecutionConfig) -> None:
        self._simulation = simulation
        self._config = config

    def step(self, asset: str, candles: list[Candle], strategy: Strategy) -> PaperStepResult:
        if not candles:
            raise ValueError("at least one candle is required")

        signal = strategy.evaluate(candles)
        if signal.action == "hold":
            return PaperStepResult(signal, None, None)
        if signal.action not in {"buy", "sell"}:
            return PaperStepResult(signal, None, RiskDecision(False, "unsupported signal action"))

        if signal.action == "buy":
            return self._buy(asset, candles[-1].close_usd, signal)
        return self._sell(asset, candles[-1].close_usd, signal)

    def _buy(self, asset: str, close: Decimal, signal: Signal) -> PaperStepResult:
        portfolio = self._simulation.portfolio
        if portfolio.cash_usd <= 0:
            return PaperStepResult(signal, None, RiskDecision(False, "insufficient simulated cash"))

        budget = portfolio.cash_usd * self._config.position_size_fraction
        price = close * (Decimal("1") + Decimal(self._config.slippage_bps) / Decimal("10000"))
        quantity = budget / (price * (Decimal("1") + Decimal(self._config.fee_bps) / Decimal("10000")))
        fee = quantity * price * Decimal(self._config.fee_bps) / Decimal("10000")
        intent = ExecutionIntent(asset, "buy", quantity, price, self._config.slippage_bps, fee)
        return PaperStepResult(signal, intent, self._simulation.execute(intent))

    def _sell(self, asset: str, close: Decimal, signal: Signal) -> PaperStepResult:
        portfolio = self._simulation.portfolio
        position = portfolio.positions.get(asset)
        if position is None or position.quantity <= 0:
            return PaperStepResult(signal, None, RiskDecision(False, "no simulated position to sell"))

        price = close * (Decimal("1") - Decimal(self._config.slippage_bps) / Decimal("10000"))
        fee = position.quantity * price * Decimal(self._config.fee_bps) / Decimal("10000")
        intent = ExecutionIntent(asset, "sell", position.quantity, price, self._config.slippage_bps, fee)
        return PaperStepResult(signal, intent, self._simulation.execute(intent))
