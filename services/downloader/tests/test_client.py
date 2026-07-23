import pandas as pd
import pytest
import yfinance as yf

from src.client import (
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
        result = YahooFinanceClient._make_json_safe(obj)
        assert isinstance(result, dict)
        for k, v in result.items():
            print(k, v)
            assert isinstance(k, str)
            assert isinstance(v, (str, int, float, bool)) or v is None

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
                                                            interval='1mo',
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