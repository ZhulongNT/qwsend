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

The CLI now uses subcommands to select the message type. Set the key either via `--key` or the environment variable `QWSEND_WEBHOOK_KEY`.

Examples (PowerShell):

```powershell
# set env once for the session
$env:QWSEND_WEBHOOK_KEY = "<your_key>"

# text
qwsend text "hello from CLI"

# text with mentions (repeatable)
qwsend text "hi" --mention user1 --mention user2

# markdown (use --v2 for markdown_v2)
qwsend markdown "**markdown**" --v2

# send image from file
qwsend image -f .\path\to\image.jpg

# send news from a JSON file containing an articles list
qwsend news -f .\path\to\articles.json

# upload a file (returns media_id in response)
qwsend upload -f .\path\to\file.pdf --type file

# send a file or voice by media_id
qwsend send-file <media_id>
qwsend send-voice <media_id>

# send template_card from a JSON file
qwsend template-card -f .\path\to\template.json
```

## User-Agent

The client uses a UA like: `qwsend/0.1.0 (+https://pypi.org/project/qwsend/)`.

## Tests

- Dry tests: run without network (recommended during development)
- Wet tests: live webhook calls — enabled when `QWSEND_WEBHOOK_KEY` is set in your environment. When that variable is set, running `pytest` will execute wet tests. There is no separate `-m wet` tag required now.

```bash
# run dry-only tests
pytest
# run all tests (will include wet/live tests if QWSEND_WEBHOOK_KEY is set)
export QWSEND_WEBHOOK_KEY="fakexxxx-7aoc-4bc4-97a0-0ec2sifa5aaa"
pytest
```

## Packaging

This project uses `pyproject.toml` with setuptools. Build and publish:

```bash
python -m build
python -m twine upload dist/*
```

## License

MIT
