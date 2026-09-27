from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum

class LiquidityAction(StrEnum):
    MONITOR = "monitor"
    AVOID_POOL = "avoid_pool"
    CONSIDER_LIQUIDITY = "consider_liquidity"

@dataclass(frozen=True)
class PoolSnapshot:
    protocol: str
    pool: str
    tvl_usd: Decimal
    available_liquidity_usd: Decimal
    fee_apy: Decimal
    reward_apy: Decimal
    volatility: Decimal
    price_ratio_change: Decimal
    planned_allocation_usd: Decimal
    gas_usd: Decimal
    insurance_cost_usd: Decimal

    def __post_init__(self) -> None:
        if any(value < 0 for value in (self.tvl_usd, self.available_liquidity_usd, self.fee_apy, self.reward_apy, self.volatility, self.planned_allocation_usd, self.gas_usd, self.insurance_cost_usd)):
            raise ValueError("pool amounts cannot be negative")

    @property
    def impermanent_loss(self) -> Decimal:
        ratio = self.price_ratio_change
        if ratio <= 0:
            raise ValueError("price_ratio_change must be positive")
        return (Decimal("2") * ratio.sqrt() / (Decimal("1") + ratio)) - Decimal("1")

@dataclass(frozen=True)
class LiquidityPolicy:
    min_tvl_usd: Decimal
    min_liquidity_usd: Decimal
    max_volatility: Decimal
    min_estimated_net_yield: Decimal

@dataclass(frozen=True)
class LiquidityDecision:
    action: LiquidityAction
    reason: str
    estimated_net_yield: Decimal
