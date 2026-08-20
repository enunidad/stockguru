from dataclasses import FrozenInstanceError

import pytest

from src.schemas import (
    ForecastPoint,
    ForecastRequest,
    ForecastResponse,
    ForecastSummary,
    HoldingForecast,
    HoldingInput,
    HoldingProjectionResult,
)


# =========================================================
# HoldingInput
# =========================================================


def test_holding_input_sets_required_fields() -> None:
    holding = HoldingInput(
        ticker="AAPL",
        shares=10.0,
    )

    assert holding.ticker == "AAPL"
    assert holding.shares == pytest.approx(10.0)


def test_holding_input_uses_defaults() -> None:
    holding = HoldingInput(
        ticker="AAPL",
        shares=10.0,
    )

    assert holding.average_cost is None

    assert holding.contribution_weight == pytest.approx(
        0.0
    )


def test_holding_input_accepts_optional_values() -> None:
    holding = HoldingInput(
        ticker="AAPL",
        shares=10.0,
        average_cost=125.50,
        contribution_weight=0.5,
    )

    assert holding.average_cost == pytest.approx(
        125.50
    )

    assert holding.contribution_weight == pytest.approx(
        0.5
    )


def test_holding_input_is_immutable() -> None:
    holding = HoldingInput(
        ticker="AAPL",
        shares=10.0,
    )

    with pytest.raises(
        FrozenInstanceError
    ):
        holding.shares = 20.0


# =========================================================
# ForecastRequest
# =========================================================


def test_forecast_request_uses_defaults() -> None:
    holding = HoldingInput(
        ticker="AAPL",
        shares=10.0,
    )

    request = ForecastRequest(
        holdings=[
            holding,
        ]
    )

    assert request.holdings == [
        holding,
    ]

    assert request.years == 10

    assert request.contribution_amount == pytest.approx(
        0.0
    )

    assert request.contribution_frequency == "monthly"

    assert request.drip is True


def test_forecast_request_accepts_custom_values() -> None:
    request = ForecastRequest(
        holdings=[
            HoldingInput(
                ticker="AAPL",
                shares=10.0,
                contribution_weight=1.0,
            )
        ],
        years=20,
        contribution_amount=500.0,
        contribution_frequency="quarterly",
        drip=False,
    )

    assert request.years == 20

    assert request.contribution_amount == pytest.approx(
        500.0
    )

    assert request.contribution_frequency == "quarterly"

    assert request.drip is False


def test_forecast_request_is_immutable() -> None:
    request = ForecastRequest(
        holdings=[
            HoldingInput(
                ticker="AAPL",
                shares=10.0,
            )
        ]
    )

    with pytest.raises(
        FrozenInstanceError
    ):
        request.years = 25


# =========================================================
# ForecastSummary
# =========================================================


def test_forecast_summary_stores_values() -> None:
    summary = ForecastSummary(
        initial_investment=1000.0,
        current_growth=200.0,
        future_contributions=5000.0,
        stock_growth=3000.0,
        dividends=500.0,
        future_value=9700.0,
    )

    assert summary.initial_investment == pytest.approx(
        1000.0
    )

    assert summary.current_growth == pytest.approx(
        200.0
    )

    assert summary.future_contributions == pytest.approx(
        5000.0
    )

    assert summary.stock_growth == pytest.approx(
        3000.0
    )

    assert summary.dividends == pytest.approx(
        500.0
    )

    assert summary.future_value == pytest.approx(
        9700.0
    )


def test_forecast_summary_allows_negative_current_growth() -> None:
    summary = ForecastSummary(
        initial_investment=1000.0,
        current_growth=-250.0,
        future_contributions=0.0,
        stock_growth=100.0,
        dividends=20.0,
        future_value=870.0,
    )

    assert summary.current_growth == pytest.approx(
        -250.0
    )


def test_forecast_summary_is_immutable() -> None:
    summary = ForecastSummary(
        initial_investment=1000.0,
        current_growth=0.0,
        future_contributions=0.0,
        stock_growth=0.0,
        dividends=0.0,
        future_value=1000.0,
    )

    with pytest.raises(
        FrozenInstanceError
    ):
        summary.future_value = 2000.0


