# services/downloader/tests/test_schemas.py

from __future__ import annotations

import pytest
import yfinance as yf

from src.schemas import PriceHistoryRequest, TickerMetadata
from src.exceptions import InvalidTickerError, InvalidParameterError


# ---------------------------------------------------------------------
# PriceHistoryRequest - ticker
# ---------------------------------------------------------------------

def test_ticker_string_is_converted_to_yfinance_ticker():
    request = PriceHistoryRequest(ticker="AAPL")

    assert isinstance(request.ticker, yf.Ticker)
    assert request.ticker.ticker == "AAPL"


def test_ticker_string_is_stripped_and_uppercased():
    request = PriceHistoryRequest(ticker="  aapl  ")

    assert isinstance(request.ticker, yf.Ticker)
    assert request.ticker.ticker == "AAPL"


@pytest.mark.parametrize(
    "ticker",
    [
        "",
        " ",
        "    ",
    ],
)
def test_empty_ticker_raises_invalid_ticker_error(ticker):
    with pytest.raises(
        InvalidTickerError,
        match="Ticker cannot be empty",
    ):
        PriceHistoryRequest(ticker=ticker)


@pytest.mark.parametrize(
    "ticker",
    [
        None,
        123,
        1.5,
        [],
        {},
    ],
)
def test_invalid_ticker_type_raises_invalid_ticker_error(ticker):
    with pytest.raises(InvalidTickerError):
        PriceHistoryRequest(ticker=ticker)


def test_existing_yfinance_ticker_is_preserved():
    ticker = yf.Ticker("AAPL")

    request = PriceHistoryRequest(ticker=ticker)

    assert request.ticker is ticker


# ---------------------------------------------------------------------
# PriceHistoryRequest - defaults
# ---------------------------------------------------------------------

def test_default_values():
    request = PriceHistoryRequest(ticker="AAPL")

    assert request.period == "10y"
    assert request.interval == "1d"
    assert request.auto_adjust is True
    assert request.aggregate is True


# ---------------------------------------------------------------------
# PriceHistoryRequest - time period validation
# ---------------------------------------------------------------------

@pytest.mark.parametrize(
    "period",
    [
        "1d",
        "5d",
        "29d",
        "1wk",
        "2wk",
        "29wk",
        "1mo",
        "3mo",
        "29mo",
        "1y",
        "2y",
        "10y",
        "29y",
    ],
)
def test_valid_periods_are_accepted(period):
    request = PriceHistoryRequest(
        ticker="AAPL",
        period=period,
    )

    assert request.period == period


@pytest.mark.parametrize(
    "interval",
    [
        "1d",
        "5d",
        "29d",
        "1wk",
        "2wk",
        "29wk",
        "1mo",
        "3mo",
        "29mo",
        "1y",
        "2y",
        "10y",
        "29y",
    ],
)
def test_valid_intervals_are_accepted(interval):
    request = PriceHistoryRequest(
        ticker="AAPL",
        interval=interval,
    )

    assert request.interval == interval


@pytest.mark.parametrize(
    "period",
    [
        "1h",
        "1m",
        "1hour",
        "week",
        "abc",
        "",
    ],
)
def test_unrecognized_period_suffix_raises(period):
    with pytest.raises(
        InvalidParameterError,
        match="period suffix unrecognized",
    ):
        PriceHistoryRequest(
            ticker="AAPL",
            period=period,
        )


@pytest.mark.parametrize(
    "interval",
    [
        "1h",
        "1m",
        "abc",
        "",
    ],
)
def test_unrecognized_interval_suffix_raises(interval):
    with pytest.raises(
        InvalidParameterError,
        match="interval suffix unrecognized",
    ):
        PriceHistoryRequest(
            ticker="AAPL",
            interval=interval,
        )


@pytest.mark.parametrize(
    "period",
    [
        "abcd",
        "abcwk",
        "abcmo",
        "abcy",
        "1.5y",
    ],
)
def test_non_integer_period_duration_raises(period):
    with pytest.raises(
        InvalidParameterError,
        match="period value must be castable as an integer",
    ):
        PriceHistoryRequest(
            ticker="AAPL",
            period=period,
        )


@pytest.mark.parametrize(
    "period",
    [
        "0d",
        "0wk",
        "0mo",
        "0y",
        "-1d",
        "-2wk",
        "-3mo",
        "-1y",
    ],
)
def test_non_positive_period_raises(period):
    with pytest.raises(
        InvalidParameterError,
        match="period value must be a positive integer",
    ):
        PriceHistoryRequest(
            ticker="AAPL",
            period=period,
        )


@pytest.mark.parametrize(
    "period",
    [
        "30d",
        "30wk",
        "30mo",
        "30y",
        "100d",
        "100y",
    ],
)
def test_period_30_or_greater_raises(period):
    with pytest.raises(
        InvalidParameterError,
        match="period value must be less than 30",
    ):
        PriceHistoryRequest(
            ticker="AAPL",
            period=period,
        )


