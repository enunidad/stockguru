from __future__ import annotations

from json import JSONDecodeError
from typing import Any

from aiohttp import web

from .client import (
    AnalyzerApiClient,
    DownloaderApiClient,
)
from .exceptions import (
    AnalyzerClientError,
    AnalyzerResponseError,
    DownloaderClientError,
    DownloaderResponseError,
    InvalidAnalyzerResponseError,
    InvalidDownloaderResponseError,
)
from .schemas import (
    ForecastRequest,
    HoldingInput,
)
from .service import ForecasterService


FORECASTER_SERVICE_KEY = web.AppKey(
    "forecaster_service",
    ForecasterService,
)


def create_app(
    forecaster_service: ForecasterService | None = None,
    *,
    downloader_base_url: str = "http://localhost:8080",
    analyzer_base_url: str = "http://localhost:8090",
) -> web.Application:
    """
    Create and configure the Forecaster API.
    """
    app = web.Application()

    if forecaster_service is None:
        downloader_client = DownloaderApiClient(
            base_url=downloader_base_url,
        )

        analyzer_client = AnalyzerApiClient(
            base_url=analyzer_base_url,
        )

        forecaster_service = ForecasterService(
            downloader_client=downloader_client,
            analyzer_client=analyzer_client,
        )

    app[FORECASTER_SERVICE_KEY] = forecaster_service

    app.router.add_get(
        "/health",
        health,
    )

    app.router.add_post(
        "/forecast",
        forecast,
    )

    return app


async def health(
    request: web.Request,
) -> web.Response:
    """
    Return Forecaster service health status.
    """
    return web.json_response(
        {
            "status": "ok",
            "service": "forecaster",
        }
    )


async def forecast(
    request: web.Request,
) -> web.Response:
    """
    Generate a portfolio forecast.

    Example:
        POST /forecast
    """
    try:
        payload = await request.json()

    except (
        JSONDecodeError,
        ValueError,
    ):
        return _error_response(
            status=web.HTTPBadRequest.status_code,
            error="invalid_json",
            message="Request body must contain valid JSON.",
        )

    try:
        forecast_request = _parse_forecast_request(
            payload
        )

    except (
        KeyError,
        TypeError,
        ValueError,
    ) as exc:
        return _error_response(
            status=web.HTTPBadRequest.status_code,
            error="invalid_request",
            message=str(exc),
        )

    forecaster_service = request.app[
        FORECASTER_SERVICE_KEY
    ]

    try:
        result = await forecaster_service.forecast(
            forecast_request
        )

    except DownloaderResponseError as exc:
        return _handle_dependency_response_error(
            dependency="downloader",
            status=exc.status,
            message=exc.message,
        )

    except InvalidDownloaderResponseError as exc:
        return _error_response(
            status=web.HTTPBadGateway.status_code,
            error="invalid_downloader_response",
            message=str(exc),
        )

    except DownloaderClientError as exc:
        return _error_response(
            status=web.HTTPServiceUnavailable.status_code,
            error="downloader_unavailable",
            message=str(exc),
        )

    except AnalyzerResponseError as exc:
        return _handle_dependency_response_error(
            dependency="analyzer",
            status=exc.status,
            message=exc.message,
        )

    except InvalidAnalyzerResponseError as exc:
        return _error_response(
            status=web.HTTPBadGateway.status_code,
            error="invalid_analyzer_response",
            message=str(exc),
        )

    except AnalyzerClientError as exc:
        return _error_response(
            status=web.HTTPServiceUnavailable.status_code,
            error="analyzer_unavailable",
            message=str(exc),
        )

    except ValueError as exc:
        return _error_response(
            status=web.HTTPBadRequest.status_code,
            error="forecast_error",
            message=str(exc),
        )

    return web.json_response(
        result.to_dict()
    )


def _parse_forecast_request(
    payload: Any,
) -> ForecastRequest:
    """
    Convert a JSON request body into a ForecastRequest.
    """
    if not isinstance(payload, dict):
        raise TypeError(
            "Request body must be a JSON object."
        )

    raw_holdings = payload.get("holdings")

    if not isinstance(raw_holdings, list):
        raise TypeError(
            "'holdings' must be a list."
        )

    holdings = [
        _parse_holding(holding)
        for holding in raw_holdings
    ]

    years = payload.get(
        "years",
        10,
    )

    if (
        not isinstance(years, int)
        or isinstance(years, bool)
    ):
        raise TypeError(
            "'years' must be an integer."
        )

    contribution_amount = _read_number(
        payload.get(
            "contribution_amount",
            0.0,
        ),
        "contribution_amount",
    )

    contribution_frequency = payload.get(
        "contribution_frequency",
        "monthly",
    )

    if not isinstance(
        contribution_frequency,
        str,
    ):
        raise TypeError(
            "'contribution_frequency' must be a string."
        )

    drip = payload.get(
        "drip",
        True,
    )

    if not isinstance(drip, bool):
        raise TypeError(
            "'drip' must be a boolean."
        )

    return ForecastRequest(
        holdings=holdings,
        years=years,
        contribution_amount=contribution_amount,
        contribution_frequency=(
            contribution_frequency
        ),
        drip=drip,
    )


def _parse_holding(
    payload: Any,
) -> HoldingInput:
    """
    Convert one holding JSON object into HoldingInput.
    """
    if not isinstance(payload, dict):
        raise TypeError(
            "Each holding must be a JSON object."
        )

    ticker = payload.get("ticker")

    if not isinstance(ticker, str):
        raise TypeError(
            "Holding 'ticker' must be a string."
        )

    if "shares" not in payload:
        raise ValueError(
            "Holding 'shares' is required."
        )

    shares = _read_number(
        payload["shares"],
        "shares",
    )

    average_cost_raw = payload.get(
        "average_cost"
    )

    average_cost = (
        None
        if average_cost_raw is None
        else _read_number(
            average_cost_raw,
            "average_cost",
        )
    )

    contribution_weight = _read_number(
        payload.get(
            "contribution_weight",
            0.0,
        ),
        "contribution_weight",
    )

    return HoldingInput(
        ticker=ticker,
        shares=shares,
        average_cost=average_cost,
        contribution_weight=contribution_weight,
    )


def _read_number(
    value: Any,
    field_name: str,
) -> float:
    """
    Read a JSON numeric field.
    """
    if (
        isinstance(value, bool)
        or not isinstance(
            value,
            (int, float),
        )
    ):
        raise TypeError(
            f"'{field_name}' must be numeric."
        )

    return float(value)


def _handle_dependency_response_error(
    *,
    dependency: str,
    status: int,
    message: str,
) -> web.Response:
    """
    Translate dependency HTTP failures into Forecaster
    HTTP responses.
    """
    if 400 <= status < 500:
        return _error_response(
            status=status,
            error=f"{dependency}_request_error",
            message=message,
        )

    return _error_response(
        status=web.HTTPBadGateway.status_code,
        error=f"{dependency}_error",
        message=message,
    )


def _error_response(
    *,
    status: int,
    error: str,
    message: str,
) -> web.Response:
    """
    Create a consistent JSON error response.
    """
    return web.json_response(
        {
            "error": error,
            "message": message,
        },
        status=status,
    )