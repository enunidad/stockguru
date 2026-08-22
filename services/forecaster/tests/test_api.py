from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from aiohttp.test_utils import TestClient, TestServer

from src.api import (
    _handle_dependency_response_error,
    _parse_forecast_request,
    _parse_holding,
    _read_number,
    create_app,
)
from src.exceptions import (
    AnalyzerClientError,
    AnalyzerResponseError,
    DownloaderClientError,
    DownloaderResponseError,
    InvalidAnalyzerResponseError,
    InvalidDownloaderResponseError,
)
from src.schemas import ForecastRequest, HoldingInput
from src.service import ForecasterService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class FakeForecastResponse:
    def __init__(self, payload=None):
        self.payload = payload or {
            "summary": {
                "initial_investment": 1000.0,
                "future_value": 1500.0,
            },
            "timeline": [
                {
                    "year": 0,
                    "value": 1000.0,
                },
                {
                    "year": 1,
                    "value": 1500.0,
                },
            ],
            "holdings": [],
        }

    def to_dict(self):
        return self.payload


@pytest.fixture
def service():
    return AsyncMock(spec=ForecasterService)


@pytest_asyncio.fixture
async def client(service):
    app = create_app(service)

    server = TestServer(app)
    test_client = TestClient(server)

    await test_client.start_server()

    yield test_client

    await test_client.close()


def valid_payload():
    return {
        "holdings": [
            {
                "ticker": "AAPL",
                "shares": 10,
                "average_cost": 100.0,
                "contribution_weight": 1.0,
            }
        ],
        "years": 10,
        "contribution_amount": 200.0,
        "contribution_frequency": "monthly",
        "drip": True,
    }


# ---------------------------------------------------------------------------
# App / health
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_returns_ok(client):
    response = await client.get(
        "/health"
    )

    assert response.status == 200

    assert await response.json() == {
        "status": "ok",
        "service": "forecaster",
    }


@pytest.mark.asyncio
async def test_unknown_route_returns_not_found(client):
    response = await client.get(
        "/does-not-exist"
    )

    assert response.status == 404


@pytest.mark.asyncio
async def test_forecast_only_accepts_post(client):
    response = await client.get(
        "/forecast"
    )

    assert response.status == 405


# ---------------------------------------------------------------------------
# Number parsing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (1, 1.0),
        (1.5, 1.5),
        (0, 0.0),
        (-5, -5.0),
    ],
)
def test_read_number_accepts_numbers(
    value,
    expected,
):
    result = _read_number(
        value,
        "amount",
    )

    assert result == expected
    assert isinstance(result, float)


@pytest.mark.parametrize(
    "value",
    [
        True,
        False,
        "10",
        None,
        [],
        {},
    ],
)
def test_read_number_rejects_non_numeric_values(
    value,
):
    with pytest.raises(
        TypeError,
        match="'amount' must be numeric",
    ):
        _read_number(
            value,
            "amount",
        )


# ---------------------------------------------------------------------------
# Holding parsing
# ---------------------------------------------------------------------------


def test_parse_holding_returns_holding_input():
    result = _parse_holding(
        {
            "ticker": "AAPL",
            "shares": 10,
            "average_cost": 100.0,
            "contribution_weight": 0.5,
        }
    )

    assert isinstance(
        result,
        HoldingInput,
    )

    assert result.ticker == "AAPL"
    assert result.shares == 10.0
    assert result.average_cost == 100.0
    assert result.contribution_weight == 0.5


def test_parse_holding_defaults_average_cost_to_none():
    result = _parse_holding(
        {
            "ticker": "AAPL",
            "shares": 10,
        }
    )

    assert result.average_cost is None


def test_parse_holding_defaults_contribution_weight_to_zero():
    result = _parse_holding(
        {
            "ticker": "AAPL",
            "shares": 10,
        }
    )

    assert result.contribution_weight == 0.0


def test_parse_holding_rejects_non_object():
    with pytest.raises(
        TypeError,
        match="Each holding must be a JSON object",
    ):
        _parse_holding(
            "AAPL"
        )


@pytest.mark.parametrize(
    "ticker",
    [
        None,
        123,
        [],
        {},
        True,
    ],
)
def test_parse_holding_rejects_non_string_ticker(
    ticker,
):
    with pytest.raises(
        TypeError,
        match="Holding 'ticker' must be a string",
    ):
        _parse_holding(
            {
                "ticker": ticker,
                "shares": 10,
            }
        )


def test_parse_holding_requires_shares():
    with pytest.raises(
        ValueError,
        match="Holding 'shares' is required",
    ):
        _parse_holding(
            {
                "ticker": "AAPL",
            }
        )


