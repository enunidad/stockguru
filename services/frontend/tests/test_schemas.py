from dataclasses import FrozenInstanceError

import pytest

from src.schemas import PriceHistoryRequest


def test_price_history_request_defaults() -> None:
    request = PriceHistoryRequest(ticker="AAPL")

    assert request.ticker == "AAPL"
    assert request.period == "10y"
    assert request.interval == "1d"


def test_price_history_request_accepts_custom_values() -> None:
    request = PriceHistoryRequest(
        ticker="MSFT",
        period="5y",
        interval="1wk",
    )

    assert request.ticker == "MSFT"
    assert request.period == "5y"
    assert request.interval == "1wk"


def test_price_history_request_is_immutable() -> None:
    request = PriceHistoryRequest(ticker="AAPL")

    with pytest.raises(FrozenInstanceError):
        request.ticker = "MSFT"