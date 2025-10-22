import base64
import hashlib
import os
from unittest.mock import patch

import httpx
import pytest

from qwsend.client import _build_user_agent
from qwsend import cli
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


def run_cli(argv):
    # run cli.main with argv list, capture exit code
    return cli.main(argv)


def test_user_agent_contains_name_and_version():
    ua = _build_user_agent()
    assert ua.startswith("qwsend/")
    assert "pypi.org" in ua


def test_send_text_cli():
    if IS_WET:
        key = os.environ["QWSEND_WEBHOOK_KEY"]
        rc = run_cli(["--key", key, "text", "qwsend unified text", "--mention", "@all"])  # type: ignore[arg-type]
        assert rc == 0
    else:
        with patch.object(httpx.Client, "post", return_value=DummyResp()) as m:
            rc = run_cli(["--key", "dummy", "text", "hello", "--mention", "@all"])  # type: ignore[arg-type]
            assert rc == 0
        args, kwargs = m.call_args
        assert "webhook/send" in args[0]
        assert kwargs["json"]["msgtype"] == "text"
        assert kwargs["json"]["text"]["content"] == "hello"
        assert kwargs["json"]["text"]["mentioned_list"] == ["@all"]


@pytest.mark.parametrize("v2", [False, True])
def test_send_markdown_cli(v2: bool):
    flag = ["--v2"] if v2 else []
    if IS_WET:
        key = os.environ["QWSEND_WEBHOOK_KEY"]
        rc = run_cli(["--key", key, "markdown", "# title"] + flag)
        assert rc == 0
    else:
        with patch.object(httpx.Client, "post", return_value=DummyResp()) as m:
            rc = run_cli(["--key", "dummy", "markdown", "# title"] + flag)
            assert rc == 0
        _, kwargs = m.call_args
        assert kwargs["json"]["msgtype"] == ("markdown_v2" if v2 else "markdown")


def test_send_image_cli():
    img = fixture_jpg_bytes()
    # write a temp file
    p = "tests/.tmp_image.jpg"
    with open(p, "wb") as f:
        f.write(img)
    try:
        if IS_WET:
            key = os.environ["QWSEND_WEBHOOK_KEY"]
            rc = run_cli(["--key", key, "image", "-f", p])
            assert rc == 0
        else:
            with patch.object(httpx.Client, "post", return_value=DummyResp()) as m:
                rc = run_cli(["--key", "dummy", "image", "-f", p])
                assert rc == 0
            _, kwargs = m.call_args
            body = kwargs["json"]
            assert body["msgtype"] == "image"
            calc_md5 = hashlib.md5(img).hexdigest()
            assert body["image"]["md5"] == calc_md5
    finally:
        try:
            os.remove(p)
        except Exception:
            pass


def test_send_markdown_from_file_cli():
    # create a temp markdown file
    p = "tests/.tmp_markdown.md"
    md = "# Hello\n\nThis is a test markdown file."
    with open(p, "w", encoding="utf-8") as f:
        f.write(md)
    try:
        if IS_WET:
            key = os.environ["QWSEND_WEBHOOK_KEY"]
            rc = run_cli(["--key", key, "markdown", "-f", p])
            assert rc == 0
        else:
            with patch.object(httpx.Client, "post", return_value=DummyResp()) as m:
                rc = run_cli(["--key", "dummy", "markdown", "-f", p])
                assert rc == 0
            _, kwargs = m.call_args
            assert kwargs["json"]["msgtype"] == "markdown"
            assert "Hello" in kwargs["json"]["markdown"]["content"]
    finally:
        try:
            os.remove(p)
        except Exception:
            pass


