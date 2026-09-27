from decimal import Decimal
import unittest
from defi_manager.domain.models import ExecutionIntent
from defi_manager.domain.risk import RiskManager, RiskPolicy

class RiskManagerTests(unittest.TestCase):
    def test_risk_rejects_excessive_slippage(self) -> None:
        manager = RiskManager(RiskPolicy(Decimal("100"), Decimal("25"), 50))
        decision = manager.evaluate(ExecutionIntent("ETH", "buy", Decimal("1"), Decimal("10"), 51), Decimal("0"))
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "slippage exceeds limit")

    def test_risk_rejects_after_daily_loss_limit(self) -> None:
        manager = RiskManager(RiskPolicy(Decimal("100"), Decimal("25"), 50))
        decision = manager.evaluate(ExecutionIntent("ETH", "buy", Decimal("1"), Decimal("10"), 1), Decimal("-25"))
        self.assertFalse(decision.allowed)
