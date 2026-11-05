import json
import os
import re
import urllib.parse
import urllib.request
import urllib.error

try:
    from build_list import parse_issue_body
except ImportError:
    from scripts.build_list import parse_issue_body

PLATFORM_LABELS = ("wii", "gamecube", "channel")
GAME_ID_RE = re.compile(r"^[A-Z0-9]{4}$|^[A-Z0-9]{6}$")
COMMENT_TEXT = (
    "The Game ID in this report doesn't look right. "
    "Please edit this issue and fix the Game ID. "
    "You can find it on the game's page in RiftWii "
    "(6 characters for Wii and GameCube games, 4 characters for channels, for example RMGE01)."
)


def _api_request(method, url, token, payload=None):
    data = None
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "riftwii-compatibility-labeler",
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read().decode("utf-8")
            if raw:
                return resp.status, json.loads(raw)
            return resp.status, None
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8")
        except Exception:
            body = ""
        return e.code, body


def _platform_label(platform: str):
    p = (platform or "").lower()
    if "gamecube" in p:
        return "gamecube"
    if "channel" in p or "wiiware" in p or "/ vc" in p or p.strip() == "vc":
        return "channel"
    if "wii" in p:
        return "wii"
    return None


def main():
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    number = os.environ.get("ISSUE_NUMBER", "").strip()
    body = os.environ.get("ISSUE_BODY", "")
    if not repo or not number:
        raise SystemExit("Missing GITHUB_REPOSITORY or ISSUE_NUMBER")
    parsed = parse_issue_body(body)
    game_id = (parsed.get("game_id") or "").strip().upper()
    base = f"https://api.github.com/repos/{repo}"
    valid = bool(GAME_ID_RE.match(game_id))
    game_label = f"game:{game_id}" if valid else None
    plat = _platform_label(parsed.get("platform") or "") if valid else None
    # Take off labels left from an earlier version of the report (another game,
    # another type, or a Game ID that is no longer valid).
    status, current = _api_request("GET", f"{base}/issues/{number}/labels?per_page=100", token)
    if status == 200 and isinstance(current, list):
        for lab in current:
            name = lab.get("name") or ""
            stale_game = name.startswith("game:") and name != game_label
            stale_platform = name in PLATFORM_LABELS and name != plat
            if stale_game or stale_platform:
                _api_request("DELETE", f"{base}/issues/{number}/labels/{urllib.parse.quote(name, safe='')}", token)
    if not valid:
        status, comments = _api_request("GET", f"{base}/issues/{number}/comments?per_page=100", token)
        exists = False
        if status == 200 and isinstance(comments, list):
            for c in comments:
                user = (c.get("user") or {}).get("login", "")
                cbody = c.get("body") or ""
                if user == "github-actions[bot]" and COMMENT_TEXT in cbody:
                    exists = True
                    break
        if not exists:
            _api_request("POST", f"{base}/issues/{number}/comments", token, {"body": COMMENT_TEXT})
        return
    _api_request("POST", f"{base}/labels", token, {"name": game_label, "color": "0a7fb8"})
    labels = [game_label]
    if plat:
        labels.append(plat)
    _api_request("POST", f"{base}/issues/{number}/labels", token, {"labels": labels})


if __name__ == "__main__":
    main()
