# services/downloader/tests/test_client.py

from __future__ import annotations

from unittest.mock import patch

import pandas as pd
import pytest
import yfinance as yf

from src.client import YahooFinanceClient
from src.schemas import PriceHistoryRequest, TickerMetadata
from src.exceptions import (
    DownloaderClientError,
    EmptyDownloadError,
    InvalidTickerError,
)


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------


@pytest.fixture
def client():
    return YahooFinanceClient()


@pytest.fixture
def ticker():
    return yf.Ticker("AAPL")


@pytest.fixture
def price_request(ticker):
    return PriceHistoryRequest(
        ticker=ticker,
        period="10y",
        interval="1d",
        auto_adjust=True,
        aggregate=True,
    )


@pytest.fixture
def history():
    return pd.DataFrame(
        {
            "Open": [100.0, 105.0],
            "High": [110.0, 115.0],
            "Low": [95.0, 100.0],
            "Close": [108.0, 112.0],
            "Volume": [1000, 1200],
        },
        index=["2026-01-01", "2026-01-02"],
    )


# ---------------------------------------------------------------------
# download
# ---------------------------------------------------------------------


def test_download_returns_all_three_objects(
    client,
    price_request,
    history,
):
    metadata = TickerMetadata(
        ticker="AAPL",
        currency="USD",
    )

    dividends = pd.Series(
        [0.25],
        index=pd.to_datetime(["2026-01-01"]),
        name="Dividends",
    )

    with (
        patch.object(
            client,
            "download_metadata",
            return_value=metadata,
        ) as metadata_mock,
        patch.object(
            client,
            "download_price_history",
            return_value=history,
        ) as history_mock,
        patch.object(
            client,
            "download_dividends",
            return_value=dividends,
        ) as dividends_mock,
    ):
        result = client.download(price_request)

    assert result["metadata"] is metadata
    assert result["price_history"] is history
    assert result["dividends"] is dividends

    metadata_mock.assert_called_once_with(price_request)
    history_mock.assert_called_once_with(price_request)
    dividends_mock.assert_called_once_with(price_request)


def test_download_returns_expected_keys(
    client,
    price_request,
    history,
):
    metadata = TickerMetadata(ticker="AAPL")
    dividends = pd.Series(dtype=float)

    with (
        patch.object(
            client,
            "download_metadata",
            return_value=metadata,
        ),
        patch.object(
            client,
            "download_price_history",
            return_value=history,
        ),
        patch.object(
            client,
            "download_dividends",
            return_value=dividends,
        ),
    ):
        result = client.download(price_request)

    assert set(result) == {
        "metadata",
        "price_history",
        "dividends",
    }


# ---------------------------------------------------------------------
# Metadata
# ---------------------------------------------------------------------


def test_download_metadata_returns_ticker_metadata(
    client,
    price_request,
    ticker,
):
    fast_info = {
        "currency": "USD",
        "exchange": "NMS",
        "timezone": "America/New_York",
        "quoteType": "EQUITY",
    }

    info = {
        "longName": "Apple Inc.",
        "sector": "Technology",
        "industry": "Consumer Electronics",
        "country": "United States",
    }

    with (
        patch.object(
            type(ticker),
            "fast_info",
            new_callable=lambda: property(lambda self: fast_info),
        ),
        patch.object(
            type(ticker),
            "info",
            new_callable=lambda: property(lambda self: info),
        ),
    ):
        result = client.download_metadata(price_request)

    assert isinstance(result, TickerMetadata)

    assert result.ticker == "AAPL"
    assert result.currency == "USD"
    assert result.exchange == "NMS"
    assert result.timezone == "America/New_York"
    assert result.quote_type == "EQUITY"

    assert result.name == "Apple Inc."
    assert result.sector == "Technology"
    assert result.industry == "Consumer Electronics"
    assert result.country == "United States"


