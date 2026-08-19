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
    HoldingProjectionResult,
)
from .calculations import project_holding


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
        self._validate_request(request)

        results = []

        for holding in request.holdings:
            prepared = await self._prepare_holding(
                holding
            )

            contribution_amount = (
                request.contribution_amount
                * holding.contribution_weight
            )

            result = project_holding(
                ticker=prepared["ticker"],
                shares=holding.shares,
                current_price=prepared["latest_close"],
                initial_investment=prepared["initial_investment"],
                annual_growth_rate=prepared["annual_growth_rate"],
                annual_dividend_per_share=prepared["annual_dividend"],
                years=request.years,
                contribution_amount=contribution_amount,
                contribution_frequency=request.contribution_frequency,
                drip=request.drip,
            )

            results.append(result)

        return self._build_response(
            results,
            years=request.years,
        )
    
    @staticmethod
    def _build_response(
        results: list[HoldingProjectionResult],
        *,
        years: int,
    ) -> ForecastResponse:
        """
        Combine individual holding projections into a
        portfolio-level forecast response.
        """
        holdings = [
            HoldingForecast(
                ticker=result.ticker,
                initial_investment=result.initial_investment,
                contributions=result.contributions,
                growth=result.growth,
                dividends=result.dividends,
                future_value=result.future_value,
            )
            for result in results
        ]

        summary = ForecastSummary(
            initial_investment=round(
                sum(
                    result.initial_investment
                    for result in results
                ),
                2,
            ),
            future_contributions=round(
                sum(
                    result.contributions
                    for result in results
                ),
                2,
            ),
            stock_growth=round(
                sum(
                    result.growth
                    for result in results
                ),
                2,
            ),
            dividends=round(
                sum(
                    result.dividends
                    for result in results
                ),
                2,
            ),
            future_value=round(
                sum(
                    result.future_value
                    for result in results
                ),
                2,
            ),
        )

        timeline = []

        for year in range(years + 1):
            value = sum(
                result.timeline[year].value
                for result in results
            )

            timeline.append(
                ForecastPoint(
                    year=year,
                    value=round(value, 2),
                )
            )

        return ForecastResponse(
            summary=summary,
            timeline=timeline,
            holdings=holdings,
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
                auto_adjust=False,
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

        cost_per_share = (
            holding.average_cost
            if holding.average_cost is not None
            else latest_close
        )

        initial_investment = (
            holding.shares * cost_per_share
        )

        print(
            "FORECAST INPUT",
            {
                "ticker": ticker,
                "latest_close": latest_close,
                "analyzer_start_price": analysis.get("start_price"),
                "analyzer_current_price": analysis.get("current_price"),
                "cagr": annual_growth_rate,
            },
        )

        return {
            "ticker": ticker,
            "latest_close": latest_close,
            "initial_investment": initial_investment,
            "annual_growth_rate": annual_growth_rate,
            "annual_dividend": annual_dividend,
        }
    
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