from __future__ import annotations

from json import JSONDecodeError
from unittest.mock import AsyncMock, patch

import aiohttp
import pytest

from src.client import MyClient
from src.exceptions import (
    AnalyzerClientError,
    AnalyzerResponseError,
    DownloaderClientError,
    DownloaderResponseError,
    InvalidAnalyzerResponseError,
    InvalidDownloaderResponseError,
    WorkerResponseError,
    InvalidWorkerResponseError,
)


class FakeResponse:
    def __init__(
        self,
        *,
        status: int = 200,
        json_data=None,
        json_error: Exception | None = None,
        text_data: str = "",
    ):
        self.status = status
        self._json_data = json_data
        self._json_error = json_error
        self._text_data = text_data

    async def json(self):
        if self._json_error is not None:
            raise self._json_error

        return self._json_data

    async def text(self):
        return self._text_data


class FakeResponseContext:
    def __init__(self, response):
        self.response = response

    async def __aenter__(self):
        return self.response

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeSession:
    def __init__(
        self,
        response=None,
        *,
        request_error: Exception | None = None,
        **kwargs,
    ):
        self.response = response
        self.request_error = request_error
        self.url = None
        self.params = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def get(self, url, params=None):
        self.url = url
        self.params = params

        if self.request_error is not None:
            raise self.request_error

        return FakeResponseContext(self.response)


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


def test_client_uses_provided_base_urls():
    client = MyClient(
        downloader_url="http://downloader/",
        analyzer_url="http://analyzer/",
    )

    assert client._downloader == "http://downloader"
    assert client._analyzer == "http://analyzer"


def test_client_creates_timeout():
    client = MyClient(timeout_seconds=12.5)

    assert client._timeout.total == 12.5


# ---------------------------------------------------------------------------
# Ticker normalization
# ---------------------------------------------------------------------------


def test_normalize_ticker():
    assert MyClient._normalize_ticker("  aapl  ") == "AAPL"


def test_normalize_ticker_preserves_exchange_suffix():
    assert MyClient._normalize_ticker("  ffn.to ") == "FFN.TO"


def test_normalize_ticker_rejects_empty_string():
    with pytest.raises(
        InvalidDownloaderResponseError,
        match="Ticker cannot be empty",
    ):
        MyClient._normalize_ticker("   ")


def test_normalize_ticker_rejects_non_string():
    with pytest.raises(
        InvalidDownloaderResponseError,
        match="Ticker must be a string",
    ):
        MyClient._normalize_ticker(None)


# ---------------------------------------------------------------------------
# Error message parsing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_read_error_message_uses_message():
    response = FakeResponse(
        status=400,
        json_data={
            "message": "Ticker does not exist.",
        },
    )

    result = await MyClient._read_error_message(
        response,
        "Downloader",
    )

    assert result == "Ticker does not exist."


@pytest.mark.asyncio
async def test_read_error_message_falls_back_to_error():
    response = FakeResponse(
        status=400,
        json_data={
            "error": "Bad request",
        },
    )

    result = await MyClient._read_error_message(
        response,
        "Downloader",
    )

    assert result == "Bad request"


@pytest.mark.asyncio
async def test_read_error_message_uses_plain_text():
    response = FakeResponse(
        status=500,
        json_error=JSONDecodeError(
            "Invalid JSON",
            "",
            0,
        ),
        text_data="Server exploded",
    )

    result = await MyClient._read_error_message(
        response,
        "Downloader",
    )

    assert result == "Server exploded"


@pytest.mark.asyncio
async def test_read_error_message_uses_default_when_body_empty():
    response = FakeResponse(
        status=500,
        json_error=JSONDecodeError(
            "Invalid JSON",
            "",
            0,
        ),
        text_data="",
    )

    result = await MyClient._read_error_message(
        response,
        "Downloader",
    )

    assert result == "Downloader returned an error."


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_read_response_returns_dict():
    client = MyClient()

    response = FakeResponse(
        status=200,
        json_data={
            "data": [1, 2, 3],
        },
    )

    result = await client._read_response(
        response,
        "downloader",
    )

    assert result == {
        "data": [1, 2, 3],
    }


