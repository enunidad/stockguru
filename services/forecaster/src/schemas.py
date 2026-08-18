from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Optional


@dataclass(frozen=True)
class HoldingInput:
    """
    A single holding supplied by the user.

    average_cost:
        Optional user-provided cost basis per share.
        If omitted, the forecaster will use the most recent
        closing price when calculating the initial investment.

    contribution_weight:
        Portion of recurring contributions allocated to this
        holding. Expected as a decimal between 0 and 1.
    """

    ticker: str
    shares: float
    average_cost: Optional[float] = None
    contribution_weight: float = 0.0


@dataclass(frozen=True)
class ForecastRequest:
    """
    Input required to generate a portfolio forecast.
    """

    holdings: list[HoldingInput]

    years: int = 10

    contribution_amount: float = 0.0
    contribution_frequency: str = "monthly"

    drip: bool = True


@dataclass(frozen=True)
class ForecastSummary:
    """
    Portfolio-level totals at the end of the projection.
    """

    initial_investment: float
    future_contributions: float
    stock_growth: float
    dividends: float
    future_value: float


@dataclass(frozen=True)
class ForecastPoint:
    """
    Portfolio value at a point in the forecast timeline.
    """

    year: int
    value: float


@dataclass(frozen=True)
class HoldingForecast:
    """
    Forecast result for a single holding.
    """

    ticker: str

    initial_investment: float
    contributions: float
    growth: float
    dividends: float
    future_value: float


@dataclass(frozen=True)
class ForecastResponse:
    """
    Complete portfolio forecast returned by the service.
    """

    summary: ForecastSummary
    timeline: list[ForecastPoint]
    holdings: list[HoldingForecast]

    def to_dict(self) -> dict:
        return asdict(self)