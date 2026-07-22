from __future__ import annotations

import pytest
from aiohttp import web

from src.client import DownloaderApiClient
from src.exceptions import (
    ApiClientError,
    InvalidResponseError,
)
from src.schemas import PriceHistoryRequest


@pytest.mark.asyncio
async def test_get_price_history_returns_downloader_response(
    aiohttp_server,
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

    app = web.Application()
    app.router.add_get("/history/{ticker}", history_handler)

    server = await aiohttp_server(app)

    client = DownloaderApiClient(
        base_url=str(server.make_url("")).rstrip("/")
    )

    result = await client.get_price_history(
        PriceHistoryRequest(
            ticker="AAPL",
            period="5y",
            interval="1wk",
        )
    )

    assert result["ticker"] == "AAPL"
    assert result["rows"] == 1
    assert result["data"][0]["Close"] == 315.32

    assert received_request == {
        "ticker": "AAPL",
        "period": "5y",
        "interval": "1wk",
    }


@pytest.mark.asyncio
async def test_get_price_history_raises_for_http_error(
    aiohttp_server,
) -> None:
    async def history_handler(
        request: web.Request,
    ) -> web.Response:
        return web.json_response(
            {
                "error": "InvalidTickerError",
                "message": "Ticker was invalid.",
            },
            status=400,
        )

    app = web.Application()
    app.router.add_get("/history/{ticker}", history_handler)

    server = await aiohttp_server(app)

    client = DownloaderApiClient(
        base_url=str(server.make_url("")).rstrip("/")
    )

    with pytest.raises(
        ApiClientError,
        match="Downloader returned HTTP 400",
    ):
        await client.get_price_history(
            PriceHistoryRequest(ticker="BAD")
        )


@pytest.mark.asyncio
async def test_get_price_history_raises_for_invalid_json(
    aiohttp_server,
) -> None:
    async def history_handler(
        request: web.Request,
    ) -> web.Response:
        return web.Response(
            text="not-json",
            content_type="text/plain",
        )

    app = web.Application()
    app.router.add_get("/history/{ticker}", history_handler)

    server = await aiohttp_server(app)

    client = DownloaderApiClient(
        base_url=str(server.make_url("")).rstrip("/")
    )

    with pytest.raises(
        InvalidResponseError,
        match="Downloader returned invalid JSON",
    ):
        await client.get_price_history(
            PriceHistoryRequest(ticker="AAPL")
        )


@pytest.mark.asyncio
async def test_get_price_history_rejects_non_object_json(
    aiohttp_server,
) -> None:
    async def history_handler(
        request: web.Request,
    ) -> web.Response:
        return web.json_response(
            [
                {
                    "ticker": "AAPL",
                    "rows": 1,
                }
            ]
        )

    app = web.Application()
    app.router.add_get("/history/{ticker}", history_handler)

    server = await aiohttp_server(app)

    client = DownloaderApiClient(
        base_url=str(server.make_url("")).rstrip("/")
    )

    with pytest.raises(
        InvalidResponseError,
        match="must be a JSON object",
    ):
        await client.get_price_history(
            PriceHistoryRequest(ticker="AAPL")
        )


@pytest.mark.asyncio
async def test_get_price_history_requires_ticker(
    aiohttp_server,
) -> None:
    async def history_handler(
        request: web.Request,
    ) -> web.Response:
        return web.json_response(
            {
                "rows": 1,
                "data": [],
            }
        )

    app = web.Application()
    app.router.add_get("/history/{ticker}", history_handler)

    server = await aiohttp_server(app)

    client = DownloaderApiClient(
        base_url=str(server.make_url("")).rstrip("/")
    )

    with pytest.raises(
        InvalidResponseError,
        match="Missing ticker",
    ):
        await client.get_price_history(
            PriceHistoryRequest(ticker="AAPL")
        )


@pytest.mark.asyncio
async def test_get_price_history_requires_rows(
    aiohttp_server,
) -> None:
    async def history_handler(
        request: web.Request,
    ) -> web.Response:
        return web.json_response(
            {
                "ticker": "AAPL",
                "data": [],
            }
        )

    app = web.Application()
    app.router.add_get("/history/{ticker}", history_handler)

    server = await aiohttp_server(app)

    client = DownloaderApiClient(
        base_url=str(server.make_url("")).rstrip("/")
    )

    with pytest.raises(
        InvalidResponseError,
        match="Missing price history",
    ):
        await client.get_price_history(
            PriceHistoryRequest(ticker="AAPL")
        )