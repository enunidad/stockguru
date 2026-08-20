import math

import pytest

from src.calculations import (
    GROWTH_HALF_LIFE_YEARS,
    HoldingProjectionState,
    annual_to_monthly_rate,
    apply_contribution,
    apply_dividend,
    apply_price_growth,
    decayed_annual_growth_rate,
    project_holding,
    total_shares,
    total_value,
)


# =========================================================
# annual_to_monthly_rate
# =========================================================


def test_annual_to_monthly_rate_preserves_annual_compounding() -> None:
    annual_rate = 0.12

    monthly_rate = annual_to_monthly_rate(
        annual_rate
    )

    compounded = (
        (1.0 + monthly_rate) ** 12
        - 1.0
    )

    assert compounded == pytest.approx(
        annual_rate
    )


def test_annual_to_monthly_rate_zero_returns_zero() -> None:
    assert annual_to_monthly_rate(0.0) == pytest.approx(
        0.0
    )


# =========================================================
# decayed_annual_growth_rate
# =========================================================


def test_decayed_growth_starts_at_historical_rate() -> None:
    result = decayed_annual_growth_rate(
        historical_growth_rate=0.15,
        elapsed_years=0.0,
    )

    assert result == pytest.approx(
        0.15
    )


def test_decayed_growth_reaches_halfway_after_one_half_life() -> None:
    result = decayed_annual_growth_rate(
        historical_growth_rate=0.15,
        elapsed_years=GROWTH_HALF_LIFE_YEARS,
        long_term_growth_rate=0.05,
    )

    assert result == pytest.approx(
        0.10
    )


def test_decayed_growth_does_not_raise_low_growth_stock() -> None:
    result = decayed_annual_growth_rate(
        historical_growth_rate=0.03,
        elapsed_years=20.0,
        long_term_growth_rate=0.05,
    )

    assert result == pytest.approx(
        0.03
    )


def test_decayed_growth_preserves_negative_growth() -> None:
    result = decayed_annual_growth_rate(
        historical_growth_rate=-0.10,
        elapsed_years=20.0,
        long_term_growth_rate=0.05,
    )

    assert result == pytest.approx(
        -0.10
    )


def test_decayed_growth_rejects_negative_elapsed_years() -> None:
    with pytest.raises(
        ValueError,
        match="Elapsed years cannot be negative.",
    ):
        decayed_annual_growth_rate(
            historical_growth_rate=0.10,
            elapsed_years=-1.0,
        )


@pytest.mark.parametrize(
    "half_life",
    [
        0.0,
        -1.0,
        math.inf,
        math.nan,
    ],
)
def test_decayed_growth_rejects_invalid_half_life(
    half_life,
) -> None:
    with pytest.raises(
        ValueError,
        match="Growth half-life must be",
    ):
        decayed_annual_growth_rate(
            historical_growth_rate=0.10,
            elapsed_years=1.0,
            half_life_years=half_life,
        )


# =========================================================
# HoldingProjectionState helpers
# =========================================================


def test_total_shares_combines_investment_and_drip_shares() -> None:
    state = HoldingProjectionState(
        ticker="AAPL",
        price=100.0,
        investment_shares=10.0,
        dividend_shares=2.5,
    )

    assert total_shares(state) == pytest.approx(
        12.5
    )


def test_total_value_includes_dividend_cash() -> None:
    state = HoldingProjectionState(
        ticker="AAPL",
        price=100.0,
        investment_shares=10.0,
        dividend_shares=2.0,
        dividend_cash=50.0,
    )

    assert total_value(state) == pytest.approx(
        1250.0
    )


def test_apply_price_growth_updates_price() -> None:
    state = HoldingProjectionState(
        ticker="AAPL",
        price=100.0,
        investment_shares=10.0,
    )

    apply_price_growth(
        state,
        0.05,
    )

    assert state.price == pytest.approx(
        105.0
    )


# =========================================================
# Contributions
# =========================================================


def test_apply_contribution_purchases_shares_at_current_price() -> None:
    state = HoldingProjectionState(
        ticker="AAPL",
        price=100.0,
        investment_shares=10.0,
    )

    apply_contribution(
        state,
        250.0,
    )

    assert state.investment_shares == pytest.approx(
        12.5
    )

    assert state.contributions == pytest.approx(
        250.0
    )


