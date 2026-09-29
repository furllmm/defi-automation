from datetime import UTC, datetime
from decimal import Decimal
from defi_manager.core.events import Event, EventBus
from defi_manager.core.safety import AutomationSafetyController
from defi_manager.domain.models import ExecutionIntent, PnLTracker, PortfolioState
from defi_manager.domain.risk import RiskDecision, RiskManager
from defi_manager.domain.preflight import ExecutionPreflight
from defi_manager.adapters.dex import SwapQuote

class SimulationEnvironment:
    def __init__(self, portfolio: PortfolioState, pnl: PnLTracker, risk: RiskManager, events: EventBus, safety: AutomationSafetyController) -> None:
        self._portfolio, self._pnl, self._risk, self._events = portfolio, pnl, risk, events
        self._safety = safety

    @property
    def portfolio(self) -> PortfolioState:
        return self._portfolio

    @property
    def pnl(self) -> PnLTracker:
        return self._pnl

    def execute(self, intent: ExecutionIntent) -> RiskDecision:
        safety = self._safety.execution_decision()
        if not safety.allowed:
            self._events.publish(Event("safety.execution_rejected", {"reason": safety.reason, "asset": intent.asset}))
            return RiskDecision(False, safety.reason)
        decision = self._evaluate_risk(intent)
        self._events.publish(Event("risk.decision", {"allowed": decision.allowed, "reason": decision.reason, "asset": intent.asset}))
        if not decision.allowed:
            return decision
        funding = self._funding_decision(intent)
        if not funding.allowed:
            self._events.publish(
                Event(
                    "simulation.fill_rejected",
                    {"asset": intent.asset, "reason": funding.reason},
                )
            )
            return funding
        self._apply_approved_fill(intent)
        return decision

    def _evaluate_risk(self, intent: ExecutionIntent) -> RiskDecision:
        position = self._portfolio.positions.get(intent.asset)
        exposure = Decimal("0") if position is None else position.quantity * intent.price_usd
        daily_pnl = self._pnl.daily_pnl(datetime.now(UTC))
        return self._risk.evaluate(intent, daily_pnl, exposure)

    def _funding_decision(self, intent: ExecutionIntent) -> RiskDecision:
        if intent.side != "buy":
            return RiskDecision(True, "funding check not required")
        required_cash = intent.notional_usd + intent.estimated_fee_usd
        if required_cash > self._portfolio.cash_usd:
            return RiskDecision(False, "insufficient simulated cash")
        return RiskDecision(True, "funding available")

    def _apply_approved_fill(self, intent: ExecutionIntent) -> None:
        # Mutate the portfolio first. PnL is committed only after the fill succeeds,
        # so a failed balance check cannot leave accounting state partially updated.
        self._portfolio.apply_fill(intent)
        self._pnl.record_fill(self._portfolio, intent)
        self._events.publish(
            Event(
                "simulation.fill",
                {
                    "asset": intent.asset,
                    "side": intent.side,
                    "quantity": str(intent.quantity),
                    "price_usd": str(intent.price_usd),
                },
            )
        )

    def execute_with_preflight(
        self,
        quote: SwapQuote,
        intent: ExecutionIntent,
        preflight: ExecutionPreflight,
    ) -> RiskDecision:
        safety = self._safety.execution_decision()
        if not safety.allowed:
            self._events.publish(Event("safety.execution_rejected", {"reason": safety.reason, "asset": intent.asset}))
            return RiskDecision(False, safety.reason)

        position = self._portfolio.positions.get(intent.asset)
        exposure = Decimal("0") if position is None else position.quantity * intent.price_usd
        daily_pnl = self._pnl.daily_pnl(datetime.now(UTC))
        result = preflight.evaluate(quote, intent, daily_pnl, exposure)
        self._events.publish(
            Event(
                "execution.preflight",
                {"allowed": result.allowed, "reason": result.reason, "asset": intent.asset},
            )
        )
        if not result.allowed:
            return result.execution_decision
        funding = self._funding_decision(intent)
        if not funding.allowed:
            self._events.publish(
                Event(
                    "simulation.fill_rejected",
                    {"asset": intent.asset, "reason": funding.reason},
                )
            )
            return funding

        self._apply_approved_fill(intent)
        return result.execution_decision
