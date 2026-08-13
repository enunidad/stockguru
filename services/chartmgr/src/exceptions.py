class DownloaderClientError(AnalyzerError):
    """Raised when communication with the downloader fails."""

class DownloaderResponseError(DownloaderClientError):
    """Raised when the downloader returns an unsuccessful HTTP response."""

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


class InvalidDownloaderResponseError(
    DownloaderClientError
):
    """Raised when the downloader response cannot be parsed."""

