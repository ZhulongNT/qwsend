from __future__ import annotations

class QWSendError(Exception):
    """Base exception for qwsend errors."""


class HTTPError(QWSendError):
    """Raised when HTTP status is not 200 OK or response indicates error."""

    def __init__(self, status_code: int, message: str | None = None, *, payload: dict | None = None):
        self.status_code = status_code
        self.payload = payload
        msg = f"{status_code} - {message}" or f"HTTP error: {status_code}"
        super().__init__(msg)


class RateLimit(HTTPError):
    """Raised when the API reports a rate limit (errcode 45009).

    This subclasses :class:`HTTPError` so callers catching HTTPError will still
    receive rate limit errors. The original response payload (if any) is
    available on the ``payload`` attribute.
    """

    def __init__(self, status_code: int, message: str | None = None, *, payload: dict | None = None):
        super().__init__(status_code, message, payload=payload)


class MaxLengthExceeded(HTTPError):
    """Raised when the API reports that a message exceeded maximum allowed length (errcode 40058)."""

    def __init__(self, status_code: int, message: str | None = None, *, payload: dict | None = None):
        super().__init__(status_code, message, payload=payload)


class ClientValidationError(QWSendError):
    """Base class for client-side validation errors raised before making HTTP requests."""


class ClientMaxLengthExceeded(ClientValidationError):
    """Raised when client-side validation detects data exceeding allowed length."""

    def __init__(self, message: str | None = None):
        super().__init__(message)


class ClientLengthBelowMinimum(ClientValidationError):
    """Raised when client-side validation detects uploaded data smaller than allowed minimum."""

    def __init__(self, message: str | None = None):
        super().__init__(message)
