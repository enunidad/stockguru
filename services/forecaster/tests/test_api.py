from unittest.mock import AsyncMock

import pytest
import pytest_asyncio

from src.api import create_app
from src.exceptions import (
    AnalyzerClientError,
    AnalyzerResponseError,
    DownloaderClientError,
    DownloaderResponseError,
    InvalidAnalyzerResponseError,
    InvalidDownloaderResponseError,
)
from src.schemas import (
    ForecastPoint,
    ForecastResponse,
    ForecastSummary,
    HoldingForecast,
)
from src.service import ForecasterService


# =========================================================
# Fixtures
# =========================================================


@pytest.fixture
def forecaster_service():
    return AsyncMock(
        spec=ForecasterService
    )


@pytest_asyncio.fixture
async def client(
    aiohttp_client,
    forecaster_service,
):
    app = create_app(
        forecaster_service=forecaster_service
    )

    return await aiohttp_client(
        app
    )


def make_forecast_response():
    return ForecastResponse(
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


def valid_payload():
    return {
        "holdings": [
            {
                "ticker": "AAPL",
                "shares": 10.0,
                "average_cost": 100.0,
                "contribution_weight": 1.0,
            }
        ],
        "years": 10,
        "contribution_amount": 500.0,
        "contribution_frequency": "monthly",
        "drip": True,
    }


# =========================================================
# /health
# =========================================================


@pytest.mark.asyncio
async def test_health_returns_ok(
    client,
) -> None:
    response = await client.get(
        "/health"
    )

    assert response.status == 200

    assert await response.json() == {
        "status": "ok",
        "service": "forecaster",
    }


# =========================================================
# /forecast
# Successful Request
# =========================================================


@pytest.mark.asyncio
async def test_forecast_returns_forecast_response(
    client,
    forecaster_service,
) -> None:
    forecaster_service.forecast.return_value = (
        make_forecast_response()
    )

    response = await client.post(
        "/forecast",
        json=valid_payload(),
    )

    assert response.status == 200

    assert await response.json() == {
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


@pytest.mark.asyncio
async def test_forecast_builds_forecast_request(
    client,
    forecaster_service,
) -> None:
    forecaster_service.forecast.return_value = (
        make_forecast_response()
    )

    await client.post(
        "/forecast",
        json={
            "holdings": [
                {
                    "ticker": "AAPL",
                    "shares": 10,
                    "average_cost": 75,
                    "contribution_weight": 0.6,
                },
                {
                    "ticker": "MSFT",
                    "shares": 5,
                    "average_cost": None,
                    "contribution_weight": 0.4,
                },
            ],
            "years": 20,
            "contribution_amount": 600,
            "contribution_frequency": "quarterly",
            "drip": False,
        },
    )

    forecaster_service.forecast.assert_awaited_once()

    request = (
        forecaster_service
        .forecast
        .await_args
        .args[0]
    )

    assert request.years == 20

    assert request.contribution_amount == pytest.approx(
        600.0
    )

    assert (
        request.contribution_frequency
        == "quarterly"
    )

    assert request.drip is False

    assert len(request.holdings) == 2

    first = request.holdings[0]

    assert first.ticker == "AAPL"
    assert first.shares == pytest.approx(10.0)
    assert first.average_cost == pytest.approx(75.0)
    assert first.contribution_weight == pytest.approx(
        0.6
    )

    second = request.holdings[1]

    assert second.ticker == "MSFT"
    assert second.shares == pytest.approx(5.0)
    assert second.average_cost is None
    assert second.contribution_weight == pytest.approx(
        0.4
    )


# =========================================================
# Request Defaults
# =========================================================


@pytest.mark.asyncio
async def test_forecast_uses_request_defaults(
    client,
    forecaster_service,
) -> None:
    forecaster_service.forecast.return_value = (
        make_forecast_response()
    )

    response = await client.post(
        "/forecast",
        json={
            "holdings": [
                {
                    "ticker": "AAPL",
                    "shares": 10,
                }
            ]
        },
    )

    assert response.status == 200

    request = (
        forecaster_service
        .forecast
        .await_args
        .args[0]
    )

    assert request.years == 10

    assert request.contribution_amount == pytest.approx(
        0.0
    )

    assert (
        request.contribution_frequency
        == "monthly"
    )

    assert request.drip is True

    assert (
        request.holdings[0].average_cost
        is None
    )

    assert (
        request.holdings[0].contribution_weight
        == pytest.approx(0.0)
    )


# =========================================================
# Invalid JSON
# =========================================================


@pytest.mark.asyncio
async def test_forecast_rejects_invalid_json(
    client,
    forecaster_service,
) -> None:
    response = await client.post(
        "/forecast",
        data="{ definitely-not-json",
        headers={
            "Content-Type": "application/json",
        },
    )

    assert response.status == 400

    assert await response.json() == {
        "error": "invalid_json",
        "message": (
            "Request body must contain valid JSON."
        ),
    }

    forecaster_service.forecast.assert_not_awaited()


# =========================================================
# Invalid Root Payload
# =========================================================


@pytest.mark.asyncio
async def test_forecast_rejects_non_object_payload(
    client,
    forecaster_service,
) -> None:
    response = await client.post(
        "/forecast",
        json=[
            {
                "ticker": "AAPL",
            }
        ],
    )

    assert response.status == 400

    assert await response.json() == {
        "error": "invalid_request",
        "message": (
            "Request body must be a JSON object."
        ),
    }

    forecaster_service.forecast.assert_not_awaited()


@pytest.mark.asyncio
async def test_forecast_requires_holdings_list(
    client,
    forecaster_service,
) -> None:
    response = await client.post(
        "/forecast",
        json={},
    )

    assert response.status == 400

    assert await response.json() == {
        "error": "invalid_request",
        "message": "'holdings' must be a list.",
    }

    forecaster_service.forecast.assert_not_awaited()


@pytest.mark.asyncio
async def test_forecast_rejects_non_list_holdings(
    client,
    forecaster_service,
) -> None:
    response = await client.post(
        "/forecast",
        json={
            "holdings": {
                "ticker": "AAPL",
                "shares": 10,
            }
        },
    )

    assert response.status == 400

    assert await response.json() == {
        "error": "invalid_request",
        "message": "'holdings' must be a list.",
    }

    forecaster_service.forecast.assert_not_awaited()


# =========================================================
# Holding Parsing
# =========================================================


@pytest.mark.asyncio
async def test_forecast_rejects_non_object_holding(
    client,
    forecaster_service,
) -> None:
    response = await client.post(
        "/forecast",
        json={
            "holdings": [
                "AAPL"
            ]
        },
    )

    assert response.status == 400

    assert await response.json() == {
        "error": "invalid_request",
        "message": (
            "Each holding must be a JSON object."
        ),
    }

    forecaster_service.forecast.assert_not_awaited()


@pytest.mark.asyncio
async def test_forecast_requires_string_ticker(
    client,
    forecaster_service,
) -> None:
    response = await client.post(
        "/forecast",
        json={
            "holdings": [
                {
                    "ticker": 123,
                    "shares": 10,
                }
            ]
        },
    )

    assert response.status == 400

    assert await response.json() == {
        "error": "invalid_request",
        "message": (
            "Holding 'ticker' must be a string."
        ),
    }

    forecaster_service.forecast.assert_not_awaited()


@pytest.mark.asyncio
async def test_forecast_requires_shares(
    client,
    forecaster_service,
) -> None:
    response = await client.post(
        "/forecast",
        json={
            "holdings": [
                {
                    "ticker": "AAPL",
                }
            ]
        },
    )

    assert response.status == 400

    assert await response.json() == {
        "error": "invalid_request",
        "message": (
            "Holding 'shares' is required."
        ),
    }

    forecaster_service.forecast.assert_not_awaited()


@pytest.mark.parametrize(
    (
        "field",
        "value",
    ),
    [
        (
            "shares",
            "10",
        ),
        (
            "shares",
            True,
        ),
        (
            "average_cost",
            "100",
        ),
        (
            "average_cost",
            False,
        ),
        (
            "contribution_weight",
            "1.0",
        ),
        (
            "contribution_weight",
            True,
        ),
    ],
)
@pytest.mark.asyncio
async def test_forecast_rejects_non_numeric_holding_fields(
    client,
    forecaster_service,
    field,
    value,
) -> None:
    holding = {
        "ticker": "AAPL",
        "shares": 10,
    }

    holding[field] = value

    response = await client.post(
        "/forecast",
        json={
            "holdings": [
                holding
            ]
        },
    )

    assert response.status == 400

    body = await response.json()

    assert body["error"] == "invalid_request"

    assert (
        body["message"]
        == f"'{field}' must be numeric."
    )

    forecaster_service.forecast.assert_not_awaited()


# =========================================================
# Forecast Field Parsing
# =========================================================


@pytest.mark.parametrize(
    "years",
    [
        10.5,
        "10",
        True,
        None,
    ],
)
@pytest.mark.asyncio
async def test_forecast_requires_integer_years(
    client,
    forecaster_service,
    years,
) -> None:
    payload = valid_payload()

    payload["years"] = years

    response = await client.post(
        "/forecast",
        json=payload,
    )

    assert response.status == 400

    assert await response.json() == {
        "error": "invalid_request",
        "message": "'years' must be an integer.",
    }

    forecaster_service.forecast.assert_not_awaited()


@pytest.mark.parametrize(
    "value",
    [
        "500",
        True,
        None,
    ],
)
@pytest.mark.asyncio
async def test_forecast_requires_numeric_contribution_amount(
    client,
    forecaster_service,
    value,
) -> None:
    payload = valid_payload()

    payload["contribution_amount"] = value

    response = await client.post(
        "/forecast",
        json=payload,
    )

    assert response.status == 400

    assert await response.json() == {
        "error": "invalid_request",
        "message": (
            "'contribution_amount' must be numeric."
        ),
    }

    forecaster_service.forecast.assert_not_awaited()


@pytest.mark.parametrize(
    "value",
    [
        123,
        True,
        None,
    ],
)
@pytest.mark.asyncio
async def test_forecast_requires_string_contribution_frequency(
    client,
    forecaster_service,
    value,
) -> None:
    payload = valid_payload()

    payload["contribution_frequency"] = value

    response = await client.post(
        "/forecast",
        json=payload,
    )

    assert response.status == 400

    assert await response.json() == {
        "error": "invalid_request",
        "message": (
            "'contribution_frequency' must be a string."
        ),
    }

    forecaster_service.forecast.assert_not_awaited()


@pytest.mark.parametrize(
    "value",
    [
        1,
        0,
        "true",
        None,
    ],
)
@pytest.mark.asyncio
async def test_forecast_requires_boolean_drip(
    client,
    forecaster_service,
    value,
) -> None:
    payload = valid_payload()

    payload["drip"] = value

    response = await client.post(
        "/forecast",
        json=payload,
    )

    assert response.status == 400

    assert await response.json() == {
        "error": "invalid_request",
        "message": (
            "'drip' must be a boolean."
        ),
    }

    forecaster_service.forecast.assert_not_awaited()


# =========================================================
# Service Validation Errors
# =========================================================


@pytest.mark.asyncio
async def test_forecast_returns_400_for_forecast_validation_error(
    client,
    forecaster_service,
) -> None:
    forecaster_service.forecast.side_effect = (
        ValueError(
            "Contribution weights must sum to 1.0."
        )
    )

    response = await client.post(
        "/forecast",
        json=valid_payload(),
    )

    assert response.status == 400

    assert await response.json() == {
        "error": "forecast_error",
        "message": (
            "Contribution weights must sum to 1.0."
        ),
    }


# =========================================================
# Downloader Errors
# =========================================================


@pytest.mark.asyncio
async def test_forecast_preserves_downloader_4xx(
    client,
    forecaster_service,
) -> None:
    forecaster_service.forecast.side_effect = (
        DownloaderResponseError(
            status=404,
            message="Ticker not found.",
        )
    )

    response = await client.post(
        "/forecast",
        json=valid_payload(),
    )

    assert response.status == 404

    assert await response.json() == {
        "error": "downloader_request_error",
        "message": "Ticker not found.",
    }


@pytest.mark.asyncio
async def test_forecast_converts_downloader_5xx_to_502(
    client,
    forecaster_service,
) -> None:
    forecaster_service.forecast.side_effect = (
        DownloaderResponseError(
            status=500,
            message="Downloader failed.",
        )
    )

    response = await client.post(
        "/forecast",
        json=valid_payload(),
    )

    assert response.status == 502

    assert await response.json() == {
        "error": "downloader_error",
        "message": "Downloader failed.",
    }


@pytest.mark.asyncio
async def test_forecast_returns_502_for_invalid_downloader_response(
    client,
    forecaster_service,
) -> None:
    forecaster_service.forecast.side_effect = (
        InvalidDownloaderResponseError(
            "Downloader returned invalid data."
        )
    )

    response = await client.post(
        "/forecast",
        json=valid_payload(),
    )

    assert response.status == 502

    assert await response.json() == {
        "error": "invalid_downloader_response",
        "message": (
            "Downloader returned invalid data."
        ),
    }


@pytest.mark.asyncio
async def test_forecast_returns_503_when_downloader_unavailable(
    client,
    forecaster_service,
) -> None:
    forecaster_service.forecast.side_effect = (
        DownloaderClientError(
            "Unable to communicate with Downloader."
        )
    )

    response = await client.post(
        "/forecast",
        json=valid_payload(),
    )

    assert response.status == 503

    assert await response.json() == {
        "error": "downloader_unavailable",
        "message": (
            "Unable to communicate with Downloader."
        ),
    }


# =========================================================
# Analyzer Errors
# =========================================================


@pytest.mark.asyncio
async def test_forecast_preserves_analyzer_4xx(
    client,
    forecaster_service,
) -> None:
    forecaster_service.forecast.side_effect = (
        AnalyzerResponseError(
            status=400,
            message="Unable to analyze ticker.",
        )
    )

    response = await client.post(
        "/forecast",
        json=valid_payload(),
    )

    assert response.status == 400

    assert await response.json() == {
        "error": "analyzer_request_error",
        "message": (
            "Unable to analyze ticker."
        ),
    }


@pytest.mark.asyncio
async def test_forecast_converts_analyzer_5xx_to_502(
    client,
    forecaster_service,
) -> None:
    forecaster_service.forecast.side_effect = (
        AnalyzerResponseError(
            status=500,
            message="Analyzer failed.",
        )
    )

    response = await client.post(
        "/forecast",
        json=valid_payload(),
    )

    assert response.status == 502

    assert await response.json() == {
        "error": "analyzer_error",
        "message": "Analyzer failed.",
    }


@pytest.mark.asyncio
async def test_forecast_returns_502_for_invalid_analyzer_response(
    client,
    forecaster_service,
) -> None:
    forecaster_service.forecast.side_effect = (
        InvalidAnalyzerResponseError(
            "Analyzer returned invalid data."
        )
    )

    response = await client.post(
        "/forecast",
        json=valid_payload(),
    )

    assert response.status == 502

    assert await response.json() == {
        "error": "invalid_analyzer_response",
        "message": (
            "Analyzer returned invalid data."
        ),
    }


@pytest.mark.asyncio
async def test_forecast_returns_503_when_analyzer_unavailable(
    client,
    forecaster_service,
) -> None:
    forecaster_service.forecast.side_effect = (
        AnalyzerClientError(
            "Unable to communicate with Analyzer."
        )
    )

    response = await client.post(
        "/forecast",
        json=valid_payload(),
    )

    assert response.status == 503

    assert await response.json() == {
        "error": "analyzer_unavailable",
        "message": (
            "Unable to communicate with Analyzer."
        ),
    }