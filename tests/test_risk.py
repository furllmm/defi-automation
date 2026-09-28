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

    def test_module_exposure_limit(self) -> None:
        manager = RiskManager(RiskPolicy(Decimal("100"), Decimal("25"), 50, max_module_exposure_usd=Decimal("200")))
        self.assertTrue(manager.evaluate_module_exposure(Decimal("150"), Decimal("50")).allowed)
        decision = manager.evaluate_module_exposure(Decimal("150"), Decimal("51"))
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "module exposure exceeds limit")

    def test_module_exposure_rejects_negative_values(self) -> None:
        manager = RiskManager(RiskPolicy(Decimal("100"), Decimal("25"), 50))
        decision = manager.evaluate_module_exposure(Decimal("-1"), Decimal("0"))
        self.assertFalse(decision.allowed)


    def test_treasury_rebalance_respects_module_limit(self) -> None:
        manager = RiskManager(RiskPolicy(Decimal("100"), Decimal("25"), 50, max_module_exposure_usd=Decimal("200")))
        decision = manager.evaluate_treasury_rebalance({"trading": Decimal("201")}, Decimal("500"), Decimal("500"), Decimal("100"))
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "module exposure exceeds limit")

    def test_treasury_rebalance_respects_available_cash(self) -> None:
        manager = RiskManager(RiskPolicy(Decimal("100"), Decimal("25"), 50))
        decision = manager.evaluate_treasury_rebalance({"trading": Decimal("150")}, Decimal("500"), Decimal("40"), Decimal("100"))
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "treasury allocation exceeds available cash")

    def test_treasury_rebalance_approves_valid_projection(self) -> None:
        manager = RiskManager(RiskPolicy(Decimal("100"), Decimal("25"), 50))
        decision = manager.evaluate_treasury_rebalance({"trading": Decimal("120"), "lending": Decimal("80")}, Decimal("500"), Decimal("50"), Decimal("150"))
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.reason, "approved")


    def test_risk_rejects_excessive_leverage(self) -> None:
        manager = RiskManager(RiskPolicy(Decimal("100"), Decimal("25"), 50, max_leverage=Decimal("1")))
        decision = manager.evaluate(
            ExecutionIntent("ETH", "buy", Decimal("1"), Decimal("10"), 1, leverage=Decimal("2")),
            Decimal("0"),
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.reason, "leverage exceeds limit")


    def test_risk_rejects_excessive_price_impact_and_gas(self) -> None:
        manager = RiskManager(
            RiskPolicy(Decimal("100"), Decimal("25"), 50, max_price_impact_bps=100, max_gas_usd=Decimal("5"))
        )
        impact = manager.evaluate(
            ExecutionIntent("ETH", "buy", Decimal("1"), Decimal("10"), 10, price_impact_bps=101),
            Decimal("0"),
        )
        self.assertFalse(impact.allowed)
        self.assertEqual(impact.reason, "price impact exceeds limit")

        gas = manager.evaluate(
            ExecutionIntent("ETH", "buy", Decimal("1"), Decimal("10"), 10, estimated_gas_usd=Decimal("5.01")),
            Decimal("0"),
        )
        self.assertFalse(gas.allowed)
        self.assertEqual(gas.reason, "gas cost exceeds limit")
