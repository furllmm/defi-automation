from typing import Protocol

from defi_manager.staking.models import StakingSnapshot


class StakingAdapter(Protocol):
    """Read-only protocol contract; stake, unstake, claim, and restake are excluded."""

    def snapshot(self) -> StakingSnapshot: ...


class FixedStakingAdapter:
    """Deterministic local adapter for tests and simulation."""

    def __init__(self, snapshot: StakingSnapshot) -> None:
        self._snapshot = snapshot

    def snapshot(self) -> StakingSnapshot:
        return self._snapshot

