from __future__ import annotations

from math import sqrt
from typing import Sequence

import numpy as np

from .exceptions import (
    InvalidCalculationParameterError,
    InvalidPriceHistoryError,
)


def _to_price_array(
    prices: Sequence[float],
    *,
    minimum_length: int = 1,
) -> np.ndarray:
    """
    Convert price history into a validated one-dimensional NumPy array.

    Raises:
        InvalidPriceHistoryError:
            If the price history is empty, too short, multidimensional,
            contains non-numeric values, contains non-finite values,
            or contains values less than or equal to zero.
    """
    try:
        values = np.asarray(prices, dtype=float)
    except (TypeError, ValueError) as exc:
        raise InvalidPriceHistoryError(
            "Price history must contain numeric values."
        ) from exc

    if values.ndim != 1:
        raise InvalidPriceHistoryError(
            "Price history must be one-dimensional."
        )

    if len(values) < minimum_length:
        raise InvalidPriceHistoryError(
            f"At least {minimum_length} price values are required."
        )

    if not np.all(np.isfinite(values)):
        raise InvalidPriceHistoryError(
            "Price history must contain only finite values."
        )

    if np.any(values <= 0):
        raise InvalidPriceHistoryError(
            "Price values must be greater than zero."
        )

    return values


def calculate_total_return(
    prices: Sequence[float],
) -> float:
    """
    Calculate total return from the first price to the last price.

    Returns:
        Total return as a decimal.

    Example:
        [100, 120] returns 0.20.
    """
    values = _to_price_array(
        prices,
        minimum_length=2,
    )

    return float(values[-1] / values[0] - 1)


def calculate_cagr(
    prices: Sequence[float],
    years: float,
) -> float:
    """
    Calculate compound annual growth rate.

    Returns:
        CAGR as a decimal.

    Example:
        Prices growing from 100 to 121 over two years return 0.10.
    """
    values = _to_price_array(
        prices,
        minimum_length=2,
    )

    if isinstance(years, bool):
        raise InvalidCalculationParameterError(
            "Years must be a numeric value greater than zero."
        )

    try:
        numeric_years = float(years)
    except (TypeError, ValueError) as exc:
        raise InvalidCalculationParameterError(
            "Years must be a numeric value."
        ) from exc

    if not np.isfinite(numeric_years):
        raise InvalidCalculationParameterError(
            "Years must be finite."
        )

    if numeric_years <= 0:
        raise InvalidCalculationParameterError(
            "Years must be greater than zero."
        )

    growth_multiple = values[-1] / values[0]

    return float(
        growth_multiple ** (1 / numeric_years) - 1
    )


def calculate_annualized_volatility(
    prices: Sequence[float],
    trading_periods: int = 252,
) -> float:
    """
    Calculate annualized volatility using simple period returns.

    Args:
        prices:
            Historical prices ordered from oldest to newest.
        trading_periods:
            Number of observations in one year. Common values are
            252 for daily data, 52 for weekly data, and 12 for monthly data.

    Returns:
        Annualized volatility as a decimal.
    """
    values = _to_price_array(
        prices,
        minimum_length=3,
    )

    if (
        isinstance(trading_periods, bool)
        or not isinstance(trading_periods, int)
    ):
        raise InvalidCalculationParameterError(
            "Trading periods must be an integer."
        )

    if trading_periods <= 0:
        raise InvalidCalculationParameterError(
            "Trading periods must be greater than zero."
        )

    period_returns = values[1:] / values[:-1] - 1

    period_volatility = np.std(
        period_returns,
        ddof=1,
    )

    annualized_volatility = (
        period_volatility * sqrt(trading_periods)
    )

    return float(annualized_volatility)


def calculate_max_drawdown(
    prices: Sequence[float],
) -> float:
    """
    Calculate the largest peak-to-trough decline.

    Returns:
        Maximum drawdown as a negative decimal or zero.

    Example:
        [100, 120, 90] returns -0.25.
    """
    values = _to_price_array(
        prices,
        minimum_length=1,
    )

    running_peaks = np.maximum.accumulate(values)
    drawdowns = values / running_peaks - 1

    return float(np.min(drawdowns))


def calculate_simple_moving_average(
    prices: Sequence[float],
    window: int,
) -> float:
    """
    Calculate the average of the most recent prices in the window.

    Returns:
        The latest simple moving-average value.

    Example:
        Prices [100, 110, 120] with a window of 2 return 115.
    """
    values = _to_price_array(
        prices,
        minimum_length=1,
    )

    if isinstance(window, bool) or not isinstance(window, int):
        raise InvalidCalculationParameterError(
            "Moving-average window must be an integer."
        )

    if window <= 0:
        raise InvalidCalculationParameterError(
            "Moving-average window must be greater than zero."
        )

    if window > len(values):
        raise InvalidCalculationParameterError(
            "Moving-average window cannot exceed the price-history length."
        )

    return float(
        np.mean(values[-window:])
    )