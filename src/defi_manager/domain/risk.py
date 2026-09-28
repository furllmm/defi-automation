from dataclasses import dataclass
from decimal import Decimal

from defi_manager.domain.models import ExecutionIntent


@dataclass(frozen=True)
class RiskPolicy:
    max_trade_notional_usd: Decimal
    max_daily_loss_usd: Decimal
    max_slippage_bps: int
    max_price_impact_bps: int = 500
    max_gas_usd: Decimal = Decimal("100")
    max_asset_exposure_usd: Decimal = Decimal("5000")
    max_module_exposure_usd: Decimal = Decimal("10000")
    max_leverage: Decimal = Decimal("1")


@dataclass(frozen=True)
class RiskDecision:
    allowed: bool
    reason: str


class RiskManager:
    def __init__(self, policy: RiskPolicy) -> None:
        self._policy = policy

    @property
    def policy(self) -> RiskPolicy:
        return self._policy

    def evaluate_module_exposure(
        self,
        current_exposure_usd: Decimal,
        requested_increase_usd: Decimal,
    ) -> RiskDecision:
        if current_exposure_usd < 0 or requested_increase_usd < 0:
            return RiskDecision(False, "module exposure values cannot be negative")
        if current_exposure_usd + requested_increase_usd > self._policy.max_module_exposure_usd:
            return RiskDecision(False, "module exposure exceeds limit")
        return RiskDecision(True, "approved")

    def evaluate_treasury_rebalance(
        self,
        projected_allocations_usd: dict[str, Decimal],
        total_equity_usd: Decimal,
        available_cash_usd: Decimal,
        current_allocated_usd: Decimal,
    ) -> RiskDecision:
        if total_equity_usd < 0:
            return RiskDecision(False, "total equity cannot be negative")
        if available_cash_usd < 0:
            return RiskDecision(False, "available cash cannot be negative")
        if current_allocated_usd < 0:
            return RiskDecision(False, "current allocated capital cannot be negative")

        if any(not module or amount < 0 for module, amount in projected_allocations_usd.items()):
            return RiskDecision(False, "treasury allocations cannot be negative")

        projected_total = sum(projected_allocations_usd.values(), Decimal("0"))
        if projected_total > total_equity_usd:
            return RiskDecision(False, "treasury allocation exceeds total equity")

        net_increase = projected_total - current_allocated_usd
        if net_increase > available_cash_usd:
            return RiskDecision(False, "treasury allocation exceeds available cash")

        if any(amount > self._policy.max_module_exposure_usd for amount in projected_allocations_usd.values()):
            return RiskDecision(False, "module exposure exceeds limit")

        return RiskDecision(True, "approved")

    def evaluate(
        self,
        intent: ExecutionIntent,
        realized_daily_pnl_usd: Decimal,
        current_asset_exposure_usd: Decimal = Decimal("0"),
    ) -> RiskDecision:
        if intent.side not in {"buy", "sell"}:
            return RiskDecision(False, "unsupported side")
        if intent.quantity <= 0 or intent.price_usd <= 0:
            return RiskDecision(False, "quantity and price must be positive")
        if intent.leverage <= 0:
            return RiskDecision(False, "leverage must be positive")
        if intent.leverage > self._policy.max_leverage:
            return RiskDecision(False, "leverage exceeds limit")
        if intent.notional_usd > self._policy.max_trade_notional_usd:
            return RiskDecision(False, "trade notional exceeds limit")
        if current_asset_exposure_usd < 0:
            return RiskDecision(False, "current asset exposure cannot be negative")
        if (
            intent.side == "buy"
            and current_asset_exposure_usd + intent.notional_usd
            > self._policy.max_asset_exposure_usd
        ):
            return RiskDecision(False, "asset exposure exceeds limit")
        if intent.side == "sell" and intent.notional_usd > current_asset_exposure_usd:
            return RiskDecision(False, "sell exceeds current asset exposure")
        if intent.slippage_bps > self._policy.max_slippage_bps:
            return RiskDecision(False, "slippage exceeds limit")
        if realized_daily_pnl_usd <= -self._policy.max_daily_loss_usd:
            return RiskDecision(False, "daily loss limit reached")
        return RiskDecision(True, "approved")
