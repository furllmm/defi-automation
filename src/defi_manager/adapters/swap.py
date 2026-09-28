from decimal import Decimal

from defi_manager.adapters.dex import SwapQuote
from defi_manager.domain.models import ExecutionIntent


class SwapIntentBuilder:
    """Converts a validated exact-input quote into an execution intent."""

    def build(
        self,
        quote: SwapQuote,
        base_asset_price_usd: Decimal,
        side: str = "buy",
    ) -> ExecutionIntent:
        if side not in {"buy", "sell"}:
            raise ValueError("side must be buy or sell")
        if base_asset_price_usd <= 0:
            raise ValueError("base_asset_price_usd must be positive")

        return ExecutionIntent(
            asset=quote.base_asset,
            side=side,
            quantity=quote.amount_in,
            price_usd=base_asset_price_usd,
            slippage_bps=self._slippage_bps(quote),
            estimated_fee_usd=quote.estimated_gas_usd,
        )

    @staticmethod
    def _slippage_bps(quote: SwapQuote) -> int:
        ratio = quote.minimum_amount_out / quote.expected_amount_out
        return int((Decimal("1") - ratio) * Decimal("10000"))
