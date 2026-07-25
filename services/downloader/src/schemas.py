from dataclasses import dataclass, field
from typing import Any, Optional

@dataclass(frozen=True)
class PriceHistoryRequest:
    ticker: str
    period: str = "10y"
    interval: str = "1d"
    auto_adjust: bool = True

@dataclass(frozen=True)
class TickerMetadata:
    ticker: str
    #fast_info
    currency: Optional[str] = None
    exchange: Optional[str] = None
    timezone: Optional[str] = None
    quote_type: Optional[str] = None

    #info
    name: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    country: Optional[str] = None

    raw: dict[str, Any] = field(default_factory=dict)

