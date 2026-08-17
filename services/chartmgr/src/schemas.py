from dataclasses import dataclass, field
from typing import Any, Optional

@dataclass(frozen=True)
class ChartRequest:
    ticker: str
    period: str = "10y"
    interval: str = "1mo"
    auto_adjust: bool = True
    aggregate: bool = True

@dataclass(frozen=True)
class ChartResponse:
    chart_type: str
    title: str
    xaxis_label: Optional[str] = None
    yaxis_label: Optional[str] = None
    legend: bool = False
    x_values: list[Any] = field(default_factory = list)
    y_values: dict[str, list[Any]] = field(default_factory = dict)

    def to_dict(self) -> dict[str, Any]:
        return {'chart_type': self.chart_type,
                'title': self.title,
                'data': {'x_values': self.x_values, 'y_values': self.y_values},
                'labels': {'x': self.xaxis_label, 
                            'y': self.yaxis_label},
                'legend': self.legend}