class WorkerResponseError(Exception):
    """Base exception for errors with codes >= 400"""

class InvalidWorkerResponseError(Exception):
    """Base exception for some worker returning invalid response."""

class DownloaderClientError(Exception):
    """Base exception for errors communicating with Downloader."""


class DownloaderResponseError(DownloaderClientError):
    """Raised when Downloader returns an HTTP error response."""

    def __init__(
        self,
        status: int,
        message: str,
    ) -> None:
        self.status = status
        self.message = message

        super().__init__(
            f"Downloader returned HTTP {status}: {message}"
        )


class InvalidDownloaderResponseError(DownloaderClientError):
    """Raised when Downloader returns an unexpected response."""

class AnalyzerClientError(Exception):
    """Base exception for errors communicating with Analyzer."""


class AnalyzerResponseError(AnalyzerClientError):
    """Raised when Analyzer returns an HTTP error response."""

    def __init__(
        self,
        status: int,
        message: str,
    ) -> None:
        self.status = status
        self.message = message

        super().__init__(
            f"Analyzer returned HTTP {status}: {message}"
        )


class InvalidAnalyzerResponseError(
    AnalyzerClientError
):
    """Raised when Analyzer returns an unexpected response."""