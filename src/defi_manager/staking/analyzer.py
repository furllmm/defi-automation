from defi_manager.core.events import Event, EventBus
from defi_manager.staking.models import StakingAction, StakingDecision, StakingPolicy, StakingSnapshot


class StakingAnalyzer:
    """Produces reward-management recommendations only; it never calls a protocol."""

    def __init__(self, policy: StakingPolicy, events: EventBus) -> None:
        self._policy = policy
        self._events = events

    def evaluate(self, snapshot: StakingSnapshot) -> StakingDecision:
        decision = self._decision(snapshot)
        self._events.publish(Event("staking.decision", {
            "protocol": snapshot.protocol,
            "action": decision.action,
            "reason": decision.reason,
            "pending_rewards_usd": str(snapshot.pending_rewards_usd),
            "claim_gas_usd": str(snapshot.claim_gas_usd),
            "estimated_net_value_usd": str(decision.estimated_net_value_usd),
        }))
        return decision

    def _decision(self, snapshot: StakingSnapshot) -> StakingDecision:
        net_claim = snapshot.net_claim_value_usd
        if snapshot.pending_rewards_usd == 0:
            return StakingDecision(StakingAction.MONITOR, "no rewards pending", net_claim)
        if net_claim < self._policy.min_net_claim_usd:
            return StakingDecision(StakingAction.DEFER_CLAIM, "net reward does not meet claim threshold", net_claim)
        net_restake = net_claim - snapshot.restake_gas_usd
        if self._policy.auto_restake and net_restake >= self._policy.min_restake_net_usd:
            return StakingDecision(StakingAction.CLAIM_AND_RESTAKE, "net reward meets restake threshold", net_restake)
        return StakingDecision(StakingAction.CLAIM_REWARDS, "net reward meets claim threshold", net_claim)

