from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from defi_manager.core.config import Settings
from defi_manager.core.container import Container
from defi_manager.liquidity.models import LiquidityAction, PoolSnapshot

class LiquidityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = TemporaryDirectory()
        self.app = Container.build(Settings(database_path=Path(self.tmp.name) / "db.sqlite3"))
        self.addCleanup(self.app.database.connection.close)
    def tearDown(self) -> None: self.tmp.cleanup()
    def test_low_liquidity_is_avoided_and_audited(self) -> None:
        pool = PoolSnapshot("paper", "ETH-USDC", Decimal("9000"), Decimal("4000"), Decimal("0.1"), Decimal("0.1"), Decimal("0.1"), Decimal("1"), Decimal("100"), Decimal("1"), Decimal("1"))
        decision = self.app.liquidity.evaluate(pool)
        self.assertEqual(decision.action, LiquidityAction.AVOID_POOL)
        self.assertEqual(self.app.audit.all()[-1]["name"], "liquidity.decision")
    def test_healthy_pool_is_considered(self) -> None:
        pool = PoolSnapshot("paper", "ETH-USDC", Decimal("100000"), Decimal("50000"), Decimal("0.1"), Decimal("0.1"), Decimal("0.1"), Decimal("1"), Decimal("100"), Decimal("1"), Decimal("1"))
        self.assertEqual(self.app.liquidity.evaluate(pool).action, LiquidityAction.CONSIDER_LIQUIDITY)
