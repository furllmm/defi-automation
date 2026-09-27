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

@dataclass(frozen=True)
class RiskDecision:
    allowed: bool
    reason: str

class RiskManager:
    def __init__(self, policy: RiskPolicy) -> None:
        self._policy = policy

    def evaluate_module_exposure(self, current_exposure_usd: Decimal, requested_increase_usd: Decimal) -> RiskDecision:\n        if current_exposure_usd < 0 or requested_increase_usd < 0:\n            return RiskDecision(False, "module exposure values cannot be negative")\n        if current_exposure_usd + requested_increase_usd > self._policy.max_module_exposure_usd:\n            return RiskDecision(False, "module exposure exceeds limit")\n        return RiskDecision(True, "approved")\n\n    @property
    def policy(self) -> RiskPolicy:
        return self._policy

    def evaluate(self, intent: ExecutionIntent, realized_daily_pnl_usd: Decimal, current_asset_exposure_usd: Decimal = Decimal("0")) -> RiskDecision:
        if intent.side not in {"buy", "sell"}:
            return RiskDecision(False, "unsupported side")
        if intent.quantity <= 0 or intent.price_usd <= 0:
            return RiskDecision(False, "quantity and price must be positive")
        if intent.notional_usd > self._policy.max_trade_notional_usd:
            return RiskDecision(False, "trade notional exceeds limit")
        if current_asset_exposure_usd < 0:
            return RiskDecision(False, "current asset exposure cannot be negative")
        if intent.side == "buy" and current_asset_exposure_usd + intent.notional_usd > self._policy.max_asset_exposure_usd:
            return RiskDecision(False, "asset exposure exceeds limit")
        if intent.side == "sell" and intent.notional_usd > current_asset_exposure_usd:
            return RiskDecision(False, "sell exceeds current asset exposure")
        if intent.slippage_bps > self._policy.max_slippage_bps:
            return RiskDecision(False, "slippage exceeds limit")
        if realized_daily_pnl_usd <= -self._policy.max_daily_loss_usd:
            return RiskDecision(False, "daily loss limit reached")
        return RiskDecision(True, "approved")

