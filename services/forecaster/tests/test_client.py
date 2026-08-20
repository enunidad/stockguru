from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from aiohttp import web

from src.client import (
    AnalyzerApiClient,
    DownloaderApiClient,
)
from src.exceptions import (
    AnalyzerResponseError,
    DownloaderResponseError,
    InvalidAnalyzerResponseError,
    InvalidDownloaderResponseError,
)


# =========================================================
# DownloaderApiClient
# Initialization
# =========================================================


def test_downloader_client_uses_default_base_url() -> None:
    client = DownloaderApiClient()

    assert client._base_url == "http://localhost:8080"


def test_downloader_client_removes_trailing_slash() -> None:
    client = DownloaderApiClient(
        base_url="http://localhost:8080/",
    )

    assert client._base_url == "http://localhost:8080"


def test_downloader_client_sets_timeout() -> None:
    client = DownloaderApiClient(
        timeout_seconds=15.0,
    )

    assert client._timeout.total == 15.0


# =========================================================
# DownloaderApiClient
# Ticker Normalization
# =========================================================


def test_downloader_normalizes_ticker() -> None:
    result = DownloaderApiClient._normalize_ticker(
        "  aapl  "
    )

    assert result == "AAPL"


def test_downloader_rejects_empty_ticker() -> None:
    with pytest.raises(
        InvalidDownloaderResponseError,
        match="Ticker cannot be empty.",
    ):
        DownloaderApiClient._normalize_ticker(
            "   "
        )


def test_downloader_rejects_non_string_ticker() -> None:
    with pytest.raises(
        InvalidDownloaderResponseError,
        match="Ticker must be a string.",
    ):
        DownloaderApiClient._normalize_ticker(
            123
        )


# =========================================================
# DownloaderApiClient
# Price History
# =========================================================


@pytest.mark.asyncio
async def test_price_history_returns_data(
    aiohttp_server,
) -> None:
    async def handler(
        request: web.Request,
    ) -> web.Response:
        return web.json_response(
            {
                "ticker": "AAPL",
                "data": [
                    {
                        "Date": "2026-08-18",
                        "Close": 230.50,
                    },
                    {
                        "Date": "2026-08-19",
                        "Close": 232.25,
                    },
                ],
            }
        )

    app = web.Application()

    app.router.add_get(
        "/history/{ticker}",
        handler,
    )

    server = await aiohttp_server(
        app
    )

    client = DownloaderApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    result = await client.price_history(
        "AAPL"
    )

    assert result == [
        {
            "Date": "2026-08-18",
            "Close": 230.50,
        },
        {
            "Date": "2026-08-19",
            "Close": 232.25,
        },
    ]


@pytest.mark.asyncio
async def test_price_history_normalizes_ticker_and_sends_parameters(
    aiohttp_server,
) -> None:
    received = {}

    async def handler(
        request: web.Request,
    ) -> web.Response:
        received["ticker"] = (
            request.match_info["ticker"]
        )

        received["query"] = dict(
            request.query
        )

        return web.json_response(
            {
                "data": [],
            }
        )

    app = web.Application()

    app.router.add_get(
        "/history/{ticker}",
        handler,
    )

    server = await aiohttp_server(
        app
    )

    client = DownloaderApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    await client.price_history(
        " aapl ",
        period="5y",
        interval="1wk",
        aggregate=True,
        auto_adjust=False,
    )

    assert received["ticker"] == "AAPL"

    assert received["query"] == {
        "period": "5y",
        "interval": "1wk",
        "aggregate": "true",
        "autoadjust": "false",
    }


@pytest.mark.asyncio
async def test_price_history_uses_defaults(
    aiohttp_server,
) -> None:
    received = {}

    async def handler(
        request: web.Request,
    ) -> web.Response:
        received.update(
            request.query
        )

        return web.json_response(
            {
                "data": [],
            }
        )

    app = web.Application()

    app.router.add_get(
        "/history/{ticker}",
        handler,
    )

    server = await aiohttp_server(
        app
    )

    client = DownloaderApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    await client.price_history(
        "AAPL"
    )

    assert received == {
        "period": "10y",
        "interval": "1d",
        "aggregate": "false",
        "autoadjust": "true",
    }


