import math

import numpy as np
import pytest

from src.calculations import (
    calculate_annualized_volatility,
    calculate_cagr,
    calculate_max_drawdown,
    calculate_simple_moving_average,
    calculate_total_return,
)
from src.exceptions import (
    InvalidCalculationParameterError,
    InvalidPriceHistoryError,
)


def test_calculate_total_return():
    assert calculate_total_return([100.0, 120.0]) == pytest.approx(0.20)


def test_calculate_cagr():
    assert calculate_cagr([100.0, 121.0], years=2) == pytest.approx(0.10)


def test_calculate_annualized_volatility():
    prices = [100.0, 110.0, 99.0]
    returns = np.array([0.10, -0.10])
    expected = np.std(returns, ddof=1) * math.sqrt(12)

    assert calculate_annualized_volatility(
        prices,
        trading_periods=12,
    ) == pytest.approx(expected)


def test_calculate_max_drawdown():
    assert calculate_max_drawdown([100.0, 120.0, 90.0, 110.0]) == pytest.approx(-0.25)


def test_calculate_max_drawdown_is_zero_when_prices_only_rise():
    assert calculate_max_drawdown([100.0, 110.0, 120.0]) == pytest.approx(0.0)


def test_calculate_simple_moving_average():
    assert calculate_simple_moving_average(
        [100.0, 110.0, 120.0],
        window=2,
    ) == pytest.approx(115.0)


@pytest.mark.parametrize(
    "prices",
    [
        [],
        [100.0, 0.0],
        [100.0, -1.0],
        [100.0, float("nan")],
        [[100.0, 101.0]],
        ["not-a-price", 101.0],
    ],
)
def test_price_validation_rejects_invalid_history(prices):
    with pytest.raises(InvalidPriceHistoryError):
        calculate_max_drawdown(prices)


@pytest.mark.parametrize("years", [0, -1, True, float("inf"), "bad"])
def test_calculate_cagr_rejects_invalid_years(years):
    with pytest.raises(InvalidCalculationParameterError):
        calculate_cagr([100.0, 110.0], years=years)


@pytest.mark.parametrize("trading_periods", [0, -1, True, 12.5])
def test_calculate_annualized_volatility_rejects_invalid_trading_periods(
    trading_periods,
):
    with pytest.raises(InvalidCalculationParameterError):
        calculate_annualized_volatility(
            [100.0, 101.0, 102.0],
            trading_periods=trading_periods,
        )


@pytest.mark.parametrize("window", [0, -1, True, 1.5, 4])
def test_calculate_simple_moving_average_rejects_invalid_window(window):
    with pytest.raises(InvalidCalculationParameterError):
        calculate_simple_moving_average(
            [100.0, 110.0, 120.0],
            window=window,
        )
