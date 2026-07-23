from __future__ import annotations

from aiohttp import web

from .client import DownloaderApiClient
from .exceptions import (
    CalculationError,
    DownloaderClientError,
    DownloaderResponseError,
    InvalidDownloaderResponseError,
)
from .service import AnalyzerService


ANALYZER_SERVICE_KEY = web.AppKey(
    "analyzer_service",
    AnalyzerService,
)


def create_app(
    analyzer_service: AnalyzerService | None = None,
    *,
    downloader_base_url: str = "http://localhost:8080",
) -> web.Application:
    app = web.Application()

    if analyzer_service is None:
        downloader_client = DownloaderApiClient(
            base_url=downloader_base_url,
        )

        analyzer_service = AnalyzerService(
            downloader_client=downloader_client,
        )

    app[ANALYZER_SERVICE_KEY] = analyzer_service

    app.router.add_get(
        "/health",
        health,
    )

    app.router.add_get(
        "/analysis/{ticker}",
        analyze_ticker,
    )

    return app


async def health(
    request: web.Request,
) -> web.Response:
    """Return the analyzer service health status."""
    return web.json_response(
        {
            "status": "ok",
            "service": "analyzer",
        }
    )


async def analyze_ticker(
    request: web.Request,
) -> web.Response:
    """
    Analyze historical price data for a ticker.

    Example:
        GET /analysis/AAPL?period=10y&interval=1d
    """
    ticker = request.match_info["ticker"]

    period = request.query.get(
        "period",
        "10y",
    )

    interval = request.query.get(
        "interval",
        "1mo",
    )

    analyzer_service = request.app[
        ANALYZER_SERVICE_KEY
    ]

    try:
        result = await analyzer_service.analyze_ticker(
            ticker,
            period=period,
            interval=interval,
        )

    except DownloaderResponseError as exc:
        return _handle_downloader_response_error(exc)

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

    except CalculationError as exc:
        return _error_response(
            status=web.HTTPBadRequest.status_code,
            error="calculation_error",
            message=str(exc),
        )

    return web.json_response(
        result.to_dict()
    )


def _handle_downloader_response_error(
    exc: DownloaderResponseError,
) -> web.Response:
    """
    Translate downloader HTTP failures into analyzer HTTP responses.

    Client-side downloader failures remain 4xx responses. Downloader
    server failures become 502 because the analyzer's dependency failed.
    """
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