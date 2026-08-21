from __future__ import annotations

import traceback

from aiohttp import web

from .client import (
    AnalyzerApiClient,
    DownloaderApiClient,
)
from .exceptions import (
    DownloaderClientError,
    DownloaderResponseError,
    InvalidDownloaderResponseError,
)
from .schemas import PortfolioOverviewRequest
from .service import ChartMgrService


CHARTMGR_SERVICE_KEY = web.AppKey(
    "chartmgr_service",
    ChartMgrService,
)


def create_app(
    chartmgr_service: ChartMgrService | None = None,
    *,
    downloader_base_url: str = "http://localhost:8080",
    analyzer_base_url: str = "http://localhost:8090",
) -> web.Application:

    app = web.Application()

    if chartmgr_service is None:

        downloader_client = DownloaderApiClient(
            base_url=downloader_base_url,
        )

        analyzer_client = AnalyzerApiClient(
            base_url=analyzer_base_url,
        )

        chartmgr_service = ChartMgrService(
            downloader_client=downloader_client,
            analyzer_client=analyzer_client,
        )

    app[CHARTMGR_SERVICE_KEY] = chartmgr_service


    # -----------------------------------------------------
    # Routes
    # -----------------------------------------------------

    app.router.add_get(
        "/health",
        health,
    )

    app.router.add_get(
        "/charting/price_history/{ticker}",
        get_price_history,
    )

    app.router.add_get(
        "/charting/volume/{ticker}",
        get_volume,
    )

    app.router.add_post(
        "/charting/portfolio_overview",
        get_portfolio_overview,
    )

    return app


# =========================================================
# Health
# =========================================================

async def health(
    request: web.Request,
) -> web.Response:
    """Return the chartmgr service health status."""

    return web.json_response(
        {
            "status": "ok",
            "service": "chartmgr",
        }
    )


# =========================================================
# Portfolio Overview
# =========================================================

async def get_portfolio_overview(
    request: web.Request,
) -> web.Response:
    """
    Return chart-ready portfolio composition data.

    Financial values are supplied by Forecaster.
    ChartMgr only validates and formats them for display.
    """

    chartmgr_service = request.app[
        CHARTMGR_SERVICE_KEY
    ]


    # -----------------------------------------------------
    # Read request
    # -----------------------------------------------------

    try:
        payload = await request.json()

    except ValueError:
        return _error_response(
            status=web.HTTPBadRequest.status_code,
            error="invalid_json",
            message=(
                "Request body must contain valid JSON."
            ),
        )


    if not isinstance(payload, dict):
        return _error_response(
            status=web.HTTPBadRequest.status_code,
            error="invalid_request",
            message=(
                "Portfolio overview request must be "
                "a JSON object."
            ),
        )


    # -----------------------------------------------------
    # Build request schema
    # -----------------------------------------------------

    try:

        overview_request = PortfolioOverviewRequest(
            **payload
        )

    except TypeError as exc:

        return _error_response(
            status=web.HTTPBadRequest.status_code,
            error="invalid_request",
            message=str(exc),
        )


    # -----------------------------------------------------
    # Build chart
    # -----------------------------------------------------

    try:

        result = (
            chartmgr_service
            .get_portfolio_overview(
                overview_request
            )
        )

    except ValueError as exc:

        return _error_response(
            status=web.HTTPBadRequest.status_code,
            error="invalid_portfolio_overview",
            message=str(exc),
        )

    except Exception as exc:

        return _error_handle(exc)


    return web.json_response(
        result.to_dict()
    )


# =========================================================
# Volume
# =========================================================

async def get_volume(
    request: web.Request,
) -> web.Response:
    """
    Return charting data for volume.
    """

    ticker = request.match_info[
        "ticker"
    ]

    period = request.query.get(
        "period",
        "10y",
    )

    interval = request.query.get(
        "interval",
        "1mo",
    )

    chartmgr_service = request.app[
        CHARTMGR_SERVICE_KEY
    ]


    try:

        result = (
            await chartmgr_service
            .get_volume_history(
                ticker,
                period=period,
                interval=interval,
            )
        )

    except Exception as exc:

        return _error_handle(exc)


    return web.json_response(
        result.to_dict()
    )


# =========================================================
# Price History
# =========================================================

async def get_price_history(
    request: web.Request,
) -> web.Response:
    """
    Return charting data for prices.
    """

    ticker = request.match_info[
        "ticker"
    ]

    period = request.query.get(
        "period",
        "10y",
    )

    interval = request.query.get(
        "interval",
        "1mo",
    )

    chartmgr_service = request.app[
        CHARTMGR_SERVICE_KEY
    ]


    try:

        result = (
            await chartmgr_service
            .get_price_history(
                ticker,
                period=period,
                interval=interval,
            )
        )

    except Exception as exc:

        return _error_handle(exc)


    return web.json_response(
        result.to_dict()
    )


# =========================================================
# Error Handling
# =========================================================

def _error_handle(
    exc: Exception,
) -> web.Response:

    if isinstance(
        exc,
        DownloaderResponseError,
    ):

        if 400 <= exc.status < 500:

            return _error_response(
                status=exc.status,
                error="downloader_request_error",
                message=exc.message,
            )

        return _error_response(
            status=web.HTTPBadGateway.status_code,
            error="downloader_error",
            message=exc.message,
        )


    if isinstance(
        exc,
        InvalidDownloaderResponseError,
    ):

        return _error_response(
            status=web.HTTPBadGateway.status_code,
            error="invalid_downloader_response",
            message=str(exc),
        )


    if isinstance(
        exc,
        DownloaderClientError,
    ):

        return _error_response(
            status=(
                web.HTTPServiceUnavailable
                .status_code
            ),
            error="downloader_unavailable",
            message=str(exc),
        )


    traceback.print_exc()

    return _error_response(
        status=web.HTTPInternalServerError.status_code,
        error="unexpected_internal_error",
        message=str(exc),
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