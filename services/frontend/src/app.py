from __future__ import annotations

from pathlib import Path

from aiohttp import web

from .client import AnalyzerApiClient, DownloaderApiClient
from .exceptions import ApiClientError, InvalidResponseError
from .schemas import PriceHistoryRequest


BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"


ANALYZER_CLIENT_KEY = web.AppKey(
    "analyzer_client",
    AnalyzerApiClient,
)

DOWNLOADER_CLIENT_KEY = web.AppKey(
    "downloader_client",
    DownloaderApiClient,
)


async def index(
    request: web.Request,
) -> web.FileResponse:
    """Serve the main frontend page."""

    index_path = TEMPLATES_DIR / "index.html"

    if not index_path.exists():
        raise web.HTTPInternalServerError(
            reason=f"Frontend template not found: {index_path}"
        )

    return web.FileResponse(index_path)


async def health(
    request: web.Request,
) -> web.Response:
    """Return the frontend service health status."""

    return web.json_response(
        {
            "status": "ok",
            "service": "frontend",
        }
    )


async def get_price_history(
    request: web.Request,
) -> web.Response:
    """Proxy a browser request to the downloader service."""

    ticker = request.match_info["ticker"].strip().upper()
    period = request.query.get("period", "10y")
    interval = request.query.get("interval", "1mo")

    if not ticker:
        raise web.HTTPBadRequest(
            reason="Ticker cannot be empty."
        )

    downloader_client = request.app[
        DOWNLOADER_CLIENT_KEY
    ]

    price_request = PriceHistoryRequest(
        ticker=ticker,
        period=period,
        interval=interval,
    )

    try:
        payload = await downloader_client.get_price_history(
            price_request
        )

    except InvalidResponseError as exc:
        return web.json_response(
            {
                "error": "invalid_downloader_response",
                "message": str(exc),
            },
            status=502,
        )

    except ApiClientError as exc:
        return web.json_response(
            {
                "error": "downloader_unavailable",
                "message": str(exc),
            },
            status=503,
        )

    return web.json_response(payload)

async def get_metadata(request: web.Request) -> web.Response:
    ticker = request.match_info["ticker"]

    downloader_client = request.app[
        DOWNLOADER_CLIENT_KEY
    ]

    metadata = await downloader_client.get_metadata(
        ticker,
    )

    return web.json_response(metadata)


async def get_analysis(
    request: web.Request,
) -> web.Response:
    """Proxy a browser request to the analyzer service."""

    ticker = request.match_info["ticker"].strip().upper()
    period = request.query.get("period", "10y")
    interval = request.query.get("interval", "1mo")

    if not ticker:
        raise web.HTTPBadRequest(
            reason="Ticker cannot be empty."
        )

    analyzer_client = request.app[
        ANALYZER_CLIENT_KEY
    ]

    try:
        analysis = await analyzer_client.get_analysis(
            ticker,
            period=period,
            interval=interval,
        )

    except InvalidResponseError as exc:
        return web.json_response(
            {
                "error": "invalid_analyzer_response",
                "message": str(exc),
            },
            status=502,
        )

    except ApiClientError as exc:
        return web.json_response(
            {
                "error": "analyzer_unavailable",
                "message": str(exc),
            },
            status=503,
        )

    return web.json_response(analysis)


def create_app(
    downloader_client: DownloaderApiClient,
    analyzer_client: AnalyzerApiClient,
) -> web.Application:
    """Create and configure the frontend application."""

    app = web.Application()

    app[DOWNLOADER_CLIENT_KEY] = downloader_client
    app[ANALYZER_CLIENT_KEY] = analyzer_client

    app.router.add_get(
        "/health",
        health,
    )

    app.router.add_get(
        "/api/prices/{ticker}",
        get_price_history,
    )

    app.router.add_get(
        "/api/analysis/{ticker}",
        get_analysis,
    )

    app.router.add_get(
        "/",
        index,
    )

    app.router.add_get(
        "/api/metadata/{ticker}",
        get_metadata,
    )

    app.router.add_static(
        "/static/",
        path=STATIC_DIR,
        name="static",
    )

    return app