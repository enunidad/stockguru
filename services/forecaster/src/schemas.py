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

    initial_investment:
        Total user cost basis for the starting portfolio.

    current_growth:
        Gain or loss already present in the portfolio at the
        start of the forecast.

    future_contributions:
        Additional money supplied by the user during the
        forecast horizon.

    stock_growth:
        Price appreciation generated from the start of the
        forecast forward.

    dividends:
        Dividend value generated during the forecast.

    future_value:
        Total projected portfolio value at the end of the
        forecast horizon.
    """

    initial_investment: float
    current_growth: float

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
    current_growth: float

    contributions: float
    growth: float
    dividends: float

    future_value: float

    dividend_yield: float

    purchased_shares: float
    drip_shares: float
    total_shares: float

    ending_price: float


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


@dataclass(frozen=True)
class HoldingProjectionResult:
    """
    Internal result produced by the calculator for one holding.

    purchased_shares:
        Shares owned because of user-supplied money. This includes
        the user's starting shares plus shares purchased using
        future contributions.

    drip_shares:
        Additional shares purchased using reinvested dividends.

    total_shares:
        Total projected shares at the end of the forecast.
    """

    ticker: str

    initial_investment: float
    current_growth: float

    contributions: float
    growth: float
    dividends: float

    future_value: float

    dividend_yield: float

    purchased_shares: float
    drip_shares: float
    total_shares: float

    ending_price: float

    timeline: list[ForecastPoint]