@pytest.mark.parametrize(
    "amount",
    [
        0.0,
        -100.0,
    ],
)
def test_apply_contribution_ignores_non_positive_amount(
    amount,
) -> None:
    state = HoldingProjectionState(
        ticker="AAPL",
        price=100.0,
        investment_shares=10.0,
    )

    apply_contribution(
        state,
        amount,
    )

    assert state.investment_shares == pytest.approx(
        10.0
    )

    assert state.contributions == pytest.approx(
        0.0
    )


# =========================================================
# Dividends
# =========================================================


def test_apply_dividend_with_drip_purchases_dividend_shares() -> None:
    state = HoldingProjectionState(
        ticker="AAPL",
        price=100.0,
        investment_shares=10.0,
    )

    apply_dividend(
        state,
        1.0,
        drip=True,
    )

    assert state.dividend_shares == pytest.approx(
        0.1
    )

    assert state.dividend_cash == pytest.approx(
        0.0
    )


def test_apply_dividend_without_drip_accumulates_cash() -> None:
    state = HoldingProjectionState(
        ticker="AAPL",
        price=100.0,
        investment_shares=10.0,
    )

    apply_dividend(
        state,
        1.0,
        drip=False,
    )

    assert state.dividend_shares == pytest.approx(
        0.0
    )

    assert state.dividend_cash == pytest.approx(
        10.0
    )


def test_drip_dividend_includes_existing_drip_shares() -> None:
    state = HoldingProjectionState(
        ticker="AAPL",
        price=100.0,
        investment_shares=10.0,
        dividend_shares=2.0,
    )

    apply_dividend(
        state,
        1.0,
        drip=True,
    )

    # 12 shares produce $12.
    # $12 / $100 = 0.12 new shares.
    assert state.dividend_shares == pytest.approx(
        2.12
    )


def test_apply_dividend_ignores_zero_dividend() -> None:
    state = HoldingProjectionState(
        ticker="AAPL",
        price=100.0,
        investment_shares=10.0,
    )

    apply_dividend(
        state,
        0.0,
        drip=True,
    )

    assert state.dividend_shares == pytest.approx(
        0.0
    )

    assert state.dividend_cash == pytest.approx(
        0.0
    )


# =========================================================
# project_holding
# =========================================================


def test_project_holding_without_growth_or_dividends_preserves_value() -> None:
    result = project_holding(
        ticker=" aapl ",
        shares=10.0,
        current_price=100.0,
        initial_investment=800.0,
        annual_growth_rate=0.0,
        annual_dividend_per_share=0.0,
        years=1,
    )

    assert result.ticker == "AAPL"

    assert result.initial_investment == pytest.approx(
        800.0
    )

    # Current market value is $1,000 with an $800 basis.
    assert result.current_growth == pytest.approx(
        200.0
    )

    # No forecast-period price appreciation.
    assert result.growth == pytest.approx(
        0.0
    )

    assert result.contributions == pytest.approx(
        0.0
    )

    assert result.dividends == pytest.approx(
        0.0
    )

    assert result.future_value == pytest.approx(
        1000.0
    )

    assert result.purchased_shares == pytest.approx(
        10.0
    )

    assert result.drip_shares == pytest.approx(
        0.0
    )

    assert result.total_shares == pytest.approx(
        10.0
    )

    assert result.ending_price == pytest.approx(
        100.0
    )

    assert result.dividend_yield == pytest.approx(
        0.0
    )


def test_project_holding_creates_yearly_timeline() -> None:
    result = project_holding(
        ticker="AAPL",
        shares=10.0,
        current_price=100.0,
        initial_investment=1000.0,
        annual_growth_rate=0.0,
        annual_dividend_per_share=0.0,
        years=5,
    )

    assert len(result.timeline) == 6

    assert [
        point.year
        for point in result.timeline
    ] == [
        0,
        1,
        2,
        3,
        4,
        5,
    ]


