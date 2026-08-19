from __future__ import annotations

from datetime import date, datetime
from math import isfinite

from .client import DownloaderApiClient, AnalyzerApiClient
from .exceptions import (
    DownloaderResponseError,
    DownloaderClientError,
    InvalidDownloaderResponseError,
)
from .schemas import (
    ChartResponse,
    ChartRequest,
    PortfolioOverviewRequest,
    PortfolioOverviewResponse,
)


class ChartMgrService:

    def __init__(
        self,
        downloader_client: DownloaderApiClient,
        analyzer_client: AnalyzerApiClient,
    ):
        self._downloader_client = downloader_client
        self._analyzer_client = analyzer_client


    # =====================================================
    # Historical chart helpers
    # =====================================================

    @staticmethod
    def _validate_data(
        payload: list,
        expected: list[str],
    ) -> None:

        if not isinstance(payload, list):
            raise InvalidDownloaderResponseError(
                "Data format is not recognized. Must be a list."
            )

        if not payload:
            raise InvalidDownloaderResponseError(
                "Data requested is empty."
            )

        for itm in payload:

            if not isinstance(itm, dict):
                raise InvalidDownloaderResponseError(
                    "Data object is not recognized. "
                    "Objects must be dictionaries."
                )

            if not set(expected).issubset(itm):
                raise InvalidDownloaderResponseError(
                    "Some data missing required values."
                )


    async def _read_history(
        self,
        ticker,
        expected,
        *,
        period="10y",
        interval="1mo",
        auto_adjust=True,
        aggregate=True,
    ) -> list[dict]:

        request = ChartRequest(
            ticker,
            period=period,
            interval=interval,
            auto_adjust=auto_adjust,
            aggregate=aggregate,
        )

        data = await self._downloader_client.price_history(
            request
        )

        self._validate_data(
            data,
            expected,
        )

        return data


    @staticmethod
    def _format_data(
        data,
        expected,
        chart_type,
        title,
        xaxis_label,
        yaxis_label,
        legend,
    ):

        x_values = []

        y_values = {
            key: []
            for key in expected[1:]
        }


        for row in data:

            x_values.append(
                row[expected[0]]
            )

            for key in y_values:
                y_values[key].append(
                    row[key]
                )


        response_params = {
            "chart_type": chart_type,
            "title": title,
            "xaxis_label": xaxis_label,
            "yaxis_label": yaxis_label,
            "legend": legend,
            "x_values": x_values,
            "y_values": y_values,
        }


        return ChartResponse(
            **response_params
        )


    # =====================================================
    # Historical charts
    # =====================================================

    async def get_price_history(
        self,
        ticker,
        *,
        period="10y",
        interval="1mo",
        auto_adjust=True,
        aggregate=True,
    ) -> ChartResponse:

        expected = [
            "Date",
            "Open",
            "High",
            "Low",
            "Close",
        ]


        data = await self._read_history(
            ticker,
            expected,
            period=period,
            interval=interval,
            auto_adjust=auto_adjust,
            aggregate=aggregate,
        )


        return self._format_data(
            data,
            expected,
            "candlestick",
            "OHLC Price History",
            "Date",
            "Value",
            True,
        )


    async def get_volume_history(
        self,
        ticker,
        *,
        period="10y",
        interval="1mo",
        auto_adjust=True,
        aggregate=True,
    ) -> ChartResponse:

        expected = [
            "Date",
            "Volume",
        ]


        data = await self._read_history(
            ticker,
            expected,
            period=period,
            interval=interval,
            auto_adjust=auto_adjust,
            aggregate=aggregate,
        )


        return self._format_data(
            data,
            expected,
            "bar",
            "Volume History",
            "Date",
            "Volume",
            True,
        )


    # =====================================================
    # Portfolio Overview
    # =====================================================

    @staticmethod
    def _validate_portfolio_overview(
        request: PortfolioOverviewRequest,
    ) -> None:
        """
        Validate portfolio composition values.

        Investment, contributions, and dividends represent
        money added or generated and therefore cannot be
        negative.

        Current growth and future stock growth may be negative
        because a portfolio can contain unrealized or projected
        losses.
        """

        values = {
            "initial_investment":
                request.initial_investment,

            "current_growth":
                request.current_growth,

            "future_contributions":
                request.future_contributions,

            "stock_growth":
                request.stock_growth,

            "dividends":
                request.dividends,
        }


        for name, value in values.items():

            if not isinstance(
                value,
                (int, float),
            ):
                raise ValueError(
                    f"{name} must be numeric."
                )

            if not isfinite(value):
                raise ValueError(
                    f"{name} must be finite."
                )


        non_negative = {
            "initial_investment":
                request.initial_investment,

            "future_contributions":
                request.future_contributions,

            "dividends":
                request.dividends,
        }


        for name, value in non_negative.items():

            if value < 0:
                raise ValueError(
                    f"{name} cannot be negative."
                )


        total = sum(
            values.values()
        )


        if total <= 0:
            raise ValueError(
                "Portfolio overview total must be greater than zero."
            )


    def get_portfolio_overview(
        self,
        request: PortfolioOverviewRequest,
    ) -> PortfolioOverviewResponse:
        """
        Convert Forecaster portfolio totals into
        chart-ready composition data.

        ChartMgr does not calculate any financial values here.
        It only validates and formats values produced by the
        Forecaster service.
        """

        self._validate_portfolio_overview(
            request
        )


        labels = [
            "Total Invested",
            "Current Growth",
            "Future Contributions",
            "Stock Growth",
            "Dividends / DRIP",
        ]


        values = [
            round(
                request.initial_investment,
                2,
            ),

            round(
                request.current_growth,
                2,
            ),

            round(
                request.future_contributions,
                2,
            ),

            round(
                request.stock_growth,
                2,
            ),

            round(
                request.dividends,
                2,
            ),
        ]


        total = round(
            sum(values),
            2,
        )


        # A donut chart cannot meaningfully represent
        # negative slices.
        #
        # Most forecasts will use a donut. If a portfolio
        # contains a current or projected loss, return a
        # bar chart instead so the negative value is not
        # visually misrepresented.

        chart_type = (
            "donut"
            if all(
                value >= 0
                for value in values
            )
            else "bar"
        )


        return PortfolioOverviewResponse(
            chart_type=chart_type,
            title="Portfolio Overview",
            labels=labels,
            values=values,
            total=total,
            legend=True,
        )