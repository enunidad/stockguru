from __future__ import annotations

import os
from pathlib import Path
from typing import AsyncIterator

import aiohttp
from aiohttp import web


BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

DOWNLOADER_BASE_URL = os.getenv(
    "DOWNLOADER_BASE_URL",
    "http://localhost:8080",
)

FRONTEND_HOST = os.getenv("FRONTEND_HOST", "localhost")
FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", "8000"))

HTTP_SESSION_KEY: web.AppKey[aiohttp.ClientSession] = web.AppKey(
    "http_session",
    aiohttp.ClientSession,
)


async def index(request: web.Request) -> web.FileResponse:
    """
    Serve the main frontend page.
    """
    index_path = TEMPLATES_DIR / "index.html"

    if not index_path.exists():
        raise web.HTTPInternalServerError(
            reason=f"Frontend template not found: {index_path}"
        )

    return web.FileResponse(index_path)


async def health(request: web.Request) -> web.Response:
    """
    Basic health endpoint for the frontend service.
    """
    return web.json_response(
        {
            "status": "ok",
            "service": "frontend",
        }
    )


async def get_price_history(request: web.Request) -> web.Response:
    """
    Proxy a browser request to the downloader service.

    Example:
        GET /api/prices/AAPL?period=10y&interval=1d
    """
    ticker = request.match_info["ticker"].strip().upper()
    period = request.query.get("period", "10y")
    interval = request.query.get("interval", "1d")

    if not ticker:
        raise web.HTTPBadRequest(
            reason="Ticker cannot be empty."
        )

    downloader_url = (
        f"{DOWNLOADER_BASE_URL}/history/{ticker}"
    )

    session = request.app[HTTP_SESSION_KEY]

    try:
        async with session.get(
            downloader_url,
            params={
                "period": period,
                "interval": interval,
            },
        ) as response:
            try:
                payload = await response.json()
            except aiohttp.ContentTypeError:
                response_text = await response.text()

                return web.json_response(
                    {
                        "error": "invalid_downloader_response",
                        "message": (
                            "The downloader returned a response "
                            "that was not valid JSON."
                        ),
                        "details": response_text,
                    },
                    status=502,
                )

            return web.json_response(
                payload,
                status=response.status,
            )

    except aiohttp.ClientConnectorError:
        return web.json_response(
            {
                "error": "downloader_unavailable",
                "message": (
                    "The downloader service is unavailable. "
                    "Make sure it is running on port 8080."
                ),
            },
            status=503,
        )

    except aiohttp.ClientError as exc:
        return web.json_response(
            {
                "error": "downloader_request_failed",
                "message": str(exc),
            },
            status=502,
        )


async def http_session_context(
    app: web.Application,
) -> AsyncIterator[None]:
    """
    Create one reusable HTTP session for the application.

    The session is automatically closed when the server shuts down.
    """
    timeout = aiohttp.ClientTimeout(total=30)

    app[HTTP_SESSION_KEY] = aiohttp.ClientSession(
        timeout=timeout
    )

    yield

    await app[HTTP_SESSION_KEY].close()


def create_app() -> web.Application:
    """
    Build and configure the aiohttp frontend application.
    """
    app = web.Application()

    app.cleanup_ctx.append(http_session_context)

    app.router.add_get("/", index)
    app.router.add_get("/health", health)
    app.router.add_get(
        "/api/prices/{ticker}",
        get_price_history,
    )

    if not STATIC_DIR.exists():
        raise RuntimeError(
            f"Static directory not found: {STATIC_DIR}"
        )

    app.router.add_static(
        "/static/",
        path=STATIC_DIR,
        name="static",
    )

    return app


def main() -> None:
    app = create_app()

    web.run_app(
        app,
        host=FRONTEND_HOST,
        port=FRONTEND_PORT,
    )


if __name__ == "__main__":
    main()