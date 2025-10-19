import json
import os
from unittest.mock import patch

import httpx

from qwsend.client import WebhookClient, _build_user_agent


class DummyResp:
    def __init__(self, status_code=200, data=None):
        self.status_code = status_code
        self._data = data or {"errcode": 0, "errmsg": "ok"}

    def json(self):
        return self._data


def test_user_agent_contains_name_and_version():
    ua = _build_user_agent()
    assert ua.startswith("qwsend/")
    assert "pypi.org" in ua


def test_send_text_payload():
    client = WebhookClient("dummy")
    with patch.object(httpx.Client, "post", return_value=DummyResp()) as m:
        client.send_text("hello", mentioned_list=["@all"]) 
    args, kwargs = m.call_args
    assert "webhook/send" in args[0]
    assert kwargs["json"]["msgtype"] == "text"
    assert kwargs["json"]["text"]["content"] == "hello"
    assert kwargs["json"]["text"]["mentioned_list"] == ["@all"]


def test_send_markdown_v2_payload():
    client = WebhookClient("dummy")
    with patch.object(httpx.Client, "post", return_value=DummyResp()) as m:
        client.send_markdown("# title", v2=True)
    args, kwargs = m.call_args
    assert kwargs["json"]["msgtype"] == "markdown_v2"
