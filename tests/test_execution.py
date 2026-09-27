from decimal import Decimal
import unittest

from defi_manager.domain.models import ExecutionIntent, PnLTracker, PortfolioState
from defi_manager.domain.risk import RiskManager, RiskPolicy
from defi_manager.core.events import EventBus
from defi_manager.core.safety import AutomationSafetyController
from defi_manager.simulation.environment import SimulationEnvironment
from defi_manager.execution import LiveExecutor, PaperExecutor


class ExecutionTests(unittest.TestCase):
    def _simulation(self) -> SimulationEnvironment:
        return SimulationEnvironment(
            PortfolioState(cash_usd=Decimal("1000")),
            PnLTracker(),
            RiskManager(RiskPolicy(Decimal("500"), Decimal("100"), 100)),
            EventBus(),
            AutomationSafetyController(EventBus()),
        )

    def test_paper_executor_delegates_to_simulation(self) -> None:
        simulation = self._simulation()
        result = PaperExecutor(simulation).execute(
            ExecutionIntent("ETH", "buy", Decimal("0.1"), Decimal("2000"), 10)
        )
        self.assertTrue(result.allowed)

    def test_live_executor_is_disabled(self) -> None:
        result = LiveExecutor().execute(
            ExecutionIntent("ETH", "buy", Decimal("0.1"), Decimal("2000"), 10)
        )
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, "live execution is disabled")
