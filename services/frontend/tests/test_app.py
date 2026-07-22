from __future__ import annotations

from pathlib import Path

import pytest
from aiohttp import web

import src.app as frontend_app


@pytest.mark.asyncio
async def test_health_endpoint(aiohttp_client) -> None:
    app = frontend_app.create_app()
    client = await aiohttp_client(app)

    response = await client.get("/health")
    body = await response.json()

    assert response.status == 200
    assert body == {
        "status": "ok",
        "service": "frontend",
    }


@pytest.mark.asyncio
async def test_index_returns_html(aiohttp_client) -> None:
    app = frontend_app.create_app()
    client = await aiohttp_client(app)

    response = await client.get("/")
    body = await response.text()

    assert response.status == 200
    assert response.content_type == "text/html"
    assert "StocksGuru" in body
    assert 'id="stock-form"' in body


@pytest.mark.asyncio
async def test_static_javascript_is_served(
    aiohttp_client,
) -> None:
    app = frontend_app.create_app()
    client = await aiohttp_client(app)

    response = await client.get("/static/app.js")
    body = await response.text()

    assert response.status == 200
    assert "loadPrices" in body
    assert "stock-form" in body


@pytest.mark.asyncio
async def test_price_proxy_returns_downloader_response(
    aiohttp_client,
    aiohttp_server,
    monkeypatch,
) -> None:
    received_request: dict[str, str] = {}

    async def history_handler(
        request: web.Request,
    ) -> web.Response:
        received_request["ticker"] = request.match_info["ticker"]
        received_request["period"] = request.query["period"]
        received_request["interval"] = request.query["interval"]

        return web.json_response(
            {
                "ticker": "AAPL",
                "period": "5y",
                "interval": "1wk",
                "rows": 1,
                "data": [
                    {
                        "Date": "2026-07-10",
                        "Close": 315.32,
                    }
                ],
            }
        )

    downstream_app = web.Application()
    downstream_app.router.add_get(
        "/history/{ticker}",
        history_handler,
    )

    downstream_server = await aiohttp_server(
        downstream_app
    )

    monkeypatch.setattr(
        frontend_app,
        "DOWNLOADER_BASE_URL",
        str(downstream_server.make_url("")).rstrip("/"),
    )

    app = frontend_app.create_app()
    client = await aiohttp_client(app)

    response = await client.get(
        "/api/prices/aapl?period=5y&interval=1wk"
    )
    body = await response.json()

    assert response.status == 200
    assert body["ticker"] == "AAPL"
    assert body["rows"] == 1
    assert body["data"][0]["Close"] == 315.32

    assert received_request == {
        "ticker": "AAPL",
        "period": "5y",
        "interval": "1wk",
    }


@pytest.mark.asyncio
async def test_price_proxy_uses_default_query_values(
    aiohttp_client,
    aiohttp_server,
    monkeypatch,
) -> None:
    received_request: dict[str, str] = {}

    async def history_handler(
        request: web.Request,
    ) -> web.Response:
        received_request["period"] = request.query["period"]
        received_request["interval"] = request.query["interval"]

        return web.json_response(
            {
                "ticker": "AAPL",
                "period": request.query["period"],
                "interval": request.query["interval"],
                "rows": 0,
                "data": [],
            }
        )

    downstream_app = web.Application()
    downstream_app.router.add_get(
        "/history/{ticker}",
        history_handler,
    )

    downstream_server = await aiohttp_server(
        downstream_app
    )

    monkeypatch.setattr(
        frontend_app,
        "DOWNLOADER_BASE_URL",
        str(downstream_server.make_url("")).rstrip("/"),
    )

    app = frontend_app.create_app()
    client = await aiohttp_client(app)

    response = await client.get("/api/prices/AAPL")

    assert response.status == 200
    assert received_request == {
        "period": "10y",
        "interval": "1d",
    }


@pytest.mark.asyncio
async def test_price_proxy_preserves_downloader_error_status(
    aiohttp_client,
    aiohttp_server,
    monkeypatch,
) -> None:
    async def history_handler(
        request: web.Request,
    ) -> web.Response:
        return web.json_response(
            {
                "error": "EmptyDownloadError",
                "message": "No price history returned.",
            },
            status=400,
        )

    downstream_app = web.Application()
    downstream_app.router.add_get(
        "/history/{ticker}",
        history_handler,
    )

    downstream_server = await aiohttp_server(
        downstream_app
    )

    monkeypatch.setattr(
        frontend_app,
        "DOWNLOADER_BASE_URL",
        str(downstream_server.make_url("")).rstrip("/"),
    )

    app = frontend_app.create_app()
    client = await aiohttp_client(app)

    response = await client.get("/api/prices/BAD")
    body = await response.json()

    assert response.status == 400
    assert body == {
        "error": "EmptyDownloadError",
        "message": "No price history returned.",
    }


@pytest.mark.asyncio
async def test_price_proxy_returns_502_for_invalid_json(
    aiohttp_client,
    aiohttp_server,
    monkeypatch,
) -> None:
    async def history_handler(
        request: web.Request,
    ) -> web.Response:
        return web.Response(
            text="404: Not Found",
            content_type="text/plain",
            status=404,
        )

    downstream_app = web.Application()
    downstream_app.router.add_get(
        "/history/{ticker}",
        history_handler,
    )

    downstream_server = await aiohttp_server(
        downstream_app
    )

    monkeypatch.setattr(
        frontend_app,
        "DOWNLOADER_BASE_URL",
        str(downstream_server.make_url("")).rstrip("/"),
    )

    app = frontend_app.create_app()
    client = await aiohttp_client(app)

    response = await client.get("/api/prices/AAPL")
    body = await response.json()

    assert response.status == 502
    assert body["error"] == "invalid_downloader_response"
    assert body["details"] == "404: Not Found"


@pytest.mark.asyncio
async def test_price_proxy_returns_503_when_downloader_unavailable(
    aiohttp_client,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        frontend_app,
        "DOWNLOADER_BASE_URL",
        "http://127.0.0.1:1",
    )

    app = frontend_app.create_app()
    client = await aiohttp_client(app)

    response = await client.get("/api/prices/AAPL")
    body = await response.json()

    assert response.status == 503
    assert body["error"] == "downloader_unavailable"


@pytest.mark.asyncio
async def test_index_returns_500_when_template_missing(
    aiohttp_client,
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        frontend_app,
        "TEMPLATES_DIR",
        tmp_path,
    )

    app = frontend_app.create_app()
    client = await aiohttp_client(app)

    response = await client.get("/")

    assert response.status == 500