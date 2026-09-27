from dataclasses import dataclass
from decimal import Decimal
from .models import PortfolioState

@dataclass(frozen=True)
class TreasurySnapshot:
    total_equity_usd: Decimal
    cash_usd: Decimal
    invested_usd: Decimal
    target_amounts_usd: dict[str, Decimal]
    actual_amounts_usd: dict[str, Decimal]

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

    def snapshot(self, portfolio: PortfolioState, prices: dict[str, Decimal], actual_amounts_usd: dict[str, Decimal] | None = None) -> TreasurySnapshot:
        total_equity = portfolio.market_value_usd(prices)
        invested = total_equity - portfolio.cash_usd
        actual = dict(actual_amounts_usd or {})
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
        )

    def validate(self) -> None:
        if sum(self.allocations.values()) != Decimal("1.00"):
            raise ValueError("Treasury allocations must sum to 1.00")
        if any(value < 0 for value in self.allocations.values()):
            raise ValueError("Treasury allocations cannot be negative")

