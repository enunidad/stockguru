from dataclasses import FrozenInstanceError

import pytest

from src.schemas import PriceHistoryRequest, TickerMetadata


def test_price_history_request_uses_default_values():
    request = PriceHistoryRequest(ticker="AAPL")

    assert request.period == "10y"
    assert request.interval == "1mo"
    assert request.auto_adjust == True


def test_price_history_request_accepts_custom_values():
    request = PriceHistoryRequest(
        ticker="MSFT",
        period="5y",
        interval="1wk",
        auto_adjust=False,
    )

    assert request.ticker == "MSFT"
    assert request.period == "5y"
    assert request.interval == "1wk"
    assert request.auto_adjust == False


def test_price_history_request_is_frozen():
    request = PriceHistoryRequest(ticker="AAPL")

    with pytest.raises(FrozenInstanceError):
        request.ticker = "MSFT"

def test_ticker_metadata_uses_default_values():
    request = TickerMetadata(ticker="AAPL")

    assert request.currency is None
    assert request.exchange is None
    assert request.timezone is None
    assert request.quote_type is None
    assert isinstance(request.raw, dict)

def test_ticker_metadata_accepts_custom_values():
    request = TickerMetadata(
                ticker='MSFT',
                currency='USD',
                exchange='EMX',
                quote_type='test_quote',
                raw={'foo': 1, 'bar':2}
    )

    assert request.ticker == 'MSFT'
    assert request.currency == 'USD'
    assert request.exchange == 'EMX'
    assert request.quote_type == 'test_quote'
    assert isinstance(request.raw, dict)

def test_ticker_metadata_is_frozen():
    request = TickerMetadata(ticker="AAPL")

    with pytest.raises(FrozenInstanceError):
        request.ticker = "MSFT"