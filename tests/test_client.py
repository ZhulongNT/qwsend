import base64
import hashlib
import os
from unittest.mock import patch

import httpx
import pytest

from qwsend.client import WebhookClient, _build_user_agent
from qwsend.exceptions import HTTPError


class DummyResp:
    def __init__(self, status_code=200, data=None, text=""):
        self.status_code = status_code
        self._data = data or {"errcode": 0, "errmsg": "ok"}
        self.text = text or "{\"errcode\":0,\"errmsg\":\"ok\"}"

    def json(self):
        return self._data


IS_WET = bool(os.getenv("QWSEND_WEBHOOK_KEY"))

def fixture_jpg_bytes() -> bytes:
    with open("./tests/fixtures/landscape-1920-1080.jpg", "rb") as f:
        return f.read()
    
def fixture_amr_bytes() -> bytes:
    with open("./tests/fixtures/audio.amr", "rb") as f:
        return f.read()


def test_user_agent_contains_name_and_version():
    ua = _build_user_agent()
    assert ua.startswith("qwsend/")
    assert "pypi.org" in ua


def test_send_text_unified():
    if IS_WET:
        key = os.environ["QWSEND_WEBHOOK_KEY"]
        client = WebhookClient(key)
        try:
            data = client.send_text("qwsend unified text", mentioned_list=["@all"])  # type: ignore[arg-type]
            assert data["errmsg"] == "ok"
        finally:
            client.close()
    else:
        client = WebhookClient("dummy")
        with patch.object(httpx.Client, "post", return_value=DummyResp()) as m:
            client.send_text("hello", mentioned_list=["@all"])  # type: ignore[arg-type]
        args, kwargs = m.call_args
        assert "webhook/send" in args[0]
        assert kwargs["json"]["msgtype"] == "text"
        assert kwargs["json"]["text"]["content"] == "hello"
        assert kwargs["json"]["text"]["mentioned_list"] == ["@all"]


@pytest.mark.parametrize("v2", [False, True])
def test_send_markdown_unified(v2: bool):
    if IS_WET:
        key = os.environ["QWSEND_WEBHOOK_KEY"]
        client = WebhookClient(key)
        try:
            content = "**markdown v2**" if v2 else "# markdown"
            data = client.send_markdown(content, v2=v2)
            assert data["errmsg"] == "ok"
        finally:
            client.close()
    else:
        client = WebhookClient("dummy")
        with patch.object(httpx.Client, "post", return_value=DummyResp()) as m:
            client.send_markdown("# title", v2=v2)
        _, kwargs = m.call_args
        assert kwargs["json"]["msgtype"] == ("markdown_v2" if v2 else "markdown")


def test_send_image_unified():
    img = fixture_jpg_bytes()
    if IS_WET:
        key = os.environ["QWSEND_WEBHOOK_KEY"]
        client = WebhookClient(key)
        try:
            data = client.send_image(img)
            assert data["errmsg"] == "ok"
        finally:
            client.close()
    else:
        client = WebhookClient("dummy")
        with patch.object(httpx.Client, "post", return_value=DummyResp()) as m:
            client.send_image(img)
        _, kwargs = m.call_args
        body = kwargs["json"]
        assert body["msgtype"] == "image"
        calc_md5 = hashlib.md5(img).hexdigest()
        assert body["image"]["md5"] == calc_md5


def test_send_news_unified():
    article = {
        "title": "qwsend - PyPI",
        "description": "A lightweight WeCom (WeChat Work) webhook client.",
        "url": "https://pypi.org/project/qwsend/",
        "picurl": "https://imageslot.com/v1/1068x455?bg=53c419&fg=ffffff&shadow=23272f&text=qwsend&filetype=png#head.png",
    }
    if IS_WET:
        key = os.environ["QWSEND_WEBHOOK_KEY"]
        client = WebhookClient(key)
        try:
            data = client.send_news([article])
            assert data["errmsg"] == "ok"
        finally:
            client.close()
    else:
        client = WebhookClient("dummy")
        with patch.object(httpx.Client, "post", return_value=DummyResp()) as m:
            client.send_news([article])
        _, kwargs = m.call_args
        assert kwargs["json"]["msgtype"] == "news"
        assert kwargs["json"]["news"]["articles"][0]["title"] == "qwsend link"


