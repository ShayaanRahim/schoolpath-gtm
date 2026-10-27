"""
tracked links. every reply gets its own utm_content, so the weekly "signups by utm" export
maps back to one exact reply, and through the queue to its channel, post type, and reply style.

if SHORTLINK_BASE is set (e.g. https://schoolpath.co/r), replies show a clean short link and
the redirect table maps code -> full utm url. see docs/offshore-dev-spec.md.
"""
import os
from urllib.parse import urlencode

from .common import CONFIG, ROOT, is_live, read_csv, write_csv

REDIRECTS = ROOT / "sheet" / "redirects.csv"


def channel_of(source: str) -> str:
    s = source.lower()
    for name in ("reddit", "nextdoor", "facebook", "thebump"):
        if name in s:
            return name
    return "other"


def build(reply_id, landing_key, source, post_type):
    """
    makes the full utm url and, when configured, a short code for it.
    input: reply id, landing page key from config, post source, post type.
    returns (link_to_post, full_utm_url). reply style is joined later through reply_id.
    """
    path = CONFIG["landing_pages"].get(landing_key, CONFIG["landing_pages"]["find_school"])
    params = {
        "utm_source": channel_of(source),
        "utm_medium": "community",
        "utm_campaign": CONFIG["campaign"] + ("" if is_live() else "_shadow"),
        "utm_content": reply_id,                    # one reply = one id
        "utm_term": post_type,                      # backup copy of the experiment label
    }
    full = f"{CONFIG['site_base']}{path}?{urlencode(params)}"
    base = os.environ.get("SHORTLINK_BASE", "").rstrip("/")
    if not base:
        return full, full
    code = reply_id.split("-")[-1]
    short = f"{base}/{code}"
    if is_live():
        rows = [r for r in read_csv(REDIRECTS) if r["code"] != code]
        rows.append({"code": code, "target": full})
        write_csv(REDIRECTS, rows, ["code", "target"])
    return short, full
