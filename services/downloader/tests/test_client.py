import pandas as pd
import pytest

from src.client import (
    InvalidTickerError,
    YahooFinanceClient,
)


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