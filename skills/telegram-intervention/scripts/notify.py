#!/usr/bin/env python3
"""Send a plain-text alert using credentials supplied by the execution environment."""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("event", choices=("blocked", "done"))
    parser.add_argument("--force", action="store_true", help="send an explicitly requested completion alert")
    args = parser.parse_args()
    if args.event == "done" and not args.force and os.environ.get("TELEGRAM_NOTIFY_DONE") != "1":
        print("Completion notification disabled (TELEGRAM_NOTIFY_DONE is not 1).")
        return 0

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        print("Telegram notification requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.", file=sys.stderr)
        return 1
    text = sys.stdin.read().strip()
    if not text or len(text.encode("utf-16-le")) // 2 > 4096:
        print("Notification must contain 1–4096 UTF-16 units of plain text.", file=sys.stderr)
        return 1
    payload = {"chat_id": chat_id, "text": text, "link_preview_options": {"is_disabled": True}}
    topic = os.environ.get("TELEGRAM_MESSAGE_THREAD_ID")
    if topic:
        try:
            payload["message_thread_id"] = int(topic)
            if payload["message_thread_id"] <= 0:
                raise ValueError
        except ValueError:
            print("TELEGRAM_MESSAGE_THREAD_ID must be a positive integer.", file=sys.stderr)
            return 1
    request = urllib.request.Request(
        "https://api.telegram.org/bot" + token + "/sendMessage",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            result = json.load(response)
        if not isinstance(result, dict) or result.get("ok") is not True:
            print("Telegram rejected the notification.", file=sys.stderr)
            return 1
    except urllib.error.HTTPError as error:
        # Never print exception URLs or response bodies: they may contain secrets.
        print("Telegram notification failed (HTTP %s)." % error.code, file=sys.stderr)
        return 1
    except (urllib.error.URLError, OSError, ValueError):
        print("Telegram notification failed (transport or response error); delivery is unconfirmed.", file=sys.stderr)
        return 1
    print("Telegram accepted the notification.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
