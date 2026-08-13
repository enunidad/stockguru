from dataclasses import dataclass, field
from typing import Any, Optional

@dataclass(frozen=True)
class ChartRequest:
    ticker: str
    period: str = "10y"
    interval: str = "1d"
    auto_adjust: bool = True
    aggregate: bool = True

@dataclass(frozen=True)
class ChartResponse:
    chart_type: str
    title: str
    xaxis_label: Optional[str] = None
    yaxis_label: Optional[str] = None
    legend: Optional[bool] = False
    x_values: list[Any] = field(default_factory = list)
    y_values: dict[str, list[Any]] = field(default_factory = dict)