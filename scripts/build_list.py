import json
import os
import re
import urllib.request
import urllib.error


LABEL_TO_ID = {
    "Game ID": "game_id",
    "Game name": "game_name",
    "Game type": "platform",
    "How it runs": "status",
    "Loaded from": "source",
    "File type": "file_type",
    "Console": "console",
    "cIOS": "cios",
    "Controller": "controller",
    "USB pad model": "usb_pad",
    "Mods": "mods",
    "RiftWii version": "version",
    "Notes": "notes",
    "Problem report link": "problem_report",
}

LIST_URL = "https://riftwii.github.io/compatibility.html"
REDIRECT_PAGE = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>RiftWii game compatibility</title>
<meta http-equiv="refresh" content="0; url={LIST_URL}">
<link rel="canonical" href="{LIST_URL}">
</head>
<body>
<p>The list is at <a href="{LIST_URL}">{LIST_URL}</a>. The data behind it is <a href="data.json">data.json</a>.</p>
</body>
</html>
"""

LABEL_ORDER = {label: i for i, label in enumerate(LABEL_TO_ID)}

STATUS_ORDER = ["Perfect", "Playable", "Has problems", "Won't start"]
STATUS_RANK = {s: i for i, s in enumerate(STATUS_ORDER)}
GAME_ID_RE = re.compile(r"^[A-Z0-9]{4}$|^[A-Z0-9]{6}$")
VERSION_RE = re.compile(r"(?<!\d)(\d{4})\s*-\s*(\d+)(?!\d)")


def parse_issue_body(body: str) -> dict:
    ids = [
        "game_id",
        "game_name",
        "platform",
        "status",
        "source",
        "file_type",
        "console",
        "cios",
        "controller",
        "usb_pad",
        "mods",
        "version",
        "notes",
        "problem_report",
    ]
    result = {k: "" for k in ids}
    if not body:
        return result
    sections = {}
    current_label = None
    current_lines: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        # A heading starts a field only when it is a form field that comes after
        # the current one, so "### ..." typed into Notes stays part of Notes.
        label = stripped[4:].strip() if stripped.startswith("### ") else None
        if label in LABEL_ORDER and (current_label is None or LABEL_ORDER[label] > LABEL_ORDER.get(current_label, -1)):
            if current_label is not None:
                sections[current_label] = "\n".join(current_lines).strip()
            current_label = label
            current_lines = []
        else:
            if current_label is not None:
                current_lines.append(line)
    if current_label is not None:
        sections[current_label] = "\n".join(current_lines).strip()
    for label, value in sections.items():
        fid = LABEL_TO_ID.get(label)
        if fid is None:
            continue
        v = value.strip()
        if v == "_No response_":
            v = ""
        result[fid] = v
    return result


def version_key(v: str):
    if not isinstance(v, str):
        return (-1, -1)
    m = VERSION_RE.search(v)
    if not m:
        return (-1, -1)
    try:
        return (int(m.group(1)), int(m.group(2)))
    except ValueError:
        return (-1, -1)


def _is_dolphin_report(r: dict) -> bool:
    c = (r.get("console") or "").strip()
    return c in ("Dolphin (emulator)", "Dolphin")


def _best_status_for(reports: list[dict]):
    if not reports:
        return None
    top = max(version_key(r.get("version", "")) for r in reports)
    newest = [r for r in reports if version_key(r.get("version", "")) == top]
    counts: dict[str, int] = {}
    for r in newest:
        s = (r.get("status") or "").strip()
        if s in STATUS_RANK:
            counts[s] = counts.get(s, 0) + 1
    if not counts:
        return None
    best_count = max(counts.values())
    tied = [s for s, c in counts.items() if c == best_count]
    tied.sort(key=lambda s: STATUS_RANK[s], reverse=True)
    return tied[0]


def aggregate(reports: list[dict]) -> list[dict]:
    grouped: dict[str, list[dict]] = {}
    for r in reports:
        raw_id = (r.get("game_id") or "").strip().upper()
        if not GAME_ID_RE.match(raw_id):
            continue
        status = (r.get("status") or "").strip()
        if status not in STATUS_RANK:
            continue
        grouped.setdefault(raw_id, []).append(r)
    out = []
    for game_id, items in grouped.items():
        console_reports = [r for r in items if not _is_dolphin_report(r)]
        dolphin_reports = [r for r in items if _is_dolphin_report(r)]

        def newest_first(lst: list[dict]) -> list[dict]:
            return sorted(lst, key=lambda r: version_key(r.get("version", "")), reverse=True)

        sorted_console = newest_first(console_reports)
        sorted_all = newest_first(items)

        if sorted_console:
            name = (sorted_console[0].get("game_name") or "").strip()
            if not name:
                for r in sorted_console[1:]:
                    if (r.get("game_name") or "").strip():
                        name = r.get("game_name").strip()
                        break
            platform = (sorted_console[0].get("platform") or "").strip()
            if not platform:
                for r in sorted_console[1:]:
                    if (r.get("platform") or "").strip():
                        platform = r.get("platform").strip()
                        break
        else:
            name = ""
            platform = ""
        if not name and sorted_all:
            for r in sorted_all:
                if (r.get("game_name") or "").strip():
                    name = r.get("game_name").strip()
                    break
        if not platform and sorted_all:
            for r in sorted_all:
                if (r.get("platform") or "").strip():
                    platform = r.get("platform").strip()
                    break
        if not name:
            name = game_id
        if not platform:
            platform = ""

        console_status = _best_status_for(console_reports)
        dolphin_status = _best_status_for(dolphin_reports)
        if console_status is not None:
            shown = console_status
            dolphin_only = False
        elif dolphin_status is not None:
            shown = dolphin_status
            dolphin_only = True
        else:
            continue

        if sorted_all:
            newest_version = (sorted_all[0].get("version") or "").strip()
        else:
            newest_version = ""

        consoles_seen = sorted({(r.get("console") or "").strip() for r in items if (r.get("console") or "").strip()})

        report_links = []
        for r in sorted_all:
            report_links.append(
                {
                    "url": r.get("url") or "",
                    "status": (r.get("status") or "").strip(),
                    "version": (r.get("version") or "").strip(),
                    "console": (r.get("console") or "").strip(),
                }
            )

        out.append(
            {
                "game_id": game_id,
                "game_name": name,
                "platform": platform,
                "status": shown,
                "console_status": console_status,
                "dolphin_status": dolphin_status,
                "dolphin_only": dolphin_only,
                "console_count": len(console_reports),
                "dolphin_count": len(dolphin_reports),
                "newest_version": newest_version,
                "consoles": consoles_seen,
                "reports": report_links,
            }
        )
    out.sort(key=lambda g: g.get("game_name", "").lower())
    return out


def main():
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "riftwii-compatibility-builder",
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    issues: list[dict] = []
    if repo:
        url = f"https://api.github.com/repos/{repo}/issues?label=report&state=open&per_page=100"
        while url:
            req = urllib.request.Request(url, headers=headers)
            try:
                with urllib.request.urlopen(req) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    link = resp.headers.get("Link", "")
            except urllib.error.HTTPError as e:
                raise SystemExit(f"GitHub API request failed: {e.code} {e.reason}")
            for item in data:
                if "pull_request" in item:
                    continue
                issues.append(item)
            nxt = None
            if link:
                for part in link.split(","):
                    part = part.strip()
                    if 'rel="next"' in part:
                        s = part.find("<")
                        e = part.find(">")
                        if s != -1 and e != -1:
                            nxt = part[s + 1 : e]
            url = nxt
    reports: list[dict] = []
    skipped = 0
    for item in issues:
        number = item.get("number", "?")
        body = item.get("body") or ""
        parsed = parse_issue_body(body)
        game_id = (parsed.get("game_id") or "").strip().upper()
        status = (parsed.get("status") or "").strip()
        if not GAME_ID_RE.match(game_id) or status not in STATUS_RANK:
            print(f"Warning: skipping issue #{number}: invalid game_id or status")
            skipped += 1
            continue
        reports.append(
            {
                "game_id": game_id,
                "game_name": (parsed.get("game_name") or "").strip(),
                "platform": (parsed.get("platform") or "").strip(),
                "status": status,
                "source": (parsed.get("source") or "").strip(),
                "file_type": (parsed.get("file_type") or "").strip(),
                "console": (parsed.get("console") or "").strip(),
                "cios": (parsed.get("cios") or "").strip(),
                "controller": (parsed.get("controller") or "").strip(),
                "usb_pad": (parsed.get("usb_pad") or "").strip(),
                "mods": (parsed.get("mods") or "").strip(),
                "version": (parsed.get("version") or "").strip(),
                "notes": (parsed.get("notes") or "").strip(),
                "problem_report": (parsed.get("problem_report") or "").strip(),
                "url": item.get("html_url") or "",
                "number": number,
            }
        )
    try:
        with open("data/dolphin.json", "r", encoding="utf-8") as f:
            dolphin_data = json.load(f)
    except FileNotFoundError:
        dolphin_data = []
    except json.JSONDecodeError as e:
        raise SystemExit(f"data/dolphin.json is not valid JSON: {e}")
    for entry in dolphin_data if isinstance(dolphin_data, list) else []:
        if not isinstance(entry, dict):
            skipped += 1
            continue
        game_id = str(entry.get("game_id") or "").strip().upper()
        status = str(entry.get("status") or "").strip()
        if not GAME_ID_RE.match(game_id) or status not in STATUS_RANK:
            print("Warning: skipping dolphin.json entry: invalid game_id or status")
            skipped += 1
            continue
        reports.append(
            {
                "game_id": game_id,
                "game_name": str(entry.get("game_name") or "").strip(),
                "platform": str(entry.get("platform") or "").strip(),
                "status": status,
                "source": "",
                "file_type": "",
                "console": "Dolphin (emulator)",
                "cios": "",
                "controller": "",
                "usb_pad": "",
                "mods": "",
                "version": str(entry.get("version") or "").strip(),
                "notes": str(entry.get("notes") or "").strip(),
                "problem_report": "",
                "url": "",
                "tested": str(entry.get("tested") or "").strip(),
            }
        )
    games = aggregate(reports)
    console_total = sum(g.get("console_count", 0) for g in games)
    dolphin_total = sum(g.get("dolphin_count", 0) for g in games)
    os.makedirs("site", exist_ok=True)
    with open("site/data.json", "w", encoding="utf-8") as f:
        json.dump(games, f, indent=2, ensure_ascii=False)
        f.write("\n")
    # The list page itself is on the main site (riftwii.github.io/compatibility.html);
    # this repo publishes only the data, plus a page that sends visitors there.
    with open("site/index.html", "w", encoding="utf-8") as f:
        f.write(REDIRECT_PAGE)
    print(f"Built list: {len(games)} games, {console_total} console reports, {dolphin_total} Dolphin reports, {skipped} skipped")


if __name__ == "__main__":
    main()