@pytest.mark.asyncio
async def test_read_response_rejects_non_dict_from_downloader():
    client = MyClient()

    response = FakeResponse(
        status=200,
        json_data=[
            1,
            2,
            3,
        ],
    )

    with pytest.raises(
        InvalidDownloaderResponseError,
        match="Downloader response must be a JSON object",
    ):
        await client._read_response(
            response,
            "Downloader",
        )


@pytest.mark.asyncio
async def test_read_response_rejects_non_dict_from_analyzer():
    client = MyClient()

    response = FakeResponse(
        status=200,
        json_data=[
            1,
            2,
            3,
        ],
    )

    with pytest.raises(
        InvalidAnalyzerResponseError,
        match="Analyzer response must be a JSON object",
    ):
        await client._read_response(
            response,
            "Analyzer",
        )


@pytest.mark.asyncio
async def test_read_response_rejects_non_dict_from_unknown_worker():
    client = MyClient()

    response = FakeResponse(
        status=200,
        json_data=[],
    )

    with pytest.raises(
        InvalidWorkerResponseError,
        match="response must be a JSON object",
    ):
        await client._read_response(
            response,
            "SomethingElse",
        )


@pytest.mark.asyncio
async def test_read_response_rejects_invalid_downloader_json():
    client = MyClient()

    response = FakeResponse(
        status=200,
        json_error=JSONDecodeError(
            "Invalid JSON",
            "",
            0,
        ),
    )

    with pytest.raises(
        InvalidDownloaderResponseError,
        match="Downloader returned an invalid JSON",
    ):
        await client._read_response(
            response,
            "Downloader",
        )


@pytest.mark.asyncio
async def test_read_response_rejects_invalid_analyzer_json():
    client = MyClient()

    response = FakeResponse(
        status=200,
        json_error=JSONDecodeError(
            "Invalid JSON",
            "",
            0,
        ),
    )

    with pytest.raises(
        InvalidAnalyzerResponseError,
        match="Analyzer returned an invalid JSON",
    ):
        await client._read_response(
            response,
            "Analyzer",
        )


@pytest.mark.asyncio
async def test_read_response_raises_downloader_response_error():
    client = MyClient()

    response = FakeResponse(
        status=404,
        json_data={
            "message": "Ticker not found.",
        },
    )

    with pytest.raises(DownloaderResponseError):
        await client._read_response(
            response,
            "Downloader",
        )


@pytest.mark.asyncio
async def test_read_response_raises_analyzer_response_error():
    client = MyClient()

    response = FakeResponse(
        status=500,
        json_data={
            "message": "Analysis failed.",
        },
    )

    with pytest.raises(AnalyzerResponseError):
        await client._read_response(
            response,
            "Analyzer",
        )


@pytest.mark.asyncio
async def test_read_response_raises_worker_response_error():
    client = MyClient()

    response = FakeResponse(
        status=500,
        json_data={
            "message": "Something failed.",
        },
    )

    with pytest.raises(WorkerResponseError):
        await client._read_response(
            response,
            "UnknownWorker",
        )


# ---------------------------------------------------------------------------
# Price history
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_price_history_returns_data():
    client = MyClient(
        downloader_url="http://downloader",
    )

    expected = [
        {
            "Date": "2026-01-01",
            "Close": 100.0,
        },
        {
            "Date": "2026-01-02",
            "Close": 101.0,
        },
    ]

    response = FakeResponse(
        json_data={
            "data": expected,
        },
    )

    fake_session = FakeSession(response)

    with patch(
        "src.client.aiohttp.ClientSession",
        return_value=fake_session,
    ):
        result = await client.price_history(
            " aapl ",
            period="5y",
            interval="1wk",
            aggregate=True,
            auto_adjust=False,
        )

    assert result == expected

    assert fake_session.url == (
        "http://downloader/history/AAPL"
    )

    assert fake_session.params == {
        "period": "5y",
        "interval": "1wk",
        "aggregate": "true",
        "autoadjust": "false",
    }


@pytest.mark.asyncio
async def test_price_history_uses_defaults():
    client = MyClient(
        downloader_url="http://downloader",
    )

    response = FakeResponse(
        json_data={
            "data": [],
        },
    )

    fake_session = FakeSession(response)

    with patch(
        "src.client.aiohttp.ClientSession",
        return_value=fake_session,
    ):
        await client.price_history("AAPL")

    assert fake_session.params == {
        "period": "10y",
        "interval": "1d",
        "aggregate": "false",
        "autoadjust": "true",
    }


