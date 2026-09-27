from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

@dataclass(frozen=True)
class Candle:
    timestamp: datetime
    close_usd: Decimal

    def __post_init__(self) -> None:
        if self.close_usd <= 0:
            raise ValueError("close_usd must be positive")

