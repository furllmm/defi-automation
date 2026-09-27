from decimal import Decimal

from defi_manager.domain.models import PortfolioState
from defi_manager.domain.treasury import Treasury


def test_treasury_snapshot_uses_portfolio_equity():
    portfolio = PortfolioState(cash_usd=Decimal("100"))
    treasury = Treasury.default()

    snapshot = treasury.snapshot(portfolio, {})

    assert snapshot.total_equity_usd == Decimal("100")
    assert snapshot.cash_usd == Decimal("100")
    assert snapshot.invested_usd == Decimal("0")
    assert snapshot.target_amounts_usd["trading"] == Decimal("20")
    assert snapshot.target_amounts_usd["reserve"] == Decimal("15")
    assert snapshot.actual_amounts_usd == {}


def test_treasury_snapshot_includes_position_value():
    portfolio = PortfolioState(cash_usd=Decimal("50"))
    from defi_manager.domain.models import Position
    portfolio.positions["ETH"] = Position(quantity=Decimal("2"), average_entry_usd=Decimal("20"))
    treasury = Treasury.default()

    snapshot = treasury.snapshot(portfolio, {"ETH": Decimal("30")})

    assert snapshot.total_equity_usd == Decimal("110")
    assert snapshot.invested_usd == Decimal("60")
    assert snapshot.target_amounts_usd["lending"] == Decimal("33")


def test_unknown_treasury_module_is_rejected():
    treasury = Treasury.default()
    try:
        treasury.allocation_for("unknown")
    except KeyError:
        pass
    else:
        raise AssertionError("unknown treasury module should raise KeyError")


def test_treasury_snapshot_tracks_actual_module_exposure():
    portfolio = PortfolioState(cash_usd=Decimal("1000"))
    treasury = Treasury.default()

    snapshot = treasury.snapshot(
        portfolio,
        {},
        {"trading": Decimal("120"), "lending": Decimal("80")},
    )

    assert snapshot.actual_amounts_usd["trading"] == Decimal("120")
    assert snapshot.actual_amounts_usd["lending"] == Decimal("80")


def test_treasury_rejects_actual_exposure_above_equity():
    portfolio = PortfolioState(cash_usd=Decimal("100"))
    treasury = Treasury.default()

    try:
        treasury.snapshot(portfolio, {}, {"trading": Decimal("101")})
    except ValueError:
        pass
    else:
        raise AssertionError("actual treasury exposure above equity should be rejected")
