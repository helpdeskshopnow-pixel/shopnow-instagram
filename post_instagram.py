#!/usr/bin/env python3
"""Shop-Now.net daily Instagram poster (runs hourly from GitHub Actions, posts once per local day).

Posts the next product card in rotation (see ORDER) through the Composio API using the
already-connected Instagram account.

Secrets/env: COMPOSIO_API_KEY (secret), IG_CONNECTED_ACCOUNT_ID (variable or secret, the Composio
connected account id for Instagram), IG_USER_ID (default 28310084391998367),
POST_TZ (default Asia/Kabul), POST_HOUR (8), LATEST_HOUR (20), GITHUB_REPOSITORY (set by Actions).
Modes: CHECK=1 only reads the Instagram profile to prove the connection works; DRY_RUN=1 prints
what would be posted; FORCE=1 ignores the hour/once-a-day checks.
"""
import datetime as dt, json, os, sys, time
from pathlib import Path
from zoneinfo import ZoneInfo
import requests

HERE = Path(__file__).parent
HISTORY = HERE / "ig_history.json"
ORDER = ["rice", "flour", "sugar", "salt", "olive", "oil", "almonds", "pistachios", "raisins", "soap", "notebook", "pens"]
API = "https://backend.composio.dev/api/v3.1/tools/execute/"
KEY = os.environ.get("COMPOSIO_API_KEY", "")
ACC = os.environ.get("IG_CONNECTED_ACCOUNT_ID", "")
IG_USER = os.environ.get("IG_USER_ID") or "28310084391998367"
TZ = ZoneInfo(os.environ.get("POST_TZ") or "Asia/Kabul")
POST_HOUR = int(os.environ.get("POST_HOUR") or 8)
LATEST_HOUR = int(os.environ.get("LATEST_HOUR") or 20)
REPO = os.environ.get("GITHUB_REPOSITORY", "")
BRANCH = os.environ.get("IMG_BRANCH") or "main"


