from __future__ import annotations

from dataclasses import fields
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pandas as pd
import pytest

from src.client import MyClient
from src.schemas import (
    ForecastPoint,
    ForecastRequest,
    ForecastResponse,
    ForecastSummary,
    HoldingForecast,
    HoldingInput,
)
from src.service import ForecasterService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_holding(
    *,
    ticker: str = "AAPL",
    shares: float = 10.0,
    average_cost: float | None = 100.0,
    contribution_weight: float = 1.0,
) -> HoldingInput:
    return HoldingInput(
        ticker=ticker,
        shares=shares,
        average_cost=average_cost,
        contribution_weight=contribution_weight,
    )


def make_request(
    *,
    holdings: list[HoldingInput] | None = None,
    years: int = 10,
    contribution_amount: float = 0.0,
    contribution_frequency: str = "monthly",
    drip: bool = True,
) -> ForecastRequest:
    if holdings is None:
        holdings = [
            make_holding(),
        ]

    return ForecastRequest(
        holdings=holdings,
        years=years,
        contribution_amount=contribution_amount,
        contribution_frequency=contribution_frequency,
        drip=drip,
    )


def make_projection_result(
    *,
    ticker: str = "AAPL",
    years: int = 2,
    values: list[float] | None = None,
    overrides: dict | None = None,
):
    """
    Create a lightweight object containing everything _build_response()
    expects from a HoldingProjectionResult.

    This intentionally derives required fields from the schema so this
    helper remains useful if HoldingForecast / ForecastSummary evolve.
    """
    if values is None:
        values = [
            1000.0,
            1100.0,
            1210.0,
        ]

    attrs = {}

    # Every field copied into HoldingForecast.
    for field in fields(HoldingForecast):
        if not field.init:
            continue

        if field.name == "ticker":
            attrs[field.name] = ticker
        elif field.name == "timeline":
            attrs[field.name] = [
                ForecastPoint(
                    year=year,
                    value=values[year],
                )
                for year in range(years + 1)
            ]
        else:
            attrs[field.name] = 0.0

    # Every field consumed when constructing ForecastSummary.
    summary_aliases = {
        "future_contributions": "contributions",
        "stock_growth": "growth",
    }

    for field in fields(ForecastSummary):
        if not field.init:
            continue

        result_name = summary_aliases.get(
            field.name,
            field.name,
        )

        if not hasattr(SimpleNamespace(**attrs), result_name):
            attrs[result_name] = 0.0

    # _build_response accesses result.timeline directly even if it
    # isn't part of HoldingForecast.
    attrs["timeline"] = [
        ForecastPoint(
            year=year,
            value=values[year],
        )
        for year in range(years + 1)
    ]

    if overrides:
        attrs.update(overrides)

    return SimpleNamespace(**attrs)


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_service_uses_provided_client():
    client = AsyncMock(spec=MyClient)

    service = ForecasterService(client)

    assert service._client is client


def test_service_creates_client_when_not_provided():
    with patch(
        "src.service.MyClient",
    ) as client_cls:
        service = ForecasterService()

    client_cls.assert_called_once_with()
    assert service._client is client_cls.return_value


# ---------------------------------------------------------------------------
# Request validation
# ---------------------------------------------------------------------------


def test_validate_request_accepts_valid_request():
    request = make_request()

    ForecasterService._validate_request(request)


def test_validate_request_rejects_empty_holdings():
    request = make_request(
        holdings=[],
    )

    with pytest.raises(
        ValueError,
        match="At least one holding is required",
    ):
        ForecasterService._validate_request(request)


def test_validate_request_rejects_zero_years():
    request = make_request(
        years=0,
    )

    with pytest.raises(
        ValueError,
        match="greater than zero",
    ):
        ForecasterService._validate_request(request)


def test_validate_request_rejects_negative_years():
    request = make_request(
        years=-1,
    )

    with pytest.raises(
        ValueError,
        match="greater than zero",
    ):
        ForecasterService._validate_request(request)


def test_validate_request_accepts_39_years():
    request = make_request(
        years=39,
    )

    ForecasterService._validate_request(request)


