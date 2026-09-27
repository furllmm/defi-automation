from dataclasses import dataclass
from decimal import Decimal

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

    def validate(self) -> None:
        if sum(self.allocations.values()) != Decimal("1.00"):
            raise ValueError("Treasury allocations must sum to 1.00")
        if any(value < 0 for value in self.allocations.values()):
            raise ValueError("Treasury allocations cannot be negative")