@pytest.mark.asyncio
async def test_price_history_rejects_missing_data(
    aiohttp_server,
) -> None:
    async def handler(
        request: web.Request,
    ) -> web.Response:
        return web.json_response(
            {
                "ticker": "AAPL",
            }
        )

    app = web.Application()

    app.router.add_get(
        "/history/{ticker}",
        handler,
    )

    server = await aiohttp_server(
        app
    )

    client = DownloaderApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    with pytest.raises(
        InvalidDownloaderResponseError,
        match="Downloader response 'data' must be a list.",
    ):
        await client.price_history(
            "AAPL"
        )


@pytest.mark.asyncio
async def test_price_history_rejects_non_list_data(
    aiohttp_server,
) -> None:
    async def handler(
        request: web.Request,
    ) -> web.Response:
        return web.json_response(
            {
                "data": {
                    "Close": 200.0,
                },
            }
        )

    app = web.Application()

    app.router.add_get(
        "/history/{ticker}",
        handler,
    )

    server = await aiohttp_server(
        app
    )

    client = DownloaderApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    with pytest.raises(
        InvalidDownloaderResponseError,
        match="Downloader response 'data' must be a list.",
    ):
        await client.price_history(
            "AAPL"
        )


@pytest.mark.asyncio
async def test_price_history_rejects_non_object_response(
    aiohttp_server,
) -> None:
    async def handler(
        request: web.Request,
    ) -> web.Response:
        return web.json_response(
            [
                {
                    "data": [],
                },
            ]
        )

    app = web.Application()

    app.router.add_get(
        "/history/{ticker}",
        handler,
    )

    server = await aiohttp_server(
        app
    )

    client = DownloaderApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    with pytest.raises(
        InvalidDownloaderResponseError,
        match="Downloader response must be a JSON object.",
    ):
        await client.price_history(
            "AAPL"
        )


@pytest.mark.asyncio
async def test_price_history_rejects_invalid_json(
    aiohttp_server,
) -> None:
    async def handler(
        request: web.Request,
    ) -> web.Response:
        return web.Response(
            text="not-json",
            content_type="text/plain",
        )

    app = web.Application()

    app.router.add_get(
        "/history/{ticker}",
        handler,
    )

    server = await aiohttp_server(
        app
    )

    client = DownloaderApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    with pytest.raises(
        InvalidDownloaderResponseError,
        match="Downloader returned invalid JSON.",
    ):
        await client.price_history(
            "AAPL"
        )


@pytest.mark.asyncio
async def test_price_history_raises_downloader_response_error(
    aiohttp_server,
) -> None:
    async def handler(
        request: web.Request,
    ) -> web.Response:
        return web.json_response(
            {
                "message": "Ticker not found.",
            },
            status=404,
        )

    app = web.Application()

    app.router.add_get(
        "/history/{ticker}",
        handler,
    )

    server = await aiohttp_server(
        app
    )

    client = DownloaderApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    with pytest.raises(
        DownloaderResponseError
    ) as exc_info:
        await client.price_history(
            "BAD"
        )

    assert exc_info.value.status == 404

    assert (
        exc_info.value.message
        == "Ticker not found."
    )


@pytest.mark.asyncio
async def test_price_history_http_error_uses_error_field(
    aiohttp_server,
) -> None:
    async def handler(
        request: web.Request,
    ) -> web.Response:
        return web.json_response(
            {
                "error": "Invalid ticker.",
            },
            status=400,
        )

    app = web.Application()

    app.router.add_get(
        "/history/{ticker}",
        handler,
    )

    server = await aiohttp_server(
        app
    )

    client = DownloaderApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    with pytest.raises(
        DownloaderResponseError
    ) as exc_info:
        await client.price_history(
            "BAD"
        )

    assert (
        exc_info.value.message
        == "Invalid ticker."
    )


@pytest.mark.asyncio
async def test_price_history_http_error_falls_back_to_text(
    aiohttp_server,
) -> None:
    async def handler(
        request: web.Request,
    ) -> web.Response:
        return web.Response(
            text="Service unavailable",
            status=503,
            content_type="text/plain",
        )

    app = web.Application()

    app.router.add_get(
        "/history/{ticker}",
        handler,
    )

    server = await aiohttp_server(
        app
    )

    client = DownloaderApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    with pytest.raises(
        DownloaderResponseError
    ) as exc_info:
        await client.price_history(
            "AAPL"
        )

    assert exc_info.value.status == 503

    assert (
        exc_info.value.message
        == "Service unavailable"
    )


