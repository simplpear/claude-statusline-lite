#!/usr/bin/env python3
"""Claude Code status line — real rate limits via OAuth API. No dependencies."""
import json, sys, os, re, time, subprocess, urllib.request

CACHE_DIR = os.path.expanduser("~/.cache/claude-statusline")
USAGE_CACHE = os.path.join(CACHE_DIR, "usage.json")
CRED_FILE = os.path.expanduser("~/.claude/.credentials.json")
CACHE_TTL = 60

B = "\u2503"  # ┃

BRIGHT = "\033[1m"
DIM = "\033[2m"
RST = "\033[0m"


def bar(pct):
    if pct is None:
        return DIM + B * 10 + RST, "--"
    pct = max(0, min(100, int(pct)))
    n = round(pct / 10)
    return BRIGHT + B * n + RST + DIM + B * (10 - n) + RST, str(pct)


def fmt_reset(iso):
    if not iso or iso == "null":
        return "---"
    try:
        from datetime import datetime, timezone
        clean = re.sub(r"\.\d+", "", iso).replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean).astimezone(timezone.utc)
        now = datetime.now(timezone.utc)
        secs = int((dt - now).total_seconds())
        if secs <= 0:
            return "now"
        days, rem = divmod(secs, 86400)
        hours, rem = divmod(rem, 3600)
        mins = rem // 60
        if days > 0:
            return f"in {days}d {hours}h {mins}m"
        if hours > 0:
            return f"in {hours}h {mins}m"
        return f"in {mins}m"
    except Exception:
        return "---"


def get_token():
    try:
        r = subprocess.run(
            ["security", "find-generic-password", "-s", "Claude Code-credentials", "-w"],
            capture_output=True, text=True, timeout=3,
        )
        if r.returncode == 0 and r.stdout.strip():
            t = json.loads(r.stdout.strip()).get("claudeAiOauth", {}).get("accessToken")
            if t:
                return t
    except Exception:
        pass
    try:
        with open(CRED_FILE) as f:
            return json.load(f).get("claudeAiOauth", {}).get("accessToken")
    except Exception:
        return None


def load_cache():
    try:
        age = time.time() - os.path.getmtime(USAGE_CACHE)
        with open(USAGE_CACHE) as f:
            return json.load(f), age
    except Exception:
        return None, 999


def save_cache(data):
    os.makedirs(CACHE_DIR, mode=0o700, exist_ok=True)
    tmp = USAGE_CACHE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f)
    os.replace(tmp, USAGE_CACHE)


def fetch(version):
    token = get_token()
    if not token:
        return None
    req = urllib.request.Request(
        "https://api.anthropic.com/api/oauth/usage",
        headers={
            "Authorization": f"Bearer {token}",
            "anthropic-beta": "oauth-2025-04-20",
            "Accept": "application/json",
            "User-Agent": f"claude-code/{version}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read())
        if "five_hour" in data:
            save_cache(data)
            return data
    except Exception:
        pass
    return None


# --- main ---
try:
    inp = json.load(sys.stdin)
except Exception:
    inp = {}

cw = inp.get("context_window", {})
ver = inp.get("version", "unknown")

ctx_b, ctx_v = bar(cw.get("used_percentage"))

cached, age = load_cache()
if age < CACHE_TTL:
    usage = cached
else:
    usage = fetch(ver) or cached

fh_pct = wk_pct = None
fh_rst = wk_rst = "---"

if usage:
    fh = usage.get("five_hour", {})
    wk = usage.get("seven_day", {})
    if fh.get("utilization") is not None:
        fh_pct = int(fh["utilization"])
    fh_rst = fmt_reset(fh.get("resets_at"))
    if wk.get("utilization") is not None:
        wk_pct = int(wk["utilization"])
    wk_rst = fmt_reset(wk.get("resets_at"))

fh_b, fh_v = bar(fh_pct)
wk_b, wk_v = bar(wk_pct)

print(f"context: {ctx_b} {ctx_v}% | 5-hour: {fh_b} {fh_v}% | weekly: {wk_b} {wk_v}%")
print(f"{DIM}5h res: {fh_rst} | 7d res: {wk_rst}{RST}")
