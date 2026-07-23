from dataclasses import dataclass, field
from typing import Any, Optional

@dataclass(frozen=True)
class PriceHistoryRequest:
    ticker: str
    period: str = "10y"
    interval: str = "1mo"
    auto_adjust: bool = True

@dataclass(frozen=True)
class TickerMetadata:
    ticker: str
    currency: str or None = None
    exchange: str or None = None
    timezone: str or None = None
    quote_type: str or None = None
    raw: dict[str, Any] = field(default_factory=dict)