@pytest.mark.parametrize(
    "period",
    [
        None,
        1,
        10,
        True,
        [],
    ],
)
def test_non_string_period_raises(period):
    with pytest.raises(
        InvalidParameterError,
        match="period parameter must be a string",
    ):
        PriceHistoryRequest(
            ticker="AAPL",
            period=period,
        )


def test_non_string_interval_raises():
    with pytest.raises(
        InvalidParameterError,
        match="interval parameter must be a string",
    ):
        PriceHistoryRequest(
            ticker="AAPL",
            interval=2,
        )


# ---------------------------------------------------------------------
# PriceHistoryRequest - boolean normalization
# ---------------------------------------------------------------------

@pytest.mark.parametrize(
    "value",
    [
        "true",
        "TRUE",
        "True",
        "yes",
        "YES",
        "1",
        "on",
        "ON",
    ],
)
def test_auto_adjust_true_strings_are_converted_to_true(value):
    request = PriceHistoryRequest(
        ticker="AAPL",
        auto_adjust=value,
    )

    assert request.auto_adjust is True


@pytest.mark.parametrize(
    "value",
    [
        "false",
        "FALSE",
        "False",
        "no",
        "NO",
        "0",
        "off",
        "OFF",
    ],
)
def test_auto_adjust_false_strings_are_converted_to_false(value):
    request = PriceHistoryRequest(
        ticker="AAPL",
        auto_adjust=value,
    )

    assert request.auto_adjust is False


@pytest.mark.parametrize(
    "value",
    [
        "true",
        "TRUE",
        "yes",
        "1",
        "on",
    ],
)
def test_aggregate_true_strings_are_converted_to_true(value):
    request = PriceHistoryRequest(
        ticker="AAPL",
        aggregate=value,
    )

    assert request.aggregate is True


@pytest.mark.parametrize(
    "value",
    [
        "false",
        "FALSE",
        "no",
        "0",
        "off",
    ],
)
def test_aggregate_false_strings_are_converted_to_false(value):
    request = PriceHistoryRequest(
        ticker="AAPL",
        aggregate=value,
    )

    assert request.aggregate is False


def test_boolean_values_are_preserved():
    request = PriceHistoryRequest(
        ticker="AAPL",
        auto_adjust=False,
        aggregate=True,
    )

    assert request.auto_adjust is False
    assert request.aggregate is True


@pytest.mark.parametrize(
    "value",
    [
        "maybe",
        "truthy",
        "falsey",
        "",
    ],
)
def test_invalid_auto_adjust_string_raises(value):
    with pytest.raises(
        InvalidParameterError,
        match="auto_adjust parameter must be one of",
    ):
        PriceHistoryRequest(
            ticker="AAPL",
            auto_adjust=value,
        )


@pytest.mark.parametrize(
    "value",
    [
        None,
        123,
        [],
        {},
    ],
)
def test_invalid_auto_adjust_type_raises(value):
    with pytest.raises(
        InvalidParameterError,
        match="auto_adjust parameter is invalid",
    ):
        PriceHistoryRequest(
            ticker="AAPL",
            auto_adjust=value,
        )


def test_invalid_aggregate_string_raises():
    with pytest.raises(
        InvalidParameterError,
        match="aggregate parameter must be one of",
    ):
        PriceHistoryRequest(
            ticker="AAPL",
            aggregate="maybe",
        )


def test_invalid_aggregate_type_raises():
    with pytest.raises(
        InvalidParameterError,
        match="aggregate parameter is invalid",
    ):
        PriceHistoryRequest(
            ticker="AAPL",
            aggregate=123,
        )


# ---------------------------------------------------------------------
# TickerMetadata
# ---------------------------------------------------------------------

def test_ticker_metadata_minimum_construction():
    metadata = TickerMetadata(ticker="AAPL")

    assert metadata.ticker == "AAPL"
    assert metadata.currency is None
    assert metadata.exchange is None
    assert metadata.timezone is None
    assert metadata.quote_type is None
    assert metadata.name is None
    assert metadata.sector is None
    assert metadata.industry is None
    assert metadata.country is None
    assert metadata.raw == {}


def test_ticker_metadata_full_construction():
    raw = {
        "fast_info": {"currency": "USD"},
        "info": {"longName": "Apple Inc."},
    }

    metadata = TickerMetadata(
        ticker="AAPL",
        currency="USD",
        exchange="NMS",
        timezone="America/New_York",
        quote_type="EQUITY",
        name="Apple Inc.",
        sector="Technology",
        industry="Consumer Electronics",
        country="United States",
        raw=raw,
    )

    assert metadata.ticker == "AAPL"
    assert metadata.currency == "USD"
    assert metadata.exchange == "NMS"
    assert metadata.timezone == "America/New_York"
    assert metadata.quote_type == "EQUITY"
    assert metadata.name == "Apple Inc."
    assert metadata.sector == "Technology"
    assert metadata.industry == "Consumer Electronics"
    assert metadata.country == "United States"
    assert metadata.raw == raw


def test_ticker_metadata_raw_default_is_not_shared():
    first = TickerMetadata(ticker="AAPL")
    second = TickerMetadata(ticker="MSFT")

    first.raw["test"] = "value"

    assert second.raw == {}