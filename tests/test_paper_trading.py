from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from defi_manager.core.config import Settings
from defi_manager.core.container import Container
from defi_manager.trading.market import Candle
from defi_manager.trading.paper import PaperExecutionConfig, PaperTradingEngine
from defi_manager.trading.strategy import Signal


class BuyStrategy:
    name = "test-buy"

    def evaluate(self, candles: list[Candle]) -> Signal:
        return Signal("buy", "test entry")


class SellStrategy:
    name = "test-sell"

    def evaluate(self, candles: list[Candle]) -> Signal:
        return Signal("sell", "test exit")


class PaperTradingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        path = Path(self.temporary_directory.name) / "manager.sqlite3"
        self.app = Container.build(Settings(database_path=path))
        self.app.portfolio.cash_usd = Decimal("100")
        self.addCleanup(self.app.database.connection.close)
        self.addCleanup(self.temporary_directory.cleanup)

    def _engine(self, **kwargs: object) -> PaperTradingEngine:
        return PaperTradingEngine(
            self.app.simulation,
            PaperExecutionConfig(**kwargs),
        )

    def test_strategy_signal_passes_through_risk_gate(self) -> None:
        candle = Candle.fromisoformat if False else None
        # Keep the test independent of market-data providers.
        from datetime import UTC, datetime
        from defi_manager.trading.market import Candle
        result = self._engine(fee_bps=10).step(
            "ETH",
            [Candle(datetime(2026, 1, 1, tzinfo=UTC), Decimal("2000"))],
            BuyStrategy(),
        )
        self.assertTrue(result.decision is not None and result.decision.allowed)
        self.assertIsNotNone(result.intent)
        self.assertGreater(self.app.portfolio.positions["ETH"].quantity, Decimal("0"))

    def test_risk_rejection_does_not_mutate_portfolio(self) -> None:
        self.app = Container.build(
            Settings(database_path=Path(self.temporary_directory.name) / "risk.sqlite3",
                     max_trade_notional_usd=Decimal("10"))
        )
        self.app.portfolio.cash_usd = Decimal("100")
        from datetime import UTC, datetime
        from defi_manager.trading.market import Candle
        result = self._engine().step(
            "ETH",
            [Candle(datetime(2026, 1, 1, tzinfo=UTC), Decimal("2000"))],
            BuyStrategy(),
        )
        self.assertIsNotNone(result.decision)
        self.assertFalse(result.decision.allowed)
        self.assertEqual(self.app.portfolio.cash_usd, Decimal("100"))
        self.assertEqual(self.app.portfolio.positions, {})
