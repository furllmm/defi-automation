from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from defi_manager.core.config import Settings
from defi_manager.core.container import Container
from defi_manager.lending.models import LendingAction, LendingSnapshot


class LendingAnalyzerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.app = Container.build(Settings(database_path=Path(self.temporary_directory.name) / "manager.sqlite3"))
        self.addCleanup(self.app.database.connection.close)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_emergency_health_factor_requests_repay_and_audits(self) -> None:
        snapshot = LendingSnapshot("paper-lending", Decimal("1000"), Decimal("800"), Decimal("0.90"), Decimal("0.05"), Decimal("0.10"), Decimal("10000"))
        decision = self.app.lending.evaluate(snapshot)
        self.assertEqual(decision.action, LendingAction.EMERGENCY_REPAY)
        self.assertGreater(decision.suggested_repay_usd, Decimal("0"))
        self.assertEqual(self.app.audit.all()[-1]["name"], "lending.decision")

    def test_safe_snapshot_is_monitor_only_and_calculates_net_yield(self) -> None:
        snapshot = LendingSnapshot("paper-lending", Decimal("1000"), Decimal("200"), Decimal("0.85"), Decimal("0.08"), Decimal("0.05"), Decimal("10000"))
        decision = self.app.lending.evaluate(snapshot)
        self.assertEqual(decision.action, LendingAction.MONITOR)
        self.assertEqual(snapshot.annual_net_yield_usd, Decimal("70.00"))
