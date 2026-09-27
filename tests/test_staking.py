from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from defi_manager.core.config import Settings
from defi_manager.core.container import Container
from defi_manager.staking.models import StakingAction, StakingSnapshot


class StakingAnalyzerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary_directory = TemporaryDirectory()
        self.app = Container.build(Settings(database_path=Path(self.temporary_directory.name) / "manager.sqlite3"))
        self.addCleanup(self.app.database.connection.close)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_defers_claim_when_gas_exceeds_reward(self) -> None:
        snapshot = StakingSnapshot("paper-staking", Decimal("100"), Decimal("0.10"), Decimal("0.05"), Decimal("0.06"), Decimal("0.20"), Decimal("0.10"), 0, 7)
        decision = self.app.staking.evaluate(snapshot)
        self.assertEqual(decision.action, StakingAction.DEFER_CLAIM)
        self.assertEqual(decision.estimated_net_value_usd, Decimal("-0.10"))

    def test_recommends_claim_and_restake_when_net_reward_covers_costs(self) -> None:
        snapshot = StakingSnapshot("paper-staking", Decimal("100"), Decimal("5"), Decimal("0.05"), Decimal("0.06"), Decimal("0.20"), Decimal("0.30"), 0, 7)
        decision = self.app.staking.evaluate(snapshot)
        self.assertEqual(decision.action, StakingAction.CLAIM_AND_RESTAKE)
        self.assertEqual(decision.estimated_net_value_usd, Decimal("4.50"))
        self.assertEqual(self.app.audit.all()[-1]["name"], "staking.decision")
