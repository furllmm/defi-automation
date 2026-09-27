from __future__ import annotations

import csv
import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
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


class BinanceMarketDataProvider:
    """Read-only OHLCV adapter for Binance public market data.

    The adapter only calls the public klines endpoint; it has no order or
    account-management capability. Asset names are mapped explicitly to
    symbols to avoid turning user input into arbitrary API paths.
    """

    INTERVALS_MS = {
        "1m": 60_000,
        "5m": 300_000,
        "15m": 900_000,
        "1h": 3_600_000,
        "4h": 14_400_000,
        "1d": 86_400_000,
    }

    def __init__(
        self,
        symbols: dict[str, str],
        interval: str = "1h",
        base_url: str = "https://api.binance.com/api/v3/klines",
        timeout_seconds: float = 10.0,
        max_pages: int = 100,
    ) -> None:
        if interval not in self.INTERVALS_MS:
            raise ValueError(f"unsupported interval: {interval}")
        if timeout_seconds <= 0 or max_pages <= 0:
            raise ValueError("timeout_seconds and max_pages must be positive")
        self._symbols = dict(symbols)
        self._interval = interval
        self._base_url = base_url
        self._timeout = timeout_seconds
        self._max_pages = max_pages

    def candles(self, asset: str, start: datetime, end: datetime) -> list[Candle]:
        if start >= end:
            raise ValueError("start must be before end")
        if start.tzinfo is None or end.tzinfo is None:
            raise ValueError("start and end must be timezone-aware")
        try:
            symbol = self._symbols[asset]
        except KeyError as exc:
            raise ValueError(f"unknown Binance symbol mapping for {asset}") from exc

        start_ms = int(start.timestamp() * 1000)
        end_ms = int(end.timestamp() * 1000)
        step_ms = self.INTERVALS_MS[self._interval]
        result: list[Candle] = []
        cursor_ms = start_ms

        for _ in range(self._max_pages):
            if cursor_ms >= end_ms:
                break
            query = urlencode({
                "symbol": symbol.upper(),
                "interval": self._interval,
                "startTime": cursor_ms,
                "endTime": end_ms - 1,
                "limit": 1000,
            })
            request = Request(
                f"{self._base_url}?{query}",
                headers={"Accept": "application/json", "User-Agent": "ai-defi-manager/0.1"},
            )
            with urlopen(request, timeout=self._timeout) as response:
                payload = json.load(response)
            if not isinstance(payload, list):
                raise ValueError("Binance returned an invalid klines payload")
            if not payload:
                break

            for row in payload:
                if not isinstance(row, list) or len(row) < 6:
                    raise ValueError("Binance returned an invalid kline row")
                timestamp = datetime.fromtimestamp(int(row[0]) / 1000, tz=UTC)
                if start <= timestamp < end:
                    result.append(
                        Candle(
                            timestamp=timestamp,
                            open_usd=Decimal(str(row[1])),
                            high_usd=Decimal(str(row[2])),
                            low_usd=Decimal(str(row[3])),
                            close_usd=Decimal(str(row[4])),
                            volume=Decimal(str(row[5])),
                        )
                    )

            last_open_ms = int(payload[-1][0])
            next_cursor = last_open_ms + step_ms
            if next_cursor <= cursor_ms:
                raise ValueError("Binance returned non-advancing kline timestamps")
            cursor_ms = next_cursor
            if len(payload) < 1000:
                break
        else:
            raise ValueError("market-data request exceeded max_pages")

        return result


def _optional_decimal(value: str | None) -> Decimal | None:
    if value is None or value == "":
        return None
    return Decimal(value)
