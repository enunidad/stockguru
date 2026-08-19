from __future__ import annotations

from pathlib import Path

from aiohttp import web
import aiohttp_jinja2
import jinja2

from .client import AnalyzerApiClient, DownloaderApiClient, ChartMgrApiClient, ForecasterApiClient
from .exceptions import ApiClientError, InvalidResponseError, ApiResponseError, ServiceUnavailableError
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

CHARTMGR_CLIENT_KEY = web.AppKey(
    "chartmgr_client",
    ChartMgrApiClient,
)

FORECASTER_CLIENT_KEY = web.AppKey(
    "forecaster_client",
    ForecasterApiClient,
)

@aiohttp_jinja2.template("index.html")
async def index(
    request: web.Request,
) -> dict:
    """Serve the main frontend page."""
    return {
        "active_page": "home",
    }


@aiohttp_jinja2.template("analyzer.html")
async def analyzer(
    request: web.Request,
) -> dict:
    """Serve the stock analyzer page."""
    return {
        "active_page": "analyzer",
    }


@aiohttp_jinja2.template("forecaster.html")
async def forecaster(
    request: web.Request,
) -> dict:
    """Serve the portfolio forecaster page."""
    return {
        "active_page": "forecaster",
    }


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

async def get_price_history_chart(request: web.Request, ) -> web.Response:
    ticker = request.match_info["ticker"].strip().upper()

    if not ticker:
        raise web.HTTPBadRequest(
            reason="Ticker cannot be empty.",
        )
    
    chartmgr_client = request.app[
        CHARTMGR_CLIENT_KEY
    ]

    period = request.query.get("period", "10y")
    interval = request.query.get("interval", "1mo")

    try:
        payload = await chartmgr_client.get_history_chart(ticker, period=period, interval=interval, )

    except InvalidResponseError as exc:
        return web.json_response(
            {
                "error": "invalid_chartmgr_response",
                "message": str(exc),
            },
            status=502,
        )

    except ApiResponseError as exc:
        if 400 <= exc.status < 500:
            return web.json_response(
                {
                    "error": "chartmgr_request_error",
                    "message": exc.message,
                },
                status=exc.status,
            )

        return web.json_response(
            {
                "error": "chartmgr_error",
                "message": exc.message,
            },
            status=502,
        )

    except ServiceUnavailableError as exc:
        return web.json_response(
            {
                "error": "chartmgr_unavailable",
                "message": str(exc),
            },
            status=503,
        )

    return web.json_response(payload)

async def get_price_history(
    request: web.Request,
) -> web.Response:
    """Proxy a monthly price-history request to the downloader service."""

    ticker = request.match_info["ticker"].strip().upper()

    if not ticker:
        raise web.HTTPBadRequest(
            reason="Ticker cannot be empty.",
        )

    downloader_client = request.app[
        DOWNLOADER_CLIENT_KEY
    ]

    price_request = PriceHistoryRequest(
        ticker=ticker,
        period="10y",
        interval="1mo",
    )

    try:
        payload = await downloader_client.get_price_history(
            price_request,
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

async def get_metadata(
    request: web.Request,
) -> web.Response:
    ticker = (
        request.match_info["ticker"]
        .strip()
        .upper()
    )

    if not ticker:
        raise web.HTTPBadRequest(
            reason="Ticker cannot be empty.",
        )

    downloader_client = request.app[
        DOWNLOADER_CLIENT_KEY
    ]

    try:
        metadata = await downloader_client.get_metadata(
            ticker,
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

    return web.json_response(metadata)

async def get_analysis(
    request: web.Request,
) -> web.Response:
    """Proxy a browser request to the analyzer service."""

    ticker = request.match_info["ticker"].strip().upper()
    period = request.query.get("period", "10y")

    if not ticker:
        raise web.HTTPBadRequest(
            reason="Ticker cannot be empty.",
        )

    analyzer_client = request.app[
        ANALYZER_CLIENT_KEY
    ]

    try:
        analysis = await analyzer_client.get_analysis(
            ticker,
            period=period,
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

async def run_forecast(
    request: web.Request,
) -> web.Response:
    """Proxy a forecast request to the Forecaster service."""

    try:
        payload = await request.json()

    except ValueError:
        return web.json_response(
            {
                "error": "invalid_json",
                "message": "Request body must contain valid JSON.",
            },
            status=400,
        )

    forecaster_client = request.app[
        FORECASTER_CLIENT_KEY
    ]

    try:
        result = await forecaster_client.forecast(
            payload
        )

    except InvalidResponseError as exc:
        return web.json_response(
            {
                "error": "invalid_forecaster_response",
                "message": str(exc),
            },
            status=502,
        )

    except ApiResponseError as exc:
        if 400 <= exc.status < 500:
            return web.json_response(
                {
                    "error": "forecaster_request_error",
                    "message": exc.message,
                },
                status=exc.status,
            )

        return web.json_response(
            {
                "error": "forecaster_error",
                "message": exc.message,
            },
            status=502,
        )

    except ServiceUnavailableError as exc:
        return web.json_response(
            {
                "error": "forecaster_unavailable",
                "message": str(exc),
            },
            status=503,
        )

    return web.json_response(result)


def create_app(
    downloader_client: DownloaderApiClient,
    analyzer_client: AnalyzerApiClient,
    chartmgr_client: ChartMgrApiClient,
    forecaster_client: ForecasterApiClient
) -> web.Application:
    """Create and configure the frontend application."""

    app = web.Application()

    aiohttp_jinja2.setup(
        app,
        loader=jinja2.FileSystemLoader(
            str(TEMPLATES_DIR)
        ),
    )

    app[DOWNLOADER_CLIENT_KEY] = downloader_client
    app[ANALYZER_CLIENT_KEY] = analyzer_client
    app[CHARTMGR_CLIENT_KEY] = chartmgr_client
    app[FORECASTER_CLIENT_KEY] = forecaster_client

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
    "/analyzer",
    analyzer,
    )

    app.router.add_get(
        "/forecaster",
        forecaster,
    )

    app.router.add_post(
        "/api/forecast",
        run_forecast,
    )

    app.router.add_get(
        "/api/charting/price_history/{ticker}",
        get_price_history_chart,
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