import pytest
from aiohttp import web

from src.client import DownloaderApiClient
from src.exceptions import (
    DownloaderResponseError,
    InvalidDownloaderResponseError,
)


@pytest.mark.asyncio
async def test_get_price_history_returns_parsed_history(aiohttp_server):
    received = {}

    async def history(request):
        received["ticker"] = request.match_info["ticker"]
        received["period"] = request.query["period"]
        received["interval"] = request.query["interval"]
        return web.json_response(
            {
                "ticker": request.match_info["ticker"],
                "period": request.query["period"],
                "interval": request.query["interval"],
                "rows": 2,
                "data": [
                    {"Date": "2024-01-01", "Close": 100.0},
                    {"Date": "2024-02-01", "Close": 110.0},
                ],
            }
        )

    app = web.Application()
    app.router.add_get("/history/{ticker}", history)
    server = await aiohttp_server(app)
    client = DownloaderApiClient(base_url=str(server.make_url("/")))

    result = await client.get_price_history(
        " aapl ",
        period="1y",
        interval="1mo",
    )

    assert received == {
        "ticker": "AAPL",
        "period": "1y",
        "interval": "1mo",
    }
    assert result.ticker == "AAPL"
    assert result.closing_prices == (100.0, 110.0)


@pytest.mark.asyncio
async def test_get_price_history_raises_for_downloader_http_error(aiohttp_server):
    async def history(request):
        return web.json_response(
            {"message": "Unknown ticker."},
            status=404,
        )

    app = web.Application()
    app.router.add_get("/history/{ticker}", history)
    server = await aiohttp_server(app)
    client = DownloaderApiClient(base_url=str(server.make_url("/")))

    with pytest.raises(DownloaderResponseError) as exc_info:
        await client.get_price_history("BAD")

    assert exc_info.value.status == 404
    assert exc_info.value.message == "Unknown ticker."


@pytest.mark.asyncio
async def test_get_price_history_rejects_invalid_json(aiohttp_server):
    async def history(request):
        return web.Response(text="not json", content_type="text/plain")

    app = web.Application()
    app.router.add_get("/history/{ticker}", history)
    server = await aiohttp_server(app)
    client = DownloaderApiClient(base_url=str(server.make_url("/")))

    with pytest.raises(InvalidDownloaderResponseError):
        await client.get_price_history("AAPL")


@pytest.mark.asyncio
async def test_get_price_history_rejects_non_object_json(aiohttp_server):
    async def history(request):
        return web.json_response([1, 2, 3])

    app = web.Application()
    app.router.add_get("/history/{ticker}", history)
    server = await aiohttp_server(app)
    client = DownloaderApiClient(base_url=str(server.make_url("/")))

    with pytest.raises(InvalidDownloaderResponseError):
        await client.get_price_history("AAPL")


@pytest.mark.asyncio
async def test_get_price_history_rejects_empty_rows(aiohttp_server):
    async def history(request):
        return web.json_response(
            {
                "ticker": "AAPL",
                "period": "1y",
                "interval": "1mo",
                "rows": 0,
                "data": [],
            }
        )

    app = web.Application()
    app.router.add_get("/history/{ticker}", history)
    server = await aiohttp_server(app)
    client = DownloaderApiClient(base_url=str(server.make_url("/")))

    with pytest.raises(InvalidDownloaderResponseError):
        await client.get_price_history("AAPL")


@pytest.mark.parametrize("ticker", ["", "   ", None, 123])
def test_normalize_ticker_rejects_invalid_values(ticker):
    with pytest.raises(InvalidDownloaderResponseError):
        DownloaderApiClient._normalize_ticker(ticker)
