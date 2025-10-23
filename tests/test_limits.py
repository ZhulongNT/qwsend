import os
import logging
from unittest.mock import patch

import pytest
import httpx

from qwsend.client import WebhookClient, TEXT_MAX, MARKDOWN_MAX, MIN_UPLOAD_BYTES
from qwsend.exceptions import ClientMaxLengthExceeded, MaxLengthExceeded, ClientLengthBelowMinimum


IS_WET = bool(os.getenv("QWSEND_WEBHOOK_KEY"))


class DummyResp:
    def __init__(self, status_code=200, data=None, text=None):
        self.status_code = status_code
        self._data = data or {"errcode": 0, "errmsg": "ok"}
        self.text = text or ("{" + '"errcode":0,"errmsg":"ok"' + "}")

    def json(self):
        return self._data


@pytest.mark.skipif(IS_WET, reason="Skip client-local tests in wet mode")
def test_markdown_too_long_raises_client():
    client = WebhookClient("dummy")
    too_long = "x" * (MARKDOWN_MAX + 1)
    with pytest.raises(ClientMaxLengthExceeded):
        client.send_markdown(too_long)


@pytest.mark.skipif(IS_WET, reason="Skip client-local tests in wet mode")
def test_text_over_limit_logs_warning(caplog):
    caplog.set_level(logging.WARNING)
    client = WebhookClient("dummy")
    long_text = "a" * (TEXT_MAX + 10)
    with patch.object(httpx.Client, "post", return_value=DummyResp()):
        client.send_text(long_text)
    # ensure a warning was logged about truncation
    assert any("text.content" in rec.getMessage() or "exceeds limit" in rec.getMessage() for rec in caplog.records)


@pytest.mark.skipif(IS_WET, reason="Skip client-local tests in wet mode")
def test_upload_too_small_raises_client():
    client = WebhookClient("dummy")
    small = b"x" * (MIN_UPLOAD_BYTES - 1)
    with pytest.raises(ClientLengthBelowMinimum):
        client.upload_media(small, "tiny.txt", type_="file")


@pytest.mark.skipif(IS_WET, reason="Skip client-local tests in wet mode")
def test_server_returns_40058_raises_server_exception():
    client = WebhookClient("dummy")

    def side_effect(url, *args, **kwargs):
        return DummyResp(data={"errcode": 40058, "errmsg": "message too long"})

    with patch.object(httpx.Client, "post", side_effect=side_effect):
        with pytest.raises(MaxLengthExceeded):
            # send_file doesn't perform client-side length checks, so server response triggers
            client.send_file("MID")
