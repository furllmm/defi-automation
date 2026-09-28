from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from defi_manager.ai import AIEngine
from defi_manager.core.config import Settings
from defi_manager.core.container import Container
from defi_manager.core.safety import PauseReason


class AIExecutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.app = Container.build(
            Settings(database_path=Path(self.temporary_directory.name) / "manager.sqlite3")
        )
        self.addCleanup(self.app.database.connection.close)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_ai_only_produces_intents(self) -> None:
        self.app.portfolio.cash_usd = Decimal("100")
        ai = AIEngine()

        proposals = ai.propose(
            self.app.portfolio,
            asset="ETH",
            price_usd=Decimal("10"),
            quantity=Decimal("1"),
        )

        self.assertEqual(len(proposals), 1)
        self.assertEqual(proposals[0].intent.asset, "ETH")
        self.assertFalse(hasattr(ai, "execute"))

    def test_ai_execution_uses_safety_gate(self) -> None:
        self.app.portfolio.cash_usd = Decimal("100")
        self.app.safety.observe(PauseReason.NETWORK, healthy=False, detail="offline")

        results = self.app.ai_execution.propose_and_execute(
            self.app.portfolio,
            asset="ETH",
            price_usd=Decimal("10"),
            quantity=Decimal("1"),
        )

        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].decision.allowed)
        self.assertEqual(results[0].decision.reason, "automation paused: ['network']")
        self.assertEqual(self.app.portfolio.cash_usd, Decimal("100"))

    def test_ai_execution_still_uses_risk_gate(self) -> None:
        self.app.portfolio.cash_usd = Decimal("100")

        results = self.app.ai_execution.propose_and_execute(
            self.app.portfolio,
            asset="ETH",
            price_usd=Decimal("10"),
            quantity=Decimal("101"),
        )

        self.assertEqual(len(results), 1)
        self.assertFalse(results[0].decision.allowed)
        self.assertEqual(results[0].decision.reason, "trade notional exceeds limit")
        self.assertEqual(self.app.portfolio.cash_usd, Decimal("100"))

    def test_ai_execution_reaches_paper_executor_when_allowed(self) -> None:
        self.app.portfolio.cash_usd = Decimal("100")

        results = self.app.ai_execution.propose_and_execute(
            self.app.portfolio,
            asset="ETH",
            price_usd=Decimal("10"),
            quantity=Decimal("1"),
        )

        self.assertEqual(len(results), 1)
        self.assertTrue(results[0].decision.allowed)
        self.assertEqual(self.app.portfolio.positions["ETH"].quantity, Decimal("1"))
        self.assertEqual(self.app.portfolio.cash_usd, Decimal("90"))
