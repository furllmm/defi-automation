from dataclasses import dataclass
from decimal import Decimal

from defi_manager.domain.models import ExecutionIntent, PortfolioState


@dataclass(frozen=True)
class AIProposal:
    """An AI-generated intent plus human-readable rationale.

    The proposal is data only. It has no executor, wallet, signer, or risk-manager
    access and therefore cannot execute a transaction by itself.
    """

    intent: ExecutionIntent
    reason: str


class AIEngine:
    """Phase-1 deterministic AI boundary.

    This is intentionally a placeholder for a future model-backed strategy engine.
    It may propose intents, but execution remains outside the AI layer.
    """

    def propose(
        self,
        portfolio: PortfolioState,
        *,
        asset: str,
        price_usd: Decimal,
        quantity: Decimal = Decimal("1"),
        slippage_bps: int = 0,
    ) -> list[AIProposal]:
        if portfolio.cash_usd <= 0:
            return []

        intent = ExecutionIntent(
            asset=asset,
            side="buy",
            quantity=quantity,
            price_usd=price_usd,
            slippage_bps=slippage_bps,
        )
        return [
            AIProposal(
                intent=intent,
                reason="phase-1 simulation proposal",
            )
        ]
