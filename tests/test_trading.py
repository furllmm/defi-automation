from datetime import UTC, datetime, timedelta
from decimal import Decimal
import unittest

from defi_manager.adapters.dex import FixedPriceDexAdapter, SwapQuote
from defi_manager.domain.quote_risk import QuoteRiskEvaluator
from defi_manager.domain.risk import RiskPolicy
from defi_manager.trading.backtest import BacktestConfig, BacktestRunner, ExitPolicy
from defi_manager.trading.market import Candle, InMemoryMarketDataProvider
from defi_manager.trading.strategy import MovingAverageCrossStrategy, RsiStrategy, Signal


class TradingTests(unittest.TestCase):
    def test_fixed_price_quote_applies_minimum_received(self) -> None:
        adapter = FixedPriceDexAdapter({"USDC": Decimal("1"), "ETH": Decimal("2000")})
        quote = adapter.quote_exact_input("USDC", "ETH", Decimal("200"), 100)
        self.assertEqual(quote.expected_amount_out, Decimal("0.1"))
        self.assertEqual(quote.minimum_amount_out, Decimal("0.099"))

    def test_fixed_price_quote_rejects_invalid_price_and_slippage(self) -> None:
        adapter = FixedPriceDexAdapter({"USDC": Decimal("1"), "ETH": Decimal("2000")})
        with self.assertRaises(ValueError):
            adapter.quote_exact_input("USDC", "ETH", Decimal("100"), 10001)
        with self.assertRaises(ValueError):
            FixedPriceDexAdapter({"USDC": Decimal("0"), "ETH": Decimal("2000")}).quote_exact_input(
                "USDC", "ETH", Decimal("100"), 100
            )

    def test_swap_quote_rejects_minimum_above_expected(self) -> None:
        from defi_manager.adapters.dex import SwapQuote
        with self.assertRaises(ValueError):
            SwapQuote("test", "USDC", "ETH", Decimal("100"), Decimal("1"), Decimal("2"), 0, Decimal("1"))

    def test_quote_risk_rejects_excessive_impact_and_gas(self) -> None:
        policy = RiskPolicy(Decimal("1000"), Decimal("100"), 100, max_price_impact_bps=50, max_gas_usd=Decimal("5"))
        evaluator = QuoteRiskEvaluator(policy)
        quote = SwapQuote("test", "ETH", "USDC", Decimal("1"), Decimal("2000"), Decimal("1980"), 100, Decimal("1"))
        self.assertFalse(evaluator.evaluate(quote).allowed)
        expensive = SwapQuote("test", "ETH", "USDC", Decimal("1"), Decimal("2000"), Decimal("1980"), 10, Decimal("6"))
        self.assertFalse(evaluator.evaluate(expensive).allowed)

    def test_quote_risk_accepts_reasonable_quote(self) -> None:
        policy = RiskPolicy(Decimal("1000"), Decimal("100"), 100, max_price_impact_bps=50, max_gas_usd=Decimal("5"))
        quote = SwapQuote("test", "ETH", "USDC", Decimal("1"), Decimal("2000"), Decimal("1980"), 20, Decimal("2"))
        self.assertTrue(QuoteRiskEvaluator(policy).evaluate(quote).allowed)

    def test_backtest_executes_a_cross_and_tracks_fees(self) -> None:
        start = datetime(2025, 1, 1, tzinfo=UTC)
        closes = [10, 9, 8, 9, 11, 12, 11, 9]
        candles = [Candle(start + timedelta(days=index), Decimal(price)) for index, price in enumerate(closes)]
        result = BacktestRunner().run(
            "ETH", candles, MovingAverageCrossStrategy(2, 3), BacktestConfig(Decimal("100"), fee_bps=10)
        )
        self.assertGreaterEqual(result.trade_count, 1)
        self.assertGreater(result.fees_usd, Decimal("0"))
        self.assertEqual(len(result.equity_curve), len(candles))

    def test_stop_loss_closes_position_even_when_strategy_holds(self) -> None:
        start = datetime(2025, 1, 1, tzinfo=UTC)
        candles = [Candle(start + timedelta(days=index), Decimal(price)) for index, price in enumerate([10, 10, 8])]
        result = BacktestRunner().run(
            "ETH", candles, BuyThenHold(), BacktestConfig(Decimal("100"), exits=ExitPolicy(stop_loss=Decimal("0.10")))
        )
        self.assertEqual(result.trade_count, 2)
        self.assertEqual(result.completed_trades[0].exit_reason, "stop loss")
        self.assertEqual(result.win_rate, Decimal("0"))
        self.assertGreater(result.max_drawdown, Decimal("0"))

    def test_rsi_strategy_reports_overbought_signal(self) -> None:
        start = datetime(2025, 1, 1, tzinfo=UTC)
        candles = [Candle(start + timedelta(days=index), Decimal(index + 1)) for index in range(4)]
        signal = RsiStrategy(period=3).evaluate(candles)
        self.assertEqual(signal.action, "sell")


    def test_backtest_can_load_candles_from_market_data_provider(self) -> None:
        start = datetime(2025, 1, 1, tzinfo=UTC)
        candles = [Candle(start + timedelta(days=index), Decimal(price)) for index, price in enumerate([10, 9, 8, 9, 11])]
        provider = InMemoryMarketDataProvider({"ETH": candles})
        result = BacktestRunner().run_from_provider(
            "ETH",
            provider,
            start,
            start + timedelta(days=5),
            MovingAverageCrossStrategy(2, 3),
            BacktestConfig(Decimal("100")),
        )
        self.assertEqual(len(result.equity_curve), 5)

    def test_backtest_rejects_unsorted_candles(self) -> None:
        start = datetime(2025, 1, 1, tzinfo=UTC)
        candles = [
            Candle(start + timedelta(days=1), Decimal("10")),
            Candle(start, Decimal("9")),
        ]
        with self.assertRaises(ValueError):
            BacktestRunner().run("ETH", candles, MovingAverageCrossStrategy(2, 3), BacktestConfig(Decimal("100")))

class BuyThenHold:
    name = "buy-then-hold"

    def evaluate(self, candles: list[Candle]) -> Signal:
        return Signal("buy", "initial entry") if len(candles) == 1 else Signal.hold()
