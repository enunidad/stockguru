from __future__ import annotations

from datetime import date, datetime

from .calculations import (
    calculate_annualized_volatility,
    calculate_cagr,
    calculate_max_drawdown,
    calculate_simple_moving_average,
    calculate_total_return,
)
from .client import DownloaderApiClient
from .exceptions import InvalidPriceHistoryError
from .schemas import AnalysisResult, PriceHistory


class AnalyzerService:
    """Coordinates price retrieval and financial analysis."""

    def __init__(
        self,
        downloader_client: DownloaderApiClient,
    ) -> None:
        self._downloader_client = downloader_client

    async def analyze_ticker(
        self,
        ticker: str,
        *,
        period: str = "10y",
        interval: str = "1mo",
    ) -> AnalysisResult:
        """
        Retrieve historical prices and calculate investment metrics.

        Args:
            ticker:
                Stock ticker symbol, such as ``AAPL``.
            period:
                Historical period requested from the downloader.
            interval:
                Price observation interval.

        Returns:
            AnalysisResult containing the calculated metrics.

        Raises:
            DownloaderClientError:
                If the downloader request fails.
            InvalidDownloaderResponseError:
                If the downloader returns invalid data.
            InvalidPriceHistoryError:
                If the returned history cannot support the analysis.
            InvalidCalculationParameterError:
                If a calculation receives an invalid parameter.
        """
        history = await self._downloader_client.get_price_history(
            ticker,
            period=period,
            interval=interval,
        )

        return self._analyze_history(history)

    def _analyze_history(
        self,
        history: PriceHistory,
    ) -> AnalysisResult:
        self._validate_history(history)

        prices = history.closing_prices
        first_record = history.rows[0]
        last_record = history.rows[-1]

        start_date = self._parse_date(first_record.date)
        end_date = self._parse_date(last_record.date)

        years = self._calculate_years(
            start_date=start_date,
            end_date=end_date,
        )

        trading_periods = self._get_trading_periods(
            history.interval
        )

        return AnalysisResult(
            ticker=history.ticker,
            period=history.period,
            interval=history.interval,
            observations=len(history.rows),
            start_date=first_record.date,
            end_date=last_record.date,
            start_price=prices[0],
            current_price=prices[-1],
            total_return=calculate_total_return(prices),
            cagr=calculate_cagr(
                prices,
                years=years,
            ),
            annualized_volatility=(
                calculate_annualized_volatility(
                    prices,
                    trading_periods=trading_periods,
                )
            ),
            max_drawdown=calculate_max_drawdown(
                prices
            ),
            moving_average_50=self._calculate_moving_average(
                prices,
                window=50,
            ),
            moving_average_200=self._calculate_moving_average(
                prices,
                window=200,
            ),
        )

    @staticmethod
    def _validate_history(
        history: PriceHistory,
    ) -> None:
        if len(history.rows) < 3:
            raise InvalidPriceHistoryError(
                "At least three price-history rows are required "
                "to perform an analysis."
            )

    @staticmethod
    def _parse_date(
        value: str,
    ) -> date:
        """
        Parse a downloader date into a date object.

        Supports plain ISO dates such as ``2026-07-22`` and ISO
        datetimes such as ``2026-07-22T16:00:00``.
        """
        try:
            return datetime.fromisoformat(
                value.replace("Z", "+00:00")
            ).date()
        except (TypeError, ValueError) as exc:
            raise InvalidPriceHistoryError(
                f"Invalid price-history date: {value!r}."
            ) from exc

    @staticmethod
    def _calculate_years(
        *,
        start_date: date,
        end_date: date,
    ) -> float:
        elapsed_days = (
            end_date - start_date
        ).days

        if elapsed_days <= 0:
            raise InvalidPriceHistoryError(
                "Price-history end date must be later "
                "than its start date."
            )

        return elapsed_days / 365.2425

    @staticmethod
    def _get_trading_periods(
        interval: str,
    ) -> int:
        trading_periods_by_interval = {
            "1d": 252,
            "5d": 52,
            "1wk": 52,
            "1mo": 12,
            "3mo": 4,
        }

        try:
            return trading_periods_by_interval[interval]
        except KeyError as exc:
            raise InvalidPriceHistoryError(
                f"Unsupported price interval: {interval!r}."
            ) from exc

    @staticmethod
    def _calculate_moving_average(
        prices: tuple[float, ...],
        *,
        window: int,
    ) -> float | None:
        if len(prices) < window:
            return None

        return calculate_simple_moving_average(
            prices,
            window=window,
        )