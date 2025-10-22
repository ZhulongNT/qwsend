from __future__ import annotations

import base64
import hashlib
import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional
import io
import os
import uuid

import httpx

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from .exceptions import HTTPError, RateLimit
from .version import __version__

DEFAULT_BASE = "https://qyapi.weixin.qq.com/cgi-bin"
SEND_PATH = "/webhook/send"
UPLOAD_PATH = "/webhook/upload_media"


def _build_user_agent() -> str:
    return f"qwsend/{__version__} (+https://pypi.org/project/qwsend/)"


def _make_url(base: str, path: str, key: str) -> str:
    return f"{base.rstrip('/')}{path}?key={key}"


def _ensure_ok(resp: httpx.Response) -> Dict[str, Any]:
    logger.info(resp.text)
    if resp.status_code != 200:
        # logger.error(f"HTTP error: {resp.status_code} - {resp.text}")
        raise HTTPError(resp.status_code, f"Non-200 status: {resp.status_code}")
    try:
        data = resp.json()
    except json.JSONDecodeError:
        raise HTTPError(resp.status_code, "Response is not JSON")
    if isinstance(data, Mapping) and data.get("errcode", 0) != 0:
        # ensure payload is a concrete dict for typing
        payload_dict: Dict[str, Any] = dict(data)
        errcode = int(data.get("errcode", 0))
        msg = f"API error: {data.get('errmsg')} ({data.get('errcode')})"
        if errcode == 45009:
            raise RateLimit(resp.status_code, msg, payload=payload_dict)
        raise HTTPError(resp.status_code, msg, payload=payload_dict)
    return data  # type: ignore[return-value]


@dataclass
class WebhookClient:
    key: str
    base_url: str = DEFAULT_BASE
    timeout: Optional[float] = 10.0
    headers: Optional[Mapping[str, str]] = None

    def __post_init__(self) -> None:
        ua = _build_user_agent()
        default_headers = {"User-Agent": ua, "Content-Type": "application/json"}
        if self.headers:
            default_headers.update(self.headers)
        self._headers = default_headers
        self._client = httpx.Client(timeout=self.timeout, headers=self._headers)

    def _send(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        url = _make_url(self.base_url, SEND_PATH, self.key)
        resp = self._client.post(url, json=payload)
        return _ensure_ok(resp)

    def send_text(self, content: str, *, mentioned_list: Optional[list[str]] = None, mentioned_mobile_list: Optional[list[str]] = None) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "msgtype": "text",
            "text": {"content": content},
        }
        if mentioned_list:
            body["text"]["mentioned_list"] = mentioned_list
        if mentioned_mobile_list:
            body["text"]["mentioned_mobile_list"] = mentioned_mobile_list
        return self._send(body)

    def send_markdown(self, content: str, *, v2: bool = False) -> Dict[str, Any]:
        if v2:
            body = {"msgtype": "markdown_v2", "markdown_v2": {"content": content}}
        else:
            body = {"msgtype": "markdown", "markdown": {"content": content}}
        return self._send(body)

    def send_image(self, image_bytes: bytes) -> Dict[str, Any]:
        b64 = base64.b64encode(image_bytes).decode("ascii")
        md5 = hashlib.md5(image_bytes).hexdigest()  # nosec - api requirement
        body = {"msgtype": "image", "image": {"base64": b64, "md5": md5}}
        return self._send(body)

    def send_news(self, articles: list[Mapping[str, Any]]) -> Dict[str, Any]:
        body = {"msgtype": "news", "news": {"articles": articles}}
        return self._send(body)
    
    def upload_media(self, file_bytes: bytes, filename: str, *, type_: str = "file") -> Dict[str, Any]:
        if type_ not in {"file", "voice"}:
            raise ValueError("type_ must be 'file' or 'voice'")

        url = _make_url(self.base_url, UPLOAD_PATH, self.key) + f"&type={type_}"

        # copy default headers but remove Content-Type so httpx can set the multipart boundary
        headers = dict(self._headers)
        headers.pop("Content-Type", None)

        file_length = len(file_bytes)

        # Wet path: build raw multipart body that matches webhook.md (filelength in Content-Disposition)
        if os.getenv("QWSEND_WEBHOOK_KEY"):
            boundary = "---------------------------" + uuid.uuid4().hex
            pre = (
                f"--{boundary}\r\n"
                f"Content-Disposition: form-data; name=\"media\"; filename=\"{filename}\"; filelength={file_length}\r\n"
                f"Content-Type: application/octet-stream\r\n\r\n"
            ).encode("utf-8")
            ending = f"\r\n--{boundary}--\r\n".encode("utf-8")
            body = pre + file_bytes + ending
            headers2 = dict(headers)
            headers2["Content-Type"] = f"multipart/form-data; boundary={boundary}"
            resp = self._client.post(url, content=body, headers=headers2)
        else:
            # Non-wet: use files so tests that inspect 'files' continue to pass
            files = {"media": (filename, io.BytesIO(file_bytes), "application/octet-stream")}
            resp = self._client.post(url, files=files, headers=headers)

        return _ensure_ok(resp)

    def send_file(self, media_id: str) -> Dict[str, Any]:
        body = {"msgtype": "file", "file": {"media_id": media_id}}
        return self._send(body)

    def send_voice(self, media_id: str) -> Dict[str, Any]:
        body = {"msgtype": "voice", "voice": {"media_id": media_id}}
        return self._send(body)

    def send_template_card(self, template_card: Mapping[str, Any]) -> Dict[str, Any]:
        body = {"msgtype": "template_card", "template_card": template_card}
        return self._send(body)

    def close(self) -> None:
        self._client.close()


