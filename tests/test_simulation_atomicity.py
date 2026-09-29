from decimal import Decimal
import unittest

from defi_manager.core.events import EventBus
from defi_manager.core.safety import AutomationSafetyController
from defi_manager.domain.models import ExecutionIntent, PnLTracker, PortfolioState
from defi_manager.domain.risk import RiskManager, RiskPolicy
from defi_manager.simulation.environment import SimulationEnvironment


class SimulationAtomicityTests(unittest.TestCase):
    def _simulation(self) -> SimulationEnvironment:
        events = EventBus()
        return SimulationEnvironment(
            PortfolioState(cash_usd=Decimal("100")),
            PnLTracker(),
            RiskManager(RiskPolicy(Decimal("1000"), Decimal("100"), 100)),
            events,
            AutomationSafetyController(events),
        )

    def test_insufficient_cash_does_not_mutate_portfolio_or_pnl(self) -> None:
        simulation = self._simulation()
        intent = ExecutionIntent(
            "ETH",
            "buy",
            Decimal("1"),
            Decimal("101"),
            10,
            estimated_fee_usd=Decimal("1"),
        )

        result = simulation.execute(intent)

        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, "insufficient simulated cash")
        self.assertEqual(simulation.portfolio.cash_usd, Decimal("100"))
        self.assertNotIn("ETH", simulation.portfolio.positions)
        self.assertEqual(simulation.pnl.realized_usd, Decimal("0"))
        self.assertEqual(simulation.pnl.fees_usd, Decimal("0"))

    def test_successful_fill_commits_portfolio_and_pnl(self) -> None:
        simulation = self._simulation()
        intent = ExecutionIntent(
            "ETH",
            "buy",
            Decimal("0.1"),
            Decimal("100"),
            10,
            estimated_fee_usd=Decimal("1"),
        )

        result = simulation.execute(intent)

        self.assertTrue(result.allowed)
        self.assertEqual(simulation.portfolio.cash_usd, Decimal("89"))
        self.assertEqual(simulation.portfolio.positions["ETH"].quantity, Decimal("0.1"))
        self.assertEqual(simulation.pnl.fees_usd, Decimal("1"))


if __name__ == "__main__":
    unittest.main()
