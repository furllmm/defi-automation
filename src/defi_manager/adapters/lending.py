from decimal import Decimal
from typing import Protocol

from defi_manager.lending.models import LendingSnapshot


class LendingAdapter(Protocol):
    """Read-only protocol contract; supply/borrow/repay submission is excluded."""

    def snapshot(self) -> LendingSnapshot: ...


class FixedLendingAdapter:
    """Deterministic local adapter for tests and simulation."""

    def __init__(self, snapshot: LendingSnapshot) -> None:
        self._snapshot = snapshot

    def snapshot(self) -> LendingSnapshot:
        return self._snapshot

