"""Client for the Walking Pad Community Worker (community/). Runs inside the logger, so the
account token never reaches the browser. Only DAILY TOTALS are ever sent."""
import json
import urllib.error
import urllib.request


class CommunityError(Exception):
    def __init__(self, message, status=502):
        super().__init__(message)
        self.status = status


def call(server, method, path, token=None, body=None, timeout=12):
    url = server.rstrip("/") + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json", "User-Agent": "walking-pad-logger"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read() or b"{}").get("error") or e.reason
        except ValueError:
            msg = e.reason
        if e.code == 429:
            msg = f"Too many requests. Try again in {e.headers.get('Retry-After', 'a few')} seconds."
        raise CommunityError(str(msg), e.code)
    except (urllib.error.URLError, TimeoutError, OSError):
        raise CommunityError("The community server can't be reached right now.", 502)


def sync_payload(state):
    """Build the /v1/sync body from engine.compute() output (last ~40 days)."""
    days = [{"date": d, "steps": int(v["steps"]), "minutes": float(v["minutes"]), "km": float(v["km"]), "goal_met": bool(v["goal_met"])}
            for d, v in sorted(state.get("_days", {}).items())]
    return {"days": days[-62:], "streak": int(state["streak"]["days"])}
