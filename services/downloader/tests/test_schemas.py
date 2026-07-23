from dataclasses import FrozenInstanceError

import pytest

from src.schemas import PriceHistoryRequest


def test_price_history_request_uses_default_values():
    request = PriceHistoryRequest(ticker="AAPL")

    assert request.period == "10y"
    assert request.interval == "1mo"
    assert request.auto_adjust is False


def test_price_history_request_accepts_custom_values():
    request = PriceHistoryRequest(
        ticker="MSFT",
        period="5y",
        interval="1wk",
        auto_adjust=True,
    )

    assert request.ticker == "MSFT"
    assert request.period == "5y"
    assert request.interval == "1wk"
    assert request.auto_adjust is True


def test_price_history_request_is_frozen():
    request = PriceHistoryRequest(ticker="AAPL")

    with pytest.raises(FrozenInstanceError):
        request.ticker = "MSFT"