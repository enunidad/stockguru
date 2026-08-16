from __future__ import annotations

from aiohttp import web
from typing import Optional

from .client import DownloaderApiClient, AnalyzerApiClient
from .exceptions import DownloaderResponseError, DownloaderClientError, InvalidDownloaderResponseError
from .service import ChartMgrService

import traceback


CHARTMGR_SERVICE_KEY = web.AppKey("chartmgr_service", ChartMgrService, )


def create_app(
    chartmgr_service: ChartMgrService | None = None,
    *,
    downloader_base_url: str = "http://localhost:8080",
    analyzer_base_url: str = "http://localhost:8090",
) -> web.Application:
    app = web.Application()

    if chartmgr_service is None:
        downloader_client = DownloaderApiClient(base_url=downloader_base_url, )
        analyzer_client = AnalyzerApiClient(base_url=analyzer_base_url, )

        chartmgr_service = ChartMgrService(downloader_client=downloader_client, 
                                            analyzer_client=analyzer_client)

    app[CHARTMGR_SERVICE_KEY] = chartmgr_service

    app.router.add_get("/health", health, )

    app.router.add_get("/charting/price_history/{ticker}", get_price_history, )
    app.router.add_get("/charting/volume/{ticker}", get_volume)

    return app


async def health(request: web.Request, ) -> web.Response:
    """Return the chartmgr service health status."""
    return web.json_response(
        {
            "status": "ok",
            "service": "chartmgr",
        }
    )

def _error_handle(exc: Exception) -> web.Response:
    if isinstance(exc, DownloaderResponseError):
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
    if isinstance(exc, InvalidDownloaderResponseError):
        return _error_response(
            status=web.HTTPBadGateway.status_code,
            error="invalid_downloader_response",
            message=str(exc),
        )
    if isinstance(exc, DownloaderClientError):
        return _error_response(
            status=web.HTTPServiceUnavailable.status_code,
            error="downloader_unavailable",
            message=str(exc),
        )
    traceback.print_exc()
    return _error_response(
            status=web.HTTPInternalServerError.status_code,
            error="Unexpected internal Error",
            message=str(exc),
        )
    

async def get_volume(request: web.Request) -> web.Response:
    """
    Return charting data for volume
    """
    ticker = request.match_info["ticker"]
    period = request.query.get("period", "10y", )
    interval = request.query.get("interval", "1mo", )
    chartmgr_service = request.app[CHARTMGR_SERVICE_KEY]

    try:
        result = await chartmgr_service.get_volume_history(ticker, period=period, interval=interval)
    except Exception as exc:
        return _error_handle(exc)

    return web.json_response(
        result.to_dict()
    )

async def get_price_history(request: web.Request, ) -> web.Response:
    """
    Return charting data for prices 
    """
    ticker = request.match_info["ticker"]
    period = request.query.get("period", "10y", )
    interval = request.query.get("interval", "1mo", )

    chartmgr_service = request.app[CHARTMGR_SERVICE_KEY]

    try:
        result = await chartmgr_service.get_price_history(ticker, period=period, interval=interval)
    except Exception as exc:
        return _error_handle(exc)

    return web.json_response(result.to_dict())


def _error_response(
    *,
    status: int,
    error: str,
    message: str,
) -> web.Response:
    """Create a consistent JSON error response."""
    return web.json_response(
        {
            "error": error,
            "message": message,
        },
        status=status,
    )