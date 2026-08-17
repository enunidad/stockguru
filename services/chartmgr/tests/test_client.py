from __future__ import annotations

from json import JSONDecodeError
from unittest.mock import AsyncMock

import aiohttp
import pytest

from src.client import DownloaderApiClient, AnalyzerApiClient
from src.exceptions import (
    DownloaderClientError,
    DownloaderResponseError,
    InvalidDownloaderResponseError,
)
from src.schemas import ChartRequest


# =========================================================
# Helpers
# =========================================================

class FakeResponse:
    def __init__(
        self,
        *,
        status: int = 200,
        json_data=None,
        json_error: Exception | None = None,
        text: str = "",
    ) -> None:
        self.status = status
        self._json_data = json_data
        self._json_error = json_error
        self._text = text

    async def json(self):
        if self._json_error:
            raise self._json_error

        return self._json_data

    async def text(self):
        return self._text


class FakeResponseContext:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response

    async def __aenter__(self):
        return self.response

    async def __aexit__(self, exc_type, exc, tb):
        return False


class FakeSession:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.requested_url = None
        self.requested_params = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def get(self, url, *, params):
        self.requested_url = url
        self.requested_params = params

        return FakeResponseContext(self.response)


# =========================================================
# DownloaderApiClient initialization
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
# _normalize_ticker
# =========================================================

def test_normalize_ticker() -> None:
    result = DownloaderApiClient._normalize_ticker("  aapl  ")

    assert result == "AAPL"


def test_normalize_ticker_rejects_empty_string() -> None:
    with pytest.raises(
        InvalidDownloaderResponseError,
        match="Ticker cannot be empty.",
    ):
        DownloaderApiClient._normalize_ticker("   ")


def test_normalize_ticker_rejects_non_string() -> None:
    with pytest.raises(
        InvalidDownloaderResponseError,
        match="Ticker must be a string.",
    ):
        DownloaderApiClient._normalize_ticker(123)


# =========================================================
# _read_response
# =========================================================

@pytest.mark.asyncio
async def test_read_response_returns_json_object() -> None:
    response = FakeResponse(
        status=200,
        json_data={
            "ticker": "AAPL",
            "data": [],
        },
    )

    result = await DownloaderApiClient._read_response(response)

    assert result == {
        "ticker": "AAPL",
        "data": [],
    }


@pytest.mark.asyncio
async def test_read_response_rejects_non_dict_payload() -> None:
    response = FakeResponse(
        status=200,
        json_data=[1, 2, 3],
    )

    with pytest.raises(
        InvalidDownloaderResponseError,
        match="Downloader response must be a JSON object.",
    ):
        await DownloaderApiClient._read_response(response)


@pytest.mark.asyncio
async def test_read_response_rejects_invalid_json() -> None:
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
        match="Downloader returned invalid JSON.",
    ):
        await DownloaderApiClient._read_response(response)


@pytest.mark.asyncio
async def test_read_response_raises_for_http_error() -> None:
    response = FakeResponse(
        status=404,
        json_data={
            "message": "Ticker not found.",
        },
    )

    with pytest.raises(DownloaderResponseError):
        await DownloaderApiClient._read_response(response)


# =========================================================
# _read_error_message
# =========================================================

@pytest.mark.asyncio
async def test_read_error_message_uses_message_field() -> None:
    response = FakeResponse(
        status=400,
        json_data={
            "message": "Invalid ticker.",
        },
    )

    result = await DownloaderApiClient._read_error_message(response)

    assert result == "Invalid ticker."


@pytest.mark.asyncio
async def test_read_error_message_uses_error_field() -> None:
    response = FakeResponse(
        status=400,
        json_data={
            "error": "Something failed.",
        },
    )

    result = await DownloaderApiClient._read_error_message(response)

    assert result == "Something failed."


@pytest.mark.asyncio
async def test_read_error_message_uses_default_for_empty_object() -> None:
    response = FakeResponse(
        status=500,
        json_data={},
    )

    result = await DownloaderApiClient._read_error_message(response)

    assert result == "Downloader returned an error."


