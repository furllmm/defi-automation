from datetime import UTC, datetime, timedelta
from decimal import Decimal
import unittest

from defi_manager.adapters.dex import FixedPriceDexAdapter
from defi_manager.adapters.swap import SwapIntentBuilder
from defi_manager.domain.models import ExecutionIntent, PnLTracker, PortfolioState
from defi_manager.domain.preflight import ExecutionPreflight
from defi_manager.domain.quote_risk import QuoteRiskEvaluator
from defi_manager.domain.risk import RiskManager, RiskPolicy
from defi_manager.core.events import EventBus
from defi_manager.core.safety import AutomationSafetyController
from defi_manager.simulation.environment import SimulationEnvironment
from defi_manager.execution import LiveExecutor, PaperExecutor


class ExecutionTests(unittest.TestCase):
    def _simulation(self) -> SimulationEnvironment:
        events = EventBus()
        return SimulationEnvironment(
            PortfolioState(cash_usd=Decimal("10000")),
            PnLTracker(),
            RiskManager(RiskPolicy(Decimal("5000"), Decimal("100"), 100, max_price_impact_bps=50, max_gas_usd=Decimal("5"))),
            events,
            AutomationSafetyController(events),
        )

    def test_risk_uses_daily_pnl_not_all_time_realized_pnl(self) -> None:
        simulation = self._simulation()
        now = datetime.now(UTC)
        simulation.pnl.record_loss("trading", Decimal("150"), occurred_at=now - timedelta(days=1))
        result = PaperExecutor(simulation).execute(
            ExecutionIntent("ETH", "buy", Decimal("0.1"), Decimal("2000"), 10)
        )
        self.assertTrue(result.allowed)

    def test_paper_executor_delegates_to_simulation(self) -> None:
        simulation = self._simulation()
        result = PaperExecutor(simulation).execute(
            ExecutionIntent("ETH", "buy", Decimal("0.1"), Decimal("2000"), 10)
        )
        self.assertTrue(result.allowed)

    def test_quote_aware_execution_requires_preflight(self) -> None:
        simulation = self._simulation()
        adapter = FixedPriceDexAdapter({"ETH": Decimal("2000"), "USDC": Decimal("1")}, gas_usd=Decimal("2"))
        quote = adapter.quote_exact_input("ETH", "USDC", Decimal("1"), 50)
        intent = SwapIntentBuilder().build(quote, Decimal("2000"))
        result = PaperExecutor(simulation).execute_with_quote(quote, intent)
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, "preflight is required for quote-aware execution")

    def test_quote_aware_execution_runs_preflight(self) -> None:
        simulation = self._simulation()
        policy = RiskPolicy(Decimal("5000"), Decimal("100"), 100, max_price_impact_bps=50, max_gas_usd=Decimal("5"))
        risk = RiskManager(policy)
        preflight = ExecutionPreflight(QuoteRiskEvaluator(policy), risk)
        adapter = FixedPriceDexAdapter({"ETH": Decimal("2000"), "USDC": Decimal("1")}, gas_usd=Decimal("2"))
        quote = adapter.quote_exact_input("ETH", "USDC", Decimal("1"), 50)
        intent = SwapIntentBuilder().build(quote, Decimal("2000"))
        result = PaperExecutor(simulation, preflight).execute_with_quote(quote, intent)
        self.assertTrue(result.allowed)
        self.assertEqual(simulation.portfolio.positions["ETH"].quantity, Decimal("1"))

    def test_live_executor_is_disabled(self) -> None:
        result = LiveExecutor().execute(
            ExecutionIntent("ETH", "buy", Decimal("0.1"), Decimal("2000"), 10)
        )
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, "live execution is disabled")
