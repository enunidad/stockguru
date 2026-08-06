from dataclasses import dataclass, field
from typing import Any, Optional

@dataclass(frozen=True)
class PriceHistoryRequest:
    """
    Price history request object.

    Args:
        ticker (str): The symbol for the stock requested
        period (str): The length of history requested. any of product(['1', '2', '3', ...], ['d', 'wk', 'm', 'y'])
        interval (str): The interval for reporting history. any of product(['1', '2', '3', ...], ['d', 'wk', 'm', 'y'])
        auto_adjust (bool): Flag for adjusting prices if stock went through splits.
        aggregate (bool): flag for displaying monthly stats instead of daily, reducing space required on the frontend
    """
    ticker: str
    period: str = "10y"
    interval: str = "1d"
    auto_adjust: bool = True
    aggregate: bool = True

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

