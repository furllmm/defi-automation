from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

@dataclass(frozen=True)
class SwapQuote:
    adapter: str
    base_asset: str
    quote_asset: str
    amount_in: Decimal
    expected_amount_out: Decimal
    minimum_amount_out: Decimal
    price_impact_bps: int
    estimated_gas_usd: Decimal

    def __post_init__(self) -> None:
        if not self.adapter:
            raise ValueError("adapter is required")
        if not self.base_asset or not self.quote_asset:
            raise ValueError("base_asset and quote_asset are required")
        if self.amount_in <= 0:
            raise ValueError("amount_in must be positive")
        if self.expected_amount_out <= 0:
            raise ValueError("expected_amount_out must be positive")
        if self.minimum_amount_out <= 0:
            raise ValueError("minimum_amount_out must be positive")
        if self.minimum_amount_out > self.expected_amount_out:
            raise ValueError("minimum_amount_out cannot exceed expected_amount_out")
        if self.price_impact_bps < 0:
            raise ValueError("price_impact_bps cannot be negative")
        if self.estimated_gas_usd < 0:
            raise ValueError("estimated_gas_usd cannot be negative")

    @property
    def effective_price_usd(self) -> Decimal:
        if self.expected_amount_out <= 0:
            raise ValueError("expected output must be positive")
        return self.amount_in / self.expected_amount_out

class DexAdapter(Protocol):
    """Read-only quote contract. Live submission is intentionally excluded."""

    def quote_exact_input(
        self, base_asset: str, quote_asset: str, amount_in: Decimal, max_slippage_bps: int
    ) -> SwapQuote: ...

class FixedPriceDexAdapter:
    """Deterministic quote source for tests and paper-trading demonstrations."""

    name = "fixed-price-paper-dex"

    def __init__(self, prices_usd: dict[str, Decimal], gas_usd: Decimal = Decimal("0")) -> None:
        self._prices_usd = prices_usd
        self._gas_usd = gas_usd

    def quote_exact_input(
        self, base_asset: str, quote_asset: str, amount_in: Decimal, max_slippage_bps: int
    ) -> SwapQuote:
        if amount_in <= 0:
            raise ValueError("amount_in must be positive")
        if max_slippage_bps < 0 or max_slippage_bps > 10000:
            raise ValueError("max_slippage_bps must be between 0 and 10000")
        try:
            base_price = self._prices_usd[base_asset]
            quote_price = self._prices_usd[quote_asset]
        except KeyError as exc:
            raise ValueError(f"unknown paper price for {exc.args[0]}") from exc
        if base_price <= 0 or quote_price <= 0:
            raise ValueError("paper prices must be positive")
        expected_out = amount_in * base_price / quote_price
        minimum_out = expected_out * (Decimal("1") - Decimal(max_slippage_bps) / Decimal("10000"))
        return SwapQuote(self.name, base_asset, quote_asset, amount_in, expected_out, minimum_out, 0, self._gas_usd)

