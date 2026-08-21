import pandas as pd
import pytest
import yfinance as yf

from src.client import (
    DownloaderClientError,
    InvalidTickerError,
    YahooFinanceClient,
)

from src.schemas import TickerMetadata, PriceHistoryRequest


def test_normalize_ticker_strips_whitespace_and_uppercases():
    base_case = 'AAPL'
    base = YahooFinanceClient._normalize_ticker(base_case)

    incorrect_tickers = [' aapl', ' aapl ', ' AAPL', ' AAPL ', 'AaPL']
    for ticker in incorrect_tickers:
        result = YahooFinanceClient._normalize_ticker(ticker)
        assert result == base_case


def test_normalize_ticker_rejects_empty_string():
    with pytest.raises(InvalidTickerError):
        YahooFinanceClient._normalize_ticker("   ")


def test_flatten_columns_converts_multiindex_to_simple_columns():
    data = pd.DataFrame(
        [[100, 110]],
        columns=pd.MultiIndex.from_tuples(
            [
                ("Open", "AAPL"),
                ("Close", "AAPL"),
            ]
        ),
    )

    result = YahooFinanceClient._flatten_columns(data)

    assert list(result.columns) == ["Open", "Close"]


def test_flatten_columns_leaves_normal_columns_unchanged():
    data = pd.DataFrame(
        {
            "Open": [100],
            "Close": [110],
        }
    )

    result = YahooFinanceClient._flatten_columns(data)

    assert list(result.columns) == ["Open", "Close"]


def test_standardize_index_sets_index_name_to_date():
    data = pd.DataFrame(
        {
            "Open": [100],
            "Close": [110],
        },
        index=pd.to_datetime(["2024-01-01"]),
    )

    result = YahooFinanceClient._standardize_index(data)

    assert result.index.name == "Date"

def test_as_optional_string():
    test_values = ['test', 1, 1.3, True, [1, 2, 3], {'foo': 'words', 'bar': 4.6}, None]
    for value in test_values:
        result = YahooFinanceClient._as_optional_string(value)
        assert isinstance(result, str) or result is None

def test_make_json_safe():
    objects = [{'foo': 1},
                {'foo': None},
                {'foo': 'bar'},
                {'foo': True},
                {'foo': 1.6},
                {'foo': [1, 2, 3]},
                {'foo': (1, 2, 3)},
                {'foo': {'bar': 1}}]
    for obj in objects:
        result = YahooFinanceClient()._make_json_safe(obj)
        assert isinstance(result, dict)
        for k, v in result.items():
            assert isinstance(k, str)
            assert isinstance(v, (str, int, float, bool, tuple, list, dict)) or v is None

def test_ticker_metadata_helper():
    symbol = 'AAPL'
    ticker = yf.Ticker(symbol)
    result = YahooFinanceClient()._ticker_metadata_helper(ticker)
    print('>'*10, result)
    assert isinstance(result, TickerMetadata)

def test_ticker_history_helper():
    symbol = 'AAPL'
    ticker = yf.Ticker(symbol)
    result = YahooFinanceClient()._ticker_history_helper(ticker=ticker,
                                                            period='10y',
                                                            auto_adjust=True)
    assert isinstance(result, pd.DataFrame)

def test_download_metadata():
    request = PriceHistoryRequest(
            ticker='AAPL',
            period='10y',
            interval='1mo',
            auto_adjust=True,)
    result = YahooFinanceClient().download_metadata(request)
    assert isinstance(result, TickerMetadata)

def test_download_price_history():
    request = PriceHistoryRequest(
            ticker='AAPL',
            period='10y',
            interval='1mo',
            auto_adjust=True,)
    result = YahooFinanceClient().download_price_history(request)
    assert isinstance(result, pd.DataFrame)

# =========================================================
# Dividend Downloads
# =========================================================


def test_download_dividends_returns_series(
    monkeypatch,
) -> None:
    expected = pd.Series(
        [
            0.24,
            0.25,
            0.25,
        ],
        index=pd.to_datetime(
            [
                "2026-02-01",
                "2026-05-01",
                "2026-08-01",
            ],
            utc=True,
        ),
        name="Dividends",
    )

    class FakeTicker:
        def __init__(
            self,
            ticker,
        ):
            self.ticker = ticker

        def get_dividends(
            self,
        ):
            return expected

    monkeypatch.setattr(
        yf,
        "Ticker",
        FakeTicker,
    )

    client = YahooFinanceClient()

    result = client.download_dividends(
        "AAPL"
    )

    pd.testing.assert_series_equal(
        result,
        expected,
    )


def test_download_dividends_normalizes_ticker(
    monkeypatch,
) -> None:
    received = {}

    class FakeTicker:
        def __init__(
            self,
            ticker,
        ):
            received["ticker"] = ticker
            self.ticker = ticker

        def get_dividends(
            self,
        ):
            return pd.Series(
                dtype=float,
                name="Dividends",
            )

    monkeypatch.setattr(
        yf,
        "Ticker",
        FakeTicker,
    )

    client = YahooFinanceClient()

    client.download_dividends(
        "  aapl  "
    )

    assert received["ticker"] == "AAPL"


def test_download_dividends_calls_yfinance_get_dividends(
    monkeypatch,
) -> None:
    calls = {
        "count": 0,
    }

    class FakeTicker:
        def __init__(
            self,
            ticker,
        ):
            self.ticker = ticker

        def get_dividends(
            self,
        ):
            calls["count"] += 1

            return pd.Series(
                dtype=float,
                name="Dividends",
            )

    monkeypatch.setattr(
        yf,
        "Ticker",
        FakeTicker,
    )

    client = YahooFinanceClient()

    client.download_dividends(
        "AAPL"
    )

    assert calls["count"] == 1


def test_download_dividends_returns_empty_series(
    monkeypatch,
) -> None:
    expected = pd.Series(
        dtype=float,
        name="Dividends",
    )

    class FakeTicker:
        def __init__(
            self,
            ticker,
        ):
            self.ticker = ticker

        def get_dividends(
            self,
        ):
            return expected

    monkeypatch.setattr(
        yf,
        "Ticker",
        FakeTicker,
    )

    client = YahooFinanceClient()

    result = client.download_dividends(
        "AAPL"
    )

    pd.testing.assert_series_equal(
        result,
        expected,
    )

    assert result.empty


def test_download_dividends_wraps_yfinance_error(
    monkeypatch,
) -> None:
    class FakeTicker:
        def __init__(
            self,
            ticker,
        ):
            self.ticker = ticker

        def get_dividends(
            self,
        ):
            raise RuntimeError(
                "Yahoo failed"
            )

    monkeypatch.setattr(
        yf,
        "Ticker",
        FakeTicker,
    )

    client = YahooFinanceClient()

    with pytest.raises(
        DownloaderClientError,
        match=(
            "Failed to download dividends "
            "for ticker 'AAPL'."
        ),
    ):
        client.download_dividends(
            "AAPL"
        )


def test_download_dividends_rejects_empty_ticker(
    monkeypatch,
) -> None:
    ticker_called = False

    class FakeTicker:
        def __init__(
            self,
            ticker,
        ):
            nonlocal ticker_called

            ticker_called = True

    monkeypatch.setattr(
        yf,
        "Ticker",
        FakeTicker,
    )

    client = YahooFinanceClient()

    with pytest.raises(
        InvalidTickerError,
        match="Ticker cannot be empty.",
    ):
        client.download_dividends(
            "   "
        )

    assert ticker_called is False