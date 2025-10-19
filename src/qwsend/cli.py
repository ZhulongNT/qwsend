from __future__ import annotations

import argparse
import os
import sys
from typing import Optional

from .client import WebhookClient


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="qwsend", description="Send messages to WeCom webhook")
    p.add_argument("content", help="message content")
    p.add_argument("--key", dest="key", help="webhook key (or set QWSEND_WEBHOOK_KEY)")
    p.add_argument("--markdown", action="store_true", help="send as markdown")
    p.add_argument("--markdown-v2", action="store_true", dest="markdown_v2", help="send as markdown_v2")
    return p


def main(argv: Optional[list[str]] = None) -> int:
    parser = _build_parser()
    ns = parser.parse_args(argv)
    key = ns.key or os.getenv("QWSEND_WEBHOOK_KEY")
    if not key:
        parser.error("--key or environment variable QWSEND_WEBHOOK_KEY is required")
        return 2
    client = WebhookClient(key)
    try:
        if ns.markdown_v2:
            client.send_markdown(ns.content, v2=True)
        elif ns.markdown:
            client.send_markdown(ns.content)
        else:
            client.send_text(ns.content)
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
