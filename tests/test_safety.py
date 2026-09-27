from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from defi_manager.core.config import Settings
from defi_manager.core.container import Container
from defi_manager.core.safety import PauseReason
from defi_manager.domain.models import ExecutionIntent


class AutomationSafetyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.app = Container.build(Settings(database_path=Path(self.temporary_directory.name) / "manager.sqlite3"))
        self.addCleanup(self.app.database.connection.close)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_network_failure_requires_explicit_resume_after_health_restores(self) -> None:
        self.app.portfolio.cash_usd = Decimal("100")
        self.app.safety.observe(PauseReason.NETWORK, healthy=False, detail="offline")
        rejected = self.app.simulation.execute(ExecutionIntent("ETH", "buy", Decimal("0.01"), Decimal("2000"), 1))
        self.assertFalse(rejected.allowed)
        self.assertEqual(self.app.portfolio.cash_usd, Decimal("100"))

        self.app.safety.observe(PauseReason.NETWORK, healthy=True, detail="restored")
        waiting = self.app.simulation.execute(ExecutionIntent("ETH", "buy", Decimal("0.01"), Decimal("2000"), 1))
        self.assertFalse(waiting.allowed)
        self.assertTrue(self.app.safety.resume().allowed)
        recovered = self.app.simulation.execute(ExecutionIntent("ETH", "buy", Decimal("0.01"), Decimal("2000"), 1))
        self.assertTrue(recovered.allowed)

    def test_emergency_recovery_requires_manual_resume(self) -> None:
        self.app.safety.emergency_stop("operator request")
        self.assertFalse(self.app.safety.resume().allowed)
        self.assertTrue(self.app.safety.recover_emergency("review complete").allowed)
        self.assertFalse(self.app.safety.execution_decision().allowed)
        self.assertTrue(self.app.safety.resume().allowed)
        self.assertTrue(self.app.safety.execution_decision().allowed)
