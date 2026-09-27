from decimal import Decimal

from defi_manager.core.events import Event, EventBus
from defi_manager.lending.models import LendingAction, LendingDecision, LendingPolicy, LendingSnapshot


class LendingAnalyzer:
    """Produces safety recommendations only; it never calls a lending protocol."""

    def __init__(self, policy: LendingPolicy, events: EventBus) -> None:
        self._policy = policy
        self._events = events

    def evaluate(self, snapshot: LendingSnapshot) -> LendingDecision:
        decision = self._decision(snapshot)
        self._events.publish(Event("lending.decision", {
            "protocol": snapshot.protocol,
            "action": decision.action,
            "reason": decision.reason,
            "ltv": str(snapshot.ltv),
            "health_factor": str(snapshot.health_factor),
            "suggested_repay_usd": str(decision.suggested_repay_usd),
        }))
        return decision

    def _decision(self, snapshot: LendingSnapshot) -> LendingDecision:
        if snapshot.debt_usd > self._policy.max_debt_usd:
            return LendingDecision(LendingAction.BLOCK_NEW_DEBT, "maximum debt exceeded")
        if snapshot.available_liquidity_usd < self._policy.min_liquidity_usd:
            return LendingDecision(LendingAction.BLOCK_NEW_DEBT, "protocol liquidity below minimum")
        if snapshot.health_factor <= self._policy.emergency_health_factor:
            return LendingDecision(LendingAction.EMERGENCY_REPAY, "emergency health factor breached", self._repay_to_health_factor(snapshot, self._policy.min_health_factor))
        if snapshot.health_factor <= self._policy.min_health_factor:
            return LendingDecision(LendingAction.DELEVERAGE, "minimum health factor breached", self._repay_to_health_factor(snapshot, self._policy.min_health_factor))
        if snapshot.ltv >= self._policy.max_ltv:
            return LendingDecision(LendingAction.DELEVERAGE, "maximum LTV reached", self._repay_to_ltv(snapshot))
        return LendingDecision(LendingAction.MONITOR, "within lending limits")

    def _repay_to_health_factor(self, snapshot: LendingSnapshot, target: Decimal) -> Decimal:
        safe_debt = (snapshot.collateral_usd * snapshot.liquidation_threshold) / target
        return max(Decimal("0"), snapshot.debt_usd - safe_debt)

    def _repay_to_ltv(self, snapshot: LendingSnapshot) -> Decimal:
        safe_debt = snapshot.collateral_usd * self._policy.max_ltv
        return max(Decimal("0"), snapshot.debt_usd - safe_debt)

