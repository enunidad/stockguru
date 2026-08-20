from unittest.mock import AsyncMock

import pytest

from src.client import (
    AnalyzerApiClient,
    DownloaderApiClient,
)
from src.schemas import (
    ForecastPoint,
    ForecastRequest,
    HoldingInput,
    HoldingProjectionResult,
)
from src.service import ForecasterService


# =========================================================
# Fixtures
# =========================================================


@pytest.fixture
def downloader_client():
    return AsyncMock(
        spec=DownloaderApiClient
    )


@pytest.fixture
def analyzer_client():
    return AsyncMock(
        spec=AnalyzerApiClient
    )


@pytest.fixture
def service(
    downloader_client,
    analyzer_client,
):
    return ForecasterService(
        downloader_client=downloader_client,
        analyzer_client=analyzer_client,
    )


def make_holding(
    *,
    ticker="AAPL",
    shares=10.0,
    average_cost=None,
    contribution_weight=1.0,
):
    return HoldingInput(
        ticker=ticker,
        shares=shares,
        average_cost=average_cost,
        contribution_weight=contribution_weight,
    )


def make_projection_result(
    *,
    ticker="AAPL",
    initial_investment=1000.0,
    current_growth=100.0,
    contributions=1200.0,
    growth=300.0,
    dividends=50.0,
    future_value=2650.0,
    dividend_yield=0.01,
    purchased_shares=20.0,
    drip_shares=0.5,
    total_shares=20.5,
    ending_price=125.0,
    timeline=None,
):
    if timeline is None:
        timeline = [
            ForecastPoint(
                year=0,
                value=1100.0,
            ),
            ForecastPoint(
                year=1,
                value=2650.0,
            ),
        ]

    return HoldingProjectionResult(
        ticker=ticker,
        initial_investment=initial_investment,
        current_growth=current_growth,
        contributions=contributions,
        growth=growth,
        dividends=dividends,
        future_value=future_value,
        dividend_yield=dividend_yield,
        purchased_shares=purchased_shares,
        drip_shares=drip_shares,
        total_shares=total_shares,
        ending_price=ending_price,
        timeline=timeline,
    )


# =========================================================
# _read_cagr
# =========================================================


def test_read_cagr_returns_numeric_value() -> None:
    result = ForecasterService._read_cagr(
        {
            "cagr": 0.125,
        }
    )

    assert result == pytest.approx(
        0.125
    )


def test_read_cagr_accepts_numeric_string() -> None:
    result = ForecasterService._read_cagr(
        {
            "cagr": "0.125",
        }
    )

    assert result == pytest.approx(
        0.125
    )


def test_read_cagr_rejects_missing_value() -> None:
    with pytest.raises(
        ValueError,
        match="Analyzer response is missing CAGR.",
    ):
        ForecasterService._read_cagr(
            {}
        )


