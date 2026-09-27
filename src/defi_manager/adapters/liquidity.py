from typing import Protocol
from defi_manager.liquidity.models import PoolSnapshot

class LiquidityAdapter(Protocol):
    """Read-only pool discovery/inspection contract."""
    def snapshot(self) -> PoolSnapshot: ...

class FixedLiquidityAdapter:
    def __init__(self, snapshot: PoolSnapshot) -> None:
        self._snapshot = snapshot
    def snapshot(self) -> PoolSnapshot:
        return self._snapshot