@pytest.mark.parametrize(
    "shares",
    [
        True,
        "10",
        None,
        [],
    ],
)
def test_parse_holding_rejects_invalid_shares(
    shares,
):
    with pytest.raises(
        TypeError,
        match="'shares' must be numeric",
    ):
        _parse_holding(
            {
                "ticker": "AAPL",
                "shares": shares,
            }
        )


@pytest.mark.parametrize(
    "average_cost",
    [
        True,
        "100",
        [],
        {},
    ],
)
def test_parse_holding_rejects_invalid_average_cost(
    average_cost,
):
    with pytest.raises(
        TypeError,
        match="'average_cost' must be numeric",
    ):
        _parse_holding(
            {
                "ticker": "AAPL",
                "shares": 10,
                "average_cost": average_cost,
            }
        )


@pytest.mark.parametrize(
    "weight",
    [
        True,
        "0.5",
        None,
        [],
    ],
)
def test_parse_holding_rejects_invalid_contribution_weight(
    weight,
):
    with pytest.raises(
        TypeError,
        match="'contribution_weight' must be numeric",
    ):
        _parse_holding(
            {
                "ticker": "AAPL",
                "shares": 10,
                "contribution_weight": weight,
            }
        )


# ---------------------------------------------------------------------------
# Forecast request parsing
# ---------------------------------------------------------------------------


def test_parse_forecast_request_returns_request():
    result = _parse_forecast_request(
        valid_payload()
    )

    assert isinstance(
        result,
        ForecastRequest,
    )

    assert len(result.holdings) == 1

    assert result.holdings[0].ticker == "AAPL"
    assert result.holdings[0].shares == 10.0

    assert result.years == 10
    assert result.contribution_amount == 200.0
    assert result.contribution_frequency == "monthly"
    assert result.drip is True


def test_parse_forecast_request_uses_defaults():
    result = _parse_forecast_request(
        {
            "holdings": [
                {
                    "ticker": "AAPL",
                    "shares": 10,
                }
            ]
        }
    )

    assert result.years == 10
    assert result.contribution_amount == 0.0
    assert result.contribution_frequency == "monthly"
    assert result.drip is True


def test_parse_forecast_request_rejects_non_object():
    with pytest.raises(
        TypeError,
        match="Request body must be a JSON object",
    ):
        _parse_forecast_request(
            []
        )


@pytest.mark.parametrize(
    "holdings",
    [
        None,
        {},
        "AAPL",
        10,
    ],
)
def test_parse_forecast_request_requires_holdings_list(
    holdings,
):
    with pytest.raises(
        TypeError,
        match="'holdings' must be a list",
    ):
        _parse_forecast_request(
            {
                "holdings": holdings,
            }
        )


def test_parse_forecast_request_allows_empty_holdings_at_parser_level():
    result = _parse_forecast_request(
        {
            "holdings": [],
        }
    )

    assert result.holdings == []


@pytest.mark.parametrize(
    "years",
    [
        True,
        False,
        10.0,
        "10",
        None,
    ],
)
def test_parse_forecast_request_rejects_invalid_years(
    years,
):
    with pytest.raises(
        TypeError,
        match="'years' must be an integer",
    ):
        payload = valid_payload()
        payload["years"] = years

        _parse_forecast_request(
            payload
        )


@pytest.mark.parametrize(
    "amount",
    [
        True,
        "100",
        None,
        [],
    ],
)
def test_parse_forecast_request_rejects_invalid_contribution_amount(
    amount,
):
    with pytest.raises(
        TypeError,
        match="'contribution_amount' must be numeric",
    ):
        payload = valid_payload()
        payload["contribution_amount"] = amount

        _parse_forecast_request(
            payload
        )


@pytest.mark.parametrize(
    "frequency",
    [
        None,
        10,
        True,
        [],
    ],
)
def test_parse_forecast_request_rejects_non_string_frequency(
    frequency,
):
    with pytest.raises(
        TypeError,
        match="'contribution_frequency' must be a string",
    ):
        payload = valid_payload()
        payload["contribution_frequency"] = frequency

        _parse_forecast_request(
            payload
        )


@pytest.mark.parametrize(
    "drip",
    [
        1,
        0,
        "true",
        None,
        [],
    ],
)
def test_parse_forecast_request_rejects_non_boolean_drip(
    drip,
):
    with pytest.raises(
        TypeError,
        match="'drip' must be a boolean",
    ):
        payload = valid_payload()
        payload["drip"] = drip

        _parse_forecast_request(
            payload
        )