# =========================================================
# DownloaderApiClient
# Latest Close
# =========================================================


@pytest.mark.asyncio
async def test_latest_close_returns_most_recent_valid_close() -> None:
    client = DownloaderApiClient()

    client.price_history = AsyncMock(
        return_value=[
            {
                "Date": "2026-08-17",
                "Close": 100.0,
            },
            {
                "Date": "2026-08-18",
                "Close": 101.0,
            },
            {
                "Date": "2026-08-19",
                "Close": 102.0,
            },
        ]
    )

    result = await client.latest_close(
        "AAPL"
    )

    assert result == pytest.approx(
        102.0
    )


@pytest.mark.asyncio
async def test_latest_close_requests_one_year_daily_history() -> None:
    client = DownloaderApiClient()

    client.price_history = AsyncMock(
        return_value=[
            {
                "Close": 100.0,
            },
        ]
    )

    await client.latest_close(
        "AAPL"
    )

    client.price_history.assert_awaited_once_with(
        "AAPL",
        period="1y",
        interval="1d",
        aggregate=False,
        auto_adjust=True,
    )


@pytest.mark.asyncio
async def test_latest_close_skips_invalid_trailing_rows() -> None:
    client = DownloaderApiClient()

    client.price_history = AsyncMock(
        return_value=[
            {
                "Close": 95.0,
            },
            {
                "Close": None,
            },
            {
                "Close": "banana",
            },
            {
                "Close": -1.0,
            },
        ]
    )

    result = await client.latest_close(
        "AAPL"
    )

    assert result == pytest.approx(
        95.0
    )


@pytest.mark.asyncio
async def test_latest_close_skips_non_object_rows() -> None:
    client = DownloaderApiClient()

    client.price_history = AsyncMock(
        return_value=[
            {
                "Close": 100.0,
            },
            "bad-row",
            None,
        ]
    )

    result = await client.latest_close(
        "AAPL"
    )

    assert result == pytest.approx(
        100.0
    )


@pytest.mark.asyncio
async def test_latest_close_rejects_empty_history() -> None:
    client = DownloaderApiClient()

    client.price_history = AsyncMock(
        return_value=[]
    )

    with pytest.raises(
        InvalidDownloaderResponseError,
        match="Downloader returned no price history.",
    ):
        await client.latest_close(
            "AAPL"
        )


@pytest.mark.asyncio
async def test_latest_close_rejects_history_without_valid_close() -> None:
    client = DownloaderApiClient()

    client.price_history = AsyncMock(
        return_value=[
            {
                "Close": None,
            },
            {
                "Close": "invalid",
            },
            {
                "Close": 0,
            },
            {
                "Close": -5,
            },
        ]
    )

    with pytest.raises(
        InvalidDownloaderResponseError,
        match="Downloader returned no valid closing price",
    ):
        await client.latest_close(
            "AAPL"
        )


# =========================================================
# DownloaderApiClient
# Dividends
# =========================================================


@pytest.mark.asyncio
async def test_get_dividends_returns_data(
    aiohttp_server,
) -> None:
    async def handler(
        request: web.Request,
    ) -> web.Response:
        return web.json_response(
            {
                "ticker": "AAPL",
                "data": [
                    {
                        "Date": "2026-05-09",
                        "Dividend": 0.26,
                    },
                    {
                        "Date": "2026-08-08",
                        "Dividend": 0.26,
                    },
                ],
            }
        )

    app = web.Application()

    app.router.add_get(
        "/dividends/{ticker}",
        handler,
    )

    server = await aiohttp_server(
        app
    )

    client = DownloaderApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    result = await client.get_dividends(
        "AAPL"
    )

    assert result == [
        {
            "Date": "2026-05-09",
            "Dividend": 0.26,
        },
        {
            "Date": "2026-08-08",
            "Dividend": 0.26,
        },
    ]