@pytest.mark.asyncio
async def test_read_error_message_falls_back_to_response_text() -> None:
    response = FakeResponse(
        status=500,
        json_error=JSONDecodeError(
            "Invalid JSON",
            "",
            0,
        ),
        text="Internal server error",
    )

    result = await DownloaderApiClient._read_error_message(response)

    assert result == "Internal server error"


@pytest.mark.asyncio
async def test_read_error_message_uses_default_when_text_empty() -> None:
    response = FakeResponse(
        status=500,
        json_error=JSONDecodeError(
            "Invalid JSON",
            "",
            0,
        ),
        text="",
    )

    result = await DownloaderApiClient._read_error_message(response)

    assert result == "Downloader returned an error."


# =========================================================
# price_history
# =========================================================

@pytest.mark.asyncio
async def test_price_history_returns_data(monkeypatch) -> None:
    response = FakeResponse(
        status=200,
        json_data={
            "ticker": "AAPL",
            "data": [
                {
                    "Date": "2026-01",
                    "Open": 100.0,
                    "High": 110.0,
                    "Low": 95.0,
                    "Close": 108.0,
                },
            ],
        },
    )

    fake_session = FakeSession(response)

    monkeypatch.setattr(
        aiohttp,
        "ClientSession",
        lambda **kwargs: fake_session,
    )

    client = DownloaderApiClient()

    request = ChartRequest(
        ticker="aapl",
        period="5y",
        interval="1mo",
        auto_adjust=True,
        aggregate=True,
    )

    result = await client.price_history(request)

    assert result == [
        {
            "Date": "2026-01",
            "Open": 100.0,
            "High": 110.0,
            "Low": 95.0,
            "Close": 108.0,
        },
    ]


@pytest.mark.asyncio
async def test_price_history_builds_correct_url(monkeypatch) -> None:
    response = FakeResponse(
        status=200,
        json_data={
            "data": [],
        },
    )

    fake_session = FakeSession(response)

    monkeypatch.setattr(
        aiohttp,
        "ClientSession",
        lambda **kwargs: fake_session,
    )

    client = DownloaderApiClient(
        base_url="http://downloader:8080/",
    )

    request = ChartRequest(
        ticker=" aapl ",
    )

    await client.price_history(request)

    assert fake_session.requested_url == (
        "http://downloader:8080/history/AAPL"
    )


@pytest.mark.asyncio
async def test_price_history_passes_request_parameters(monkeypatch) -> None:
    response = FakeResponse(
        status=200,
        json_data={
            "data": [],
        },
    )

    fake_session = FakeSession(response)

    monkeypatch.setattr(
        aiohttp,
        "ClientSession",
        lambda **kwargs: fake_session,
    )

    client = DownloaderApiClient()

    request = ChartRequest(
        ticker="AAPL",
        period="5y",
        interval="1wk",
        auto_adjust=False,
        aggregate=True,
    )

    await client.price_history(request)

    assert fake_session.requested_params == {
        "period": "5y",
        "interval": "1wk",
        "aggregate": "true",
        "autoadjust": "false",
    }


@pytest.mark.asyncio
async def test_price_history_rejects_missing_data(monkeypatch) -> None:
    response = FakeResponse(
        status=200,
        json_data={
            "ticker": "AAPL",
        },
    )

    fake_session = FakeSession(response)

    monkeypatch.setattr(
        aiohttp,
        "ClientSession",
        lambda **kwargs: fake_session,
    )

    client = DownloaderApiClient()

    request = ChartRequest(
        ticker="AAPL",
    )

    with pytest.raises(
        InvalidDownloaderResponseError,
        match="Downloader response 'data' must be a list.",
    ):
        await client.price_history(request)


@pytest.mark.asyncio
async def test_price_history_rejects_non_list_data(monkeypatch) -> None:
    response = FakeResponse(
        status=200,
        json_data={
            "data": {
                "Date": "2026-01",
            },
        },
    )

    fake_session = FakeSession(response)

    monkeypatch.setattr(
        aiohttp,
        "ClientSession",
        lambda **kwargs: fake_session,
    )

    client = DownloaderApiClient()

    request = ChartRequest(
        ticker="AAPL",
    )

    with pytest.raises(
        InvalidDownloaderResponseError,
        match="Downloader response 'data' must be a list.",
    ):
        await client.price_history(request)


# =========================================================
# AnalyzerApiClient
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