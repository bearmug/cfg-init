#!/usr/bin/env python3
"""Evaluate real loopback System One services; retain response identity and usage."""
import argparse
import json
import os
from pathlib import Path
import time
from urllib.parse import urlparse
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True, help="API root, without /v1/systemone")
    parser.add_argument("--model", required=True, help="Accepted server model id/alias, not a revision suffix")
    parser.add_argument("--selector", required=True, help="Unique report identity for this pinned trial")
    parser.add_argument("--response-model", required=True, help="Exact expected model field in responses")
    parser.add_argument("--routing-model", help="Exact routing.model when the server auto-routes checkpoints")
    parser.add_argument("--fixture", default=str(Path(__file__).with_name("fixtures.jsonl")))
    parser.add_argument("--out", required=True)
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--max-len", type=int, help="Laya token budget; not part of the portable System One schema")
    args = parser.parse_args()
    if urlparse(args.url).hostname not in ("127.0.0.1", "localhost"):
        parser.error("Local trials must use loopback endpoints")
    if Path(args.fixture).resolve() == Path(args.out).resolve():
        parser.error("Output must not overwrite fixtures")
    headers = {"Content-Type": "application/json"}
    if os.environ.get("OMP_LOCAL_API_KEY"):
        headers["Authorization"] = "Bearer " + os.environ["OMP_LOCAL_API_KEY"]
    failures = 0
    with open(args.fixture, encoding="utf-8") as source, open(args.out, "w", encoding="utf-8") as output:
        for line in source:
            if not line.strip():
                continue
            fixture = json.loads(line)
            payload = {"state": fixture["state"], "questions": fixture["questions"], "model": args.model}
            if args.max_len is not None:
                payload["max_len"] = args.max_len
            request = Request(args.url.rstrip("/") + "/v1/systemone", data=json.dumps(payload).encode(),
                              headers=headers, method="POST")
            started = time.perf_counter()
            row = {"id": fixture["id"], "selector": args.selector, "native": True, "api": "typesafe"}
            try:
                with urlopen(request, timeout=args.timeout) as response:
                    body = json.load(response)
                row.update(model=body.get("model"), responseModel=body.get("model"),
                           routing=body.get("routing"), answers=body["answers"], usage=body.get("usage", {}))
                if body.get("model") != args.response_model:
                    raise ValueError("Unexpected response model: " + str(body.get("model")))
                if args.routing_model and (body.get("routing") or {}).get("model") != args.routing_model:
                    raise ValueError("Unexpected checkpoint routing: " + str(body.get("routing")))
            except Exception as error:
                failures += 1
                row["error"] = str(error)
            row["elapsedMs"] = round((time.perf_counter() - started) * 1000, 3)
            output.write(json.dumps(row, ensure_ascii=False) + "\n")
            output.flush()
    return int(failures > 0)


if __name__ == "__main__":
    raise SystemExit(main())