@pytest.mark.asyncio
async def test_get_dividends_normalizes_ticker_and_sends_period(
    aiohttp_server,
) -> None:
    received = {}

    async def handler(
        request: web.Request,
    ) -> web.Response:
        received["ticker"] = (
            request.match_info["ticker"]
        )

        received["period"] = (
            request.query["period"]
        )

        return web.json_response(
            {
                "data": [],
            }
        )

    app = web.Application()

    app.router.add_get(
        "/dividends/{ticker}",
        handler,
    )

    server = await aiohttp_server(
        app
    )

    client = DownloaderApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    await client.get_dividends(
        " msft ",
        period="5y",
    )

    assert received == {
        "ticker": "MSFT",
        "period": "5y",
    }


@pytest.mark.asyncio
async def test_get_dividends_rejects_non_list_data(
    aiohttp_server,
) -> None:
    async def handler(
        request: web.Request,
    ) -> web.Response:
        return web.json_response(
            {
                "data": {
                    "Dividend": 1.0,
                },
            }
        )

    app = web.Application()

    app.router.add_get(
        "/dividends/{ticker}",
        handler,
    )

    server = await aiohttp_server(
        app
    )

    client = DownloaderApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    with pytest.raises(
        InvalidDownloaderResponseError,
        match="Downloader dividend response 'data' must be a list.",
    ):
        await client.get_dividends(
            "AAPL"
        )


# =========================================================
# AnalyzerApiClient
# Initialization
# =========================================================


def test_analyzer_client_uses_default_base_url() -> None:
    client = AnalyzerApiClient()

    assert client._base_url == "http://localhost:8090"


def test_analyzer_client_removes_trailing_slash() -> None:
    client = AnalyzerApiClient(
        base_url="http://localhost:8090/",
    )

    assert client._base_url == "http://localhost:8090"


def test_analyzer_client_sets_timeout() -> None:
    client = AnalyzerApiClient(
        timeout_seconds=20.0,
    )

    assert client._timeout.total == 20.0


# =========================================================
# AnalyzerApiClient
# Ticker Normalization
# =========================================================


def test_analyzer_normalizes_ticker() -> None:
    result = AnalyzerApiClient._normalize_ticker(
        " msft "
    )

    assert result == "MSFT"


def test_analyzer_rejects_empty_ticker() -> None:
    with pytest.raises(
        InvalidAnalyzerResponseError,
        match="Ticker cannot be empty.",
    ):
        AnalyzerApiClient._normalize_ticker(
            " "
        )


def test_analyzer_rejects_non_string_ticker() -> None:
    with pytest.raises(
        InvalidAnalyzerResponseError,
        match="Ticker must be a string.",
    ):
        AnalyzerApiClient._normalize_ticker(
            None
        )


# =========================================================
# AnalyzerApiClient
# Analysis
# =========================================================


@pytest.mark.asyncio
async def test_get_analysis_returns_payload(
    aiohttp_server,
) -> None:
    async def handler(
        request: web.Request,
    ) -> web.Response:
        return web.json_response(
            {
                "ticker": "AAPL",
                "cagr": 0.123,
                "volatility": 0.20,
            }
        )

    app = web.Application()

    app.router.add_get(
        "/analysis/{ticker}",
        handler,
    )

    server = await aiohttp_server(
        app
    )

    client = AnalyzerApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    result = await client.get_analysis(
        "AAPL"
    )

    assert result == {
        "ticker": "AAPL",
        "cagr": 0.123,
        "volatility": 0.20,
    }


@pytest.mark.asyncio
async def test_get_analysis_normalizes_ticker_and_sends_parameters(
    aiohttp_server,
) -> None:
    received = {}

    async def handler(
        request: web.Request,
    ) -> web.Response:
        received["ticker"] = (
            request.match_info["ticker"]
        )

        received["query"] = dict(
            request.query
        )

        return web.json_response(
            {
                "cagr": 0.10,
            }
        )

    app = web.Application()

    app.router.add_get(
        "/analysis/{ticker}",
        handler,
    )

    server = await aiohttp_server(
        app
    )

    client = AnalyzerApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    await client.get_analysis(
        " aapl ",
        period="5y",
        interval="1wk",
        aggregate=True,
        auto_adjust=False,
    )

    assert received["ticker"] == "AAPL"

    assert received["query"] == {
        "period": "5y",
        "interval": "1wk",
        "aggregate": "true",
        "autoadjust": "false",
    }