# =========================================================
# ForecastPoint
# =========================================================


def test_forecast_point_stores_year_and_value() -> None:
    point = ForecastPoint(
        year=5,
        value=12345.67,
    )

    assert point.year == 5

    assert point.value == pytest.approx(
        12345.67
    )


def test_forecast_point_is_immutable() -> None:
    point = ForecastPoint(
        year=1,
        value=1000.0,
    )

    with pytest.raises(
        FrozenInstanceError
    ):
        point.value = 2000.0


# =========================================================
# HoldingForecast
# =========================================================


def test_holding_forecast_stores_projection_values() -> None:
    holding = HoldingForecast(
        ticker="AAPL",
        initial_investment=1000.0,
        current_growth=200.0,
        contributions=1200.0,
        growth=500.0,
        dividends=100.0,
        future_value=3000.0,
        dividend_yield=0.01,
        purchased_shares=20.0,
        drip_shares=1.5,
        total_shares=21.5,
        ending_price=140.0,
    )

    assert holding.ticker == "AAPL"

    assert holding.initial_investment == pytest.approx(
        1000.0
    )

    assert holding.current_growth == pytest.approx(
        200.0
    )

    assert holding.contributions == pytest.approx(
        1200.0
    )

    assert holding.growth == pytest.approx(
        500.0
    )

    assert holding.dividends == pytest.approx(
        100.0
    )

    assert holding.future_value == pytest.approx(
        3000.0
    )

    assert holding.dividend_yield == pytest.approx(
        0.01
    )

    assert holding.purchased_shares == pytest.approx(
        20.0
    )

    assert holding.drip_shares == pytest.approx(
        1.5
    )

    assert holding.total_shares == pytest.approx(
        21.5
    )

    assert holding.ending_price == pytest.approx(
        140.0
    )


def test_holding_forecast_is_immutable() -> None:
    holding = HoldingForecast(
        ticker="AAPL",
        initial_investment=1000.0,
        current_growth=0.0,
        contributions=0.0,
        growth=0.0,
        dividends=0.0,
        future_value=1000.0,
        dividend_yield=0.0,
        purchased_shares=10.0,
        drip_shares=0.0,
        total_shares=10.0,
        ending_price=100.0,
    )

    with pytest.raises(
        FrozenInstanceError
    ):
        holding.ticker = "MSFT"


# =========================================================
# HoldingProjectionResult
# =========================================================


def test_holding_projection_result_stores_internal_projection() -> None:
    timeline = [
        ForecastPoint(
            year=0,
            value=1000.0,
        ),
        ForecastPoint(
            year=1,
            value=1200.0,
        ),
    ]

    result = HoldingProjectionResult(
        ticker="AAPL",
        initial_investment=900.0,
        current_growth=100.0,
        contributions=0.0,
        growth=150.0,
        dividends=50.0,
        future_value=1200.0,
        dividend_yield=0.02,
        purchased_shares=10.0,
        drip_shares=0.5,
        total_shares=10.5,
        ending_price=110.0,
        timeline=timeline,
    )

    assert result.ticker == "AAPL"

    assert result.initial_investment == pytest.approx(
        900.0
    )

    assert result.current_growth == pytest.approx(
        100.0
    )

    assert result.contributions == pytest.approx(
        0.0
    )

    assert result.growth == pytest.approx(
        150.0
    )

    assert result.dividends == pytest.approx(
        50.0
    )

    assert result.future_value == pytest.approx(
        1200.0
    )

    assert result.dividend_yield == pytest.approx(
        0.02
    )

    assert result.purchased_shares == pytest.approx(
        10.0
    )

    assert result.drip_shares == pytest.approx(
        0.5
    )

    assert result.total_shares == pytest.approx(
        10.5
    )

    assert result.ending_price == pytest.approx(
        110.0
    )

    assert result.timeline == timeline


def test_holding_projection_result_is_immutable() -> None:
    result = HoldingProjectionResult(
        ticker="AAPL",
        initial_investment=1000.0,
        current_growth=0.0,
        contributions=0.0,
        growth=0.0,
        dividends=0.0,
        future_value=1000.0,
        dividend_yield=0.0,
        purchased_shares=10.0,
        drip_shares=0.0,
        total_shares=10.0,
        ending_price=100.0,
        timeline=[],
    )

    with pytest.raises(
        FrozenInstanceError
    ):
        result.future_value = 2000.0


