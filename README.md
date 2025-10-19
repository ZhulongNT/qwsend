# qwsend

WeCom (企业微信) webhook client based on httpx with a clear, reusable API. It sets a custom User-Agent built from the project name and version.

- Sync and async clients
- Message types: text, markdown/markdown_v2, image, news, file, voice, template_card
- Media upload helper (file/voice)
- Simple CLI: `qwsend "hello" --key <key>`

## Install

```bash
pip install qwsend
```

## Quick start

```python
from qwsend import WebhookClient

client = WebhookClient(key="<your_key>")
client.send_text("hello world")
client.send_markdown("**bold**")
client.close()
```

Async:

```python
import asyncio
from qwsend import AsyncWebhookClient

async def main():
    client = AsyncWebhookClient(key="<your_key>")
    await client.send_text("hello async")
    await client.aclose()

asyncio.run(main())
```

CLI:

```bash
# PowerShell
$env:QWSEND_WEBHOOK_KEY = "<your_key>"
qwsend "hello from CLI"
qwsend "**markdown**" --markdown
```

## User-Agent

The client uses a UA like: `qwsend/0.1.0 (+https://pypi.org/project/qwsend/)`.

## Tests

- Dry tests: run without network
- Wet tests: live webhook calls, enabled when `QWSEND_WEBHOOK_KEY` is set

```bash
pytest -m "not wet"   # dry only
pytest -m wet          # wet only (requires env)
```

## Packaging

This project uses `pyproject.toml` with setuptools. Build and publish:

```bash
python -m build
python -m twine upload dist/*
```

## License

MIT
