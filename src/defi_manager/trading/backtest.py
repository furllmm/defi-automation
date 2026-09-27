from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from defi_manager.domain.models import ExecutionIntent, PnLTracker, PortfolioState, Position
from defi_manager.trading.market import Candle
from defi_manager.trading.strategy import Signal, Strategy


@dataclass(frozen=True)
class ExitPolicy:
    """Optional paper-only exits expressed as fractions (for example, 0.10 = 10%)."""

    stop_loss: Decimal | None = None
    take_profit: Decimal | None = None
    cooldown_candles: int = 0

    def __post_init__(self) -> None:
        for name, value in (("stop_loss", self.stop_loss), ("take_profit", self.take_profit)):
            if value is not None and not Decimal("0") < value < Decimal("1"):
                raise ValueError(f"{name} must be between 0 and 1")
        if self.cooldown_candles < 0:
            raise ValueError("cooldown_candles cannot be negative")


@dataclass(frozen=True)
class BacktestConfig:
    initial_cash_usd: Decimal
    fee_bps: int = 0
    slippage_bps: int = 0
    position_size_fraction: Decimal = Decimal("1")
    exits: ExitPolicy = field(default_factory=ExitPolicy)

    def __post_init__(self) -> None:
        if self.initial_cash_usd <= 0:
            raise ValueError("initial_cash_usd must be positive")
        if self.fee_bps < 0 or self.slippage_bps < 0:
            raise ValueError("fees and slippage cannot be negative")
        if not Decimal("0") < self.position_size_fraction <= Decimal("1"):
            raise ValueError("position_size_fraction must be in (0, 1]")


@dataclass(frozen=True)
class CompletedTrade:
    entry_price_usd: Decimal
    exit_price_usd: Decimal
    quantity: Decimal
    pnl_usd: Decimal
    exit_reason: str


@dataclass(frozen=True)
class BacktestResult:
    final_equity_usd: Decimal
    net_pnl_usd: Decimal
    roi: Decimal
    trade_count: int
    fees_usd: Decimal
    max_drawdown: Decimal
    win_rate: Decimal | None
    profit_factor: Decimal | None
    completed_trades: tuple[CompletedTrade, ...]
    equity_curve: tuple[Decimal, ...] = field(default_factory=tuple)


class BacktestRunner:
    """Long-only deterministic paper backtest; it cannot send any transaction."""

    def run(self, asset: str, candles: list[Candle], strategy: Strategy, config: BacktestConfig) -> BacktestResult:
        if len(candles) < 2:
            raise ValueError("at least two candles are required")
        portfolio = PortfolioState(cash_usd=config.initial_cash_usd)
        pnl = PnLTracker()
        equity_curve: list[Decimal] = []
        completed: list[CompletedTrade] = []
        cooldown_until = -1
        trades = 0
        for index, candle in enumerate(candles):
            position = portfolio.positions.get(asset)
            signal, exit_reason = self._signal_with_exits(strategy.evaluate(candles[: index + 1]), position, candle, config.exits)
            if signal.action == "buy" and portfolio.cash_usd > 0 and index >= cooldown_until:
                budget = portfolio.cash_usd * config.position_size_fraction
                intent = self._buy(asset, budget, candle.close_usd, config)
                pnl.record_fill(portfolio, intent)
                portfolio.apply_fill(intent)
                trades += 1
            elif signal.action == "sell" and position is not None and position.quantity > 0:
                intent = self._sell(asset, position.quantity, candle.close_usd, config)
                trade_pnl = (intent.price_usd - position.average_entry_usd) * intent.quantity - intent.estimated_fee_usd
                completed.append(CompletedTrade(position.average_entry_usd, intent.price_usd, intent.quantity, trade_pnl, exit_reason or signal.reason))
                pnl.record_fill(portfolio, intent)
                portfolio.apply_fill(intent)
                cooldown_until = index + config.exits.cooldown_candles + 1
                trades += 1
            equity_curve.append(portfolio.market_value_usd({asset: candle.close_usd}))
        final_equity = equity_curve[-1]
        net_pnl = final_equity - config.initial_cash_usd
        return BacktestResult(final_equity, net_pnl, net_pnl / config.initial_cash_usd, trades, pnl.fees_usd, _max_drawdown(equity_curve), _win_rate(completed), _profit_factor(completed), tuple(completed), tuple(equity_curve))

    @staticmethod
    def _signal_with_exits(signal: Signal, position: Position | None, candle: Candle, exits: ExitPolicy) -> tuple[Signal, str | None]:
        if position is None or position.quantity <= 0:
            return signal, None
        entry = position.average_entry_usd
        if exits.stop_loss is not None and candle.close_usd <= entry * (Decimal("1") - exits.stop_loss):
            return Signal("sell", "stop loss"), "stop loss"
        if exits.take_profit is not None and candle.close_usd >= entry * (Decimal("1") + exits.take_profit):
            return Signal("sell", "take profit"), "take profit"
        return signal, None

    @staticmethod
    def _buy(asset: str, budget: Decimal, close: Decimal, config: BacktestConfig) -> ExecutionIntent:
        price = close * (Decimal("1") + Decimal(config.slippage_bps) / Decimal("10000"))
        quantity = budget / (price * (Decimal("1") + Decimal(config.fee_bps) / Decimal("10000")))
        fee = quantity * price * Decimal(config.fee_bps) / Decimal("10000")
        return ExecutionIntent(asset, "buy", quantity, price, config.slippage_bps, fee)

    @staticmethod
    def _sell(asset: str, quantity: Decimal, close: Decimal, config: BacktestConfig) -> ExecutionIntent:
        price = close * (Decimal("1") - Decimal(config.slippage_bps) / Decimal("10000"))
        fee = quantity * price * Decimal(config.fee_bps) / Decimal("10000")
        return ExecutionIntent(asset, "sell", quantity, price, config.slippage_bps, fee)


def _max_drawdown(equity_curve: list[Decimal]) -> Decimal:
    peak = equity_curve[0]
    drawdown = Decimal("0")
    for value in equity_curve:
        peak = max(peak, value)
        if peak > 0:
            drawdown = max(drawdown, (peak - value) / peak)
    return drawdown


def _win_rate(trades: list[CompletedTrade]) -> Decimal | None:
    if not trades:
        return None
    return Decimal(sum(trade.pnl_usd > 0 for trade in trades)) / Decimal(len(trades))


def _profit_factor(trades: list[CompletedTrade]) -> Decimal | None:
    gains = sum((trade.pnl_usd for trade in trades if trade.pnl_usd > 0), Decimal("0"))
    losses = -sum((trade.pnl_usd for trade in trades if trade.pnl_usd < 0), Decimal("0"))
    if losses == 0:
        return None if gains == 0 else Decimal("Infinity")
    return gains / losses
