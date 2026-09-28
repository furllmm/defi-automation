from decimal import Decimal
import unittest

from defi_manager.adapters.dex import SwapQuote
from defi_manager.domain.models import ExecutionIntent
from defi_manager.domain.preflight import ExecutionPreflight
from defi_manager.domain.quote_risk import QuoteRiskEvaluator
from defi_manager.domain.risk import RiskManager, RiskPolicy


class PreflightRiskTests(unittest.TestCase):
    def test_preflight_passes_current_exposure_to_risk_manager(self) -> None:
        policy = RiskPolicy(
            max_trade_notional_usd=Decimal("1000"),
            max_daily_loss_usd=Decimal("100"),
            max_slippage_bps=100,
            max_asset_exposure_usd=Decimal("100"),
        )
        preflight = ExecutionPreflight(QuoteRiskEvaluator(policy), RiskManager(policy))
        quote = SwapQuote(
            asset="ETH",
            price_usd=Decimal("10"),
            slippage_bps=10,
            price_impact_bps=10,
            estimated_gas_usd=Decimal("1"),
        )
        intent = ExecutionIntent("ETH", "buy", Decimal("5"), Decimal("10"), 10)

        result = preflight.evaluate(
            quote,
            intent,
            realized_daily_pnl_usd=Decimal("0"),
            current_asset_exposure_usd=Decimal("96"),
        )

        self.assertFalse(result.allowed)
        self.assertEqual(result.execution_decision.reason, "asset exposure exceeds limit")
