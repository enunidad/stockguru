import math

from dataclasses import dataclass

from .schemas import (
    ForecastPoint,
    HoldingProjectionResult,
)

MONTHS_PER_YEAR = 12

CONTRIBUTION_INTERVALS = {
    "monthly": 1,
    "quarterly": 3,
    "annually": 12,
}

@dataclass
class HoldingProjectionState:
    """
    Mutable state used while calculating a holding projection.
    """

    ticker: str
    price: float

    investment_shares: float
    dividend_shares: float = 0.0

    initial_investment: float = 0.0
    contributions: float = 0.0
    dividend_cash: float = 0.0

def project_holding(
    *,
    ticker: str,
    shares: float,
    current_price: float,
    initial_investment: float,
    annual_growth_rate: float,
    annual_dividend_per_share: float,
    years: int,
    contribution_amount: float = 0.0,
    contribution_frequency: str = "monthly",
    drip: bool = True,
) -> HoldingProjectionResult:
    """
    Project a single holding forward.

    Price appreciation and dividends are tracked separately.

    Shares purchased from dividends remain in the dividend
    attribution bucket so future growth from those shares is
    also counted as dividend-derived value.
    """
    _validate_inputs(
        shares=shares,
        current_price=current_price,
        initial_investment=initial_investment,
        annual_growth_rate=annual_growth_rate,
        annual_dividend_per_share=annual_dividend_per_share,
        years=years,
        contribution_amount=contribution_amount,
        contribution_frequency=contribution_frequency,
    )

    state = HoldingProjectionState(
        ticker=ticker.strip().upper(),
        price=current_price,
        investment_shares=shares,
        initial_investment=initial_investment,
    )

    monthly_growth_rate = annual_to_monthly_rate(
        annual_growth_rate
    )

    monthly_dividend_per_share = (
        annual_dividend_per_share
        / MONTHS_PER_YEAR
    )

    contribution_interval = (
        CONTRIBUTION_INTERVALS[
            contribution_frequency
        ]
    )

    timeline = [
        ForecastPoint(
            year=0,
            value=round(
                total_value(state),
                2,
            ),
        )
    ]

    total_months = years * MONTHS_PER_YEAR

    for month in range(
        1,
        total_months + 1,
    ):
        apply_price_growth(
            state,
            monthly_growth_rate,
        )

        if (
            contribution_amount > 0
            and month % contribution_interval == 0
        ):
            apply_contribution(
                state,
                contribution_amount,
            )

        if monthly_dividend_per_share > 0:
            apply_dividend(
                state,
                monthly_dividend_per_share,
                drip=drip,
            )

        if month % MONTHS_PER_YEAR == 0:
            timeline.append(
                ForecastPoint(
                    year=month // MONTHS_PER_YEAR,
                    value=round(
                        total_value(state),
                        2,
                    ),
                )
            )

    investment_value = (
        state.investment_shares
        * state.price
    )

    dividend_value = (
        state.dividend_shares
        * state.price
        + state.dividend_cash
    )

    growth = (
        investment_value
        - state.initial_investment
        - state.contributions
    )

    future_value = (
        investment_value
        + dividend_value
    )

    print(
        "FORECAST DEBUG",
        {
            "ticker": state.ticker,
            "price": state.price,
            "investment_shares": state.investment_shares,
            "dividend_shares": state.dividend_shares,
            "initial_investment": state.initial_investment,
            "contributions": state.contributions,
            "dividend_cash": state.dividend_cash,
            "investment_value": investment_value,
            "dividend_value": dividend_value,
            "growth": growth,
            "future_value": future_value,
        },
    )
    return HoldingProjectionResult(
        ticker=state.ticker,
        initial_investment=round(
            state.initial_investment,
            2,
        ),
        contributions=round(
            state.contributions,
            2,
        ),
        growth=round(
            growth,
            2,
        ),
        dividends=round(
            dividend_value,
            2,
        ),
        future_value=round(
            future_value,
            2,
        ),
        timeline=timeline,
    )


def apply_price_growth(
    state: HoldingProjectionState,
    monthly_growth_rate: float,
) -> None:
    """
    Apply one month of price appreciation/depreciation.
    """
    state.price *= (
        1.0 + monthly_growth_rate
    )


def apply_contribution(
    state: HoldingProjectionState,
    amount: float,
) -> None:
    """
    Purchase shares using a user contribution.
    """
    if amount <= 0:
        return

    shares_purchased = (
        amount / state.price
    )

    state.investment_shares += (
        shares_purchased
    )

    state.contributions += amount


def apply_dividend(
    state: HoldingProjectionState,
    dividend_per_share: float,
    *,
    drip: bool,
) -> None:
    """
    Apply a dividend payment.

    If DRIP is enabled, dividend proceeds purchase new
    dividend-funded shares.

    Otherwise, dividend proceeds accumulate as cash.
    """
    if dividend_per_share <= 0:
        return

    shares = total_shares(state)

    dividend_amount = (
        shares
        * dividend_per_share
    )

    if drip:
        dividend_shares = (
            dividend_amount
            / state.price
        )

        state.dividend_shares += (
            dividend_shares
        )

    else:
        state.dividend_cash += (
            dividend_amount
        )


def total_shares(
    state: HoldingProjectionState,
) -> float:
    """
    Total shares currently owned.
    """
    return (
        state.investment_shares
        + state.dividend_shares
    )


def total_value(
    state: HoldingProjectionState,
) -> float:
    """
    Current total value of the holding including
    non-reinvested dividend cash.
    """
    return (
        total_shares(state)
        * state.price
        + state.dividend_cash
    )


def annual_to_monthly_rate(
    annual_rate: float,
) -> float:
    """
    Convert an effective annual rate into its equivalent
    effective monthly rate.
    """
    return (
        (1.0 + annual_rate)
        ** (1.0 / MONTHS_PER_YEAR)
        - 1.0
    )


def _validate_inputs(
    *,
    shares: float,
    current_price: float,
    initial_investment: float,
    annual_growth_rate: float,
    annual_dividend_per_share: float,
    years: int,
    contribution_amount: float,
    contribution_frequency: str,
) -> None:
    if shares < 0:
        raise ValueError(
            "Shares cannot be negative."
        )

    if (
        not math.isfinite(current_price)
        or current_price <= 0
    ):
        raise ValueError(
            "Current price must be a finite value greater than zero."
        )

    if initial_investment < 0:
        raise ValueError(
            "Initial investment cannot be negative."
        )

    if years <= 0:
        raise ValueError(
            "Forecast years must be greater than zero."
        )

    if contribution_amount < 0:
        raise ValueError(
            "Contribution amount cannot be negative."
        )

    if (
        contribution_frequency
        not in CONTRIBUTION_INTERVALS
    ):
        raise ValueError(
            "Contribution frequency must be "
            "monthly, quarterly, or annually."
        )

    if not math.isfinite(
        annual_growth_rate
    ):
        raise ValueError(
            "Annual growth rate must be finite."
        )

    if annual_growth_rate <= -1.0:
        raise ValueError(
            "Annual growth rate must be greater than -1."
        )

    if (
        not math.isfinite(
            annual_dividend_per_share
        )
        or annual_dividend_per_share < 0
    ):
        raise ValueError(
            "Annual dividend per share must be "
            "a finite non-negative value."
        )