def test_validate_request_rejects_40_years():
    request = make_request(
        years=40,
    )

    with pytest.raises(
        ValueError,
        match="less than 40",
    ):
        ForecasterService._validate_request(request)


def test_validate_request_rejects_negative_contribution():
    request = make_request(
        contribution_amount=-1.0,
    )

    with pytest.raises(
        ValueError,
        match="cannot be negative",
    ):
        ForecasterService._validate_request(request)


def test_validate_request_accepts_contribution_below_one_million():
    request = make_request(
        contribution_amount=999_999.99,
    )

    ForecasterService._validate_request(request)


def test_validate_request_rejects_one_million_contribution():
    request = make_request(
        contribution_amount=1_000_000.0,
    )

    with pytest.raises(
        ValueError,
        match="less than 1M",
    ):
        ForecasterService._validate_request(request)


@pytest.mark.parametrize(
    "frequency",
    [
        "monthly",
        "quarterly",
        "annually",
    ],
)
def test_validate_request_accepts_supported_frequency(
    frequency,
):
    request = make_request(
        contribution_frequency=frequency,
    )

    ForecasterService._validate_request(request)


def test_validate_request_rejects_invalid_frequency():
    request = make_request(
        contribution_frequency="weekly",
    )

    with pytest.raises(
        ValueError,
        match="monthly, quarterly, or annually",
    ):
        ForecasterService._validate_request(request)


def test_validate_request_requires_weights_to_sum_to_one_when_contributing():
    request = make_request(
        holdings=[
            make_holding(
                ticker="AAPL",
                contribution_weight=0.7,
            ),
            make_holding(
                ticker="MSFT",
                contribution_weight=0.2,
            ),
        ],
        contribution_amount=500.0,
    )

    with pytest.raises(
        ValueError,
        match="Contribution weights must sum to 1.0",
    ):
        ForecasterService._validate_request(request)


def test_validate_request_accepts_weights_summing_to_one():
    request = make_request(
        holdings=[
            make_holding(
                ticker="AAPL",
                contribution_weight=0.6,
            ),
            make_holding(
                ticker="MSFT",
                contribution_weight=0.4,
            ),
        ],
        contribution_amount=500.0,
    )

    ForecasterService._validate_request(request)


def test_validate_request_does_not_require_weight_sum_without_contributions():
    request = make_request(
        holdings=[
            make_holding(
                ticker="AAPL",
                contribution_weight=0.0,
            ),
            make_holding(
                ticker="MSFT",
                contribution_weight=0.0,
            ),
        ],
        contribution_amount=0.0,
    )

    ForecasterService._validate_request(request)


# ---------------------------------------------------------------------------
# Holding validation
# ---------------------------------------------------------------------------


def test_validate_holding_accepts_valid_holding():
    holding = make_holding()

    ForecasterService._validate_holding(holding)


def test_validate_holding_rejects_empty_ticker():
    holding = make_holding(
        ticker="   ",
    )

    with pytest.raises(
        ValueError,
        match="Ticker cannot be empty",
    ):
        ForecasterService._validate_holding(holding)


def test_validate_holding_accepts_zero_shares():
    holding = make_holding(
        shares=0.0,
    )

    ForecasterService._validate_holding(holding)


def test_validate_holding_rejects_negative_shares():
    holding = make_holding(
        shares=-1.0,
    )

    with pytest.raises(
        ValueError,
        match="Shares cannot be negative",
    ):
        ForecasterService._validate_holding(holding)


def test_validate_holding_accepts_missing_average_cost():
    holding = make_holding(
        average_cost=None,
    )

    ForecasterService._validate_holding(holding)


def test_validate_holding_rejects_zero_average_cost():
    holding = make_holding(
        average_cost=0.0,
    )

    with pytest.raises(
        ValueError,
        match="Average cost must be greater than zero",
    ):
        ForecasterService._validate_holding(holding)


def test_validate_holding_rejects_negative_average_cost():
    holding = make_holding(
        average_cost=-10.0,
    )

    with pytest.raises(
        ValueError,
        match="Average cost must be greater than zero",
    ):
        ForecasterService._validate_holding(holding)


