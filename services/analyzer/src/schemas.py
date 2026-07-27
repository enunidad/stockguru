from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PriceRecord:
    """
    dataclass for standardizing the data

    Args:
        date (str): The date of this price record
        close (float): THe closing value of the stockin a given period
        adjusted_close (Optional[float]): the adjusted value after splits
        open (Optional[float]): The opening value of the stock in a given period
        high (Optional[float]): The highest value of the stock in a given period
        low (Optional[float]): The lowest value of the stock in a given period
        volume (Optional[int]): THe total amount of trades in a given period 
    """
    date: str
    close: float
    adjusted_close: float | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    volume: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any], ) -> "PriceRecord":
        """
        helper method to convert a dictionary into this dataclass

        Args:
            data (dict[str, Any]): the data to be converted

        Returns:
            PriceRecord: this dataclass
        """
        return cls(
            date=str(data["Date"]),
            close=float(data["Close"]),
            adjusted_close=_optional_float(
                data.get("Adj Close")
            ),
            open=_optional_float(
                data.get("Open")
            ),
            high=_optional_float(
                data.get("High")
            ),
            low=_optional_float(
                data.get("Low")
            ),
            volume=_optional_int(
                data.get("Volume")
            ),
        )


@dataclass(frozen=True)
class PriceHistory:
    """
    dataclass schema for the whole history

    Args:
        ticker (str): the symbol for this stock
        period (str): the historical length
        interval (str): the reported interval
        rows (tuple[PriceRecord, ...]): the data that will be put into rows
    """
    ticker: str
    period: str
    interval: str
    rows: tuple[PriceRecord, ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any], ) -> "PriceHistory":
        """
        helper method to turn a dictionary into this dataclass schema

        Args:
            data (dict[str, Any]): the data to be converted

        Returns:
            PriceHistory: the data converted to this class

        """
        raw_rows = data.get("data", [])

        return cls(
            ticker=str(data["ticker"]),
            period=str(data["period"]),
            interval=str(data["interval"]),
            rows=tuple(
                PriceRecord.from_dict(row)
                for row in raw_rows
            ),
        )

    @property
    def closing_prices(self) -> tuple[float, ...]:
        """
        easy accessor for getting closing prices
        """
        return tuple(row.close for row in self.rows)


@dataclass(frozen=True)
class AnalysisResult:
    """
    analysis dataclass schema
    """
    ticker: str
    period: str
    interval: str
    observations: int
    start_date: str
    end_date: str
    start_price: float
    current_price: float
    total_return: float
    cagr: float
    annualized_volatility: float
    max_drawdown: float
    moving_average_50: float | None
    moving_average_200: float | None

    def to_dict(self) -> dict[str, Any]:
        """
        helper method to turn this dataclass schema into a dictionary
        """
        return {
            "ticker": self.ticker,
            "period": self.period,
            "interval": self.interval,
            "observations": self.observations,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "start_price": self.start_price,
            "current_price": self.current_price,
            "total_return": self.total_return,
            "cagr": self.cagr,
            "annualized_volatility": (
                self.annualized_volatility
            ),
            "max_drawdown": self.max_drawdown,
            "moving_average_50": (
                self.moving_average_50
            ),
            "moving_average_200": (
                self.moving_average_200
            ),
        }


def _optional_float(value: Any, ) -> float | None:
    """
    helper method to validate expected float values
    """
    if value is None:
        return None

    return float(value)


def _optional_int(value: Any, ) -> int | None:
    """
    helper metod to validate expected int values
    """
    if value is None:
        return None

    return int(value)