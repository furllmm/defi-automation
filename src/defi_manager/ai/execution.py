from dataclasses import dataclass

from defi_manager.ai.engine import AIProposal, AIEngine
from defi_manager.domain.risk import RiskDecision
from defi_manager.domain.models import PortfolioState
from defi_manager.execution import Executor


@dataclass(frozen=True)
class AIExecutionResult:
    proposal: AIProposal
    decision: RiskDecision


class AIExecutionCoordinator:
    """Connects AI proposals to the normal execution boundary.

    The AI engine only produces data. This coordinator hands the resulting intent
    to an executor, whose implementation owns safety/risk enforcement.
    """

    def __init__(self, ai: AIEngine, executor: Executor) -> None:
        self._ai = ai
        self._executor = executor

    def propose_and_execute(
        self,
        portfolio: PortfolioState,
        *,
        asset: str,
        price_usd,
        quantity=1,
        slippage_bps: int = 0,
    ) -> list[AIExecutionResult]:
        proposals = self._ai.propose(
            portfolio,
            asset=asset,
            price_usd=price_usd,
            quantity=quantity,
            slippage_bps=slippage_bps,
        )
        return [
            AIExecutionResult(
                proposal=proposal,
                decision=self._executor.execute(proposal.intent),
            )
            for proposal in proposals
        ]
