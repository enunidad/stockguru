from __future__ import annotations

from json import JSONDecodeError

import aiohttp
import pandas as pd
import pytest

import src.client as client_module
from src.client import (
    HttpDownloaderClient,
    LocalDownloaderClient,
    _parse_price_history,
)
from src.exceptions import (
    DownloaderClientError,
    DownloaderResponseError,
    InvalidDownloaderResponseError,
)


def make_payload(
    data=None,
):
    if data is None:
        data = [
            {
                "Date": "2024-01-01",
                "Close": 100.0,
            },
            {
                "Date": "2024-01-02",
                "Close": 110.0,
            },
        ]

    return {
        "ticker": "AAPL",
        "period": "10y",
        "interval": "1d",
        "rows": len(data),
        "data": data,
    }


class AsyncContextManager:
    def __init__(self, value):
        self.value = value

    async def __aenter__(self):
        return self.value

    async def __aexit__(
        self,
        exc_type,
        exc,
        traceback,
    ):
        return False


class FakeResponse:
    def __init__(
        self,
        *,
        status=200,
        payload=None,
        json_error=None,
        text="",
    ):
        self.status = status
        self.payload = payload
        self.json_error = json_error
        self.response_text = text

    async def json(self):
        if self.json_error is not None:
            raise self.json_error

        return self.payload

    async def text(self):
        return self.response_text


class FakeSession:
    def __init__(
        self,
        *,
        response=None,
        get_error=None,
    ):
        self.response = response
        self.get_error = get_error
        self.url = None
        self.params = None

    def get(
        self,
        url,
        *,
        params=None,
    ):
        self.url = url
        self.params = params

        if self.get_error is not None:
            raise self.get_error

        return AsyncContextManager(
            self.response
        )


# ============================================================
# Shared parser
# ============================================================


def test_parse_price_history_returns_history():
    history = _parse_price_history(
        make_payload()
    )

    assert history.ticker == "AAPL"
    assert history.period == "10y"
    assert history.interval == "1d"
    assert len(history.rows) == 2
    assert history.closing_prices == (
        100.0,
        110.0,
    )


def test_parse_price_history_filters_invalid_rows():
    payload = make_payload(
        [
            {
                "Date": "2024-01-01",
                "Close": 100.0,
            },
            {
                "Date": "2024-01-02",
                "Close": None,
            },
            {
                "Date": "2024-01-03",
                "Close": "bad",
            },
            {
                "Date": "2024-01-04",
                "Close": float("nan"),
            },
            {
                "Date": "2024-01-05",
                "Close": float("inf"),
            },
            "not-a-dict",
        ]
    )

    history = _parse_price_history(
        payload
    )

    assert len(history.rows) == 1
    assert history.closing_prices == (
        100.0,
    )


def test_parse_price_history_rejects_non_list_data():
    payload = make_payload()
    payload["data"] = {
        "Date": "2024-01-01",
        "Close": 100.0,
    }

    with pytest.raises(
        InvalidDownloaderResponseError,
        match="must be a list",
    ):
        _parse_price_history(payload)


def test_parse_price_history_rejects_no_valid_rows():
    payload = make_payload(
        [
            {
                "Date": "2024-01-01",
                "Close": None,
            },
            {
                "Date": "2024-01-02",
                "Close": float("nan"),
            },
        ]
    )

    with pytest.raises(
        InvalidDownloaderResponseError,
        match="no price-history rows",
    ):
        _parse_price_history(payload)


def test_parse_price_history_does_not_modify_original_payload():
    payload = make_payload(
        [
            {
                "Date": "2024-01-01",
                "Close": 100.0,
            },
            {
                "Date": "2024-01-02",
                "Close": None,
            },
        ]
    )

    original_rows = payload["rows"]

    _parse_price_history(payload)

    assert payload["rows"] == original_rows
    assert len(payload["data"]) == 2


# ============================================================
# LocalDownloaderClient
# ============================================================


@pytest.mark.asyncio
async def test_local_client_returns_parsed_history():
    service = type(
        "FakeDownloaderService",
        (),
        {},
    )()

    service.get_price_history = lambda **kwargs: pd.DataFrame(
        [
            {
                "Date": "2024-01-01",
                "Close": 100.0,
            },
            {
                "Date": "2024-01-02",
                "Close": 110.0,
            },
        ]
    )

    client = LocalDownloaderClient(
        service=service
    )

    history = await client.get_price_history(
        "aapl"
    )

    assert history.ticker == "AAPL"
    assert history.period == "10y"
    assert history.interval == "1d"
    assert len(history.rows) == 2
    assert history.closing_prices == (
        100.0,
        110.0,
    )


@pytest.mark.asyncio
async def test_local_client_forwards_request_parameters():
    calls = []

    class FakeDownloaderService:
        def get_price_history(
            self,
            **kwargs,
        ):
            calls.append(kwargs)

            return pd.DataFrame(
                [
                    {
                        "Date": "2024-01-01",
                        "Close": 100.0,
                    },
                ]
            )

    client = LocalDownloaderClient(
        service=FakeDownloaderService()
    )

    await client.get_price_history(
        "MSFT",
        period="5y",
        interval="1wk",
        aggregate=True,
        auto_adjust=False,
    )

    assert calls == [
        {
            "ticker": "MSFT",
            "period": "5y",
            "interval": "1wk",
            "aggregate": True,
            "auto_adjust": False,
        }
    ]