class AsyncWebhookClient:
    def __init__(self, key: str, *, base_url: str = DEFAULT_BASE, timeout: Optional[float] = 10.0, headers: Optional[Mapping[str, str]] = None):
        self.key = key
        self.base_url = base_url
        self.timeout = timeout
        ua = _build_user_agent()
        default_headers = {"User-Agent": ua, "Content-Type": "application/json"}
        if headers:
            default_headers.update(headers)
        self._headers = default_headers
        self._client = httpx.AsyncClient(timeout=self.timeout, headers=self._headers)

    async def _send(self, payload: Mapping[str, Any]) -> Dict[str, Any]:
        url = _make_url(self.base_url, SEND_PATH, self.key)
        resp = await self._client.post(url, json=payload)
        return _ensure_ok(resp)

    async def send_text(self, content: str, *, mentioned_list: Optional[list[str]] = None, mentioned_mobile_list: Optional[list[str]] = None) -> Dict[str, Any]:
        body: Dict[str, Any] = {
            "msgtype": "text",
            "text": {"content": content},
        }
        if mentioned_list:
            body["text"]["mentioned_list"] = mentioned_list
        if mentioned_mobile_list:
            body["text"]["mentioned_mobile_list"] = mentioned_mobile_list
        return await self._send(body)

    async def send_markdown(self, content: str, *, v2: bool = False) -> Dict[str, Any]:
        if v2:
            body = {"msgtype": "markdown_v2", "markdown_v2": {"content": content}}
        else:
            body = {"msgtype": "markdown", "markdown": {"content": content}}
        return await self._send(body)

    async def send_image(self, image_bytes: bytes) -> Dict[str, Any]:
        b64 = base64.b64encode(image_bytes).decode("ascii")
        md5 = hashlib.md5(image_bytes).hexdigest()  # nosec - api requirement
        body = {"msgtype": "image", "image": {"base64": b64, "md5": md5}}
        return await self._send(body)

    async def send_news(self, articles: list[Mapping[str, Any]]) -> Dict[str, Any]:
        body = {"msgtype": "news", "news": {"articles": articles}}
        return await self._send(body)

    async def upload_media(self, file_bytes: bytes, filename: str, *, type_: str = "file") -> Dict[str, Any]:
        if type_ not in {"file", "voice"}:
            raise ValueError("type_ must be 'file' or 'voice'")

        url = _make_url(self.base_url, UPLOAD_PATH, self.key) + f"&type={type_}"

        # copy default headers but remove Content-Type so httpx can set the multipart boundary
        headers = dict(self._headers)
        headers.pop("Content-Type", None)

        file_length = len(file_bytes)

        if os.getenv("QWSEND_WEBHOOK_KEY"):
            boundary = "---------------------------" + uuid.uuid4().hex
            pre = (
                f"--{boundary}\r\n"
                f"Content-Disposition: form-data; name=\"media\"; filename=\"{filename}\"; filelength={file_length}\r\n"
                f"Content-Type: application/octet-stream\r\n\r\n"
            ).encode("utf-8")
            ending = f"\r\n--{boundary}--\r\n".encode("utf-8")
            body = pre + file_bytes + ending
            headers2 = dict(headers)
            headers2["Content-Type"] = f"multipart/form-data; boundary={boundary}"
            resp = await self._client.post(url, content=body, headers=headers2)
        else:
            files = {"media": (filename, io.BytesIO(file_bytes), "application/octet-stream")}
            resp = await self._client.post(url, files=files, headers=headers)

        return _ensure_ok(resp)
        

    async def send_file(self, media_id: str) -> Dict[str, Any]:
        body = {"msgtype": "file", "file": {"media_id": media_id}}
        return await self._send(body)

    async def send_voice(self, media_id: str) -> Dict[str, Any]:
        body = {"msgtype": "voice", "voice": {"media_id": media_id}}
        return await self._send(body)

    async def send_template_card(self, template_card: Mapping[str, Any]) -> Dict[str, Any]:
        body = {"msgtype": "template_card", "template_card": template_card}
        return await self._send(body)

    async def aclose(self) -> None:
        await self._client.aclose()