@pytest.mark.asyncio
async def test_get_analysis_uses_defaults(
    aiohttp_server,
) -> None:
    received = {}

    async def handler(
        request: web.Request,
    ) -> web.Response:
        received.update(
            request.query
        )

        return web.json_response(
            {
                "cagr": 0.05,
            }
        )

    app = web.Application()

    app.router.add_get(
        "/analysis/{ticker}",
        handler,
    )

    server = await aiohttp_server(
        app
    )

    client = AnalyzerApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    await client.get_analysis(
        "AAPL"
    )

    assert received == {
        "period": "10y",
        "interval": "1d",
        "aggregate": "false",
        "autoadjust": "true",
    }


@pytest.mark.asyncio
async def test_get_analysis_rejects_non_object_response(
    aiohttp_server,
) -> None:
    async def handler(
        request: web.Request,
    ) -> web.Response:
        return web.json_response(
            [
                {
                    "cagr": 0.10,
                },
            ]
        )

    app = web.Application()

    app.router.add_get(
        "/analysis/{ticker}",
        handler,
    )

    server = await aiohttp_server(
        app
    )

    client = AnalyzerApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    with pytest.raises(
        InvalidAnalyzerResponseError,
        match="Analyzer response must be a JSON object.",
    ):
        await client.get_analysis(
            "AAPL"
        )


@pytest.mark.asyncio
async def test_get_analysis_rejects_invalid_json(
    aiohttp_server,
) -> None:
    async def handler(
        request: web.Request,
    ) -> web.Response:
        return web.Response(
            text="not-json",
            content_type="text/plain",
        )

    app = web.Application()

    app.router.add_get(
        "/analysis/{ticker}",
        handler,
    )

    server = await aiohttp_server(
        app
    )

    client = AnalyzerApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    with pytest.raises(
        InvalidAnalyzerResponseError,
        match="Analyzer returned invalid JSON.",
    ):
        await client.get_analysis(
            "AAPL"
        )


@pytest.mark.asyncio
async def test_get_analysis_raises_analyzer_response_error(
    aiohttp_server,
) -> None:
    async def handler(
        request: web.Request,
    ) -> web.Response:
        return web.json_response(
            {
                "message": "Unable to analyze ticker.",
            },
            status=400,
        )

    app = web.Application()

    app.router.add_get(
        "/analysis/{ticker}",
        handler,
    )

    server = await aiohttp_server(
        app
    )

    client = AnalyzerApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    with pytest.raises(
        AnalyzerResponseError
    ) as exc_info:
        await client.get_analysis(
            "BAD"
        )

    assert exc_info.value.status == 400

    assert (
        exc_info.value.message
        == "Unable to analyze ticker."
    )


@pytest.mark.asyncio
async def test_get_analysis_http_error_uses_error_field(
    aiohttp_server,
) -> None:
    async def handler(
        request: web.Request,
    ) -> web.Response:
        return web.json_response(
            {
                "error": "Analyzer failed.",
            },
            status=500,
        )

    app = web.Application()

    app.router.add_get(
        "/analysis/{ticker}",
        handler,
    )

    server = await aiohttp_server(
        app
    )

    client = AnalyzerApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    with pytest.raises(
        AnalyzerResponseError
    ) as exc_info:
        await client.get_analysis(
            "AAPL"
        )

    assert exc_info.value.status == 500

    assert (
        exc_info.value.message
        == "Analyzer failed."
    )


@pytest.mark.asyncio
async def test_get_analysis_http_error_falls_back_to_text(
    aiohttp_server,
) -> None:
    async def handler(
        request: web.Request,
    ) -> web.Response:
        return web.Response(
            text="Analyzer unavailable",
            status=503,
            content_type="text/plain",
        )

    app = web.Application()

    app.router.add_get(
        "/analysis/{ticker}",
        handler,
    )

    server = await aiohttp_server(
        app
    )

    client = AnalyzerApiClient(
        base_url=str(
            server.make_url("")
        ).rstrip("/")
    )

    with pytest.raises(
        AnalyzerResponseError
    ) as exc_info:
        await client.get_analysis(
            "AAPL"
        )

    assert exc_info.value.status == 503

    assert (
        exc_info.value.message
        == "Analyzer unavailable"
    )