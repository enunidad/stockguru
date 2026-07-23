from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class PriceHistoryRequest:
    ticker: str
    period: str = "10y"
    interval: str = "1mo"
    auto_adjust: bool = True

@dataclass(frozen=False)
class TickerMetadata:
    ticker: str
    currency: str or None
    exchange: str or None
    timezone: str or None
    quote_type: str or None
    raw: dict[str, Any]

    def __init__(self, ticker, currency=None, exchange=None, timezone=None, quote_type=None, raw=None):
        self.ticker = ticker
        self.currency = currency
        self.exchange = exchange
        self.timezone = timezone
        self.quote_type = quote_type
        self.raw = {} if raw is None else raw
        self._data = {'ticker':self.ticker, 'currency':self.currency,
                        'exchange':self.exchange, 'timezone':self.timezone,
                        'quote_type':self.quote_type, 'raw':self.raw}

    def __getitem__(self, key):
        return self._data[key]
    
    def keys(self):
        return self._data.keys()

