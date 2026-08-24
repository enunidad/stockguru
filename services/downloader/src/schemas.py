import yfinance as yf
from dataclasses import dataclass, field
from typing import Any, Optional
from .exceptions import InvalidTickerError, InvalidParameterError

@dataclass(frozen=True)
class PriceHistoryRequest:
    ticker: yf.Ticker|str
    period: str = "10y"
    interval: str = "1d"
    auto_adjust: str|bool = True
    aggregate: str|bool = True

    @staticmethod
    def _validate_time_period(val, kind):
        if isinstance(val, str):
            expected_suffixes = ["d", "wk", "mo", "y"]
            present = None
            for suffix in expected_suffixes:
                if val.endswith(suffix):
                    present = suffix
                    break
            if present is None:
                raise InvalidParameterError(f"{kind} suffix unrecognized. Must be one of {expected_suffixes}.")
            duration = val.replace(present, "")
            try:
                d = int(duration)
            except ValueError:
                raise InvalidParameterError(f"{kind} value must be castable as an integer.")
            if d <= 0:
                raise InvalidParameterError(f"{kind} value must be a positive integer.")
            if d >= 30:
                raise InvalidParameterError(f"{kind} value must be less than 30.")
        else:
            raise InvalidParameterError(f"{kind} parameter must be a string.")
    
    def _validate_boolean(self, name):
        val = getattr(self, name)
        if isinstance(val, str):
            true = ["true", "yes", "1", "on"]
            false = ["false", "no", "0", "off"]
            expected = true + false
            if val.lower() in expected:
                if val.lower() in true:
                    object.__setattr__(self, name, True)
                else:
                    object.__setattr__(self, name, False)
            else:
                raise InvalidParameterError(f"{name} parameter must be one of {expected}.")            
        elif isinstance(val, bool):
            pass
        else:
            raise InvalidParameterError(f"{name} parameter is invalid.")

    def __post_init__(self):
        if isinstance(self.ticker, str):
            symbol = self.ticker.strip().upper()
            if symbol:
                try:
                    object.__setattr__(self, "ticker", yf.Ticker(symbol))
                except Exception as exc:
                    raise InvalidTickerError(f"Ticker '{symbol}' could not be created.") from exc
            else:
                raise InvalidTickerError("Ticker cannot be empty.")
        elif isinstance(self.ticker, yf.Ticker):
            pass
        else:
            raise InvalidTickerError(f"Ticker '{self.ticker}' is not a valid symbol")
        
        self._validate_time_period(self.period, "period")
        self._validate_time_period(self.interval, "interval")

        self._validate_boolean("auto_adjust")
        self._validate_boolean("aggregate")

@dataclass(frozen=True)
class TickerMetadata:
    """
    Ticker metadata schema

    Args:
        ticker (str): The symbol for the stock metadata
        currency (Optional[str]): The currency of the stock
        exchange (Optional[str]): The location of the stock
        timezone (Optional[str]): The timezone of the exchange
        quote_type (Optional[str]):
        name (Optional[str]): The long name of the stock
        sector (Optional[str]): The sector of the stock
        industry (Optional[str]): the industry of the stock
        country (Optional[str]): The country where stock is based
        raw (dict[str, Any]): anything else that does not belong in the above that was returned
                                by the client.
    """
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