@pytest.mark.asyncio
async def test_price_history_rejects_invalid_data():
    client = MyClient(
        downloader_url="http://downloader",
    )

    response = FakeResponse(
        json_data={
            "data": {
                "Close": 100,
            },
        },
    )

    fake_session = FakeSession(response)

    with patch(
        "src.client.aiohttp.ClientSession",
        return_value=fake_session,
    ):
        with pytest.raises(
            InvalidDownloaderResponseError,
            match="'data' must be a list",
        ):
            await client.price_history("AAPL")


@pytest.mark.asyncio
async def test_price_history_maps_connection_error():
    client = MyClient()

    fake_session = FakeSession(
        request_error=aiohttp.ClientConnectionError(),
    )

    with patch(
        "src.client.aiohttp.ClientSession",
        return_value=fake_session,
    ):
        with pytest.raises(
            DownloaderClientError,
            match="Unable to connect",
        ):
            await client.price_history("AAPL")


@pytest.mark.asyncio
async def test_price_history_maps_timeout_error():
    client = MyClient()

    fake_session = FakeSession(
        request_error=aiohttp.ServerTimeoutError(),
    )

    with patch(
        "src.client.aiohttp.ClientSession",
        return_value=fake_session,
    ):
        with pytest.raises(
            DownloaderClientError,
            match="timed out",
        ):
            await client.price_history("AAPL")


@pytest.mark.asyncio
async def test_price_history_maps_generic_client_error():
    client = MyClient()

    fake_session = FakeSession(
        request_error=aiohttp.ClientError(),
    )

    with patch(
        "src.client.aiohttp.ClientSession",
        return_value=fake_session,
    ):
        with pytest.raises(
            DownloaderClientError,
            match="request failed",
        ):
            await client.price_history("AAPL")


# ---------------------------------------------------------------------------
# Latest close
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_latest_close_returns_most_recent_valid_close():
    client = MyClient()

    client.price_history = AsyncMock(
        return_value=[
            {
                "Date": "2026-01-01",
                "Close": 100.0,
            },
            {
                "Date": "2026-01-02",
                "Close": 105.25,
            },
        ]
    )

    result = await client.latest_close("AAPL")

    assert result == 105.25

    client.price_history.assert_awaited_once_with(
        "AAPL",
        period="1y",
        interval="1d",
        aggregate=False,
        auto_adjust=True,
    )


@pytest.mark.asyncio
async def test_latest_close_skips_invalid_latest_rows():
    client = MyClient()

    client.price_history = AsyncMock(
        return_value=[
            {
                "Close": 101.5,
            },
            {
                "Close": None,
            },
            {
                "Close": "garbage",
            },
            {
                "Close": float("nan"),
            },
        ]
    )

    result = await client.latest_close("AAPL")

    assert result == 101.5


@pytest.mark.asyncio
async def test_latest_close_skips_non_dict_rows():
    client = MyClient()

    client.price_history = AsyncMock(
        return_value=[
            {
                "Close": 99.0,
            },
            None,
            "bad row",
        ]
    )

    result = await client.latest_close("AAPL")

    assert result == 99.0


@pytest.mark.asyncio
async def test_latest_close_skips_rows_without_close():
    client = MyClient()

    client.price_history = AsyncMock(
        return_value=[
            {
                "Close": 123.45,
            },
            {
                "Open": 125.0,
            },
        ]
    )

    result = await client.latest_close("AAPL")

    assert result == 123.45


@pytest.mark.asyncio
async def test_latest_close_rejects_empty_history():
    client = MyClient()

    client.price_history = AsyncMock(
        return_value=[],
    )

    with pytest.raises(
        InvalidDownloaderResponseError,
        match="no price history",
    ):
        await client.latest_close("AAPL")


@pytest.mark.asyncio
async def test_latest_close_rejects_when_no_valid_close_exists():
    client = MyClient()

    client.price_history = AsyncMock(
        return_value=[
            {
                "Close": None,
            },
            {
                "Close": -1,
            },
            {
                "Close": 0,
            },
            {
                "Close": float("nan"),
            },
            {
                "Close": float("inf"),
            },
        ]
    )

    with pytest.raises(
        InvalidDownloaderResponseError,
        match="no valid closing price",
    ):
        await client.latest_close("AAPL")


