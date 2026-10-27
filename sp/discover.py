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


def _reddit_token():
    """
    oauth for reddit's official api (a free "script" app at reddit.com/prefs/apps).
    reddit now blocks most unauthenticated json requests, so this is the reliable path.
    returns a bearer token, or None if credentials aren't configured.
    """
    cid, secret = os.environ.get("REDDIT_CLIENT_ID"), os.environ.get("REDDIT_CLIENT_SECRET")
    if not (cid and secret):
        return None
    data = {"grant_type": "client_credentials"}
    if os.environ.get("REDDIT_USERNAME"):
        data = {"grant_type": "password", "username": os.environ["REDDIT_USERNAME"],
                "password": os.environ.get("REDDIT_PASSWORD", "")}
    r = requests.post("https://www.reddit.com/api/v1/access_token", auth=(cid, secret), data=data,
                      headers={"User-Agent": UA}, timeout=15)
    r.raise_for_status()
    return r.json().get("access_token")


def _reddit_json(sub, q, token):
    base = "https://oauth.reddit.com" if token else "https://www.reddit.com"
    headers = {"User-Agent": UA, **({"Authorization": f"bearer {token}"} if token else {})}
    r = requests.get(f"{base}/r/{sub}/search" + ("" if token else ".json"),
                     params={"q": q, "restrict_sr": 1, "sort": "new", "limit": 25, "t": "month"},
                     headers=headers, timeout=15)
    r.raise_for_status()
    out = []
    for child in r.json().get("data", {}).get("children", []):
        d = child["data"]
        out.append((d["id"], d["created_utc"], "https://www.reddit.com" + d["permalink"],
                    d.get("author", ""), (d.get("title", "") + "\n" + d.get("selftext", "")).strip()))
    return out


def _reddit_rss(sub, q):
    # fallback: reddit's search rss feed, which is often still open when the json endpoint is blocked
    import html
    import re
    import xml.etree.ElementTree as ET
    r = requests.get(f"https://www.reddit.com/r/{sub}/search.rss",
                     params={"q": q, "restrict_sr": "on", "sort": "new", "t": "month"},
                     headers={"User-Agent": UA}, timeout=15)
    r.raise_for_status()
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out = []
    for e in ET.fromstring(r.content).findall("a:entry", ns):
        rid = (e.findtext("a:id", "", ns) or "").replace("t3_", "")
        ts = e.findtext("a:updated", "", ns) or e.findtext("a:published", "", ns)
        created = datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp() if ts else time.time()
        link = e.find("a:link", ns).get("href") if e.find("a:link", ns) is not None else ""
        body = re.sub(r"<[^>]+>", " ", html.unescape(e.findtext("a:content", "", ns) or ""))
        body = re.sub(r"submitted by .*$", "", re.sub(r"\s+", " ", body)).strip()
        author = (e.findtext("a:author/a:name", "", ns) or "").replace("/u/", "")
        out.append((rid, created, link, author, (e.findtext("a:title", "", ns) + "\n" + body).strip()))
    return out


def from_reddit():
    """
    searches each configured subreddit for each query.
    tries, in order: official oauth api (if keys are set), public json, public rss.
    input: none (reads config). returns a list of posts newer than max_age_days.
    """
    cfg = CONFIG["sources"]["reddit"]
    cutoff = time.time() - cfg["max_age_days"] * 86400
    out, seen = [], set()
    try:
        token = _reddit_token()
    except requests.RequestException as e:
        print(f"  reddit oauth failed ({e}), falling back to public endpoints")
        token = None
    mode = "oauth" if token else "json"
    for sub in cfg["subreddits"]:
        for q in cfg["queries"]:
            try:
                items = _reddit_json(sub, q, token) if mode != "rss" else _reddit_rss(sub, q)
            except requests.RequestException as e:
                if mode == "json":
                    print("  reddit json blocked, switching to rss for the rest of the run")
                    mode = "rss"
                    try:
                        items = _reddit_rss(sub, q)
                    except Exception as e2:
                        print(f"  reddit r/{sub} '{q}': {e2}")
                        continue
                else:
                    print(f"  reddit r/{sub} '{q}': {e}")
                    continue
            except Exception as e:
                print(f"  reddit r/{sub} '{q}': {e}")
                continue
            for rid, created, link, author, text in items:
                if rid in seen or created < cutoff:
                    continue
                seen.add(rid)
                out.append({
                    "post_id": f"rd_{rid}", "source": "reddit", "group": f"r/{sub}", "url": link,
                    "author": author, "text": text,
                    "posted_at": datetime.fromtimestamp(created, timezone.utc).isoformat(),
                })
            time.sleep(1.2 if token else 2.5)  # stay well under reddit's rate limits
    print(f"  reddit: {len(out)} posts via {mode}")
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