@pytest.mark.parametrize(
    "value",
    [
        "banana",
        None,
    ],
)
def test_read_cagr_rejects_non_numeric_value(
    value,
) -> None:
    with pytest.raises(
        ValueError,
        match="Analyzer CAGR must be numeric.",
    ):
        ForecasterService._read_cagr(
            {
                "cagr": value,
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
def test_read_cagr_rejects_non_finite_value(
    value,
) -> None:
    with pytest.raises(
        ValueError,
        match="Analyzer CAGR must be finite.",
    ):
        ForecasterService._read_cagr(
            {
                "cagr": value,
            }
        )


@pytest.mark.parametrize(
    "value",
    [
        -1.0,
        -1.5,
    ],
)
def test_read_cagr_rejects_rate_at_or_below_negative_one(
    value,
) -> None:
    with pytest.raises(
        ValueError,
        match="Analyzer CAGR must be greater than -1.",
    ):
        ForecasterService._read_cagr(
            {
                "cagr": value,
            }
        )


# =========================================================
# _read_annual_dividend
# =========================================================


def test_read_annual_dividend_returns_zero_for_empty_history() -> None:
    result = ForecasterService._read_annual_dividend(
        []
    )

    assert result == pytest.approx(
        0.0
    )


def test_read_annual_dividend_sums_trailing_twelve_months() -> None:
    data = [
        {
            "Date": "2025-01-01",
            "Dividend": 0.20,
        },
        {
            "Date": "2025-08-01",
            "Dividend": 0.25,
        },
        {
            "Date": "2025-11-01",
            "Dividend": 0.25,
        },
        {
            "Date": "2026-02-01",
            "Dividend": 0.25,
        },
        {
            "Date": "2026-05-01",
            "Dividend": 0.25,
        },
    ]

    result = ForecasterService._read_annual_dividend(
        data
    )

    # Latest record is 2026-05-01.
    # Cutoff is 2025-05-01.
    # The 2025-01 dividend is excluded.
    assert result == pytest.approx(
        1.0
    )


def test_read_annual_dividend_excludes_exact_cutoff_date() -> None:
    data = [
        {
            "Date": "2025-06-01",
            "Dividend": 1.0,
        },
        {
            "Date": "2026-06-01",
            "Dividend": 2.0,
        },
    ]

    result = ForecasterService._read_annual_dividend(
        data
    )

    assert result == pytest.approx(
        2.0
    )


def test_read_annual_dividend_accepts_numeric_string() -> None:
    result = ForecasterService._read_annual_dividend(
        [
            {
                "Date": "2026-01-01",
                "Dividend": "0.50",
            },
        ]
    )

    assert result == pytest.approx(
        0.50
    )


def test_read_annual_dividend_rejects_non_object_record() -> None:
    with pytest.raises(
        ValueError,
        match="Dividend record must be an object.",
    ):
        ForecasterService._read_annual_dividend(
            [
                "invalid",
            ]
        )


@pytest.mark.parametrize(
    "record",
    [
        {
            "Dividend": 0.25,
        },
        {
            "Date": "2026-01-01",
        },
    ],
)
def test_read_annual_dividend_rejects_missing_fields(
    record,
) -> None:
    with pytest.raises(
        ValueError,
        match="Dividend record must contain Date and Dividend.",
    ):
        ForecasterService._read_annual_dividend(
            [
                record,
            ]
        )


@pytest.mark.parametrize(
    "record",
    [
        {
            "Date": "not-a-date",
            "Dividend": 0.25,
        },
        {
            "Date": "2026-01-01",
            "Dividend": "banana",
        },
    ],
)
def test_read_annual_dividend_rejects_invalid_data(
    record,
) -> None:
    with pytest.raises(
        ValueError,
        match="Dividend record contains invalid data.",
    ):
        ForecasterService._read_annual_dividend(
            [
                record,
            ]
        )


def test_read_annual_dividend_rejects_non_finite_amount() -> None:
    with pytest.raises(
        ValueError,
        match="Dividend amount must be finite.",
    ):
        ForecasterService._read_annual_dividend(
            [
                {
                    "Date": "2026-01-01",
                    "Dividend": float("nan"),
                },
            ]
        )


def test_read_annual_dividend_rejects_negative_amount() -> None:
    with pytest.raises(
        ValueError,
        match="Dividend amount cannot be negative.",
    ):
        ForecasterService._read_annual_dividend(
            [
                {
                    "Date": "2026-01-01",
                    "Dividend": -0.25,
                },
            ]
        )


# =========================================================
# _prepare_holding
# =========================================================


@pytest.mark.asyncio
async def test_prepare_holding_uses_latest_close_when_average_cost_missing(
    service,
    downloader_client,
    analyzer_client,
) -> None:
    downloader_client.latest_close.return_value = (
        150.0
    )

    downloader_client.get_dividends.return_value = (
        []
    )

    analyzer_client.get_analysis.return_value = {
        "cagr": 0.10,
    }

    holding = make_holding(
        ticker=" aapl ",
        shares=10.0,
        average_cost=None,
    )

    result = await service._prepare_holding(
        holding
    )

    assert result == {
        "ticker": "AAPL",
        "latest_close": 150.0,
        "initial_investment": 1500.0,
        "annual_growth_rate": 0.10,
        "annual_dividend": 0.0,
    }


@pytest.mark.asyncio
async def test_prepare_holding_uses_user_average_cost(
    service,
    downloader_client,
    analyzer_client,
) -> None:
    downloader_client.latest_close.return_value = (
        150.0
    )

    downloader_client.get_dividends.return_value = (
        []
    )

    analyzer_client.get_analysis.return_value = {
        "cagr": 0.10,
    }

    holding = make_holding(
        shares=10.0,
        average_cost=80.0,
    )

    result = await service._prepare_holding(
        holding
    )

    assert result["initial_investment"] == pytest.approx(
        800.0
    )

    assert result["latest_close"] == pytest.approx(
        150.0
    )


@pytest.mark.asyncio
async def test_prepare_holding_requests_required_market_data(
    service,
    downloader_client,
    analyzer_client,
) -> None:
    downloader_client.latest_close.return_value = (
        100.0
    )

    downloader_client.get_dividends.return_value = (
        []
    )

    analyzer_client.get_analysis.return_value = {
        "cagr": 0.05,
    }

    await service._prepare_holding(
        make_holding(
            ticker=" msft ",
        )
    )

    downloader_client.latest_close.assert_awaited_once_with(
        "MSFT"
    )

    analyzer_client.get_analysis.assert_awaited_once_with(
        "MSFT",
        period="10y",
        interval="1d",
        auto_adjust=False,
    )

    downloader_client.get_dividends.assert_awaited_once_with(
        "MSFT",
        period="10y",
    )


@pytest.mark.asyncio
async def test_prepare_holding_reads_trailing_dividend(
    service,
    downloader_client,
    analyzer_client,
) -> None:
    downloader_client.latest_close.return_value = (
        100.0
    )

    analyzer_client.get_analysis.return_value = {
        "cagr": 0.05,
    }

    downloader_client.get_dividends.return_value = [
        {
            "Date": "2025-09-01",
            "Dividend": 0.25,
        },
        {
            "Date": "2025-12-01",
            "Dividend": 0.25,
        },
        {
            "Date": "2026-03-01",
            "Dividend": 0.25,
        },
        {
            "Date": "2026-06-01",
            "Dividend": 0.25,
        },
    ]

    result = await service._prepare_holding(
        make_holding()
    )

    assert result["annual_dividend"] == pytest.approx(
        1.0
    )


# =========================================================
# Holding Validation
# =========================================================


@pytest.mark.parametrize(
    (
        "holding",
        "message",
    ),
    [
        (
            make_holding(
                ticker="   ",
            ),
            "Ticker cannot be empty.",
        ),
        (
            make_holding(
                shares=-1.0,
            ),
            "Shares cannot be negative.",
        ),
        (
            make_holding(
                average_cost=0.0,
            ),
            "Average cost must be greater than zero.",
        ),
        (
            make_holding(
                average_cost=-10.0,
            ),
            "Average cost must be greater than zero.",
        ),
        (
            make_holding(
                contribution_weight=-0.1,
            ),
            "Contribution weight must be between 0 and 1.",
        ),
        (
            make_holding(
                contribution_weight=1.1,
            ),
            "Contribution weight must be between 0 and 1.",
        ),
    ],
)
def test_validate_holding_rejects_invalid_input(
    holding,
    message,
) -> None:
    with pytest.raises(
        ValueError,
        match=message,
    ):
        ForecasterService._validate_holding(
            holding
        )


def test_validate_holding_accepts_valid_input() -> None:
    ForecasterService._validate_holding(
        make_holding(
            ticker="AAPL",
            shares=10.5,
            average_cost=75.0,
            contribution_weight=1.0,
        )
    )


# =========================================================
# Request Validation
# =========================================================


def test_validate_request_rejects_empty_portfolio() -> None:
    request = ForecastRequest(
        holdings=[],
    )

    with pytest.raises(
        ValueError,
        match="At least one holding is required.",
    ):
        ForecasterService._validate_request(
            request
        )


def test_validate_request_rejects_zero_years() -> None:
    request = ForecastRequest(
        holdings=[
            make_holding(),
        ],
        years=0,
    )

    with pytest.raises(
        ValueError,
        match="Forecast years must be greater than zero.",
    ):
        ForecasterService._validate_request(
            request
        )


def test_validate_request_rejects_negative_contribution() -> None:
    request = ForecastRequest(
        holdings=[
            make_holding(),
        ],
        contribution_amount=-1.0,
    )

    with pytest.raises(
        ValueError,
        match="Contribution amount cannot be negative.",
    ):
        ForecasterService._validate_request(
            request
        )


def test_validate_request_rejects_unknown_frequency() -> None:
    request = ForecastRequest(
        holdings=[
            make_holding(),
        ],
        contribution_frequency="weekly",
    )

    with pytest.raises(
        ValueError,
        match="Contribution frequency must be",
    ):
        ForecasterService._validate_request(
            request
        )


def test_validate_request_rejects_weights_not_summing_to_one() -> None:
    request = ForecastRequest(
        holdings=[
            make_holding(
                ticker="AAPL",
                contribution_weight=0.25,
            ),
            make_holding(
                ticker="MSFT",
                contribution_weight=0.25,
            ),
        ],
        contribution_amount=500.0,
    )

    with pytest.raises(
        ValueError,
        match="Contribution weights must sum to 1.0.",
    ):
        ForecasterService._validate_request(
            request
        )


def test_validate_request_accepts_valid_weights() -> None:
    request = ForecastRequest(
        holdings=[
            make_holding(
                ticker="AAPL",
                contribution_weight=0.5,
            ),
            make_holding(
                ticker="MSFT",
                contribution_weight=0.5,
            ),
        ],
        contribution_amount=500.0,
    )

    ForecasterService._validate_request(
        request
    )


def test_validate_request_does_not_require_weights_without_contributions() -> None:
    request = ForecastRequest(
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

    ForecasterService._validate_request(
        request
    )


# =========================================================
# _build_response
# =========================================================


def test_build_response_aggregates_holdings() -> None:
    first = make_projection_result(
        ticker="AAPL",
        initial_investment=1000.0,
        current_growth=100.0,
        contributions=500.0,
        growth=200.0,
        dividends=50.0,
        future_value=1850.0,
        timeline=[
            ForecastPoint(
                year=0,
                value=1100.0,
            ),
            ForecastPoint(
                year=1,
                value=1850.0,
            ),
        ],
    )

    second = make_projection_result(
        ticker="MSFT",
        initial_investment=2000.0,
        current_growth=-100.0,
        contributions=500.0,
        growth=400.0,
        dividends=100.0,
        future_value=2900.0,
        timeline=[
            ForecastPoint(
                year=0,
                value=1900.0,
            ),
            ForecastPoint(
                year=1,
                value=2900.0,
            ),
        ],
    )

    result = ForecasterService._build_response(
        [
            first,
            second,
        ],
        years=1,
    )

    assert result.summary.initial_investment == pytest.approx(
        3000.0
    )

    assert result.summary.current_growth == pytest.approx(
        0.0
    )

    assert result.summary.future_contributions == pytest.approx(
        1000.0
    )

    assert result.summary.stock_growth == pytest.approx(
        600.0
    )

    assert result.summary.dividends == pytest.approx(
        150.0
    )

    assert result.summary.future_value == pytest.approx(
        4750.0
    )

    assert result.timeline == [
        ForecastPoint(
            year=0,
            value=3000.0,
        ),
        ForecastPoint(
            year=1,
            value=4750.0,
        ),
    ]

    assert len(result.holdings) == 2

    assert result.holdings[0].ticker == "AAPL"
    assert result.holdings[1].ticker == "MSFT"


def test_build_response_preserves_share_attribution() -> None:
    projection = make_projection_result(
        purchased_shares=15.0,
        drip_shares=2.0,
        total_shares=17.0,
        dividend_yield=0.025,
        ending_price=175.0,
    )

    result = ForecasterService._build_response(
        [
            projection,
        ],
        years=1,
    )

    holding = result.holdings[0]

    assert holding.purchased_shares == pytest.approx(
        15.0
    )

    assert holding.drip_shares == pytest.approx(
        2.0
    )

    assert holding.total_shares == pytest.approx(
        17.0
    )

    assert holding.dividend_yield == pytest.approx(
        0.025
    )

    assert holding.ending_price == pytest.approx(
        175.0
    )


# =========================================================
# forecast
# =========================================================


@pytest.mark.asyncio
async def test_forecast_prepares_holding_and_calls_projector(
    service,
    downloader_client,
    analyzer_client,
    monkeypatch,
) -> None:
    downloader_client.latest_close.return_value = (
        150.0
    )

    downloader_client.get_dividends.return_value = (
        []
    )

    analyzer_client.get_analysis.return_value = {
        "cagr": 0.08,
    }

    captured = {}

    def fake_project_holding(**kwargs):
        captured.update(
            kwargs
        )

        return make_projection_result(
            ticker=kwargs["ticker"],
            initial_investment=kwargs[
                "initial_investment"
            ],
            timeline=[
                ForecastPoint(
                    year=0,
                    value=1500.0,
                ),
                ForecastPoint(
                    year=1,
                    value=2000.0,
                ),
            ],
        )

    monkeypatch.setattr(
        "src.service.project_holding",
        fake_project_holding,
    )

    request = ForecastRequest(
        holdings=[
            make_holding(
                ticker=" aapl ",
                shares=10.0,
                average_cost=100.0,
                contribution_weight=1.0,
            ),
        ],
        years=1,
        contribution_amount=500.0,
        contribution_frequency="monthly",
        drip=False,
    )

    await service.forecast(
        request
    )

    assert captured == {
        "ticker": "AAPL",
        "shares": 10.0,
        "current_price": 150.0,
        "initial_investment": 1000.0,
        "annual_growth_rate": 0.08,
        "annual_dividend_per_share": 0.0,
        "years": 1,
        "contribution_amount": 500.0,
        "contribution_frequency": "monthly",
        "drip": False,
    }


@pytest.mark.asyncio
async def test_forecast_allocates_contribution_by_weight(
    service,
    downloader_client,
    analyzer_client,
    monkeypatch,
) -> None:
    downloader_client.latest_close.return_value = (
        100.0
    )

    downloader_client.get_dividends.return_value = (
        []
    )

    analyzer_client.get_analysis.return_value = {
        "cagr": 0.05,
    }

    contribution_amounts = []

    def fake_project_holding(**kwargs):
        contribution_amounts.append(
            kwargs["contribution_amount"]
        )

        return make_projection_result(
            ticker=kwargs["ticker"],
        )

    monkeypatch.setattr(
        "src.service.project_holding",
        fake_project_holding,
    )

    request = ForecastRequest(
        holdings=[
            make_holding(
                ticker="AAPL",
                contribution_weight=0.5,
            ),
            make_holding(
                ticker="MSFT",
                contribution_weight=0.5,
            ),
        ],
        years=1,
        contribution_amount=600.0,
    )

    await service.forecast(
        request
    )

    assert contribution_amounts == pytest.approx(
        [
            300.0,
            300.0,
        ]
    )