from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class LendingAction(StrEnum):
    MONITOR = "monitor"
    BLOCK_NEW_DEBT = "block_new_debt"
    DELEVERAGE = "deleveraging_required"
    EMERGENCY_REPAY = "emergency_repay_required"


@dataclass(frozen=True)
class LendingSnapshot:
    protocol: str
    collateral_usd: Decimal
    debt_usd: Decimal
    liquidation_threshold: Decimal
    supply_apy: Decimal
    borrow_apy: Decimal
    available_liquidity_usd: Decimal

    def __post_init__(self) -> None:
        if self.collateral_usd < 0 or self.debt_usd < 0 or self.available_liquidity_usd < 0:
            raise ValueError("lending balances and liquidity cannot be negative")
        if not Decimal("0") < self.liquidation_threshold <= Decimal("1"):
            raise ValueError("liquidation_threshold must be in (0, 1]")

    @property
    def ltv(self) -> Decimal:
        return Decimal("0") if self.collateral_usd == 0 else self.debt_usd / self.collateral_usd

    @property
    def health_factor(self) -> Decimal:
        if self.debt_usd == 0:
            return Decimal("Infinity")
        return (self.collateral_usd * self.liquidation_threshold) / self.debt_usd

    @property
    def annual_net_yield_usd(self) -> Decimal:
        return self.collateral_usd * self.supply_apy - self.debt_usd * self.borrow_apy


@dataclass(frozen=True)
class LendingPolicy:
    max_ltv: Decimal
    min_health_factor: Decimal
    emergency_health_factor: Decimal
    max_debt_usd: Decimal
    min_liquidity_usd: Decimal

    def __post_init__(self) -> None:
        if not Decimal("0") < self.max_ltv < Decimal("1"):
            raise ValueError("max_ltv must be in (0, 1)")
        if not Decimal("1") < self.emergency_health_factor < self.min_health_factor:
            raise ValueError("health factor thresholds must satisfy 1 < emergency < minimum")
        if self.max_debt_usd < 0 or self.min_liquidity_usd < 0:
            raise ValueError("debt and liquidity limits cannot be negative")


@dataclass(frozen=True)
class LendingDecision:
    action: LendingAction
    reason: str
    suggested_repay_usd: Decimal = Decimal("0")

