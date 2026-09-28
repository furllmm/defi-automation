from dataclasses import dataclass
from decimal import Decimal

from defi_manager.adapters.dex import SwapQuote
from defi_manager.domain.risk import RiskPolicy


@dataclass(frozen=True)
class QuoteRiskDecision:
    allowed: bool
    reason: str


class QuoteRiskEvaluator:
    """Fails closed on quote quality before an execution intent is created."""

    def __init__(self, policy: RiskPolicy) -> None:
        self._policy = policy

    def evaluate(self, quote: SwapQuote) -> QuoteRiskDecision:
        if quote.price_impact_bps > self._policy.max_price_impact_bps:
            return QuoteRiskDecision(False, "price impact exceeds limit")
        if quote.estimated_gas_usd > self._policy.max_gas_usd:
            return QuoteRiskDecision(False, "estimated gas exceeds limit")
        if quote.minimum_amount_out <= 0:
            return QuoteRiskDecision(False, "minimum received must be positive")
        if quote.minimum_amount_out > quote.expected_amount_out:
            return QuoteRiskDecision(False, "minimum received exceeds expected output")
        return QuoteRiskDecision(True, "approved")
