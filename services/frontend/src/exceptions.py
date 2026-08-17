class ApiClientError(Exception):
    """Base exception for API client errors."""


class ServiceUnavailableError(ApiClientError):
    """Raised when the downstream service cannot be reached."""


class InvalidResponseError(ApiClientError):
    """Raised when the downstream service returns unexpected data."""

class ApiResponseError(ApiClientError):
    """Raised when a downstream service returns an HTTP error."""

    def __init__(
        self,
        status: int,
        message: str,
    ) -> None:
        self.status = status
        self.message = message
        super().__init__(message)