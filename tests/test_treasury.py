from decimal import Decimal

from defi_manager.domain.models import PortfolioState
from defi_manager.domain.treasury import CapitalAllocation, Treasury


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


def test_treasury_accepts_typed_capital_allocations():
    portfolio = PortfolioState(cash_usd=Decimal("1000"))
    treasury = Treasury.default()
    snapshot = treasury.snapshot(
        portfolio,
        {},
        [CapitalAllocation("trading", Decimal("120")), CapitalAllocation("trading", Decimal("30"))],
    )
    assert snapshot.actual_allocation("trading") == Decimal("150")


def test_capital_allocation_rejects_invalid_values():
    try:
        CapitalAllocation("", Decimal("1"))
    except ValueError:
        pass
    else:
        raise AssertionError("empty module should be rejected")

    try:
        CapitalAllocation("trading", Decimal("-1"))
    except ValueError:
        pass
    else:
        raise AssertionError("negative allocation should be rejected")


def test_treasury_snapshot_exposes_typed_allocations():
    portfolio = PortfolioState(cash_usd=Decimal("500"))
    treasury = Treasury.default()

    snapshot = treasury.snapshot(portfolio, {}, {"trading": Decimal("125")})

    assert snapshot.allocations[0].module == "trading"
    assert snapshot.allocations[0].amount_usd == Decimal("125")


def test_negative_capital_allocation_is_rejected():
    from defi_manager.domain.treasury import CapitalAllocation
    try:
        CapitalAllocation("trading", Decimal("-1"))
    except ValueError:
        pass
    else:
        raise AssertionError("negative capital allocation should be rejected")


def test_treasury_applies_allocation_change():
    from defi_manager.domain.treasury import AllocationChange
    treasury = Treasury.default()
    actual = treasury.apply_change({"trading": Decimal("100")}, AllocationChange("trading", Decimal("25")))
    assert actual["trading"] == Decimal("125")


def test_treasury_deallocation_cannot_go_below_zero():
    from defi_manager.domain.treasury import AllocationChange
    treasury = Treasury.default()
    try:
        treasury.apply_change({"trading": Decimal("10")}, AllocationChange("trading", Decimal("-11")))
    except ValueError:
        pass
    else:
        raise AssertionError("allocation cannot become negative")


def test_zero_allocation_change_is_rejected():
    from defi_manager.domain.treasury import AllocationChange
    try:
        AllocationChange("trading", Decimal("0"))
    except ValueError:
        pass
    else:
        raise AssertionError("zero allocation change should be rejected")


def test_treasury_transfer_allocates_cash():
    from defi_manager.domain.treasury import AllocationChange
    portfolio = PortfolioState(cash_usd=Decimal("100"))
    treasury = Treasury.default()
    actual = treasury.transfer(portfolio, {}, AllocationChange("trading", Decimal("40")))
    assert portfolio.cash_usd == Decimal("60")
    assert actual["trading"] == Decimal("40")


def test_treasury_transfer_deallocates_back_to_cash():
    from defi_manager.domain.treasury import AllocationChange
    portfolio = PortfolioState(cash_usd=Decimal("60"))
    treasury = Treasury.default()
    actual = treasury.transfer(portfolio, {"trading": Decimal("40")}, AllocationChange("trading", Decimal("-25")))
    assert portfolio.cash_usd == Decimal("85")
    assert actual["trading"] == Decimal("15")


def test_treasury_transfer_rejects_insufficient_cash():
    from defi_manager.domain.treasury import AllocationChange
    portfolio = PortfolioState(cash_usd=Decimal("10"))
    treasury = Treasury.default()
    try:
        treasury.transfer(portfolio, {}, AllocationChange("trading", Decimal("11")))
    except ValueError:
        pass
    else:
        raise AssertionError("insufficient cash should be rejected")


def test_treasury_rebalance_moves_capital_between_modules():
    from defi_manager.domain.treasury import AllocationChange
    portfolio = PortfolioState(cash_usd=Decimal("100"))
    treasury = Treasury.default()
    actual = treasury.rebalance(
        portfolio,
        {"trading": Decimal("40"), "lending": Decimal("20")},
        (AllocationChange("trading", Decimal("-10")), AllocationChange("lending", Decimal("10"))),
    )
    assert portfolio.cash_usd == Decimal("100")
    assert actual == {"trading": Decimal("30"), "lending": Decimal("30")}


def test_treasury_rebalance_rolls_back_cash_on_failure():
    from defi_manager.domain.treasury import AllocationChange
    portfolio = PortfolioState(cash_usd=Decimal("100"))
    treasury = Treasury.default()
    try:
        treasury.rebalance(
            portfolio,
            {"trading": Decimal("20")},
            (AllocationChange("trading", Decimal("10")), AllocationChange("lending", Decimal("-1"))),
        )
    except ValueError:
        pass
    else:
        raise AssertionError("invalid rebalance should fail")
    assert portfolio.cash_usd == Decimal("100")
