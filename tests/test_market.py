from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from defi_manager.trading.market import Candle, CsvMarketDataProvider, InMemoryMarketDataProvider


class MarketDataTests(unittest.TestCase):
    def test_in_memory_provider_filters_and_sorts(self) -> None:
        start = datetime(2026, 1, 1, tzinfo=UTC)
        candles = [
            Candle(start + timedelta(days=2), Decimal("12")),
            Candle(start, Decimal("10")),
            Candle(start + timedelta(days=1), Decimal("11")),
        ]
        provider = InMemoryMarketDataProvider({"ETH": candles})
        result = provider.candles("ETH", start, start + timedelta(days=2))
        self.assertEqual([c.close_usd for c in result], [Decimal("10"), Decimal("11")])

    def test_csv_provider_loads_optional_ohlcv(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "ETH.csv"
            path.write_text(
                "timestamp,close_usd,open_usd,high_usd,low_usd,volume\n"
                "2026-01-01T00:00:00+00:00,2000,1990,2010,1980,123.4\n",
                encoding="utf-8",
            )
            start = datetime(2026, 1, 1, tzinfo=UTC)
            result = CsvMarketDataProvider(Path(directory)).candles(
                "ETH", start, start + timedelta(days=1)
            )
            self.assertEqual(result[0].high_usd, Decimal("2010"))
            self.assertEqual(result[0].volume, Decimal("123.4"))

    def test_csv_provider_rejects_missing_columns(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "ETH.csv"
            path.write_text("timestamp\n2026-01-01T00:00:00+00:00\n", encoding="utf-8")
            start = datetime(2026, 1, 1, tzinfo=UTC)
            with self.assertRaises(ValueError):
                CsvMarketDataProvider(Path(directory)).candles(
                    "ETH", start, start + timedelta(days=1)
                )
