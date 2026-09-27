from defi_manager.core.events import Event, EventBus
from defi_manager.liquidity.models import LiquidityAction, LiquidityDecision, LiquidityPolicy, PoolSnapshot

class LiquidityAnalyzer:
    """Returns audited LP recommendations only; it cannot alter liquidity."""
    def __init__(self, policy: LiquidityPolicy, events: EventBus) -> None:
        self._policy, self._events = policy, events

    def evaluate(self, snapshot: PoolSnapshot) -> LiquidityDecision:
        net = snapshot.planned_allocation_usd * (snapshot.fee_apy + snapshot.reward_apy + snapshot.impermanent_loss) - snapshot.gas_usd - snapshot.insurance_cost_usd
        if snapshot.tvl_usd < self._policy.min_tvl_usd or snapshot.available_liquidity_usd < self._policy.min_liquidity_usd:
            decision = LiquidityDecision(LiquidityAction.AVOID_POOL, "pool liquidity below minimum", net)
        elif snapshot.volatility > self._policy.max_volatility:
            decision = LiquidityDecision(LiquidityAction.AVOID_POOL, "pool volatility exceeds limit", net)
        elif net < self._policy.min_estimated_net_yield:
            decision = LiquidityDecision(LiquidityAction.AVOID_POOL, "estimated net yield below minimum", net)
        else:
            decision = LiquidityDecision(LiquidityAction.CONSIDER_LIQUIDITY, "pool meets policy limits", net)
        self._events.publish(Event("liquidity.decision", {"pool": snapshot.pool, "action": decision.action, "reason": decision.reason, "estimated_net_yield": str(net)}))
        return decision
