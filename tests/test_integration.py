from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from defi_manager.core.config import Settings
from defi_manager.core.container import Container
from defi_manager.domain.models import ExecutionIntent

class SimulationIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def _app(self, **settings: object) -> Container:
        path = Path(self.temporary_directory.name) / "manager.sqlite3"
        app = Container.build(Settings(database_path=path, **settings))
        self.addCleanup(app.database.connection.close)
        return app

    def test_approved_fill_updates_state_and_audit(self) -> None:
        app = self._app()
        app.portfolio.cash_usd = Decimal("100")
        decision = app.simulation.execute(ExecutionIntent("ETH", "buy", Decimal("0.02"), Decimal("2000"), 10, Decimal("1")))
        self.assertTrue(decision.allowed)
        self.assertEqual(app.portfolio.cash_usd, Decimal("59"))
        self.assertEqual([row["name"] for row in app.audit.all()], ["risk.decision", "simulation.fill"])

    def test_rejected_fill_does_not_mutate_portfolio(self) -> None:
        app = self._app(max_trade_notional_usd=Decimal("10"))
        app.portfolio.cash_usd = Decimal("100")
        decision = app.simulation.execute(ExecutionIntent("ETH", "buy", Decimal("1"), Decimal("20"), 1))
        self.assertFalse(decision.allowed)
        self.assertEqual(app.portfolio.cash_usd, Decimal("100"))
        self.assertEqual([row["name"] for row in app.audit.all()], ["risk.decision"])
