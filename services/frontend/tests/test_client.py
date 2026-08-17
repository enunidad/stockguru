from __future__ import annotations

import pytest
from aiohttp import web

from src.client import DownloaderApiClient, ChartMgrApiClient
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

# =========================================================
# ChartMgrApiClient
# =========================================================


@pytest.mark.asyncio
async def test_get_history_chart_returns_chartmgr_response(
    aiohttp_server,
) -> None:
    received_request: dict[str, str] = {}

    async def chart_handler(
        request: web.Request,
    ) -> web.Response:
        received_request["ticker"] = request.match_info["ticker"]
        received_request["period"] = request.query["period"]
        received_request["interval"] = request.query["interval"]

        return web.json_response(
            {
                "chart_type": "candlestick",
                "title": "Monthly OHLC",
                "data": {
                    "x_values": [
                        "2026-06",
                        "2026-07",
                    ],
                    "y_values": {
                        "Open": [200.0, 210.0],
                        "High": [220.0, 225.0],
                        "Low": [195.0, 205.0],
                        "Close": [215.0, 218.0],
                    },
                },
                "labels": {
                    "x": "Date",
                    "y": "Value",
                },
                "legend": True,
            }
        )

    app = web.Application()
    app.router.add_get(
        "/charting/price_history/{ticker}",
        chart_handler,
    )

    server = await aiohttp_server(app)

    client = ChartMgrApiClient(
        base_url=str(server.make_url("")).rstrip("/")
    )

    result = await client.get_history_chart(
        "aapl",
        period="5y",
        interval="1wk",
    )

    assert result["chart_type"] == "candlestick"
    assert result["title"] == "Monthly OHLC"
    assert result["data"]["x_values"] == [
        "2026-06",
        "2026-07",
    ]
    assert result["data"]["y_values"]["Close"] == [
        215.0,
        218.0,
    ]

    assert received_request == {
        "ticker": "AAPL",
        "period": "5y",
        "interval": "1wk",
    }


@pytest.mark.asyncio
async def test_get_history_chart_uses_defaults(
    aiohttp_server,
) -> None:
    received_request: dict[str, str] = {}

    async def chart_handler(
        request: web.Request,
    ) -> web.Response:
        received_request["period"] = request.query["period"]
        received_request["interval"] = request.query["interval"]

        return web.json_response(
            {
                "chart_type": "candlestick",
                "title": "Monthly OHLC",
                "data": {
                    "x_values": [],
                    "y_values": {},
                },
                "labels": {
                    "x": "Date",
                    "y": "Value",
                },
                "legend": True,
            }
        )

    app = web.Application()
    app.router.add_get(
        "/charting/price_history/{ticker}",
        chart_handler,
    )

    server = await aiohttp_server(app)

    client = ChartMgrApiClient(
        base_url=str(server.make_url("")).rstrip("/")
    )

    await client.get_history_chart("AAPL")

    assert received_request == {
        "period": "10y",
        "interval": "1mo",
    }


@pytest.mark.asyncio
async def test_get_history_chart_raises_for_http_error(
    aiohttp_server,
) -> None:
    async def chart_handler(
        request: web.Request,
    ) -> web.Response:
        return web.json_response(
            {
                "error": "downloader_request_error",
                "message": "Ticker was invalid.",
            },
            status=400,
        )

    app = web.Application()
    app.router.add_get(
        "/charting/price_history/{ticker}",
        chart_handler,
    )

    server = await aiohttp_server(app)

    client = ChartMgrApiClient(
        base_url=str(server.make_url("")).rstrip("/")
    )

    with pytest.raises(
        ApiClientError,
        match="ChartMgr returned HTTP 400",
    ):
        await client.get_history_chart("BAD")


@pytest.mark.asyncio
async def test_get_history_chart_raises_for_invalid_json(
    aiohttp_server,
) -> None:
    async def chart_handler(
        request: web.Request,
    ) -> web.Response:
        return web.Response(
            text="not-json",
            content_type="text/plain",
        )

    app = web.Application()
    app.router.add_get(
        "/charting/price_history/{ticker}",
        chart_handler,
    )

    server = await aiohttp_server(app)

    client = ChartMgrApiClient(
        base_url=str(server.make_url("")).rstrip("/")
    )

    with pytest.raises(
        InvalidResponseError,
        match="ChartMgr returned invalid JSON",
    ):
        await client.get_history_chart("AAPL")


@pytest.mark.asyncio
async def test_get_history_chart_rejects_non_object_json(
    aiohttp_server,
) -> None:
    async def chart_handler(
        request: web.Request,
    ) -> web.Response:
        return web.json_response(
            [
                {
                    "chart_type": "candlestick",
                }
            ]
        )

    app = web.Application()
    app.router.add_get(
        "/charting/price_history/{ticker}",
        chart_handler,
    )

    server = await aiohttp_server(app)

    client = ChartMgrApiClient(
        base_url=str(server.make_url("")).rstrip("/")
    )

    with pytest.raises(
        InvalidResponseError,
        match="ChartMgr response must be a JSON object",
    ):
        await client.get_history_chart("AAPL")