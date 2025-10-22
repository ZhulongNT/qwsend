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