@pytest.mark.parametrize(
    "weight",
    [
        0.0,
        0.25,
        0.5,
        1.0,
    ],
)
def test_validate_holding_accepts_valid_contribution_weight(
    weight,
):
    holding = make_holding(
        contribution_weight=weight,
    )

    ForecasterService._validate_holding(holding)


@pytest.mark.parametrize(
    "weight",
    [
        -0.01,
        1.01,
    ],
)
def test_validate_holding_rejects_invalid_contribution_weight(
    weight,
):
    holding = make_holding(
        contribution_weight=weight,
    )

    with pytest.raises(
        ValueError,
        match="Contribution weight must be between 0 and 1",
    ):
        ForecasterService._validate_holding(holding)


# ---------------------------------------------------------------------------
# CAGR parsing
# ---------------------------------------------------------------------------


def test_read_cagr_returns_float():
    result = ForecasterService._read_cagr(
        {
            "cagr": 0.125,
        }
    )

    assert result == 0.125


def test_read_cagr_accepts_numeric_string():
    result = ForecasterService._read_cagr(
        {
            "cagr": "0.15",
        }
    )

    assert result == 0.15


def test_read_cagr_rejects_missing_cagr():
    with pytest.raises(
        ValueError,
        match="missing CAGR",
    ):
        ForecasterService._read_cagr({})


def test_read_cagr_rejects_non_numeric_cagr():
    with pytest.raises(
        ValueError,
        match="must be numeric",
    ):
        ForecasterService._read_cagr(
            {
                "cagr": "banana",
            }
        )


@pytest.mark.parametrize(
    "value",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
    ],
)
def test_read_cagr_rejects_non_finite_cagr(
    value,
):
    with pytest.raises(
        ValueError,
        match="must be finite",
    ):
        ForecasterService._read_cagr(
            {
                "cagr": value,
            }
        )


def test_read_cagr_accepts_value_above_negative_one():
    result = ForecasterService._read_cagr(
        {
            "cagr": -0.999,
        }
    )

    assert result == -0.999


@pytest.mark.parametrize(
    "value",
    [
        -1.0,
        -1.5,
    ],
)
def test_read_cagr_rejects_negative_one_or_less(
    value,
):
    with pytest.raises(
        ValueError,
        match="greater than -1",
    ):
        ForecasterService._read_cagr(
            {
                "cagr": value,
            }
        )


# ---------------------------------------------------------------------------
# Dividend parsing
# ---------------------------------------------------------------------------


def test_read_annual_dividend_returns_zero_for_empty_data():
    result = ForecasterService._read_annual_dividend([])

    assert result == 0.0


def test_read_annual_dividend_sums_trailing_twelve_months():
    data = [
        {
            "Date": "2024-01-01",
            "Dividend": 10.0,
        },
        {
            "Date": "2025-01-15",
            "Dividend": 0.25,
        },
        {
            "Date": "2025-04-15",
            "Dividend": 0.25,
        },
        {
            "Date": "2025-07-15",
            "Dividend": 0.25,
        },
        {
            "Date": "2025-10-15",
            "Dividend": 0.25,
        },
    ]

    result = ForecasterService._read_annual_dividend(
        data,
    )

    assert result == pytest.approx(1.0)


def test_read_annual_dividend_uses_latest_record_as_reference_date():
    data = [
        {
            "Date": "2023-01-01",
            "Dividend": 50.0,
        },
        {
            "Date": "2024-06-01",
            "Dividend": 1.0,
        },
        {
            "Date": "2025-01-01",
            "Dividend": 2.0,
        },
    ]

    result = ForecasterService._read_annual_dividend(
        data,
    )

    assert result == pytest.approx(3.0)


def test_read_annual_dividend_excludes_exact_cutoff_date():
    data = [
        {
            "Date": "2024-01-01",
            "Dividend": 5.0,
        },
        {
            "Date": "2025-01-01",
            "Dividend": 1.0,
        },
    ]

    result = ForecasterService._read_annual_dividend(
        data,
    )

    # Code uses:
    # date > cutoff_date
    # rather than >=
    assert result == pytest.approx(1.0)


