from dataclasses import dataclass
from decimal import Decimal

from defi_manager.core.events import Event, EventBus
from defi_manager.domain.models import PortfolioState
from defi_manager.domain.risk import RiskManager
from defi_manager.domain.treasury import AllocationChange, Treasury


@dataclass
class TreasuryService:
    treasury: Treasury
    risk: RiskManager
    events: EventBus

    def rebalance(
        self,
        portfolio: PortfolioState,
        actual_amounts_usd: dict[str, Decimal],
        changes: tuple[AllocationChange, ...],
        total_equity_usd: Decimal,
    ) -> dict[str, Decimal]:
        projected = self.treasury.project_rebalance(actual_amounts_usd, changes)
        current_allocated = sum(actual_amounts_usd.values(), Decimal("0"))

        decision = self.risk.evaluate_treasury_rebalance(
            projected,
            total_equity_usd,
            portfolio.cash_usd,
            current_allocated,
        )
        self.events.publish(
            Event(
                "treasury.rebalance.risk",
                {
                    "allowed": decision.allowed,
                    "reason": decision.reason,
                    "current_allocated_usd": str(current_allocated),
                    "projected_allocated_usd": str(sum(projected.values(), Decimal("0"))),
                },
            )
        )
        if not decision.allowed:
            raise ValueError(f"Treasury rebalance rejected: {decision.reason}")

        result = self.treasury.apply_rebalance(portfolio, actual_amounts_usd, changes)
        self.events.publish(
            Event(
                "treasury.rebalance.applied",
                {"allocations_usd": {module: str(amount) for module, amount in result.items()}},
            )
        )
        return result
