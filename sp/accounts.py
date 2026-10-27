"""
assigns each approved draft to a real, disclosed account and a posting window that respects
the cadence rules in config.yaml. the human still clicks post; this just tells them who and when.
"""
import random
from collections import Counter
from datetime import datetime, timedelta, timezone

from .common import CONFIG, ROOT, is_live, read_csv

ACCOUNTS = ROOT / "sheet" / "accounts.csv"   # account, persona, platforms, groups, active


def load_accounts():
    return [a for a in read_csv(ACCOUNTS) if a.get("active", "yes").lower() == "yes"]


def assign(item, used_today: Counter, group_today: Counter):
    """
    picks an account that is in the post's group/platform and still under its daily cap.
    input: queue item, counters of today's replies per account and per group.
    returns (account_name, persona, post_after_iso) or (None, None, reason).
    """
    cad = CONFIG["cadence"]
    posted = _parse(item.get("posted_at"))
    day = (posted or datetime.now(timezone.utc)).date().isoformat()   # caps are per calendar day
    gkey = f"{day}|{item['group']}"
    if group_today[gkey] >= cad["max_replies_per_group_per_day"]:
        return None, None, "group already has our reply today"
    for a in load_accounts():
        platforms = a.get("platforms", "").lower()
        groups = a.get("groups", "").lower()
        fits = item["channel"] in platforms and (not groups or item["group"].lower() in groups or groups == "*")
        akey = f"{day}|{a['account']}"
        same_group_key = f"{day}|{a['account']}|{item['group']}"
        if fits and used_today[akey] < cad["max_replies_per_account_per_day"] and not used_today[same_group_key]:
            used_today[same_group_key] += 1
            used_today[akey] += 1
            group_today[gkey] += 1
            earliest = (posted or datetime.now(timezone.utc)) + timedelta(minutes=cad["min_minutes_after_post"])
            jitter = timedelta(minutes=random.randint(0, 90))   # never post on a fixed rhythm
            when = (max(earliest, datetime.now(timezone.utc)) if is_live() else earliest) + jitter
            return a["account"], a.get("persona", "HELPER"), when.isoformat(timespec="minutes")
    return None, None, "no account with access to this group, send to ambassador request list"


def _parse(s):
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None
