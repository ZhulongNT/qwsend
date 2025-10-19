from __future__ import annotations

class QWSendError(Exception):
    """Base exception for qwsend errors."""


class HTTPError(QWSendError):
    """Raised when HTTP status is not 200 OK or response indicates error."""

    def __init__(self, status_code: int, message: str | None = None, *, payload: dict | None = None):
        self.status_code = status_code
        self.payload = payload
        msg = message or f"HTTP error: {status_code}"
        super().__init__(msg)
