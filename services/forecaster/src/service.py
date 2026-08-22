from __future__ import annotations

import math
from typing import Any
import pandas as pd
from dataclasses import fields

from .client import MyClient

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
    
    _MIN_PROJECTED_GROWTH_RATE = 0.015

    def __init__(self, client: MyClient|None = None, ) -> None:
        self._client = MyClient() if client is None else client

    async def forecast(self, request: ForecastRequest, ) -> ForecastResponse:
        self._validate_request(request)

        results = []

        for holding in request.holdings:
            prepared = await self._prepare_holding(holding)

            contribution_amount = request.contribution_amount * holding.contribution_weight

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

        return self._build_response(results, years=request.years, )
    
    @staticmethod
    def _build_response(results: list[HoldingProjectionResult], *, years: int, ) -> ForecastResponse:
        """
        Combine individual holding projections into a
        portfolio-level forecast response.
        """

        # -----------------------------------------------------
        # Per-holding results
        # -----------------------------------------------------

        holding_params = lambda x: {key.name: getattr(x, key.name) for key in fields(HoldingForecast) if key.init}
        holdings = [HoldingForecast(**holding_params(result)) for result in results]

        # -----------------------------------------------------
        # Portfolio summary
        # -----------------------------------------------------

        summary_fields = {"future_contributions":"contributions", "stock_growth":"growth",}
        summary_content = lambda x, y: round(sum(getattr(result, summary_fields.get(y, y)) for result in x), 2)
        summary_params = {key.name: summary_content(results, key.name) for key in fields(ForecastSummary) if key.init}    
        summary = ForecastSummary(**summary_params)

        # -----------------------------------------------------
        # Portfolio timeline
        # -----------------------------------------------------

        value_content = lambda results, year: round(sum(result.timeline[year].value for result in results), 2)
        timeline_params = lambda results, year: {"year": year, "value": value_content(results, year)}
        timeline = [ForecastPoint(**timeline_params(results, year)) for year in range(years + 1)]

        return ForecastResponse(summary=summary, timeline=timeline, holdings=holdings, )

    async def _prepare_holding(self, holding: HoldingInput, ) -> dict[str, Any]:
        """
        Resolve external data required for one holding.
        """
        ticker = holding.ticker.strip().upper()

        latest_close = (await self._client.latest_close(ticker))

        analysis = await self._client.get_analysis(ticker, period="10y", interval="1d", auto_adjust=False, )

        dividend_data = await self._client.get_dividends(ticker, period="10y", )

        annual_growth_rate = max(self._read_cagr(analysis), self._MIN_PROJECTED_GROWTH_RATE)

        annual_dividend = self._read_annual_dividend(dividend_data)

        cost_per_share = holding.average_cost if holding.average_cost is not None else latest_close

        initial_investment = holding.shares * cost_per_share

        return {
            "ticker": ticker,
            "latest_close": latest_close,
            "initial_investment": initial_investment,
            "annual_growth_rate": annual_growth_rate,
            "annual_dividend": annual_dividend,
        }
    
    @staticmethod
    def _read_annual_dividend(dividend_data: list[dict[str, Any]], ) -> float:
        """
        Calculate trailing 12-month dividends per share.

        Returns zero for stocks with no dividend history.
        """
        if not dividend_data:
            return 0.0

        parsed: list[tuple[pd.Timestamp, float]] = []

        for record in dividend_data:
            if not isinstance(record, dict):
                raise ValueError("Dividend record must be a dictionary.")
            if "Date" not in record or "Dividend" not in record:
                raise ValueError("Dividend record must contain Date and Dividend.")

            date = record['Date']
            amount = record["Dividend"]

            try:
                parsed_date = pd.to_datetime(date, utc=True, )
                parsed_amount = float(amount)

            except (TypeError, ValueError) as exc:
                raise ValueError("Dividend record contains invalid data.") from exc

            if not math.isfinite(parsed_amount):
                raise ValueError("Dividend amount must be finite.")

            if parsed_amount < 0:
                raise ValueError("Dividend amount cannot be negative.")

            parsed.append((parsed_date, parsed_amount, ))

        latest_date = max(date for date, _ in parsed)

        cutoff_date = latest_date - pd.DateOffset(years=1)

        annual_dividend = sum(amount for date, amount in parsed if date > cutoff_date)

        return annual_dividend

    @staticmethod
    def _read_cagr(analysis: dict[str, Any], ) -> float:
        """
        Extract CAGR from an Analyzer response.
        """
        if "cagr" not in analysis:
            raise ValueError("Analyzer response is missing CAGR.")

        try:
            cagr = float(analysis["cagr"])
        except (TypeError, ValueError) as exc:
            raise ValueError("Analyzer CAGR must be numeric.") from exc

        if not math.isfinite(cagr):
            raise ValueError("Analyzer CAGR must be finite.")

        if cagr <= -1.0:
            raise ValueError("Analyzer CAGR must be greater than -1.")

        return cagr

    @classmethod
    def _validate_request(cls, request: ForecastRequest, ) -> None:
        if not request.holdings:
            raise ValueError("At least one holding is required.")

        if request.years <= 0:
            raise ValueError("Forecast years must be greater than zero.")
        
        if request.years >= 40:
            raise ValueError("Forecast years must be less than 40.")

        if request.contribution_amount < 0:
            raise ValueError("Contribution amount cannot be negative.")
        
        if request.contribution_amount >= 1000000:
            raise ValueError("Contribution must be less than 1M.")

        if (request.contribution_frequency not in cls._CONTRIBUTION_MONTHS):
            raise ValueError("Contribution frequency must be monthly, quarterly, or annually.")

        for holding in request.holdings:
            cls._validate_holding(holding)

        if request.contribution_amount > 0:
            total_weight = sum(holding.contribution_weight for holding in request.holdings)

            if not math.isclose(total_weight, 1.0, abs_tol=1e-6, ):
                raise ValueError("Contribution weights must sum to 1.0.")

    @staticmethod
    def _validate_holding(holding: HoldingInput, ) -> None:
        if not holding.ticker.strip():
            raise ValueError("Ticker cannot be empty.")

        if holding.shares < 0:
            raise ValueError("Shares cannot be negative.")

        if (holding.average_cost is not None and holding.average_cost <= 0):
            raise ValueError("Average cost must be greater than zero.")

        if not (0.0 <= holding.contribution_weight <= 1.0):
            raise ValueError("Contribution weight must be between 0 and 1."
            )