def test_read_annual_dividend_rejects_non_dict_record():
    with pytest.raises(
        ValueError,
        match="must be a dictionary",
    ):
        ForecasterService._read_annual_dividend(
            [
                "bad record",
            ]
        )


def test_read_annual_dividend_requires_date():
    with pytest.raises(
        ValueError,
        match="must contain Date and Dividend",
    ):
        ForecasterService._read_annual_dividend(
            [
                {
                    "Dividend": 1.0,
                },
            ]
        )


def test_read_annual_dividend_requires_dividend():
    with pytest.raises(
        ValueError,
        match="must contain Date and Dividend",
    ):
        ForecasterService._read_annual_dividend(
            [
                {
                    "Date": "2025-01-01",
                },
            ]
        )


def test_read_annual_dividend_rejects_invalid_date():
    with pytest.raises(
        ValueError,
        match="contains invalid data",
    ):
        ForecasterService._read_annual_dividend(
            [
                {
                    "Date": "not-a-date",
                    "Dividend": 1.0,
                },
            ]
        )


def test_read_annual_dividend_rejects_invalid_amount():
    with pytest.raises(
        ValueError,
        match="contains invalid data",
    ):
        ForecasterService._read_annual_dividend(
            [
                {
                    "Date": "2025-01-01",
                    "Dividend": "garbage",
                },
            ]
        )


@pytest.mark.parametrize(
    "value",
    [
        float("nan"),
        float("inf"),
        float("-inf"),
    ],
)
def test_read_annual_dividend_rejects_non_finite_amount(
    value,
):
    with pytest.raises(
        ValueError,
        match="Dividend amount must be finite",
    ):
        ForecasterService._read_annual_dividend(
            [
                {
                    "Date": "2025-01-01",
                    "Dividend": value,
                },
            ]
        )


def test_read_annual_dividend_rejects_negative_amount():
    with pytest.raises(
        ValueError,
        match="cannot be negative",
    ):
        ForecasterService._read_annual_dividend(
            [
                {
                    "Date": "2025-01-01",
                    "Dividend": -0.25,
                },
            ]
        )


# ---------------------------------------------------------------------------
# Preparing holdings
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_prepare_holding_returns_expected_values():
    client = AsyncMock(spec=MyClient)

    client.latest_close.return_value = 150.0

    client.get_analysis.return_value = {
        "cagr": 0.10,
    }

    client.get_dividends.return_value = [
        {
            "Date": "2025-01-15",
            "Dividend": 0.25,
        },
        {
            "Date": "2025-04-15",
            "Dividend": 0.25,
        },
        {
            "Date": "2025-07-15",
            "Dividend": 0.25,
        },
        {
            "Date": "2025-10-15",
            "Dividend": 0.25,
        },
    ]

    service = ForecasterService(client)

    holding = make_holding(
        ticker=" aapl ",
        shares=10.0,
        average_cost=100.0,
    )

    result = await service._prepare_holding(
        holding,
    )

    assert result == {
        "ticker": "AAPL",
        "latest_close": 150.0,
        "initial_investment": 1000.0,
        "annual_growth_rate": 0.10,
        "annual_dividend": pytest.approx(1.0),
    }

    client.latest_close.assert_awaited_once_with(
        "AAPL",
    )

    client.get_analysis.assert_awaited_once_with(
        "AAPL",
        period="10y",
        interval="1d",
        auto_adjust=False,
    )

    client.get_dividends.assert_awaited_once_with(
        "AAPL",
        period="10y",
    )


@pytest.mark.asyncio
async def test_prepare_holding_uses_latest_close_when_average_cost_missing():
    client = AsyncMock(spec=MyClient)

    client.latest_close.return_value = 125.0

    client.get_analysis.return_value = {
        "cagr": 0.08,
    }

    client.get_dividends.return_value = []

    service = ForecasterService(client)

    holding = make_holding(
        shares=4.0,
        average_cost=None,
    )

    result = await service._prepare_holding(
        holding,
    )

    assert result["initial_investment"] == pytest.approx(
        500.0
    )