def test_download_metadata_uses_info_fallbacks(
    client,
    price_request,
    ticker,
):
    fast_info = {}

    info = {
        "currency": "CAD",
        "exchange": "TOR",
        "exchangeTimezoneName": "America/Toronto",
        "quoteType": "EQUITY",
        "shortName": "Test Company",
    }

    with (
        patch.object(
            type(ticker),
            "fast_info",
            new_callable=lambda: property(lambda self: fast_info),
        ),
        patch.object(
            type(ticker),
            "info",
            new_callable=lambda: property(lambda self: info),
        ),
    ):
        result = client.download_metadata(price_request)

    assert result.currency == "CAD"
    assert result.exchange == "TOR"
    assert result.timezone == "America/Toronto"
    assert result.quote_type == "EQUITY"
    assert result.name == "Test Company"


def test_download_metadata_converts_values_to_strings(
    client,
    price_request,
    ticker,
):
    fast_info = {
        "currency": 123,
    }

    info = {}

    with (
        patch.object(
            type(ticker),
            "fast_info",
            new_callable=lambda: property(lambda self: fast_info),
        ),
        patch.object(
            type(ticker),
            "info",
            new_callable=lambda: property(lambda self: info),
        ),
    ):
        result = client.download_metadata(price_request)

    assert result.currency == "123"


def test_download_metadata_wraps_yfinance_exception(
    client,
    price_request,
    ticker,
):
    def raise_error(self):
        raise RuntimeError("Yahoo exploded")

    with patch.object(
        type(ticker),
        "fast_info",
        new_callable=lambda: property(raise_error),
    ):
        with pytest.raises(
            DownloaderClientError,
            match="Failed to download metadata for ticker 'AAPL'",
        ):
            client.download_metadata(price_request)


# ---------------------------------------------------------------------
# Price history
# ---------------------------------------------------------------------


def test_download_price_history_calls_yfinance_with_request_parameters(
    client,
    price_request,
    ticker,
    history,
):
    with patch.object(
        ticker,
        "history",
        return_value=history,
    ) as history_mock:
        client.download_price_history(price_request)

    history_mock.assert_called_once_with(
        period="10y",
        interval="1d",
        auto_adjust=True,
    )


def test_download_price_history_returns_dataframe(
    client,
    price_request,
    ticker,
    history,
):
    with patch.object(
        ticker,
        "history",
        return_value=history,
    ):
        result = client.download_price_history(price_request)

    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2
    assert list(result.columns) == [
        "Open",
        "High",
        "Low",
        "Close",
        "Volume",
    ]


def test_download_price_history_standardizes_index(
    client,
    price_request,
    ticker,
    history,
):
    with patch.object(
        ticker,
        "history",
        return_value=history,
    ):
        result = client.download_price_history(price_request)

    assert isinstance(result.index, pd.DatetimeIndex)
    assert result.index.name == "Date"


def test_download_price_history_does_not_mutate_original(
    client,
    price_request,
    ticker,
    history,
):
    original = history.copy()

    with patch.object(
        ticker,
        "history",
        return_value=history,
    ):
        client.download_price_history(price_request)

    pd.testing.assert_frame_equal(history, original)


def test_download_price_history_flattens_multiindex_columns(
    client,
    price_request,
    ticker,
):
    columns = pd.MultiIndex.from_tuples(
        [
            ("Open", "AAPL"),
            ("High", "AAPL"),
            ("Low", "AAPL"),
            ("Close", "AAPL"),
        ]
    )

    history = pd.DataFrame(
        [[100.0, 110.0, 95.0, 108.0]],
        columns=columns,
        index=["2026-01-01"],
    )

    with patch.object(
        ticker,
        "history",
        return_value=history,
    ):
        result = client.download_price_history(price_request)

    assert list(result.columns) == [
        "Open",
        "High",
        "Low",
        "Close",
    ]


def test_download_price_history_raises_when_none_returned(
    client,
    price_request,
    ticker,
):
    with patch.object(
        ticker,
        "history",
        return_value=None,
    ):
        with pytest.raises(
            EmptyDownloadError,
            match="No price history returned for ticker 'AAPL'",
        ):
            client.download_price_history(price_request)


