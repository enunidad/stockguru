from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PriceRecord:
    date: str
    close: float
    adjusted_close: float | None = None
    open: float | None = None
    high: float | None = None
    low: float | None = None
    volume: int | None = None

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> "PriceRecord":
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
    ticker: str
    period: str
    interval: str
    rows: tuple[PriceRecord, ...]

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> "PriceHistory":
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
        return tuple(
            row.close
            for row in self.rows
        )


@dataclass(frozen=True)
class AnalysisResult:
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


def _optional_float(
    value: Any,
) -> float | None:
    if value is None:
        return None

    return float(value)


def _optional_int(
    value: Any,
) -> int | None:
    if value is None:
        return None

    return int(value)