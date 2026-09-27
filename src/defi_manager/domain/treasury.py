from dataclasses import dataclass
from decimal import Decimal
from .models import PortfolioState

@dataclass(frozen=True)
class CapitalAllocation:
    module: str
    amount_usd: Decimal

    def __post_init__(self) -> None:
        if not self.module:
            raise ValueError("Capital allocation module is required")
        if self.amount_usd < 0:
            raise ValueError("Capital allocation cannot be negative")


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
        return cls({"trading": Decimal("0.20"), "lending": Decimal("0.30"), "staking": Decimal("0.20"), "liquidity": Decimal("0.15"), "reserve": Decimal("0.15")})

    def allocation_for(self, module: str) -> Decimal:
        if module not in self.allocations:
            raise KeyError(f"Unknown treasury module: {module}")
        return self.allocations[module]

    def snapshot(self, portfolio: PortfolioState, prices: dict[str, Decimal], actual_amounts_usd: dict[str, Decimal] | list[CapitalAllocation] | None = None) -> TreasurySnapshot:
        total_equity = portfolio.market_value_usd(prices)
        invested = total_equity - portfolio.cash_usd
        if isinstance(actual_amounts_usd, list):
            actual: dict[str, Decimal] = {}
            for allocation in actual_amounts_usd:
                actual[allocation.module] = actual.get(allocation.module, Decimal("0")) + allocation.amount_usd
        else:
            actual = dict(actual_amounts_usd or {})
        allocations = tuple(CapitalAllocation(module, amount) for module, amount in actual.items())
        if any(value < 0 for value in actual.values()):
            raise ValueError("Treasury actual allocations cannot be negative")
        if sum(actual.values()) > total_equity:
            raise ValueError("Treasury actual allocations cannot exceed total equity")
        return TreasurySnapshot(
            total_equity_usd=total_equity,
            cash_usd=portfolio.cash_usd,
            invested_usd=invested,
            target_amounts_usd={module: total_equity * allocation for module, allocation in self.allocations.items()},
            actual_amounts_usd=actual,
            allocations=allocations,
        )

    def validate(self) -> None:
        if sum(self.allocations.values()) != Decimal("1.00"):
            raise ValueError("Treasury allocations must sum to 1.00")
        if any(value < 0 for value in self.allocations.values()):
            raise ValueError("Treasury allocations cannot be negative")