# ============================================================
# HttpDownloaderClient
# ============================================================


@pytest.mark.asyncio
async def test_http_client_returns_parsed_history(
    monkeypatch,
):
    response = FakeResponse(
        payload=make_payload()
    )

    session = FakeSession(
        response=response
    )

    monkeypatch.setattr(
        client_module.aiohttp,
        "ClientSession",
        lambda *args, **kwargs: (
            AsyncContextManager(session)
        ),
    )

    client = HttpDownloaderClient(
        "http://downloader:8080/"
    )

    history = await client.get_price_history(
        "aapl",
        period="5y",
        interval="1wk",
        aggregate=True,
        auto_adjust=False,
    )

    assert history.ticker == "AAPL"
    assert len(history.rows) == 2

    assert session.url == (
        "http://downloader:8080/history/aapl"
    )

    assert session.params == {
        "period": "5y",
        "interval": "1wk",
        "aggregate": "true",
        "autoadjust": "false",
    }


@pytest.mark.asyncio
async def test_http_client_maps_connection_error(
    monkeypatch,
):
    session = FakeSession(
        get_error=aiohttp.ClientConnectionError(
            "boom"
        )
    )

    monkeypatch.setattr(
        client_module.aiohttp,
        "ClientSession",
        lambda *args, **kwargs: (
            AsyncContextManager(session)
        ),
    )

    client = HttpDownloaderClient()

    with pytest.raises(
        DownloaderClientError,
        match="Unable to connect",
    ):
        await client.get_price_history(
            "AAPL"
        )


@pytest.mark.asyncio
async def test_http_client_maps_timeout_error(
    monkeypatch,
):
    session = FakeSession(
        get_error=aiohttp.ServerTimeoutError(
            "boom"
        )
    )

    monkeypatch.setattr(
        client_module.aiohttp,
        "ClientSession",
        lambda *args, **kwargs: (
            AsyncContextManager(session)
        ),
    )

    client = HttpDownloaderClient()

    with pytest.raises(
        DownloaderClientError,
        match="timed out",
    ):
        await client.get_price_history(
            "AAPL"
        )


@pytest.mark.asyncio
async def test_http_client_maps_generic_client_error(
    monkeypatch,
):
    session = FakeSession(
        get_error=aiohttp.ClientError(
            "boom"
        )
    )

    monkeypatch.setattr(
        client_module.aiohttp,
        "ClientSession",
        lambda *args, **kwargs: (
            AsyncContextManager(session)
        ),
    )

    client = HttpDownloaderClient()

    with pytest.raises(
        DownloaderClientError,
        match="request failed",
    ):
        await client.get_price_history(
            "AAPL"
        )


# ============================================================
# HTTP response parsing
# ============================================================


@pytest.mark.asyncio
async def test_read_response_returns_json_object():
    payload = make_payload()

    response = FakeResponse(
        status=200,
        payload=payload,
    )

    result = await (
        HttpDownloaderClient._read_response(
            response
        )
    )

    assert result == payload


@pytest.mark.asyncio
async def test_read_response_raises_for_http_error():
    response = FakeResponse(
        status=404,
        payload={
            "message": "Ticker not found."
        },
    )

    with pytest.raises(
        DownloaderResponseError
    ):
        await HttpDownloaderClient._read_response(
            response
        )


@pytest.mark.asyncio
async def test_read_response_rejects_invalid_json():
    response = FakeResponse(
        status=200,
        json_error=JSONDecodeError(
            "bad json",
            "",
            0,
        ),
    )

    with pytest.raises(
        InvalidDownloaderResponseError,
        match="invalid JSON",
    ):
        await HttpDownloaderClient._read_response(
            response
        )


@pytest.mark.asyncio
async def test_read_response_rejects_non_object_json():
    response = FakeResponse(
        status=200,
        payload=[
            {
                "Date": "2024-01-01",
                "Close": 100.0,
            }
        ],
    )

    with pytest.raises(
        InvalidDownloaderResponseError,
        match="JSON object",
    ):
        await HttpDownloaderClient._read_response(
            response
        )


# ============================================================
# HTTP error messages
# ============================================================


@pytest.mark.asyncio
async def test_read_error_message_uses_message_field():
    response = FakeResponse(
        payload={
            "message": "Ticker not found."
        }
    )

    result = await (
        HttpDownloaderClient._read_error_message(
            response
        )
    )

    assert result == "Ticker not found."


@pytest.mark.asyncio
async def test_read_error_message_uses_error_field():
    response = FakeResponse(
        payload={
            "error": "Something failed."
        }
    )

    result = await (
        HttpDownloaderClient._read_error_message(
            response
        )
    )

    assert result == "Something failed."


@pytest.mark.asyncio
async def test_read_error_message_falls_back_to_text():
    response = FakeResponse(
        json_error=JSONDecodeError(
            "bad json",
            "",
            0,
        ),
        text="Service exploded.",
    )

    result = await (
        HttpDownloaderClient._read_error_message(
            response
        )
    )

    assert result == "Service exploded."


@pytest.mark.asyncio
async def test_read_error_message_uses_default_when_empty():
    response = FakeResponse(
        payload={}
    )

    result = await (
        HttpDownloaderClient._read_error_message(
            response
        )
    )

    assert result == (
        "Downloader returned an error."
    )