@pytest.mark.asyncio
async def test_prepare_holding_applies_minimum_growth_rate():
    client = AsyncMock(spec=MyClient)

    client.latest_close.return_value = 100.0

    client.get_analysis.return_value = {
        "cagr": -0.20,
    }

    client.get_dividends.return_value = []

    service = ForecasterService(client)

    result = await service._prepare_holding(
        make_holding()
    )

    assert result["annual_growth_rate"] == pytest.approx(
        0.015
    )


@pytest.mark.asyncio
async def test_prepare_holding_keeps_growth_above_minimum():
    client = AsyncMock(spec=MyClient)

    client.latest_close.return_value = 100.0

    client.get_analysis.return_value = {
        "cagr": 0.12,
    }

    client.get_dividends.return_value = []

    service = ForecasterService(client)

    result = await service._prepare_holding(
        make_holding()
    )

    assert result["annual_growth_rate"] == pytest.approx(
        0.12
    )


# ---------------------------------------------------------------------------
# Forecast orchestration
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_forecast_calls_project_holding_with_prepared_data():
    client = AsyncMock(spec=MyClient)

    service = ForecasterService(client)

    service._prepare_holding = AsyncMock(
        return_value={
            "ticker": "AAPL",
            "latest_close": 150.0,
            "initial_investment": 1000.0,
            "annual_growth_rate": 0.08,
            "annual_dividend": 1.0,
        }
    )

    holding = make_holding(
        ticker="AAPL",
        shares=10.0,
        contribution_weight=1.0,
    )

    request = make_request(
        holdings=[
            holding,
        ],
        years=5,
        contribution_amount=200.0,
        contribution_frequency="monthly",
        drip=True,
    )

    projection = make_projection_result(
        years=5,
        values=[
            1000.0,
            1200.0,
            1400.0,
            1600.0,
            1800.0,
            2000.0,
        ],
    )

    response = ForecastResponse(
        summary=ForecastSummary(
            **{
                field.name: 0.0
                for field in fields(ForecastSummary)
                if field.init
            }
        ),
        timeline=[],
        holdings=[],
    )

    with patch(
        "src.service.project_holding",
        return_value=projection,
    ) as project_mock:
        with patch.object(
            service,
            "_build_response",
            return_value=response,
        ) as build_mock:
            result = await service.forecast(
                request,
            )

    assert result is response

    service._prepare_holding.assert_awaited_once_with(
        holding,
    )

    project_mock.assert_called_once_with(
        ticker="AAPL",
        shares=10.0,
        current_price=150.0,
        initial_investment=1000.0,
        annual_growth_rate=0.08,
        annual_dividend_per_share=1.0,
        years=5,
        contribution_amount=200.0,
        contribution_frequency="monthly",
        drip=True,
    )

    build_mock.assert_called_once_with(
        [
            projection,
        ],
        years=5,
    )


@pytest.mark.asyncio
async def test_forecast_splits_contribution_using_weights():
    client = AsyncMock(spec=MyClient)

    service = ForecasterService(client)

    prepared = {
        "AAPL": {
            "ticker": "AAPL",
            "latest_close": 100.0,
            "initial_investment": 1000.0,
            "annual_growth_rate": 0.08,
            "annual_dividend": 1.0,
        },
        "MSFT": {
            "ticker": "MSFT",
            "latest_close": 200.0,
            "initial_investment": 2000.0,
            "annual_growth_rate": 0.10,
            "annual_dividend": 2.0,
        },
    }

    async def prepare(holding):
        return prepared[
            holding.ticker
        ]

    service._prepare_holding = AsyncMock(
        side_effect=prepare,
    )

    holdings = [
        make_holding(
            ticker="AAPL",
            contribution_weight=0.25,
        ),
        make_holding(
            ticker="MSFT",
            contribution_weight=0.75,
        ),
    ]

    request = make_request(
        holdings=holdings,
        years=5,
        contribution_amount=400.0,
    )

    projection1 = make_projection_result(
        ticker="AAPL",
        years=5,
        values=[
            1,
            2,
            3,
            4,
            5,
            6,
        ],
    )

    projection2 = make_projection_result(
        ticker="MSFT",
        years=5,
        values=[
            1,
            2,
            3,
            4,
            5,
            6,
        ],
    )

    dummy_response = object()

    with patch(
        "src.service.project_holding",
        side_effect=[
            projection1,
            projection2,
        ],
    ) as project_mock:
        with patch.object(
            service,
            "_build_response",
            return_value=dummy_response,
        ):
            await service.forecast(
                request,
            )

    assert project_mock.call_count == 2

    first_call = project_mock.call_args_list[
        0
    ].kwargs

    second_call = project_mock.call_args_list[
        1
    ].kwargs

    assert first_call[
        "contribution_amount"
    ] == pytest.approx(100.0)

    assert second_call[
        "contribution_amount"
    ] == pytest.approx(300.0)


