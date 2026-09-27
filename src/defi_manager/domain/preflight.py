from dataclasses import dataclass
from decimal import Decimal

from defi_manager.adapters.dex import SwapQuote
from defi_manager.domain.models import ExecutionIntent
from defi_manager.domain.quote_risk import QuoteRiskEvaluator
from defi_manager.domain.risk import RiskManager, RiskDecision


@dataclass(frozen=True)
class PreflightResult:
    allowed: bool
    reason: str
    quote_decision: object
    execution_decision: RiskDecision


class ExecutionPreflight:
    """Single fail-closed gate before an execution intent reaches an executor."""

    def __init__(self, quote_risk: QuoteRiskEvaluator, risk_manager: RiskManager) -> None:
        self._quote_risk = quote_risk
        self._risk_manager = risk_manager

    def evaluate(
        self,
        quote: SwapQuote,
        intent: ExecutionIntent,
        realized_daily_pnl_usd: Decimal,
    ) -> PreflightResult:
        quote_decision = self._quote_risk.evaluate(quote)
        if not quote_decision.allowed:
            return PreflightResult(False, f"quote rejected: {quote_decision.reason}", quote_decision, RiskDecision(False, "not evaluated"))

        execution_decision = self._risk_manager.evaluate(intent, realized_daily_pnl_usd)
        if not execution_decision.allowed:
            return PreflightResult(False, f"execution rejected: {execution_decision.reason}", quote_decision, execution_decision)

        return PreflightResult(True, "approved", quote_decision, execution_decision)
