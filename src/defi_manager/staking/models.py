from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum


class StakingAction(StrEnum):
    MONITOR = "monitor"
    CLAIM_REWARDS = "claim_rewards"
    CLAIM_AND_RESTAKE = "claim_and_restake"
    DEFER_CLAIM = "defer_claim"


@dataclass(frozen=True)
class StakingSnapshot:
    protocol: str
    staked_usd: Decimal
    pending_rewards_usd: Decimal
    apr: Decimal
    apy: Decimal
    claim_gas_usd: Decimal
    restake_gas_usd: Decimal
    lock_remaining_days: int
    unstaking_delay_days: int

    def __post_init__(self) -> None:
        if any(value < 0 for value in (self.staked_usd, self.pending_rewards_usd, self.claim_gas_usd, self.restake_gas_usd)):
            raise ValueError("staking values cannot be negative")
        if self.apr < 0 or self.apy < 0:
            raise ValueError("APR and APY cannot be negative")
        if self.lock_remaining_days < 0 or self.unstaking_delay_days < 0:
            raise ValueError("staking durations cannot be negative")

    @property
    def annual_reward_usd(self) -> Decimal:
        return self.staked_usd * self.apy

    @property
    def net_claim_value_usd(self) -> Decimal:
        return self.pending_rewards_usd - self.claim_gas_usd


@dataclass(frozen=True)
class StakingPolicy:
    min_net_claim_usd: Decimal
    auto_restake: bool
    min_restake_net_usd: Decimal

    def __post_init__(self) -> None:
        if self.min_net_claim_usd < 0 or self.min_restake_net_usd < 0:
            raise ValueError("staking thresholds cannot be negative")


@dataclass(frozen=True)
class StakingDecision:
    action: StakingAction
    reason: str
    estimated_net_value_usd: Decimal

