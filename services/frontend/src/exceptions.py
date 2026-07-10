class ApiClientError(Exception):
    """Base exception for API client errors."""


class ServiceUnavailableError(ApiClientError):
    """Raised when the downstream service cannot be reached."""


class InvalidResponseError(ApiClientError):
    """Raised when the downstream service returns unexpected data."""
