from decimal import Decimal

from defi_manager.adapters.dex import SwapQuote
from defi_manager.domain.models import ExecutionIntent


class SwapIntentBuilder:
    """Converts a validated exact-input quote into an execution intent."""

    def build(self, quote: SwapQuote, side: str = "buy") -> ExecutionIntent:
        if side not in {"buy", "sell"}:
            raise ValueError("side must be buy or sell")

        # For the current simulation model, the intent is denominated in
        # the base asset and uses the quote's effective exchange price.
        price = quote.effective_price_usd
        if price <= 0:
            raise ValueError("quote effective price must be positive")

        slippage = self._slippage_bps(quote)
        return ExecutionIntent(
            asset=quote.base_asset,
            side=side,
            quantity=quote.amount_in,
            price_usd=price,
            slippage_bps=slippage,
            estimated_fee_usd=quote.estimated_gas_usd,
        )

    @staticmethod
    def _slippage_bps(quote: SwapQuote) -> int:
        ratio = quote.minimum_amount_out / quote.expected_amount_out
        return int((Decimal("1") - ratio) * Decimal("10000"))