def history():
    try:
        return json.loads(HISTORY.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save(h):
    HISTORY.write_text(json.dumps(h, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


MCP_URL = "https://connect.composio.dev/mcp"
_sess = {}


def _mcp(method, params=None, rid=1, timeout=120):
    h = {"x-consumer-api-key": KEY, "content-type": "application/json", "accept": "application/json, text/event-stream"}
    if _sess.get("id"):
        h["mcp-session-id"] = _sess["id"]
    body = {"jsonrpc": "2.0", "method": method}
    if params is not None:
        body["params"] = params
    if rid is not None:
        body["id"] = rid
    r = requests.post(MCP_URL, headers=h, json=body, timeout=timeout)
    if r.headers.get("mcp-session-id"):
        _sess["id"] = r.headers["mcp-session-id"]
    if rid is None:
        return None
    if r.status_code >= 400:
        raise RuntimeError(f"MCP {method}: HTTP {r.status_code} {r.text[:300]}")
    if "text/event-stream" in r.headers.get("content-type", ""):
        msgs = [json.loads(l[5:]) for l in r.text.splitlines() if l.startswith("data:") and l[5:].strip()]
        msg = next((m for m in msgs if m.get("id") == rid), msgs[-1] if msgs else {})
    else:
        msg = r.json()
    if "error" in msg:
        raise RuntimeError(f"MCP {method}: {str(msg['error'])[:300]}")
    return msg.get("result") or {}


def run_tool(slug, args, timeout=120):
    """Runs one Composio tool through the Composio MCP endpoint (ck_ consumer key) or the REST API (project key)."""
    if not KEY.startswith("ck_"):
        body = {"arguments": args}
        if ACC:
            body["connected_account_id"] = ACC
        r = requests.post(API + slug, headers={"x-api-key": KEY, "content-type": "application/json"}, json=body, timeout=timeout)
        try:
            data = r.json()
        except ValueError:
            raise RuntimeError(f"{slug}: HTTP {r.status_code}, non-JSON reply")
        if not r.ok or data.get("successful") is False or data.get("error"):
            raise RuntimeError(f"{slug}: HTTP {r.status_code} {str(data.get('error') or data)[:300]}")
        return data.get("data", data)
    if not _sess.get("init"):
        _mcp("initialize", {"protocolVersion": "2025-03-26", "capabilities": {}, "clientInfo": {"name": "shopnow-agent", "version": "1"}})
        _mcp("notifications/initialized", rid=None)
        _sess["init"] = True
    res = _mcp("tools/call", {"name": "COMPOSIO_MULTI_EXECUTE_TOOL", "arguments": {
        "tools": [{"tool_slug": slug, "arguments": args}], "sync_response_to_workbench": False}}, rid=2, timeout=timeout)
    text = "".join(c.get("text", "") for c in res.get("content", []) if isinstance(c, dict))
    try:
        data = json.loads(text)
    except ValueError:
        raise RuntimeError(f"{slug}: unreadable reply {text[:300]}")
    if res.get("isError") or data.get("successful") is False or data.get("error"):
        raise RuntimeError(f"{slug}: {str(data.get('error') or text)[:300]}")
    results = (data.get("data") or {}).get("results") or []
    first = results[0] if results else {}
    if first.get("error"):
        raise RuntimeError(f"{slug}: {str(first['error'])[:300]}")
    return first.get("response", first)


def find_id(o):
    if isinstance(o, dict):
        if isinstance(o.get("id"), (str, int)):
            return str(o["id"])
        for v in o.values():
            f = find_id(v)
            if f:
                return f
    if isinstance(o, list):
        for v in o:
            f = find_id(v)
            if f:
                return f
    return None


def next_product(h):
    sent = [e["product"] for e in h if e.get("status") in ("sent", "unconfirmed")]
    if not sent or sent[-1] not in ORDER:
        return ORDER[0]
    return ORDER[(ORDER.index(sent[-1]) + 1) % len(ORDER)]


def main():
    if not KEY:
        print("Missing COMPOSIO_API_KEY"); return 2
    if os.environ.get("CHECK") == "1":
        info = run_tool("INSTAGRAM_GET_USER_INFO", {})
        print("Connection OK. Instagram account:", json.dumps(info)[:300]); return 0
    dry, force = os.environ.get("DRY_RUN") == "1", os.environ.get("FORCE") == "1"
    now = dt.datetime.now(TZ); today = now.date().isoformat(); h = history()
    if not dry and not force:
        if any(e.get("date") == today and e.get("status") in ("sent", "unconfirmed") for e in h):
            print(f"Already posted for {today}."); return 0
        if not POST_HOUR <= now.hour < LATEST_HOUR:
            print(f"Local time {now:%H:%M} ({TZ.key}); window is {POST_HOUR}:00-{LATEST_HOUR}:00."); return 0
    product = next_product(h)
    cap = json.loads((HERE / "captions.json").read_text(encoding="utf-8"))[product]
    url = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/images/{cap['image']}"
    print(f"Product: {product}\nImage: {url}\n\n{cap['caption']}")
    if dry:
        print("\n[DRY RUN] nothing posted."); return 0
    for _ in range(6):  # make sure Meta can fetch the image
        try:
            rr = requests.head(url, timeout=20, allow_redirects=False)
            if rr.status_code == 200 and "image" in rr.headers.get("content-type", ""):
                break
        except requests.RequestException:
            pass
        time.sleep(10)
    else:
        print("Image URL not reachable (is the repository public and the image pushed?)"); return 1
    entry = {"date": today, "time_local": now.strftime("%H:%M"), "product": product}
    try:
        cont = run_tool("INSTAGRAM_POST_IG_USER_MEDIA", {"ig_user_id": IG_USER, "image_url": url, "caption": cap["caption"]})
        cid = find_id(cont)
        if not cid:
            raise RuntimeError("no container id in reply: " + json.dumps(cont)[:300])
    except Exception as e:
        entry.update(status="failed", error=str(e)[:300]); h.append(entry); save(h); print("Container failed:", e); return 1
    try:
        pub = run_tool("INSTAGRAM_POST_IG_USER_MEDIA_PUBLISH", {"ig_user_id": IG_USER, "creation_id": cid}, timeout=180)
        entry.update(status="sent", container_id=cid, media_id=find_id(pub))
        h.append(entry); save(h); print("Posted. media id:", entry["media_id"]); return 0
    except requests.ReadTimeout:
        entry.update(status="unconfirmed", container_id=cid, error="publish timed out; check Instagram")
    except Exception as e:
        entry.update(status="failed", container_id=cid, error=str(e)[:300])
    h.append(entry); save(h); print("Publish problem:", entry["error"]); return 1


if __name__ == "__main__":
    sys.exit(main())
