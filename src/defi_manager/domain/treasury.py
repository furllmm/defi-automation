from dataclasses import dataclass
from decimal import Decimal

from .models import PortfolioState
from .risk import RiskManager


@dataclass(frozen=True)
class CapitalAllocation:
    module: str
    amount_usd: Decimal

    def __post_init__(self) -> None:
        if not self.module:
            raise ValueError("module is required")
        if self.amount_usd < 0:
            raise ValueError("allocation amount cannot be negative")


@dataclass(frozen=True)
class AllocationChange:
    module: str
    amount_usd: Decimal

    def __post_init__(self) -> None:
        if not self.module:
            raise ValueError("module is required")
        if self.amount_usd == 0:
            raise ValueError("allocation change cannot be zero")


@dataclass(frozen=True)
class TreasurySnapshot:
    total_equity_usd: Decimal
    cash_usd: Decimal
    invested_usd: Decimal
    target_amounts_usd: dict[str, Decimal]
    actual_amounts_usd: dict[str, Decimal]
    allocations: tuple[CapitalAllocation, ...] = ()

    def actual_allocation(self, module: str) -> Decimal:
        return self.actual_amounts_usd.get(module, Decimal("0"))


@dataclass(frozen=True)
class Treasury:
    allocations: dict[str, Decimal]

    @classmethod
    def default(cls) -> "Treasury":
        return cls(
            {
                "trading": Decimal("0.20"),
                "lending": Decimal("0.30"),
                "staking": Decimal("0.20"),
                "liquidity": Decimal("0.15"),
                "reserve": Decimal("0.15"),
            }
        )

    def allocation_for(self, module: str) -> Decimal:
        if module not in self.allocations:
            raise KeyError(f"Unknown treasury module: {module}")
        return self.allocations[module]

    def apply_change(
        self,
        actual_amounts_usd: dict[str, Decimal],
        change: AllocationChange,
    ) -> dict[str, Decimal]:
        actual = dict(actual_amounts_usd)
        current = actual.get(change.module, Decimal("0"))
        updated = current + change.amount_usd
        if updated < 0:
            raise ValueError("allocation cannot become negative")
        if updated == 0:
            actual.pop(change.module, None)
        else:
            actual[change.module] = updated
        return actual

    def project_rebalance(
        self,
        actual_amounts_usd: dict[str, Decimal],
        changes: tuple[AllocationChange, ...],
    ) -> dict[str, Decimal]:
        if not changes:
            raise ValueError("rebalance requires at least one change")

        projected = dict(actual_amounts_usd)
        for change in changes:
            projected = self.apply_change(projected, change)
        return projected

    def _transfer(
        self,
        portfolio: PortfolioState,
        actual_amounts_usd: dict[str, Decimal],
        change: AllocationChange,
    ) -> dict[str, Decimal]:
        if change.amount_usd > 0:
            if change.amount_usd > portfolio.cash_usd:
                raise ValueError("insufficient cash for allocation")
            portfolio.cash_usd -= change.amount_usd
        else:
            release = -change.amount_usd
            current = actual_amounts_usd.get(change.module, Decimal("0"))
            if release > current:
                raise ValueError("insufficient module allocation for deallocation")
            portfolio.cash_usd += release

        return self.apply_change(actual_amounts_usd, change)

    def rebalance(
        self,
        portfolio: PortfolioState,
        actual_amounts_usd: dict[str, Decimal],
        changes: tuple[AllocationChange, ...],
        risk_manager: RiskManager,
        total_equity_usd: Decimal,
    ) -> dict[str, Decimal]:
        projected = self.project_rebalance(actual_amounts_usd, changes)
        current_allocated = sum(actual_amounts_usd.values(), Decimal("0"))

        decision = risk_manager.evaluate_treasury_rebalance(
            projected,
            total_equity_usd,
            portfolio.cash_usd,
            current_allocated,
        )
        if not decision.allowed:
            raise ValueError(f"Treasury rebalance rejected: {decision.reason}")

        cash_before = portfolio.cash_usd
        working = dict(actual_amounts_usd)
        try:
            # Release capital before allocating new capital so a valid net
            # rebalance does not fail because of its intermediate order.
            ordered_changes = tuple(
                sorted(changes, key=lambda change: change.amount_usd > 0)
            )
            for change in ordered_changes:
                working = self._transfer(portfolio, working, change)
            return working
        except Exception:
            portfolio.cash_usd = cash_before
            raise

    def snapshot(
        self,
        portfolio: PortfolioState,
        prices: dict[str, Decimal],
        actual_amounts_usd: dict[str, Decimal] | list[CapitalAllocation] | None = None,
    ) -> TreasurySnapshot:
        total_equity = portfolio.market_value_usd(prices)
        invested = total_equity - portfolio.cash_usd

        if isinstance(actual_amounts_usd, list):
            actual: dict[str, Decimal] = {}
            for allocation in actual_amounts_usd:
                actual[allocation.module] = (
                    actual.get(allocation.module, Decimal("0")) + allocation.amount_usd
                )
        else:
            actual = dict(actual_amounts_usd or {})

        allocations = tuple(
            CapitalAllocation(module, amount) for module, amount in actual.items()
        )
        if any(value < 0 for value in actual.values()):
            raise ValueError("Treasury actual allocations cannot be negative")
        if sum(actual.values()) > total_equity:
            raise ValueError("Treasury actual allocations cannot exceed total equity")

        return TreasurySnapshot(
            total_equity_usd=total_equity,
            cash_usd=portfolio.cash_usd,
            invested_usd=invested,
            target_amounts_usd={
                module: total_equity * allocation
                for module, allocation in self.allocations.items()
            },
            actual_amounts_usd=actual,
            allocations=allocations,
        )

    def validate(self) -> None:
        if sum(self.allocations.values()) != Decimal("1.00"):
            raise ValueError("Treasury allocations must sum to 1.00")
        if any(value < 0 for value in self.allocations.values()):
            raise ValueError("Treasury allocations cannot be negative")