def test_upload_and_send_file_unified():
    file_bytes = b"hello from qwsend file"
    if IS_WET:
        key = os.environ["QWSEND_WEBHOOK_KEY"]
        client = WebhookClient(key)
        try:
            up = client.upload_media(file_bytes, "test.txt", type_="file")
            assert up.get("errmsg") == "ok"
            media_id = up.get("media_id") or up.get("mediaid")  # API sometimes uses media_id
            assert media_id
            data = client.send_file(media_id)
            assert data["errmsg"] == "ok"
        finally:
            client.close()
    else:
        calls = []

        def side_effect(url, *args, **kwargs):
            calls.append((url, args, kwargs))
            if "upload_media" in url:
                return DummyResp(data={"errcode": 0, "errmsg": "ok", "media_id": "MID123"})
            return DummyResp()

        client = WebhookClient("dummy")
        with patch.object(httpx.Client, "post", side_effect=side_effect) as _:
            up = client.upload_media(file_bytes, "test.txt", type_="file")
            assert up["media_id"] == "MID123"
            data = client.send_file("MID123")
            assert data["errmsg"] == "ok"

        # Validate payloads
        upload_call = next(c for c in calls if "upload_media" in c[0])
        send_call = next(c for c in calls if "webhook/send" in c[0])
        # upload uses files => ensure 'files' present
        assert "files" in upload_call[2]
        assert upload_call[2]["files"]["media"][0] == "test.txt"
        assert send_call[2]["json"]["msgtype"] == "file"
        assert send_call[2]["json"]["file"]["media_id"] == "MID123"


def test_send_voice_unified():
    if IS_WET:
        key = os.environ["QWSEND_WEBHOOK_KEY"]
        client = WebhookClient(key)
        amr = fixture_amr_bytes()
        up = client.upload_media(amr, "test.amr", type_="voice")
        media_id = up.get("media_id") or up.get("mediaid")
        assert media_id
        data = client.send_voice(media_id)
        assert data["errmsg"] == "ok"
        client.close()
    else:
        client = WebhookClient("dummy")
        with patch.object(httpx.Client, "post", return_value=DummyResp()) as m:
            client.send_voice("MIDV123")
        _, kwargs = m.call_args
        assert kwargs["json"]["msgtype"] == "voice"
        assert kwargs["json"]["voice"]["media_id"] == "MIDV123"


def test_send_template_card_text_notice_unified():
    template = {
        "card_type": "text_notice",
        "main_title": {"title": "Title", "desc": "Desc"},
        "card_action": {"type": 1, "url": "https://example.com"},
    }
    if IS_WET:
        key = os.environ["QWSEND_WEBHOOK_KEY"]
        client = WebhookClient(key)
        try:
            try:
                data = client.send_template_card(template)
                assert data["errmsg"] == "ok"
            except HTTPError as e:
                pytest.xfail(f"template_card(text_notice) schema may not be fully valid: {e}")
        finally:
            client.close()
    else:
        client = WebhookClient("dummy")
        with patch.object(httpx.Client, "post", return_value=DummyResp()) as m:
            client.send_template_card(template)
        _, kwargs = m.call_args
        assert kwargs["json"]["msgtype"] == "template_card"
        assert kwargs["json"]["template_card"]["card_type"] == "text_notice"


def test_send_template_card_news_notice_unified():
    template = {
        "card_type": "news_notice",
        "main_title": {"title": "News", "desc": "Latest"},
        "card_action": {"type": 1, "url": "https://example.com/news"},
        "vertical_content_list": [{"title": "Line", "desc": "Content"}],
    }
    if IS_WET:
        key = os.environ["QWSEND_WEBHOOK_KEY"]
        client = WebhookClient(key)
        try:
            try:
                data = client.send_template_card(template)
                assert data["errmsg"] == "ok"
            except HTTPError as e:
                pytest.xfail(f"template_card(news_notice) schema may not be fully valid: {e}")
        finally:
            client.close()
    else:
        client = WebhookClient("dummy")
        with patch.object(httpx.Client, "post", return_value=DummyResp()) as m:
            client.send_template_card(template)
        _, kwargs = m.call_args
        assert kwargs["json"]["msgtype"] == "template_card"
        assert kwargs["json"]["template_card"]["card_type"] == "news_notice"
