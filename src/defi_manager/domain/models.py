from dataclasses import dataclass, field
from decimal import Decimal

@dataclass(frozen=True)
class ExecutionIntent:
    asset: str
    side: str
    quantity: Decimal
    price_usd: Decimal
    slippage_bps: int
    estimated_fee_usd: Decimal = Decimal("0")

    @property
    def notional_usd(self) -> Decimal:
        return self.quantity * self.price_usd

@dataclass
class Position:
    quantity: Decimal = Decimal("0")
    average_entry_usd: Decimal = Decimal("0")

@dataclass
class PortfolioState:
    cash_usd: Decimal = Decimal("0")
    positions: dict[str, Position] = field(default_factory=dict)

    def apply_fill(self, intent: ExecutionIntent) -> None:
        position = self.positions.setdefault(intent.asset, Position())
        total_cost = intent.notional_usd + intent.estimated_fee_usd
        if intent.side == "buy":
            if total_cost > self.cash_usd:
                raise ValueError("Insufficient simulated cash")
            combined_cost = position.quantity * position.average_entry_usd + intent.notional_usd
            position.quantity += intent.quantity
            position.average_entry_usd = combined_cost / position.quantity
            self.cash_usd -= total_cost
        elif intent.side == "sell":
            if intent.quantity > position.quantity:
                raise ValueError("Insufficient simulated asset balance")
            position.quantity -= intent.quantity
            self.cash_usd += intent.notional_usd - intent.estimated_fee_usd
        else:
            raise ValueError("side must be buy or sell")

    def market_value_usd(self, prices: dict[str, Decimal]) -> Decimal:
        return self.cash_usd + sum(p.quantity * prices.get(asset, Decimal("0")) for asset, p in self.positions.items())

@dataclass
class PnLTracker:
    realized_usd: Decimal = Decimal("0")
    fees_usd: Decimal = Decimal("0")

    def record_fill(self, portfolio: PortfolioState, intent: ExecutionIntent) -> None:
        position = portfolio.positions.get(intent.asset)
        if intent.side == "sell" and position is not None:
            self.realized_usd += (intent.price_usd - position.average_entry_usd) * intent.quantity - intent.estimated_fee_usd
        self.fees_usd += intent.estimated_fee_usd

