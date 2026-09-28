from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from defi_manager.adapters.dex import SwapQuote
from defi_manager.domain.models import ExecutionIntent
from defi_manager.domain.preflight import ExecutionPreflight
from defi_manager.domain.risk import RiskDecision
from defi_manager.simulation.environment import SimulationEnvironment


class Executor(Protocol):
    def execute(self, intent: ExecutionIntent) -> RiskDecision: ...


class QuoteAwareExecutor(Protocol):
    def execute_with_quote(self, quote: SwapQuote, intent: ExecutionIntent) -> RiskDecision: ...


@dataclass
class PaperExecutor:
    simulation: SimulationEnvironment
    preflight: ExecutionPreflight | None = None

    def execute(self, intent: ExecutionIntent) -> RiskDecision:
        return self.simulation.execute(intent)

    def execute_with_quote(self, quote: SwapQuote, intent: ExecutionIntent) -> RiskDecision:
        if self.preflight is None:
            return RiskDecision(False, "preflight is required for quote-aware execution")
        return self.simulation.execute_with_preflight(quote, intent, self.preflight)


class LiveExecutor:
    """Placeholder for future controlled live execution."""

    def execute(self, intent: ExecutionIntent) -> RiskDecision:
        return RiskDecision(False, "live execution is disabled")

    def execute_with_quote(self, quote: SwapQuote, intent: ExecutionIntent) -> RiskDecision:
        return RiskDecision(False, "live execution is disabled")