# ---------------------------------------------------------------------------
# Dividends
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_dividends_returns_data():
    client = MyClient(
        downloader_url="http://downloader",
    )

    expected = [
        {
            "Date": "2025-01-01",
            "Dividend": 0.25,
        },
        {
            "Date": "2025-04-01",
            "Dividend": 0.30,
        },
    ]

    response = FakeResponse(
        json_data={
            "data": expected,
        },
    )

    fake_session = FakeSession(response)

    with patch(
        "src.client.aiohttp.ClientSession",
        return_value=fake_session,
    ):
        result = await client.get_dividends(
            " aapl ",
            period="5y",
        )

    assert result == expected

    assert fake_session.url == (
        "http://downloader/dividends/AAPL"
    )

    assert fake_session.params == {
        "period": "5y",
    }


@pytest.mark.asyncio
async def test_get_dividends_rejects_invalid_data():
    client = MyClient()

    response = FakeResponse(
        json_data={
            "data": {},
        },
    )

    fake_session = FakeSession(response)

    with patch(
        "src.client.aiohttp.ClientSession",
        return_value=fake_session,
    ):
        with pytest.raises(
            InvalidDownloaderResponseError,
            match="'data' must be a list",
        ):
            await client.get_dividends("AAPL")


@pytest.mark.asyncio
async def test_get_dividends_maps_connection_error():
    client = MyClient()

    fake_session = FakeSession(
        request_error=aiohttp.ClientConnectionError(),
    )

    with patch(
        "src.client.aiohttp.ClientSession",
        return_value=fake_session,
    ):
        with pytest.raises(
            DownloaderClientError,
            match="Unable to connect",
        ):
            await client.get_dividends("AAPL")


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_analysis_returns_payload():
    client = MyClient(
        analyzer_url="http://analyzer",
    )

    expected = {
        "ticker": "AAPL",
        "cagr": 0.15,
        "volatility": 0.20,
    }

    response = FakeResponse(
        json_data=expected,
    )

    fake_session = FakeSession(response)

    with patch(
        "src.client.aiohttp.ClientSession",
        return_value=fake_session,
    ):
        result = await client.get_analysis(
            " aapl ",
            period="5y",
            interval="1wk",
            aggregate=True,
            auto_adjust=False,
        )

    assert result == expected

    assert fake_session.url == (
        "http://analyzer/analysis/AAPL"
    )

    assert fake_session.params == {
        "period": "5y",
        "interval": "1wk",
        "aggregate": "true",
        "autoadjust": "false",
    }


@pytest.mark.asyncio
async def test_get_analysis_uses_defaults():
    client = MyClient(
        analyzer_url="http://analyzer",
    )

    response = FakeResponse(
        json_data={
            "ticker": "AAPL",
        },
    )

    fake_session = FakeSession(response)

    with patch(
        "src.client.aiohttp.ClientSession",
        return_value=fake_session,
    ):
        await client.get_analysis("AAPL")

    assert fake_session.params == {
        "period": "10y",
        "interval": "1d",
        "aggregate": "false",
        "autoadjust": "true",
    }


@pytest.mark.asyncio
async def test_get_analysis_maps_connection_error():
    client = MyClient()

    fake_session = FakeSession(
        request_error=aiohttp.ClientConnectionError(),
    )

    with patch(
        "src.client.aiohttp.ClientSession",
        return_value=fake_session,
    ):
        with pytest.raises(
            AnalyzerClientError,
            match="Unable to connect",
        ):
            await client.get_analysis("AAPL")


@pytest.mark.asyncio
async def test_get_analysis_maps_timeout_error():
    client = MyClient()

    fake_session = FakeSession(
        request_error=aiohttp.ServerTimeoutError(),
    )

    with patch(
        "src.client.aiohttp.ClientSession",
        return_value=fake_session,
    ):
        with pytest.raises(
            AnalyzerClientError,
            match="timed out",
        ):
            await client.get_analysis("AAPL")


@pytest.mark.asyncio
async def test_get_analysis_maps_generic_client_error():
    client = MyClient()

    fake_session = FakeSession(
        request_error=aiohttp.ClientError(),
    )

    with patch(
        "src.client.aiohttp.ClientSession",
        return_value=fake_session,
    ):
        with pytest.raises(
            AnalyzerClientError,
            match="request failed",
        ):
            await client.get_analysis("AAPL")