def test_download_price_history_raises_when_empty(
    client,
    price_request,
    ticker,
):
    with patch.object(
        ticker,
        "history",
        return_value=pd.DataFrame(),
    ):
        with pytest.raises(
            EmptyDownloadError,
            match="No price history returned for ticker 'AAPL'",
        ):
            client.download_price_history(price_request)


def test_download_price_history_raises_when_close_missing(
    client,
    price_request,
    ticker,
):
    history = pd.DataFrame(
        {
            "Open": [100.0],
            "High": [110.0],
            "Low": [95.0],
        },
        index=["2026-01-01"],
    )

    with patch.object(
        ticker,
        "history",
        return_value=history,
    ):
        with pytest.raises(
            InvalidTickerError,
            match="missing Close price",
        ):
            client.download_price_history(price_request)


def test_download_price_history_wraps_yfinance_exception(
    client,
    price_request,
    ticker,
):
    with patch.object(
        ticker,
        "history",
        side_effect=RuntimeError("Yahoo exploded"),
    ):
        with pytest.raises(
            DownloaderClientError,
            match="Failed to download price history for ticker 'AAPL'",
        ):
            client.download_price_history(price_request)


# ---------------------------------------------------------------------
# Dividends
# ---------------------------------------------------------------------


def test_download_dividends_returns_series(
    client,
    price_request,
    ticker,
):
    expected = pd.Series(
        [0.25, 0.25],
        index=pd.to_datetime(
            ["2026-01-01", "2026-04-01"]
        ),
        name="Dividends",
    )

    with patch.object(
        ticker,
        "get_dividends",
        return_value=expected,
    ) as dividends_mock:
        result = client.download_dividends(price_request)

    pd.testing.assert_series_equal(result, expected)
    dividends_mock.assert_called_once_with()


def test_download_dividends_allows_empty_series(
    client,
    price_request,
    ticker,
):
    expected = pd.Series(
        dtype=float,
        name="Dividends",
    )

    with patch.object(
        ticker,
        "get_dividends",
        return_value=expected,
    ):
        result = client.download_dividends(price_request)

    pd.testing.assert_series_equal(result, expected)


def test_download_dividends_wraps_yfinance_exception(
    client,
    price_request,
    ticker,
):
    with patch.object(
        ticker,
        "get_dividends",
        side_effect=RuntimeError("Yahoo exploded"),
    ):
        with pytest.raises(
            DownloaderClientError,
            match="Failed to download dividends for ticker 'AAPL'",
        ):
            client.download_dividends(price_request)


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("USD", "USD"),
        (123, "123"),
        (1.5, "1.5"),
        (True, "True"),
    ],
)
def test_as_optional_string(client, value, expected):
    assert client._as_optional_string(value) == expected


def test_make_json_safe_preserves_basic_types(client):
    payload = {
        "none": None,
        "string": "hello",
        "integer": 123,
        "float": 1.5,
        "boolean": True,
    }

    result = client._make_json_safe(payload)

    assert result == payload


def test_make_json_safe_recursively_handles_nested_values(client):
    class CustomObject:
        def __str__(self):
            return "custom"

    payload = {
        "object": CustomObject(),
        "nested": {
            "object": CustomObject(),
        },
        "list": [CustomObject()],
        "tuple": (CustomObject(),),
    }

    result = client._make_json_safe(payload)

    assert result == {
        "object": "custom",
        "nested": {
            "object": "custom",
        },
        "list": ["custom"],
        "tuple": ["custom"],
    }


def test_flatten_columns_returns_normal_dataframe_unchanged(
    client,
    history,
):
    result = client._flatten_columns(history)

    pd.testing.assert_frame_equal(result, history)


def test_standardize_index_returns_copy(client, history):
    result = client._standardize_index(history)

    assert result is not history


def test_standardize_index_sets_date_index(client, history):
    result = client._standardize_index(history)

    assert isinstance(result.index, pd.DatetimeIndex)
    assert result.index.name == "Date"