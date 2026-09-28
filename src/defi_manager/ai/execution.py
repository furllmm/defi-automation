from dataclasses import dataclass
from decimal import Decimal

from defi_manager.ai.engine import AIProposal, AIEngine
from defi_manager.core.events import Event, EventBus
from defi_manager.domain.models import PortfolioState
from defi_manager.domain.risk import RiskDecision
from defi_manager.execution import Executor


@dataclass(frozen=True)
class AIExecutionResult:
    proposal: AIProposal
    decision: RiskDecision


class AIExecutionCoordinator:
    """Connects AI proposals to the normal execution boundary.

    The AI engine only produces data. This coordinator hands the resulting intent
    to an executor, whose implementation owns safety/risk enforcement. Every
    proposal and final execution decision is published to the audit/event stream.
    """

    def __init__(self, ai: AIEngine, executor: Executor, events: EventBus) -> None:
        self._ai = ai
        self._executor = executor
        self._events = events

    def propose_and_execute(
        self,
        portfolio: PortfolioState,
        *,
        asset: str,
        price_usd: Decimal,
        quantity: Decimal = Decimal("1"),
        slippage_bps: int = 0,
    ) -> list[AIExecutionResult]:
        proposals = self._ai.propose(
            portfolio,
            asset=asset,
            price_usd=price_usd,
            quantity=quantity,
            slippage_bps=slippage_bps,
        )
        results: list[AIExecutionResult] = []
        for proposal in proposals:
            intent = proposal.intent
            self._events.publish(
                Event(
                    "ai.proposal",
                    {
                        "asset": intent.asset,
                        "side": intent.side,
                        "quantity": str(intent.quantity),
                        "price_usd": str(intent.price_usd),
                        "notional_usd": str(intent.notional_usd),
                        "slippage_bps": intent.slippage_bps,
                        "reason": proposal.reason,
                    },
                )
            )
            decision = self._executor.execute(intent)
            self._events.publish(
                Event(
                    "ai.execution.decision",
                    {
                        "asset": intent.asset,
                        "side": intent.side,
                        "quantity": str(intent.quantity),
                        "allowed": decision.allowed,
                        "reason": decision.reason,
                    },
                )
            )
            results.append(AIExecutionResult(proposal=proposal, decision=decision))
        return results
