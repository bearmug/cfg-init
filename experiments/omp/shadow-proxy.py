#!/usr/bin/env python3
"""Temporary always-remote Jev proxy with best-effort local Decider shadowing."""
import argparse
import asyncio
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import stat
import time
from urllib.parse import urlparse
import uuid

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import Response
import uvicorn

LOCAL_MODEL = "decider-0.8b-v1"
REMOTE_MODEL = "jev-latest"


def _certainty(answer):
    if not isinstance(answer, dict):
        return None
    kind = answer.get("type")
    if kind == "choice":
        probabilities = answer.get("probabilities")
        value = probabilities.get(answer.get("choice")) if isinstance(probabilities, dict) else None
        return value if _unit(value) else None
    if kind in ("binary", "bool", "noul"):
        probability = answer.get("noul") if kind == "noul" else answer.get("probability")
        if _unit(probability):
            return max(probability, 1 - probability)
    if kind == "score":
        distribution = answer.get("probabilities")
        if isinstance(distribution, dict):
            values = list(distribution.values())
            if values and all(_unit(value) for value in values):
                return max(values)
    return None


def _unit(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and 0 <= value <= 1


def _agreement(left, right, kind):
    if kind == "choice":
        a, b = left.get("choice"), right.get("choice")
        return a == b if isinstance(a, str) and isinstance(b, str) else None
    if kind in ("binary", "bool", "noul"):
        def side(answer):
            p = answer.get("noul") if kind == "noul" else answer.get("probability")
            return p >= 0.5 if _unit(p) else answer.get("selected")
        a, b = side(left), side(right)
        return a == b if a is not None and b is not None else None
    return None


def _usage(answer):
    usage = answer.get("usage") if isinstance(answer, dict) else None
    if not isinstance(usage, dict):
        return {"input": None, "output": None, "cost": None}
    cost = usage.get("cost")
    if isinstance(cost, dict):
        cost = cost.get("total")
    return {"input": _number(usage.get("input", usage.get("input_tokens", usage.get("prompt_tokens")))),
            "output": _number(usage.get("output", usage.get("output_tokens", usage.get("completion_tokens")))),
            "cost": _number(cost)}


def _number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def _category(status):
    return "ok" if 200 <= status < 300 else f"http_{status}"


def _status(status, active=True):
    return _category(status) if status is not None else ("expired" if not active else "invalid")


def _answers(body):
    return body.get("answers") if isinstance(body, dict) and isinstance(body.get("answers"), dict) else {}


def create_app(local_url, remote_url, stats_path, until):
    local_endpoint = local_url.rstrip("/") + "/v1/systemone"
    remote_endpoint = remote_url.rstrip("/") + "/v1/systemone"
    lock = asyncio.Lock()
    stats_failures = 0

    async def append_row(row):
        nonlocal stats_failures
        try:
            encoded = (json.dumps(row, separators=(",", ":"), allow_nan=False) + "\n").encode()
            async with lock:
                fd = os.open(stats_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
                try:
                    os.write(fd, encoded)
                finally:
                    os.close(fd)
        except Exception:
            stats_failures += 1

    app = FastAPI()
    app.state.stats_failures = lambda: stats_failures

    @app.get("/health")
    async def health():
        return {"ok": True, "localModel": LOCAL_MODEL, "remoteModel": REMOTE_MODEL,
                "localEndpoint": local_endpoint, "remoteEndpoint": remote_endpoint,
                "statsWriteFailures": stats_failures}

    @app.get("/v1/models")
    async def models(request: Request):
        authorization = request.headers.get("authorization")
        if not authorization:
            return Response(status_code=401)
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                upstream = await client.get(remote_url.rstrip("/") + "/v1/models",
                                            headers={"Authorization": authorization})
        except httpx.TimeoutException:
            return Response(status_code=504)
        except httpx.HTTPError:
            return Response(status_code=502)
        return Response(content=upstream.content, status_code=upstream.status_code,
                        headers={k: v for k, v in upstream.headers.items()
                                 if k.lower() in ("content-type", "cache-control", "retry-after")})

    @app.post("/v1/systemone")
    async def systemone(request: Request):
        authorization = request.headers.get("authorization")
        if not authorization:
            return Response(status_code=401)
        try:
            payload = await request.json()
        except Exception:
            return Response(status_code=400)
        if (not isinstance(payload, dict) or payload.get("state") is None or
                not isinstance(payload.get("questions"), dict)):
            return Response(status_code=400)

        now = datetime.now(timezone.utc)
        raw_body = await request.body()
        active = now < until
        local_result = None
        local_duration = None
        local_status = "expired" if not active else "invalid"
        if active:
            local_payload = dict(payload)
            local_payload["model"] = LOCAL_MODEL
            started = time.perf_counter()
            try:
                async with httpx.AsyncClient(timeout=1.0) as client:
                    response = await client.post(local_endpoint, json=local_payload)
                local_duration = round((time.perf_counter() - started) * 1000, 3)
                local_status = _category(response.status_code)
                if response.is_success:
                    local_result = response.json()
                    if not isinstance(local_result, dict) or local_result.get("model") != LOCAL_MODEL:
                        local_result = None
                        local_status = "invalid"
            except httpx.TimeoutException:
                local_duration = round((time.perf_counter() - started) * 1000, 3)
                local_status = "timeout"
            except httpx.HTTPError:
                local_duration = round((time.perf_counter() - started) * 1000, 3)
                local_status = "network"
            except Exception:
                local_duration = round((time.perf_counter() - started) * 1000, 3)
                local_status = "invalid"

        remote_started = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                remote = await client.post(remote_endpoint, content=raw_body,
                                           headers={"Authorization": authorization,
                                                    "Content-Type": request.headers.get("content-type", "application/json")})
        except httpx.TimeoutException:
            await append_row(_stats_row(payload, local_result, None, active,
                                        datetime.now(timezone.utc), local_duration, local_status,
                                        round((time.perf_counter() - remote_started) * 1000, 3), "timeout"))
            return Response(status_code=504, content=b"", media_type=None)
        except httpx.HTTPError:
            await append_row(_stats_row(payload, local_result, None, active,
                                        datetime.now(timezone.utc), local_duration, local_status,
                                        round((time.perf_counter() - remote_started) * 1000, 3), "network"))
            return Response(status_code=502, content=b"", media_type=None)
        remote_duration = round((time.perf_counter() - remote_started) * 1000, 3)
        remote_json = None
        try:
            remote_json = remote.json()
        except Exception:
            pass
        await append_row(_stats_row(payload, local_result, remote_json, active, now,
                                    local_duration, local_status, remote_duration, _category(remote.status_code)))
        return Response(content=remote.content, status_code=remote.status_code,
                        headers={k: v for k, v in remote.headers.items()
                                 if k.lower() in ("content-type", "cache-control", "retry-after")})

    return app

def _stats_row(payload, local, remote, active, when, local_ms, local_status, remote_ms, remote_status):
    local_answers, remote_answers = _answers(local), _answers(remote)
    local_usage, remote_usage = _usage(local), _usage(remote)
    questions = payload["questions"]
    rows = []
    for ordinal, (key, question) in enumerate(questions.items()):
        kind = question.get("type") if isinstance(question, dict) else None
        la = local_answers.get(key)
        ra = remote_answers.get(key)
        la = la if isinstance(la, dict) and la.get("type") == kind else None
        ra = ra if isinstance(ra, dict) and ra.get("type") == kind else None
        lc, rc = _certainty(la), _certainty(ra)
        ls = _number(la.get("score")) if la else None
        rs = _number(ra.get("score")) if ra else None
        score_delta = abs(ls - rs) if kind == "score" and ls is not None and rs is not None else None
        safe_kind = kind if kind in ("choice", "binary", "bool", "noul", "score") else "unknown"
        rows.append({"ordinal": ordinal, "type": safe_kind,
                     "localCertainty": lc, "remoteCertainty": rc,
                     "agreement": _agreement(la, ra, kind) if lc is not None and rc is not None else None,
                     "scoreAbsDelta": score_delta})
    total_ms = (local_ms or 0) + (remote_ms or 0)
    return {"id": str(uuid.uuid4()), "time": when.isoformat(), "trialActive": active,
            "totalMs": round(total_ms, 3),
            "local": {"model": LOCAL_MODEL, "status": local_status, "ms": local_ms,
                      "inputTokens": local_usage["input"], "outputTokens": local_usage["output"],
                      "cost": None},
            "remote": {"model": REMOTE_MODEL, "status": remote_status, "ms": remote_ms,
                       "inputTokens": remote_usage["input"], "outputTokens": remote_usage["output"],
                       "cost": remote_usage["cost"]},
            "questions": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=18744)
    parser.add_argument("--local-url", default="http://127.0.0.1:18742")
    parser.add_argument("--remote-url", required=True, help="Fixed HTTPS API root (origin, optionally base path)")
    parser.add_argument("--stats", type=Path, required=True)
    parser.add_argument("--until", required=True, help="Trial end timestamp in ISO-8601")
    args = parser.parse_args()
    if args.host not in ("127.0.0.1", "localhost", "::1"):
        parser.error("--host must be a loopback address")
    parsed = urlparse(args.remote_url)
    local_parsed = urlparse(args.local_url)
    if local_parsed.scheme != "http" or local_parsed.hostname not in ("127.0.0.1", "localhost", "::1"):
        parser.error("--local-url must be an HTTP loopback URL")
    if parsed.scheme != "https" or not parsed.netloc or parsed.query or parsed.fragment:
        parser.error("--remote-url must be a fixed HTTPS API root")
    try:
        until = datetime.fromisoformat(args.until.replace("Z", "+00:00"))
        if until.tzinfo is None:
            raise ValueError()
    except ValueError:
        parser.error("--until must be an ISO-8601 timestamp with timezone")
    args.stats.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(args.stats.parent, stat.S_IRWXU)
    if args.stats.exists():
        os.chmod(args.stats, stat.S_IRUSR | stat.S_IWUSR)
    uvicorn.run(create_app(args.local_url, args.remote_url, str(args.stats), until),
                host=args.host, port=args.port, workers=1, access_log=False)


if __name__ == "__main__":
    main()
