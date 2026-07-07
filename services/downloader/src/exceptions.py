class DownloaderClientError(Exception):
    """Base exception for downloader client errors."""


class EmptyDownloadError(DownloaderClientError):
    """Raised when the data provider returns no rows."""


class InvalidTickerError(DownloaderClientError):
    """Raised when the ticker appears invalid or unsupported."""