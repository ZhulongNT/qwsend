from __future__ import annotations

import argparse
import os
import sys
from typing import Optional
import json

from .client import WebhookClient


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="qwsend", description="Send messages to WeCom webhook")
    p.add_argument("--key", dest="key", help="webhook key (or set QWSEND_WEBHOOK_KEY)")

    sub = p.add_subparsers(dest="command", required=True, help="sub-command to run")

    # text
    t = sub.add_parser("text", help="send a text message")
    t.add_argument("content", help="message content")
    t.add_argument("--mention", dest="mentioned_list", action="append", help="mentioned user id (can be repeated)")
    t.add_argument("--mention-mobile", dest="mentioned_mobile_list", action="append", help="mentioned mobile (can be repeated)")

    # markdown
    m = sub.add_parser("markdown", help="send markdown message")
    # content can be provided either as a positional or via -f/--file
    m.add_argument("content", nargs="?", help="markdown content")
    m.add_argument("--file", "-f", dest="file", help="path to markdown file")
    m.add_argument("--v2", dest="v2", action="store_true", help="use markdown_v2")

    # image
    img = sub.add_parser("image", help="send an image from file")
    img.add_argument("--file", "-f", required=True, help="path to image file")

    # news (articles JSON file)
    news = sub.add_parser("news", help="send news (articles JSON file)")
    news.add_argument("--file", "-f", required=True, help="path to JSON file containing articles list")

    # upload media (removed) — use `file` or `voice` subcommands which upload then send

    # send file by uploading file then sending
    sf = sub.add_parser("file", help="upload a file and send it")
    sf.add_argument("--file", "-f", required=True, help="path to file to upload and send")

    # send voice by uploading file then sending
    sv = sub.add_parser("voice", help="upload a voice file and send it")
    sv.add_argument("--file", "-f", required=True, help="path to voice file to upload and send")

    # template card
    tc = sub.add_parser("template-card", help="send a template_card JSON file")
    tc.add_argument("--file", "-f", required=True, help="path to JSON file containing template_card mapping")

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
        # dispatch subcommands
        if ns.command == "text":
            resp = client.send_text(ns.content, mentioned_list=ns.mentioned_list, mentioned_mobile_list=ns.mentioned_mobile_list)
            print(json.dumps(resp, ensure_ascii=False, indent=2))
        elif ns.command == "markdown":
            # allow content from positional or from a file
            md_content = ns.content
            if getattr(ns, "file", None):
                try:
                    with open(ns.file, "r", encoding="utf-8") as fh:
                        md_content = fh.read()
                except OSError as e:
                    parser.error(f"cannot read file: {e}")
                    return 2
            if not md_content:
                parser.error("either markdown content or --file is required")
                return 2
            resp = client.send_markdown(md_content, v2=bool(ns.v2))
            print(json.dumps(resp, ensure_ascii=False, indent=2))
        elif ns.command == "image":
            try:
                with open(ns.file, "rb") as fh:
                    b = fh.read()
            except OSError as e:
                parser.error(f"cannot read file: {e}")
                return 2
            resp = client.send_image(b)
            print(json.dumps(resp, ensure_ascii=False, indent=2))
        elif ns.command == "news":
            try:
                with open(ns.file, "r", encoding="utf-8") as fh:
                    articles = json.load(fh)
            except (OSError, json.JSONDecodeError) as e:
                parser.error(f"cannot read/parse JSON file: {e}")
                return 2
            resp = client.send_news(articles)
            print(json.dumps(resp, ensure_ascii=False, indent=2))
        # upload command intentionally disabled in favor of combined file/voice flows
        # elif ns.command == "upload":
        #     try:
        #         with open(ns.file, "rb") as fh:
        #             b = fh.read()
        #     except OSError as e:
        #         parser.error(f"cannot read file: {e}")
        #         return 2
        #     resp = client.upload_media(b, filename=ns.file.split("\\")[-1], type_=ns.type_)
        #     print(json.dumps(resp, ensure_ascii=False, indent=2))
        elif ns.command == "file":
            try:
                with open(ns.file, "rb") as fh:
                    b = fh.read()
            except OSError as e:
                parser.error(f"cannot read file: {e}")
                return 2
            # upload as type 'file' then send
            up = client.upload_media(b, filename=ns.file.split("\\")[-1], type_="file")
            media_id = up.get("media_id") if isinstance(up, dict) else None
            if not media_id:
                print(json.dumps(up, ensure_ascii=False, indent=2))
                return 1
            resp = client.send_file(media_id)
            print(json.dumps(resp, ensure_ascii=False, indent=2))
        elif ns.command == "voice":
            try:
                with open(ns.file, "rb") as fh:
                    b = fh.read()
            except OSError as e:
                parser.error(f"cannot read file: {e}")
                return 2
            # upload as type 'voice' then send
            up = client.upload_media(b, filename=ns.file.split("\\")[-1], type_="voice")
            media_id = up.get("media_id") if isinstance(up, dict) else None
            if not media_id:
                print(json.dumps(up, ensure_ascii=False, indent=2))
                return 1
            resp = client.send_voice(media_id)
            print(json.dumps(resp, ensure_ascii=False, indent=2))
        elif ns.command == "template-card":
            try:
                with open(ns.file, "r", encoding="utf-8") as fh:
                    template = json.load(fh)
            except (OSError, json.JSONDecodeError) as e:
                parser.error(f"cannot read/parse JSON file: {e}")
                return 2
            resp = client.send_template_card(template)
            print(json.dumps(resp, ensure_ascii=False, indent=2))
        else:
            parser.error("unknown command")
            return 2
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
