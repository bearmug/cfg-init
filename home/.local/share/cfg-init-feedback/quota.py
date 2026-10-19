#!/usr/bin/env python3
"""Quota-aware lane advice from `omp usage --json`: cached snapshot, freshness, safety reserve.

Advisory data source for t3_policy.py and the coordinator. A failed or unparseable reading is
`unknown`, never a crash and never a reason to block delegation.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

try:
    import fcntl
except ImportError:  # pragma: no cover - non-POSIX
    fcntl = None

LEVELS = ("ok", "reduce", "avoid")


def _number(name, default):
    try:
        return float(os.environ.get(name, default))
    except ValueError:
        return float(default)


def settings():
    """Knobs (env vars). Fractions are of each usage window; times are seconds."""
    mode = os.environ.get("T3_QUOTA", "enforce")
    return {
        "mode": mode if mode in ("enforce", "advise", "off") else "enforce",
        "buffer": _number("T3_QUOTA_BUFFER", 0.15),   # reserve kept in every window
        "margin": _number("T3_QUOTA_MARGIN", 0.15),   # reduce band above the reserve
        "ttl": _number("T3_QUOTA_TTL", 600),          # reuse a reading this long
        "ttl_tight": _number("T3_QUOTA_TTL_TIGHT", 180),  # ...or this long near the reserve
        "stale": _number("T3_QUOTA_STALE", 1800),     # older readings gate as unknown
        "retry": _number("T3_QUOTA_RETRY", 120),      # back-off after a failed refresh
        "timeout": _number("T3_QUOTA_TIMEOUT", 8),
    }


def state_dir():
    return Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local/state"))) / "cfg-init-t3"


def provider_of(model):
    return model.split("/", 1)[0] if isinstance(model, str) and "/" in model else None


def _provider_entry(providers, name):
    return providers.setdefault(name, {"fetchedAt": None, "accounts": 0, "blocked": 0,
                                       "resetCredits": 0, "limits": [], "partial": False})


def summarize(report):
    """Keep only routing-relevant numbers; drop metadata (emails, ids, org, plan) and credit ids."""
    providers = {}
    for item in report.get("reports") or []:
        name = item.get("provider")
        if not isinstance(name, str):
            continue
        entry = _provider_entry(providers, name)
        entry["accounts"] += 1
        fetched = item.get("fetchedAt")
        if _num(fetched):
            entry["fetchedAt"] = fetched if entry["fetchedAt"] is None else min(entry["fetchedAt"], fetched)
        else:
            entry["undated"] = True  # never stand in local time for OMP's fetch time
        meta = item.get("metadata") or {}
        if meta.get("limitReached") is True or meta.get("allowed") is False:
            entry["blocked"] += 1
        credits = item.get("resetCredits") or {}
        entry["resetCredits"] += int(credits.get("availableCount") or 0)
        for limit in item.get("limits") or []:
            window = limit.get("window") or {}
            amount = limit.get("amount") or {}
            entry["limits"].append({
                "window": window.get("id") or (limit.get("scope") or {}).get("windowId"),
                "durationMs": window.get("durationMs"), "resetsAt": window.get("resetsAt"),
                "remaining": amount.get("remainingFraction"), "status": limit.get("status")})
    for name, rows in (report.get("capacity") or {}).items():
        entry = _provider_entry(providers, name)
        entry["capacity"] = [{"window": row.get("window"), "meter": row.get("meter"),
                              "durationMs": row.get("durationMs"),
                              "remaining": row["remainingAccounts"] / row["accounts"]}
                             for row in rows or []
                             if _num(row.get("accounts")) and row["accounts"] > 0
                             and _num(row.get("remainingAccounts"))]
    for key in ("accountsWithoutUsage", "disabledCredentials"):
        for item in report.get(key) or []:
            name = item.get("provider") if isinstance(item, dict) else provider_of(item)
            if isinstance(name, str):
                _provider_entry(providers, name)["partial"] = True
    return providers


def _read(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return None


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = path.with_name(path.name + ".%d.tmp" % os.getpid())
    fd = os.open(str(temporary), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(data, stream)
    os.replace(str(temporary), str(path))


def _omp():
    explicit = os.environ.get("T3_OMP_BIN")
    if explicit:
        return explicit
    found = shutil.which("omp")
    fallback = Path.home() / ".local/bin/omp"
    return found or (str(fallback) if fallback.exists() else None)


def _tight(snapshot, config, now):
    """True when any provider sits in the reduce band, so readings refresh more often."""
    try:
        return any(assess(name, snapshot, config, now)["last"] != "ok"
                   for name in (snapshot.get("providers") or {}))
    except Exception:
        return False


def snapshot(config=None, refresh=False, now=None):
    """Cached reading; refreshed when older than its TTL. Never raises."""
    config = config or settings()
    now = time.time() if now is None else now
    path = state_dir() / "quota.json"
    cached = _read(path)
    if not isinstance(cached, dict):
        cached = None
    if cached and not (_num(cached.get("takenAt")) and isinstance(cached.get("providers"), dict)):
        cached = None  # Corrupt cache: refresh as if there were none.
    if cached and not refresh:
        ttl = config["ttl_tight"] if _tight(cached, config, now) else config["ttl"]
        if now - cached["takenAt"] < ttl:
            return cached
        if _num(cached.get("errorAt")) and now - cached["errorAt"] < config["retry"]:
            return cached
    lock = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if fcntl:
            lock = os.fdopen(os.open(str(path.with_name("quota.lock")), os.O_WRONLY | os.O_CREAT, 0o600), "w")
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        if lock:
            lock.close()
        return cached  # Another caller is refreshing; use what exists.
    try:
        binary = _omp()
        if not binary:
            raise RuntimeError("omp not found")
        result = subprocess.run([binary, "usage", "--json", "--redact"], capture_output=True,
                                text=True, timeout=config["timeout"])
        if result.returncode:
            raise RuntimeError("omp usage exit %d" % result.returncode)
        report = json.loads(result.stdout)
        fresh = {"takenAt": now, "providers": summarize(report)}
    except Exception as error:  # Unknown, not a crash: keep the last reading, note the failure.
        fresh = dict(cached or {"takenAt": 0, "providers": {}})
        fresh["error"] = type(error).__name__ + (": " + str(error) if isinstance(error, RuntimeError) else "")
        fresh["errorAt"] = now
    try:
        _write(path, fresh)
    except OSError:
        pass
    finally:
        if lock:
            lock.close()
    return fresh


def _num(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _windows(entry, now):
    """Live windows with headroom. A window any account has reset since the reading is skipped:
    it has fresh capacity and its numbers are outdated. Pool capacity is used when reported."""
    limits = [l for l in entry.get("limits") or [] if _num(l.get("remaining"))]
    capacity = {row.get("window"): row for row in entry.get("capacity") or [] if _num(row.get("remaining"))}
    windows = []
    for name in sorted(set(str(l.get("window")) for l in limits)):
        same = [l for l in limits if str(l.get("window")) == name]
        resets = [l["resetsAt"] for l in same if _num(l.get("resetsAt"))]
        if any(reset <= now * 1000 for reset in resets):
            continue
        row = capacity.get(name)
        statuses = [l.get("status") for l in same]
        windows.append({"window": name,
                        "remaining": row["remaining"] if row else min(l["remaining"] for l in same),
                        "durationMs": (row or {}).get("durationMs") or same[0].get("durationMs"),
                        "resetsAt": min(resets) if resets else None,
                        "status": "exhausted" if all(x == "exhausted" for x in statuses) or (
                                      not row and "exhausted" in statuses)
                        else "warning" if any(x in ("warning", "exhausted") for x in statuses) else "ok"})
    return windows


def _pace(window, config, now):
    """Projected use by reset at the current burn rate, or None when too early to tell."""
    duration, resets = window.get("durationMs"), window.get("resetsAt")
    if not (isinstance(duration, (int, float)) and duration > 0 and isinstance(resets, (int, float))):
        return None
    elapsed = 1 - (resets - now * 1000) / duration
    if elapsed < 0.15:
        return None
    return (1 - window["remaining"]) / min(elapsed, 1.0)


def assess(provider, snap, config=None, now=None):
    """{recommendation: ok|reduce|avoid|unknown, ...} for one provider."""
    config = config or settings()
    now = time.time() if now is None else now
    entry = ((snap or {}).get("providers") or {}).get(provider) if provider else None
    out = {"provider": provider, "recommendation": "unknown", "last": "unknown"}
    if snap and snap.get("error"):
        out["error"] = snap["error"]
    if not entry or not entry.get("accounts"):
        out["why"] = "no usage reading" if provider else "model has no provider prefix"
        return out
    fetched = entry.get("fetchedAt")
    if entry.get("undated") or not _num(fetched):
        out["why"] = "reading has no fetch time"
        return out
    out["ageSec"] = int(max(0, now - fetched / 1000))
    windows = _windows(entry, now)
    level, why = "ok", "headroom above reserve"
    if entry.get("blocked") and entry["blocked"] >= entry["accounts"]:
        level, why, out["limitReached"] = "avoid", "provider reports limit reached", True
    if windows:
        tight = min(windows, key=lambda w: w["remaining"])
        out.update(window=tight["window"], remaining=round(tight["remaining"], 3), resetsAt=tight.get("resetsAt"))
        exhausted = [w for w in windows if w.get("status") == "exhausted"]
        if level != "avoid" and exhausted:
            tight = exhausted[0]
            out.update(window=tight["window"], remaining=round(tight["remaining"], 3), resetsAt=tight.get("resetsAt"))
            level, why = "avoid", "provider marks the window exhausted"
        if level != "avoid":
            if tight["remaining"] <= config["buffer"]:
                level, why = "avoid", "at or below the %d%% reserve" % round(config["buffer"] * 100)
            elif tight["remaining"] <= config["buffer"] + config["margin"]:
                level, why = "reduce", "close to the reserve"
            else:
                for window in windows:
                    pace = _pace(window, config, now)
                    if window.get("status") == "warning" or (pace is not None and pace > 1 - config["buffer"]):
                        level, why = "reduce", ("provider warns on the %s window" if window.get("status") == "warning"
                                                else "%s window burning faster than it resets") % window["window"]
                        out.update(window=window["window"], remaining=round(window["remaining"], 3),
                                   resetsAt=window.get("resetsAt"))
                        break
    elif level != "avoid":
        out["why"] = "no live usage window"
        return out
    out["last"], out["why"] = level, why
    if entry.get("partial"):
        out["partial"] = True
    if entry.get("resetCredits"):
        out["resetCredits"] = entry["resetCredits"]
    out["recommendation"] = "unknown" if out["ageSec"] > config["stale"] else level
    if out["ageSec"] > config["stale"]:
        out["why"] = "reading is stale; last: " + why
    return out


def _until(ms, now):
    if not isinstance(ms, (int, float)):
        return "at an unknown time"
    minutes = max(0, int(ms / 1000 - now) // 60)
    days, hours = minutes // 1440, minutes % 1440 // 60
    return "in " + ("%dd%dh" % (days, hours) if days else "%dh%02dm" % (hours, minutes % 60))


def describe(advice, now=None):
    """One line for humans and the coordinator."""
    now = time.time() if now is None else now
    parts = [str(advice.get("provider")), advice["recommendation"]]
    if "remaining" in advice:
        parts.append("%s %d%% left, resets %s" % (advice.get("window"), round(advice["remaining"] * 100),
                                                   _until(advice.get("resetsAt"), now)))
    if "ageSec" in advice:
        parts.append("reading %dm old" % (advice["ageSec"] // 60))
    parts.append(advice.get("why", ""))
    if advice.get("error"):
        parts.append("last refresh failed (" + advice["error"] + ")")
    return ", ".join(p for p in parts if p)


def siblings(lane, tiers):
    tier = lane.split("-", 1)[0]
    own = provider_of(tiers.get(lane))
    return [name for name, model in tiers.items()
            if name != lane and name.split("-", 1)[0] == tier and provider_of(model) != own]


def lanes(tiers, config=None, refresh=False, now=None):
    config = config or settings()
    snap = snapshot(config, refresh=refresh, now=now)
    advice = {}
    for lane, model in tiers.items():
        advice[lane] = assess(provider_of(model), snap, config, now)
    return advice


class QuotaAvoid(ValueError):
    def __init__(self, message, advice):
        ValueError.__init__(self, message)
        self.advice = advice


def gate(lane, model, tiers, override=None, now=None):
    """Advice for a delegation; raises QuotaAvoid when the reserve would be spent.

    Never switches lanes: the coordinator re-delegates explicitly and tells the user. Any error
    while reading or judging quota yields `unknown` advice, never a crash or a block.
    """
    config = settings()
    if config["mode"] == "off":
        return {"recommendation": "off"}
    try:
        refusal = _judge(lane, model, tiers, override, config, now)
    except Exception as error:  # Defensive: quota must never break delegation.
        return {"recommendation": "unknown", "why": "quota check failed (%s)" % type(error).__name__}
    if isinstance(refusal, QuotaAvoid):
        raise refusal
    return refusal


def _judge(lane, model, tiers, override, config, now):
    now = time.time() if now is None else now
    snap = snapshot(config, now=now)
    advice = assess(provider_of(model), snap, config, now)
    summary = {key: advice[key] for key in ("provider", "recommendation", "window", "remaining",
                                            "resetsAt", "ageSec", "why", "limitReached") if key in advice}
    if advice["recommendation"] != "avoid" or lane == "pinned" or config["mode"] != "enforce":
        return summary
    if isinstance(override, str) and override.strip() and not advice.get("limitReached"):
        summary["override"] = override.strip()
        return summary
    others = {name: assess(provider_of(tiers[name]), snap, config, now) for name in siblings(lane, tiers)}
    usable = [name for name, item in others.items() if item["recommendation"] in ("ok", "reduce", "unknown")]
    message = "quota: %s; lane %s refused to keep the reserve." % (describe(advice, now), lane)
    if usable:
        message += " Re-delegate to same-tier sibling %s (%s) with a reason, and tell the user." % (
            usable[0], describe(others[usable[0]], now))
    else:
        message += " No same-tier sibling has headroom: ask the user (wait for reset, change tier, or approve spending the reserve)."
    if advice.get("limitReached"):
        message += " The provider reports its limit reached, so an override would fail."
    else:
        message += " Spending the reserve needs the user's approval: quotaOverride '<user approval>'."
    if advice.get("resetCredits"):
        message += " A saved usage reset is available (omp usage reset); never redeem it without the user."
    return QuotaAvoid(message, summary)


def check_lines(config=None, now=None):
    """Cached-only report for lib/check.sh: `ok|warn quota: ...`; never refreshes."""
    config = config or settings()
    snap = _read(state_dir() / "quota.json")
    if not isinstance(snap, dict) or not snap.get("providers"):
        return ["ok quota: no snapshot yet (quota.py --refresh)"]
    lines = []
    for provider in sorted(snap["providers"]):
        advice = assess(provider, snap, config, now)
        level = "ok" if advice["recommendation"] == "ok" else "warn"
        lines.append("%s quota: %s" % (level, describe(advice, now)))
    return lines


def main(argv):
    if argv[:1] == ["--check"]:
        print("\n".join(check_lines()))
        return
    if any(arg not in ("--refresh", "--json") for arg in argv):
        raise SystemExit("usage: quota.py [--refresh] [--json] | --check")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from t3_policy import TIERS  # noqa: E402 - lazy: t3_policy imports this module
    advice = lanes(TIERS, refresh="--refresh" in argv)
    if "--json" in argv:
        print(json.dumps({"settings": settings(), "lanes": advice}, indent=2))
        return
    config = settings()
    print("reserve %d%%, reduce at <=%d%%, stale after %dm" % (
        round(config["buffer"] * 100), round((config["buffer"] + config["margin"]) * 100), config["stale"] // 60))
    for lane, item in advice.items():
        print("%-11s %s" % (lane, describe(item)))


if __name__ == "__main__":
    main(sys.argv[1:])
