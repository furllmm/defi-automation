from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from defi_manager.domain.models import ExecutionIntent
from defi_manager.domain.risk import RiskDecision
from defi_manager.simulation.environment import SimulationEnvironment


class Executor(Protocol):
    def execute(self, intent: ExecutionIntent) -> RiskDecision: ...


@dataclass
class PaperExecutor:
    simulation: SimulationEnvironment

    def execute(self, intent: ExecutionIntent) -> RiskDecision:
        return self.simulation.execute(intent)


class LiveExecutor:
    """Placeholder for future controlled live execution.

    This intentionally cannot submit transactions yet.
    """

    def execute(self, intent: ExecutionIntent) -> RiskDecision:
        return RiskDecision(False, "live execution is disabled")
