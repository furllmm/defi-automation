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
        decision = self._risk.evaluate(intent, self._pnl.realized_usd)
        self._events.publish(Event("risk.decision", {"allowed": decision.allowed, "reason": decision.reason, "asset": intent.asset}))
        if not decision.allowed:
            return decision
        self._pnl.record_fill(self._portfolio, intent)
        self._portfolio.apply_fill(intent)
        self._events.publish(Event("simulation.fill", {"asset": intent.asset, "side": intent.side, "quantity": str(intent.quantity), "price_usd": str(intent.price_usd)}))
        return decision

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

        result = preflight.evaluate(quote, intent, self._pnl.realized_usd)
        self._events.publish(
            Event(
                "execution.preflight",
                {"allowed": result.allowed, "reason": result.reason, "asset": intent.asset},
            )
        )
        if not result.allowed:
            return result.execution_decision

        self._pnl.record_fill(self._portfolio, intent)
        self._portfolio.apply_fill(intent)
        self._events.publish(Event("simulation.fill", {"asset": intent.asset, "side": intent.side, "quantity": str(intent.quantity), "price_usd": str(intent.price_usd)}))
        return result.execution_decision