# ---------------------------------------------------------------------------
# Successful forecast endpoint
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_forecast_returns_forecast_response(
    client,
    service,
):
    expected = {
        "summary": {
            "initial_investment": 1000.0,
            "future_value": 1500.0,
        },
        "timeline": [
            {
                "year": 0,
                "value": 1000.0,
            },
            {
                "year": 1,
                "value": 1500.0,
            },
        ],
        "holdings": [],
    }

    service.forecast.return_value = (
        FakeForecastResponse(expected)
    )

    response = await client.post(
        "/forecast",
        json=valid_payload(),
    )

    assert response.status == 200

    assert await response.json() == expected

    service.forecast.assert_awaited_once()

    request = service.forecast.await_args.args[
        0
    ]

    assert isinstance(
        request,
        ForecastRequest,
    )

    assert request.holdings[
        0
    ].ticker == "AAPL"

    assert request.years == 10

    assert request.contribution_amount == 200.0

    assert (
        request.contribution_frequency
        == "monthly"
    )

    assert request.drip is True


# ---------------------------------------------------------------------------
# Invalid JSON / request errors
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_forecast_rejects_invalid_json(
    client,
    service,
):
    response = await client.post(
        "/forecast",
        data="{this is not JSON",
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

    service.forecast.assert_not_awaited()


@pytest.mark.asyncio
async def test_forecast_rejects_non_object_json(
    client,
    service,
):
    response = await client.post(
        "/forecast",
        json=[
            "AAPL",
        ],
    )

    assert response.status == 400

    assert await response.json() == {
        "error": "invalid_request",
        "message": (
            "Request body must be a JSON object."
        ),
    }

    service.forecast.assert_not_awaited()


@pytest.mark.asyncio
async def test_forecast_rejects_missing_holdings(
    client,
    service,
):
    response = await client.post(
        "/forecast",
        json={
            "years": 10,
        },
    )

    assert response.status == 400

    assert await response.json() == {
        "error": "invalid_request",
        "message": "'holdings' must be a list.",
    }

    service.forecast.assert_not_awaited()


@pytest.mark.asyncio
async def test_forecast_rejects_malformed_holding(
    client,
    service,
):
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

    service.forecast.assert_not_awaited()


# ---------------------------------------------------------------------------
# Service validation error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_forecast_maps_value_error_to_bad_request(
    client,
    service,
):
    service.forecast.side_effect = ValueError(
        "Contribution weights must sum to 1.0."
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


# ---------------------------------------------------------------------------
# Downloader dependency errors
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_forecast_maps_downloader_4xx_response(
    client,
    service,
):
    service.forecast.side_effect = (
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
async def test_forecast_maps_downloader_5xx_response_to_bad_gateway(
    client,
    service,
):
    service.forecast.side_effect = (
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
async def test_forecast_maps_invalid_downloader_response(
    client,
    service,
):
    service.forecast.side_effect = (
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
async def test_forecast_maps_downloader_client_error(
    client,
    service,
):
    service.forecast.side_effect = (
        DownloaderClientError(
            "Unable to connect to Downloader."
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
            "Unable to connect to Downloader."
        ),
    }


# ---------------------------------------------------------------------------
# Analyzer dependency errors
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_forecast_maps_analyzer_4xx_response(
    client,
    service,
):
    service.forecast.side_effect = (
        AnalyzerResponseError(
            status=400,
            message="Invalid analysis request.",
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
            "Invalid analysis request."
        ),
    }


@pytest.mark.asyncio
async def test_forecast_maps_analyzer_5xx_response_to_bad_gateway(
    client,
    service,
):
    service.forecast.side_effect = (
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
async def test_forecast_maps_invalid_analyzer_response(
    client,
    service,
):
    service.forecast.side_effect = (
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
async def test_forecast_maps_analyzer_client_error(
    client,
    service,
):
    service.forecast.side_effect = (
        AnalyzerClientError(
            "Unable to connect to Analyzer."
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
            "Unable to connect to Analyzer."
        ),
    }


# ---------------------------------------------------------------------------
# Dependency response helper
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "status",
    [
        400,
        401,
        403,
        404,
        422,
        499,
    ],
)
def test_handle_dependency_response_error_preserves_4xx_status(
    status,
):
    response = _handle_dependency_response_error(
        dependency="downloader",
        status=status,
        message="Bad request.",
    )

    assert response.status == status


@pytest.mark.parametrize(
    "status",
    [
        500,
        502,
        503,
        504,
    ],
)
def test_handle_dependency_response_error_maps_5xx_to_502(
    status,
):
    response = _handle_dependency_response_error(
        dependency="analyzer",
        status=status,
        message="Dependency failed.",
    )

    assert response.status == 502