# =========================================================
# ForecastResponse
# =========================================================


def test_forecast_response_stores_nested_objects() -> None:
    summary = ForecastSummary(
        initial_investment=1000.0,
        current_growth=200.0,
        future_contributions=1200.0,
        stock_growth=500.0,
        dividends=100.0,
        future_value=3000.0,
    )

    timeline = [
        ForecastPoint(
            year=0,
            value=1200.0,
        ),
        ForecastPoint(
            year=1,
            value=3000.0,
        ),
    ]

    holdings = [
        HoldingForecast(
            ticker="AAPL",
            initial_investment=1000.0,
            current_growth=200.0,
            contributions=1200.0,
            growth=500.0,
            dividends=100.0,
            future_value=3000.0,
            dividend_yield=0.01,
            purchased_shares=20.0,
            drip_shares=1.0,
            total_shares=21.0,
            ending_price=140.0,
        )
    ]

    response = ForecastResponse(
        summary=summary,
        timeline=timeline,
        holdings=holdings,
    )

    assert response.summary == summary
    assert response.timeline == timeline
    assert response.holdings == holdings


# =========================================================
# ForecastResponse.to_dict
# =========================================================


def test_forecast_response_to_dict_serializes_nested_dataclasses() -> None:
    response = ForecastResponse(
        summary=ForecastSummary(
            initial_investment=1000.0,
            current_growth=200.0,
            future_contributions=1200.0,
            stock_growth=500.0,
            dividends=100.0,
            future_value=3000.0,
        ),
        timeline=[
            ForecastPoint(
                year=0,
                value=1200.0,
            ),
            ForecastPoint(
                year=1,
                value=3000.0,
            ),
        ],
        holdings=[
            HoldingForecast(
                ticker="AAPL",
                initial_investment=1000.0,
                current_growth=200.0,
                contributions=1200.0,
                growth=500.0,
                dividends=100.0,
                future_value=3000.0,
                dividend_yield=0.01,
                purchased_shares=20.0,
                drip_shares=1.0,
                total_shares=21.0,
                ending_price=140.0,
            )
        ],
    )

    result = response.to_dict()

    assert result == {
        "summary": {
            "initial_investment": 1000.0,
            "current_growth": 200.0,
            "future_contributions": 1200.0,
            "stock_growth": 500.0,
            "dividends": 100.0,
            "future_value": 3000.0,
        },
        "timeline": [
            {
                "year": 0,
                "value": 1200.0,
            },
            {
                "year": 1,
                "value": 3000.0,
            },
        ],
        "holdings": [
            {
                "ticker": "AAPL",
                "initial_investment": 1000.0,
                "current_growth": 200.0,
                "contributions": 1200.0,
                "growth": 500.0,
                "dividends": 100.0,
                "future_value": 3000.0,
                "dividend_yield": 0.01,
                "purchased_shares": 20.0,
                "drip_shares": 1.0,
                "total_shares": 21.0,
                "ending_price": 140.0,
            }
        ],
    }


def test_forecast_response_to_dict_returns_plain_data() -> None:
    response = ForecastResponse(
        summary=ForecastSummary(
            initial_investment=1000.0,
            current_growth=0.0,
            future_contributions=0.0,
            stock_growth=0.0,
            dividends=0.0,
            future_value=1000.0,
        ),
        timeline=[],
        holdings=[],
    )

    result = response.to_dict()

    assert isinstance(
        result,
        dict,
    )

    assert isinstance(
        result["summary"],
        dict,
    )

    assert isinstance(
        result["timeline"],
        list,
    )

    assert isinstance(
        result["holdings"],
        list,
    )


def test_forecast_response_is_immutable() -> None:
    response = ForecastResponse(
        summary=ForecastSummary(
            initial_investment=1000.0,
            current_growth=0.0,
            future_contributions=0.0,
            stock_growth=0.0,
            dividends=0.0,
            future_value=1000.0,
        ),
        timeline=[],
        holdings=[],
    )

    with pytest.raises(
        FrozenInstanceError
    ):
        response.timeline = []