@pytest.mark.asyncio
async def test_forecast_validates_before_preparing_holdings():
    client = AsyncMock(spec=MyClient)

    service = ForecasterService(client)

    service._prepare_holding = AsyncMock()

    request = make_request(
        years=0,
    )

    with pytest.raises(
        ValueError,
        match="greater than zero",
    ):
        await service.forecast(
            request,
        )

    service._prepare_holding.assert_not_awaited()


# ---------------------------------------------------------------------------
# Response construction
# ---------------------------------------------------------------------------


def test_build_response_combines_timelines():
    result1 = make_projection_result(
        ticker="AAPL",
        years=2,
        values=[
            100.0,
            110.0,
            120.0,
        ],
    )

    result2 = make_projection_result(
        ticker="MSFT",
        years=2,
        values=[
            200.0,
            220.0,
            250.0,
        ],
    )

    response = ForecasterService._build_response(
        [
            result1,
            result2,
        ],
        years=2,
    )

    assert isinstance(
        response,
        ForecastResponse,
    )

    assert [
        point.year
        for point in response.timeline
    ] == [
        0,
        1,
        2,
    ]

    assert [
        point.value
        for point in response.timeline
    ] == [
        300.0,
        330.0,
        370.0,
    ]


def test_build_response_creates_one_holding_forecast_per_result():
    result1 = make_projection_result(
        ticker="AAPL",
        years=1,
        values=[
            100.0,
            110.0,
        ],
    )

    result2 = make_projection_result(
        ticker="MSFT",
        years=1,
        values=[
            200.0,
            220.0,
        ],
    )

    response = ForecasterService._build_response(
        [
            result1,
            result2,
        ],
        years=1,
    )

    assert len(
        response.holdings
    ) == 2

    assert all(
        isinstance(
            holding,
            HoldingForecast,
        )
        for holding in response.holdings
    )


def test_build_response_sums_summary_fields():
    overrides1 = {}
    overrides2 = {}

    aliases = {
        "future_contributions": "contributions",
        "stock_growth": "growth",
    }

    expected = {}

    for field in fields(
        ForecastSummary
    ):
        if not field.init:
            continue

        result_field = aliases.get(
            field.name,
            field.name,
        )

        overrides1[
            result_field
        ] = 10.25

        overrides2[
            result_field
        ] = 20.50

        expected[
            field.name
        ] = 30.75

    result1 = make_projection_result(
        ticker="AAPL",
        years=1,
        values=[
            100.0,
            110.0,
        ],
        overrides=overrides1,
    )

    result2 = make_projection_result(
        ticker="MSFT",
        years=1,
        values=[
            200.0,
            220.0,
        ],
        overrides=overrides2,
    )

    response = ForecasterService._build_response(
        [
            result1,
            result2,
        ],
        years=1,
    )

    for name, value in expected.items():
        assert getattr(
            response.summary,
            name,
        ) == pytest.approx(value)


def test_build_response_rounds_portfolio_timeline():
    result1 = make_projection_result(
        years=1,
        values=[
            100.111,
            200.555,
        ],
    )

    result2 = make_projection_result(
        ticker="MSFT",
        years=1,
        values=[
            50.222,
            100.666,
        ],
    )

    response = ForecasterService._build_response(
        [
            result1,
            result2,
        ],
        years=1,
    )

    assert response.timeline[
        0
    ].value == 150.33

    assert response.timeline[
        1
    ].value == 301.22