from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class Candle:
    timestamp: datetime
    close_usd: Decimal
    open_usd: Decimal | None = None
    high_usd: Decimal | None = None
    low_usd: Decimal | None = None
    volume: Decimal | None = None

    def __post_init__(self) -> None:
        if self.close_usd <= 0:
            raise ValueError("close_usd must be positive")
        for name in ("open_usd", "high_usd", "low_usd", "volume"):
            value = getattr(self, name)
            if value is not None and value < 0:
                raise ValueError(f"{name} cannot be negative")
        if self.high_usd is not None and self.low_usd is not None and self.high_usd < self.low_usd:
            raise ValueError("high_usd cannot be below low_usd")


class MarketDataProvider(Protocol):
    """Read-only market-data contract. Providers must not execute trades."""

    def candles(self, asset: str, start: datetime, end: datetime) -> list[Candle]: ...


class InMemoryMarketDataProvider:
    def __init__(self, data: dict[str, list[Candle]]) -> None:
        self._data = {asset: sorted(candles, key=lambda candle: candle.timestamp) for asset, candles in data.items()}

    def candles(self, asset: str, start: datetime, end: datetime) -> list[Candle]:
        if start >= end:
            raise ValueError("start must be before end")
        return [
            candle
            for candle in self._data.get(asset, [])
            if start <= candle.timestamp < end
        ]


class CsvMarketDataProvider:
    """Dependency-free OHLCV loader for deterministic local backtests."""

    REQUIRED_COLUMNS = {"timestamp", "close_usd"}

    def __init__(self, directory: Path) -> None:
        self._directory = directory

    def candles(self, asset: str, start: datetime, end: datetime) -> list[Candle]:
        if start >= end:
            raise ValueError("start must be before end")
        path = self._directory / f"{asset}.csv"
        if not path.is_file():
            raise FileNotFoundError(path)

        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            columns = set(reader.fieldnames or ())
            missing = self.REQUIRED_COLUMNS - columns
            if missing:
                raise ValueError(f"missing CSV columns: {sorted(missing)}")

            result: list[Candle] = []
            for row_number, row in enumerate(reader, start=2):
                try:
                    candle = Candle(
                        timestamp=datetime.fromisoformat(row["timestamp"]),
                        close_usd=Decimal(row["close_usd"]),
                        open_usd=_optional_decimal(row.get("open_usd")),
                        high_usd=_optional_decimal(row.get("high_usd")),
                        low_usd=_optional_decimal(row.get("low_usd")),
                        volume=_optional_decimal(row.get("volume")),
                    )
                except (KeyError, ValueError, ArithmeticError) as exc:
                    raise ValueError(f"invalid market-data row {row_number} in {path.name}") from exc
                if start <= candle.timestamp < end:
                    result.append(candle)
        return sorted(result, key=lambda candle: candle.timestamp)


def _optional_decimal(value: str | None) -> Decimal | None:
    if value is None or value == "":
        return None
    return Decimal(value)