def test_project_holding_monthly_contributions_are_recorded() -> None:
    result = project_holding(
        ticker="AAPL",
        shares=10.0,
        current_price=100.0,
        initial_investment=1000.0,
        annual_growth_rate=0.0,
        annual_dividend_per_share=0.0,
        years=1,
        contribution_amount=100.0,
        contribution_frequency="monthly",
    )

    assert result.contributions == pytest.approx(
        1200.0
    )

    assert result.purchased_shares == pytest.approx(
        22.0
    )

    assert result.future_value == pytest.approx(
        2200.0
    )

    # Contributions themselves are not stock growth.
    assert result.growth == pytest.approx(
        0.0
    )


@pytest.mark.parametrize(
    (
        "frequency",
        "expected_contributions",
    ),
    [
        ("monthly", 1200.0),
        ("quarterly", 400.0),
        ("annually", 100.0),
    ],
)
def test_project_holding_respects_contribution_frequency(
    frequency,
    expected_contributions,
) -> None:
    result = project_holding(
        ticker="AAPL",
        shares=10.0,
        current_price=100.0,
        initial_investment=1000.0,
        annual_growth_rate=0.0,
        annual_dividend_per_share=0.0,
        years=1,
        contribution_amount=100.0,
        contribution_frequency=frequency,
    )

    assert result.contributions == pytest.approx(
        expected_contributions
    )


def test_project_holding_without_drip_tracks_dividends_as_cash() -> None:
    result = project_holding(
        ticker="AAPL",
        shares=10.0,
        current_price=100.0,
        initial_investment=1000.0,
        annual_growth_rate=0.0,
        annual_dividend_per_share=12.0,
        years=1,
        drip=False,
    )

    assert result.dividends == pytest.approx(
        120.0
    )

    assert result.drip_shares == pytest.approx(
        0.0
    )

    assert result.total_shares == pytest.approx(
        10.0
    )

    assert result.future_value == pytest.approx(
        1120.0
    )

    assert result.dividend_yield == pytest.approx(
        0.12
    )


def test_project_holding_with_drip_increases_share_count() -> None:
    result = project_holding(
        ticker="AAPL",
        shares=10.0,
        current_price=100.0,
        initial_investment=1000.0,
        annual_growth_rate=0.0,
        annual_dividend_per_share=12.0,
        years=1,
        drip=True,
    )

    assert result.drip_shares > 0.0

    assert result.total_shares > 10.0

    assert result.future_value > 1120.0


# =========================================================
# Input Validation
# =========================================================


@pytest.mark.parametrize(
    (
        "override",
        "message",
    ),
    [
        (
            {"shares": -1.0},
            "Shares cannot be negative.",
        ),
        (
            {"current_price": 0.0},
            "Current price must be",
        ),
        (
            {"current_price": math.inf},
            "Current price must be",
        ),
        (
            {"initial_investment": -1.0},
            "Initial investment cannot be negative.",
        ),
        (
            {"years": 0},
            "Forecast years must be greater than zero.",
        ),
        (
            {"contribution_amount": -1.0},
            "Contribution amount cannot be negative.",
        ),
        (
            {"contribution_frequency": "weekly"},
            "Contribution frequency must be",
        ),
        (
            {"annual_growth_rate": math.nan},
            "Annual growth rate must be finite.",
        ),
        (
            {"annual_growth_rate": -1.0},
            "Annual growth rate must be greater than -1.",
        ),
        (
            {"annual_dividend_per_share": -1.0},
            "Annual dividend per share must be",
        ),
        (
            {"annual_dividend_per_share": math.nan},
            "Annual dividend per share must be",
        ),
    ],
)
def test_project_holding_rejects_invalid_inputs(
    override,
    message,
) -> None:
    arguments = {
        "ticker": "AAPL",
        "shares": 10.0,
        "current_price": 100.0,
        "initial_investment": 1000.0,
        "annual_growth_rate": 0.05,
        "annual_dividend_per_share": 1.0,
        "years": 1,
        "contribution_amount": 0.0,
        "contribution_frequency": "monthly",
        "drip": True,
    }

    arguments.update(
        override
    )

    with pytest.raises(
        ValueError,
        match=message,
    ):
        project_holding(
            **arguments
        )