def test_send_news_cli():
    article = {
        "title": "qwsend - PyPI",
        "description": "A lightweight WeCom (WeChat Work) webhook client.",
        "url": "https://pypi.org/project/qwsend/",
        "picurl": "https://imageslot.com/v1/1068x455?bg=53c419&fg=ffffff&shadow=23272f&text=qwsend&filetype=png#head.png",
    }
    # write temp json
    import json
    p = "tests/.tmp_articles.json"
    with open(p, "w", encoding="utf-8") as f:
        json.dump([article], f)
    try:
        if IS_WET:
            key = os.environ["QWSEND_WEBHOOK_KEY"]
            rc = run_cli(["--key", key, "news", "-f", p])
            assert rc == 0
        else:
            with patch.object(httpx.Client, "post", return_value=DummyResp()) as m:
                rc = run_cli(["--key", "dummy", "news", "-f", p])
                assert rc == 0
            _, kwargs = m.call_args
            assert kwargs["json"]["msgtype"] == "news"
            assert kwargs["json"]["news"]["articles"][0]["title"] == "qwsend link"
    finally:
        try:
            os.remove(p)
        except Exception:
            pass


def test_file_upload_and_send_cli():
    file_bytes = b"hello from qwsend file"
    p = "tests/.tmp_file.txt"
    with open(p, "wb") as f:
        f.write(file_bytes)
    try:
        if IS_WET:
            key = os.environ["QWSEND_WEBHOOK_KEY"]
            rc = run_cli(["--key", key, "file", "-f", p])
            assert rc == 0
        else:
            calls = []

            def side_effect(url, *args, **kwargs):
                calls.append((url, args, kwargs))
                if "upload_media" in url:
                    return DummyResp(data={"errcode": 0, "errmsg": "ok", "media_id": "MID123"})
                return DummyResp()

            with patch.object(httpx.Client, "post", side_effect=side_effect) as m:
                rc = run_cli(["--key", "dummy", "file", "-f", p])
                assert rc == 0

            upload_call = next(c for c in calls if "upload_media" in c[0])
            send_call = next(c for c in calls if "webhook/send" in c[0])
            assert "files" in upload_call[2]
            assert upload_call[2]["files"]["media"][0] == "tests/.tmp_file.txt"
            assert send_call[2]["json"]["msgtype"] == "file"
            assert send_call[2]["json"]["file"]["media_id"] == "MID123"
    finally:
        try:
            os.remove(p)
        except Exception:
            pass


def test_voice_upload_and_send_cli():
    # create small amr
    amr = fixture_amr_bytes()
    p = "tests/.tmp_audio.amr"
    with open(p, "wb") as f:
        f.write(amr)
    try:
        if IS_WET:
            key = os.environ["QWSEND_WEBHOOK_KEY"]
            rc = run_cli(["--key", key, "voice", "-f", p])
            assert rc == 0
        else:
                calls = []

                def side_effect(url, *args, **kwargs):
                    calls.append((url, args, kwargs))
                    if "upload_media" in url:
                        return DummyResp(data={"errcode": 0, "errmsg": "ok", "media_id": "MIDV123"})
                    return DummyResp()

                with patch.object(httpx.Client, "post", side_effect=side_effect) as m:
                    rc = run_cli(["--key", "dummy", "voice", "-f", p])
                    assert rc == 0

                send_call = next(c for c in calls if "webhook/send" in c[0])
                assert send_call[2]["json"]["msgtype"] == "voice"
                assert send_call[2]["json"]["voice"]["media_id"] == "MIDV123"
    finally:
        try:
            os.remove(p)
        except Exception:
            pass


def test_template_card_cli():
    template = {
        "card_type": "text_notice",
        "main_title": {"title": "Title", "desc": "Desc"},
        "card_action": {"type": 1, "url": "https://example.com"},
    }
    with open("tests/.tmp_template.json", "w", encoding="utf-8") as f:
        import json
        json.dump(template, f)
    if IS_WET:
        key = os.environ["QWSEND_WEBHOOK_KEY"]
        rc = run_cli(["--key", key, "template-card", "-f", "tests/.tmp_template.json"]) 
        assert rc == 0
    else:
        import json
        p = "tests/.tmp_template.json"
        with open(p, "w", encoding="utf-8") as f:
            json.dump(template, f)
        try:
            with patch.object(httpx.Client, "post", return_value=DummyResp()) as m:
                rc = run_cli(["--key", "dummy", "template-card", "-f", p])
                assert rc == 0
            _, kwargs = m.call_args
            assert kwargs["json"]["msgtype"] == "template_card"
            assert kwargs["json"]["template_card"]["card_type"] == "text_notice"
        finally:
            try:
                os.remove(p)
            except Exception:
                pass
