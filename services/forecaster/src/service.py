from __future__ import annotations

import math
from typing import Any
import pandas as pd

from .client import (
    AnalyzerApiClient,
    DownloaderApiClient,
)
from .schemas import (
    ForecastPoint,
    ForecastRequest,
    ForecastResponse,
    ForecastSummary,
    HoldingForecast,
    HoldingInput,
)


class ForecasterService:
    """Coordinates market data and portfolio projections."""

    _MONTHS_PER_YEAR = 12

    _CONTRIBUTION_MONTHS = {
        "monthly": 1,
        "quarterly": 3,
        "annually": 12,
    }

    def __init__(
        self,
        downloader_client: DownloaderApiClient,
        analyzer_client: AnalyzerApiClient,
    ) -> None:
        self._downloader_client = downloader_client
        self._analyzer_client = analyzer_client

    async def forecast(
        self,
        request: ForecastRequest,
    ) -> ForecastResponse:
        """
        Generate a portfolio forecast.

        Historical CAGR is used as the growth assumption.

        Dividend forecasting is intentionally left at zero until
        dividend history is available from a dependency.
        """
        self._validate_request(request)

        holding_states: list[dict[str, Any]] = []

        for holding in request.holdings:
            state = await self._prepare_holding(
                holding
            )
            holding_states.append(state)

        timeline = [
            ForecastPoint(
                year=0,
                value=round(
                    sum(
                        state["current_value"]
                        for state in holding_states
                    ),
                    2,
                ),
            )
        ]

        total_months = (
            request.years * self._MONTHS_PER_YEAR
        )

        contribution_interval = (
            self._CONTRIBUTION_MONTHS[
                request.contribution_frequency
            ]
        )

        total_contributions = 0.0

        for month in range(1, total_months + 1):

            for state in holding_states:

                state["value"] *= (
                    1.0 + state["monthly_growth_rate"]
                )

                if month % contribution_interval == 0:
                    contribution = (
                        request.contribution_amount
                        * state["contribution_weight"]
                    )

                    state["value"] += contribution
                    state["contributions"] += contribution
                    total_contributions += contribution

            if month % self._MONTHS_PER_YEAR == 0:
                timeline.append(
                    ForecastPoint(
                        year=(
                            month
                            // self._MONTHS_PER_YEAR
                        ),
                        value=round(
                            sum(
                                state["value"]
                                for state in holding_states
                            ),
                            2,
                        ),
                    )
                )

        holding_forecasts = [
            self._build_holding_forecast(state)
            for state in holding_states
        ]

        initial_investment = sum(
            result.initial_investment
            for result in holding_forecasts
        )

        future_value = sum(
            result.future_value
            for result in holding_forecasts
        )

        dividends = sum(
            result.dividends
            for result in holding_forecasts
        )

        stock_growth = (
            future_value
            - initial_investment
            - total_contributions
            - dividends
        )

        summary = ForecastSummary(
            initial_investment=round(
                initial_investment,
                2,
            ),
            future_contributions=round(
                total_contributions,
                2,
            ),
            stock_growth=round(
                stock_growth,
                2,
            ),
            dividends=round(
                dividends,
                2,
            ),
            future_value=round(
                future_value,
                2,
            ),
        )

        return ForecastResponse(
            summary=summary,
            timeline=timeline,
            holdings=holding_forecasts,
        )

    async def _prepare_holding(
        self,
        holding: HoldingInput,
    ) -> dict[str, Any]:
        """
        Resolve external data required for one holding.
        """
        ticker = holding.ticker.strip().upper()

        latest_close = (
            await self._downloader_client.latest_close(
                ticker
            )
        )

        analysis = (
            await self._analyzer_client.get_analysis(
                ticker,
                period="10y",
                interval="1d",
            )
        )

        dividend_data = (
            await self._downloader_client.get_dividends(
                ticker,
                period="10y",
            )
        )

        annual_growth_rate = self._read_cagr(
            analysis
        )

        annual_dividend = self._read_annual_dividend(
            dividend_data
        )

        monthly_growth_rate = (
            self._annual_to_monthly_rate(
                annual_growth_rate
            )
        )

        cost_per_share = (
            holding.average_cost
            if holding.average_cost is not None
            else latest_close
        )

        initial_investment = (
            holding.shares * cost_per_share
        )

        current_value = (
            holding.shares * latest_close
        )

        return {
            "ticker": ticker,
            "shares": holding.shares,
            "latest_close": latest_close,
            "initial_investment": initial_investment,
            "current_value": current_value,
            "value": current_value,
            "contribution_weight": (
                holding.contribution_weight
            ),
            "contributions": 0.0,
            "dividends": 0.0,
            "annual_growth_rate": annual_growth_rate,
            "monthly_growth_rate": monthly_growth_rate,
            "annual_dividend": annual_dividend,
        }

    @staticmethod
    def _build_holding_forecast(
        state: dict[str, Any],
    ) -> HoldingForecast:
        future_value = float(state["value"])

        initial_investment = float(
            state["initial_investment"]
        )

        contributions = float(
            state["contributions"]
        )

        dividends = float(
            state["dividends"]
        )

        growth = (
            future_value
            - initial_investment
            - contributions
            - dividends
        )

        return HoldingForecast(
            ticker=str(state["ticker"]),
            initial_investment=round(
                initial_investment,
                2,
            ),
            contributions=round(
                contributions,
                2,
            ),
            growth=round(
                growth,
                2,
            ),
            dividends=round(
                dividends,
                2,
            ),
            future_value=round(
                future_value,
                2,
            ),
        )
    
    @staticmethod
    def _read_annual_dividend(
        dividend_data: list[dict[str, Any]],
    ) -> float:
        """
        Calculate trailing 12-month dividends per share.

        Returns zero for stocks with no dividend history.
        """
        if not dividend_data:
            return 0.0

        parsed: list[tuple[pd.Timestamp, float]] = []

        for record in dividend_data:
            if not isinstance(record, dict):
                raise ValueError(
                    "Dividend record must be an object."
                )

            date = record.get("Date")
            amount = record.get("Dividend")

            if date is None or amount is None:
                raise ValueError(
                    "Dividend record must contain Date and Dividend."
                )

            try:
                parsed_date = pd.to_datetime(
                    date,
                    utc=True,
                )

                parsed_amount = float(amount)

            except (TypeError, ValueError) as exc:
                raise ValueError(
                    "Dividend record contains invalid data."
                ) from exc

            if not math.isfinite(parsed_amount):
                raise ValueError(
                    "Dividend amount must be finite."
                )

            if parsed_amount < 0:
                raise ValueError(
                    "Dividend amount cannot be negative."
                )

            parsed.append(
                (
                    parsed_date,
                    parsed_amount,
                )
            )

        latest_date = max(
            date
            for date, _ in parsed
        )

        cutoff_date = (
            latest_date
            - pd.DateOffset(years=1)
        )

        annual_dividend = sum(
            amount
            for date, amount in parsed
            if date > cutoff_date
        )

        return annual_dividend

    @staticmethod
    def _read_cagr(
        analysis: dict[str, Any],
    ) -> float:
        """
        Extract CAGR from an Analyzer response.
        """
        if "cagr" not in analysis:
            raise ValueError(
                "Analyzer response is missing CAGR."
            )

        try:
            cagr = float(analysis["cagr"])
        except (TypeError, ValueError) as exc:
            raise ValueError(
                "Analyzer CAGR must be numeric."
            ) from exc

        if not math.isfinite(cagr):
            raise ValueError(
                "Analyzer CAGR must be finite."
            )

        if cagr <= -1.0:
            raise ValueError(
                "Analyzer CAGR must be greater than -1."
            )

        return cagr

    @staticmethod
    def _annual_to_monthly_rate(
        annual_rate: float,
    ) -> float:
        """
        Convert an effective annual growth rate into an
        equivalent effective monthly rate.
        """
        return (
            (1.0 + annual_rate) ** (1.0 / 12.0)
            - 1.0
        )

    @classmethod
    def _validate_request(
        cls,
        request: ForecastRequest,
    ) -> None:
        if not request.holdings:
            raise ValueError(
                "At least one holding is required."
            )

        if request.years <= 0:
            raise ValueError(
                "Forecast years must be greater than zero."
            )

        if request.contribution_amount < 0:
            raise ValueError(
                "Contribution amount cannot be negative."
            )

        if (
            request.contribution_frequency
            not in cls._CONTRIBUTION_MONTHS
        ):
            raise ValueError(
                "Contribution frequency must be "
                "monthly, quarterly, or annually."
            )

        for holding in request.holdings:
            cls._validate_holding(holding)

        if request.contribution_amount > 0:
            total_weight = sum(
                holding.contribution_weight
                for holding in request.holdings
            )

            if not math.isclose(
                total_weight,
                1.0,
                abs_tol=1e-6,
            ):
                raise ValueError(
                    "Contribution weights must sum to 1.0."
                )

    @staticmethod
    def _validate_holding(
        holding: HoldingInput,
    ) -> None:
        if not holding.ticker.strip():
            raise ValueError(
                "Ticker cannot be empty."
            )

        if holding.shares < 0:
            raise ValueError(
                "Shares cannot be negative."
            )

        if (
            holding.average_cost is not None
            and holding.average_cost <= 0
        ):
            raise ValueError(
                "Average cost must be greater than zero."
            )

        if not (
            0.0
            <= holding.contribution_weight
            <= 1.0
        ):
            raise ValueError(
                "Contribution weight must be "
                "between 0 and 1."
            )