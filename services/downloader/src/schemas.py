from dataclasses import dataclass

@dataclass(frozen=True)
class PriceHistoryRequest:
    ticker: str
    period: str = "10y"
    interval: str = "1d"
    auto_adjust: bool = False