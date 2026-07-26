"""
Collection of exceptions in the downloader service. This is just for clarity
of expected errors. Specificity in debugging is very valuable.
"""

class DownloaderClientError(Exception):
    """Base exception for downloader client errors."""


class EmptyDownloadError(DownloaderClientError):
    """Raised when the data provider returns no rows."""


class InvalidTickerError(DownloaderClientError):
    """Raised when the ticker appears invalid or unsupported."""

class PriceAggregationError(Exception):
    """Raised when price history cannot be aggregated."""