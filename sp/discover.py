"""
discovery: pulls candidate posts from every source into one shape.

post shape: {post_id, source, group, url, author, posted_at, text}

automated sources: reddit public search, google programmable search (optional).
human sources: the Capture tab (facebook groups, nextdoor, anything with a login wall),
and the SA School Analytics csv export (historical, used for testing and vocabulary).
"""
import os
import time
from datetime import datetime, timezone

import requests

from .common import CONFIG, ROOT, read_csv, short_hash

UA = os.environ.get("REDDIT_USER_AGENT", "schoolpath-shadow/0.1 (contact: ops)")


def from_reddit():
    """
    searches each configured subreddit for each query using reddit's public json.
    input: none (reads config). returns a list of posts newer than max_age_days.
    """
    cfg = CONFIG["sources"]["reddit"]
    cutoff = time.time() - cfg["max_age_days"] * 86400
    out, seen = [], set()
    for sub in cfg["subreddits"]:
        for q in cfg["queries"]:
            url = f"https://www.reddit.com/r/{sub}/search.json"
            params = {"q": q, "restrict_sr": 1, "sort": "new", "limit": 25, "t": "month"}
            try:
                r = requests.get(url, params=params, headers={"User-Agent": UA}, timeout=15)
                r.raise_for_status()
            except requests.RequestException as e:
                print(f"  reddit r/{sub} '{q}': {e}")
                continue
            for child in r.json().get("data", {}).get("children", []):
                d = child["data"]
                if d["id"] in seen or d["created_utc"] < cutoff:
                    continue
                seen.add(d["id"])
                out.append({
                    "post_id": f"rd_{d['id']}",
                    "source": "reddit",
                    "group": f"r/{sub}",
                    "url": "https://www.reddit.com" + d["permalink"],
                    "author": d.get("author", ""),
                    "posted_at": datetime.fromtimestamp(d["created_utc"], timezone.utc).isoformat(),
                    "text": (d.get("title", "") + "\n" + d.get("selftext", "")).strip(),
                })
            time.sleep(1.2)  # stay well under reddit's unauthenticated rate limit
    return out


def from_web_search():
    """
    google programmable search for public forums (the bump, indexed nextdoor posts).
    needs GOOGLE_CSE_KEY and GOOGLE_CSE_ID; silently skipped otherwise.
    """
    key, cx = os.environ.get("GOOGLE_CSE_KEY"), os.environ.get("GOOGLE_CSE_ID")
    if not (key and cx):
        return []
    out = []
    for q in CONFIG["sources"]["web_search"]["queries"]:
        try:
            r = requests.get("https://www.googleapis.com/customsearch/v1",
                             params={"key": key, "cx": cx, "q": q, "dateRestrict": "d21"}, timeout=15)
            r.raise_for_status()
        except requests.RequestException as e:
            print(f"  web search '{q}': {e}")
            continue
        for item in r.json().get("items", []):
            out.append({
                "post_id": "ws_" + short_hash(item["link"]),
                "source": "web:" + item.get("displayLink", ""),
                "group": item.get("displayLink", ""),
                "url": item["link"],
                "author": "",
                "posted_at": "",
                "text": item.get("title", "") + "\n" + item.get("snippet", ""),
            })
    return out


def from_capture(path=ROOT / "sheet" / "capture.csv"):
    """
    rows people pasted by hand (facebook, nextdoor, group chats).
    columns: source, group, url, posted_at, text
    """
    out = []
    for row in read_csv(path):
        if not row.get("text"):
            continue
        out.append({
            "post_id": "cp_" + short_hash(row.get("url") or row["text"]),
            "source": row.get("source") or "capture",
            "group": row.get("group", ""),
            "url": row.get("url", ""),
            "author": "",
            "posted_at": row.get("posted_at", ""),
            "text": row["text"],
        })
    return out


def from_sa_export(path):
    """
    the SA School Analytics fb_school_discussions.csv export.
    used for testing the scorer on real local language, not as a live feed.
    """
    out = []
    for row in read_csv(path):
        out.append({
            "post_id": "sa_" + str(row.get("id", ""))[-12:],
            "source": "facebook (SA School Analytics export)",
            "group": row.get("source_group", ""),
            "url": row.get("post_url", "") or row.get("url", ""),
            "author": "",
            "posted_at": row.get("posted_at", ""),
            "text": row.get("post_text", "") or "",
        })
    return out


def discover(sa_export=None):
    posts = from_reddit() + from_web_search() + from_capture()
    if sa_export:
        posts += from_sa_export(sa_export)
    # de-duplicate across sources by text
    uniq = {}
    for p in posts:
        uniq.setdefault(short_hash(p["text"].lower().strip()), p)
    return list(uniq.values())
