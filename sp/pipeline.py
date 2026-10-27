"""
the daily run: discover -> prefilter -> llm score -> prioritize -> draft -> link -> assign -> queue.
shadow mode writes shadow/shadow_log.csv. live mode appends to the ops google sheet (or sheet/queue.csv).
"""
import json
import os
from collections import Counter
from datetime import datetime, timezone

import yaml

from . import accounts, links, llm
from .common import CONFIG, ROOT, fill, is_live, prompt, read_csv, short_hash, write_csv
from .discover import discover
from .prefilter import prefilter

SEEN = ROOT / "sheet" / "seen.csv"
SHADOW_LOG = ROOT / "shadow" / "shadow_log.csv"
QUEUE_CSV = ROOT / "sheet" / "queue.csv"

FIELDS = ["reply_id", "status", "priority", "intent_score", "prefilter_score", "source", "channel", "group",
          "posted_at", "url", "post_text", "summary", "geo_tier", "age_band", "post_type", "needs",
          "risk_flags", "persona", "account", "post_after", "reply_style", "draft_reply", "link",
          "full_utm_url", "reviewer_note", "skip_reason", "prefilter_reasons"]


def priority(s):
    """
    turns the llm's qualification into one 0-100 number the ops person sorts by.
    input: the score json. returns an int; 0 means never reply.
    """
    if not s or not s.get("is_parent_asking") or s.get("geo_tier") == "other" or s.get("age_band") == "older":
        return 0
    p = int(s.get("intent", 0)) * 5
    p += {"core": 30, "adjacent": 15, "unknown": 8}.get(s.get("geo_tier"), 0)
    if s.get("post_type") in ("comparison", "new_to_area", "waitlist_or_availability"):
        p += 10
    if s.get("needs"):
        p += 10
    if "already_well_answered" in s.get("risk_flags", []):
        p -= 20
    return max(0, min(100, p))


def _hours_old(ts):
    try:
        t = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return (datetime.now(timezone.utc) - t).total_seconds() / 3600
    except Exception:
        return 0  # unknown age (e.g. pasted without a date): let the human judge


def persona_for(channel):
    # closed local groups only through real local parents; open forums through a disclosed team member
    if channel in ("facebook", "nextdoor"):
        return "AMBASSADOR", "a North San Antonio parent of a preschooler who helps SchoolPath part-time"
    return "HELPER", "a named SchoolPath team member who says so plainly"


def verified_schools_text():
    rows = yaml.safe_load((ROOT / "data" / "verified_schools.yaml").read_text())
    return "\n".join(f"- {r['name']}: " + "; ".join(r["facts"]) for r in rows)


def run(sa_export=None, limit=None, input_csv=None, min_prefilter=0):
    posts = read_csv(input_csv) if input_csv else discover(sa_export)
    seen = {r["post_id"] for r in read_csv(SEEN)}
    posts = [p for p in posts if p["post_id"] not in seen]
    print(f"discovered {len(posts)} new posts")

    rows, used, groups, waiting, drafted = [], Counter(), Counter(), 0, 0
    vschools = verified_schools_text()
    for p in posts:
        pf_score, pf_reasons, keep = prefilter(p)
        if not keep or pf_score < min_prefilter:
            continue
        s = llm.ask(fill(prompt("score"), source=p["source"], group=p["group"],
                         posted_at=p["posted_at"], text=p["text"][:3000]), CONFIG["models"]["score"])
        if s is None:
            waiting += 1
            continue
        pr = priority(s)
        channel = links.channel_of(p["source"])
        reply_id = f"r{datetime.now(timezone.utc):%m%d}-{short_hash(p['post_id'], 6)}"
        row = {
            "reply_id": reply_id, "status": "skipped", "priority": pr, "intent_score": s.get("intent"),
            "prefilter_score": pf_score, "prefilter_reasons": pf_reasons, "source": p["source"],
            "channel": channel, "group": p["group"], "posted_at": p["posted_at"], "url": p["url"],
            "post_text": p["text"][:1500], "summary": s.get("one_line_summary", ""),
            "geo_tier": s.get("geo_tier"), "age_band": s.get("age_band"), "post_type": s.get("post_type"),
            "needs": ", ".join(s.get("needs", [])), "risk_flags": ", ".join(s.get("risk_flags", [])),
            "skip_reason": s.get("skip_reason", ""),
        }
        if is_live() and _hours_old(p["posted_at"]) > CONFIG["cadence"]["max_hours_after_post"]:
            row["skip_reason"] = row["skip_reason"] or "thread too old to reply naturally"
            pr = row["priority"] = 0
        if pr >= CONFIG["min_priority_to_queue"]:
            persona, notes = persona_for(channel)
            landing = s.get("best_landing") or "find_school"
            link, full = links.build(reply_id, landing, p["source"], s.get("post_type", "other"))
            drafted += 1
            if landing == "none" or drafted % CONFIG["cadence"]["link_in_every_nth_reply"] != 0:
                landing = "none"   # some replies carry no link at all: pure help builds the account's credibility
            d = llm.ask(fill(prompt("draft"), persona=persona, persona_notes=notes, text=p["text"][:3000],
                             summary=s.get("one_line_summary", ""), needs=", ".join(s.get("needs", [])),
                             post_type=s.get("post_type"), link=link if landing != "none" else "NONE",
                             verified_schools=vschools,
                             recent_phrases=recent_disclosures()), CONFIG["models"]["draft"])
            if d is None:
                waiting += 1
                continue
            row.update({
                "status": "drafted", "persona": persona,
                "reply_style": d.get("reply_style", ""), "draft_reply": d.get("reply", ""),
                "link": link if d.get("uses_link") else "", "full_utm_url": full if d.get("uses_link") else "",
                "reviewer_note": d.get("reviewer_note", ""),
            })
        rows.append(row)
        if limit and len(rows) >= limit:
            break

    flag_repeats(rows)

    # assign accounts in priority order, so the cadence caps spend our daily slots on the best posts
    rows.sort(key=lambda r: -int(r["priority"]))
    for row in rows:
        if row["status"] != "drafted":
            continue
        account, _, when_or_reason = accounts.assign(row, used, groups)
        if account:
            row.update(status="ready_for_review", account=account, post_after=when_or_reason)
        else:
            row.update(status="held", skip_reason=when_or_reason)
    if waiting:
        print(f"{waiting} prompts waiting in shadow/pending_prompts (file backend). answer them, then rerun.")
    _write(rows)
    if is_live():  # shadow runs never mark posts as seen, so they can be rerun freely
        write_csv(SEEN, read_csv(SEEN) + [{"post_id": pid} for pid in {p["post_id"] for p in posts}], ["post_id"])
    print(f"wrote {len(rows)} rows ({sum(r['status'] != 'skipped' for r in rows)} drafted) in {('LIVE' if is_live() else 'SHADOW')} mode")
    return rows


def recent_disclosures(n=15):
    # the last few disclosure sentences we posted, so the drafter can avoid repeating them
    out = []
    for r in read_csv(QUEUE_CSV)[-60:]:
        for sent in r.get("draft_reply", "").replace("(", ". ").replace(")", ". ").split(". "):
            if "schoolpath" in sent.lower() and "http" not in sent:
                out.append(sent.strip())
    return "; ".join(f'"{x}"' for x in out[-n:]) or "none yet"


def _shingles(text, n=5):
    w = [x.strip(".,!?()").lower() for x in text.split()]
    return {" ".join(w[i:i + n]) for i in range(len(w) - n + 1)}


def flag_repeats(rows, posted_csv=QUEUE_CSV):
    """
    pattern check: the same 5-word phrase showing up across several replies is exactly what makes
    someone say "this is a bot". flags any phrase shared by 3+ drafts in this batch or recent posted
    replies, and tells the reviewer to reword it.
    input: this run's rows. returns nothing; adds to reviewer_note.
    """
    from collections import defaultdict
    history = [r.get("draft_reply", "") for r in read_csv(posted_csv)[-50:]]
    drafts = [r for r in rows if r.get("draft_reply")]
    counts = defaultdict(int)
    for t in history + [r["draft_reply"] for r in drafts]:
        for sh in _shingles(t):
            counts[sh] += 1
    for r in drafts:
        hot = sorted({sh for sh in _shingles(r["draft_reply"]) if counts[sh] >= 3}, key=lambda x: -counts[x])
        if hot:
            note = "REWORD (seen in %d other replies): '%s'" % (counts[hot[0]] - 1, hot[0])
            r["reviewer_note"] = (r.get("reviewer_note", "") + " | " + note).strip(" |")


def _write(rows):
    if not is_live():
        write_csv(SHADOW_LOG, rows, FIELDS)
        return
    sheet_id = os.environ.get("GOOGLE_SHEET_ID")
    if sheet_id:
        import gspread  # only needed in live mode
        ws = gspread.service_account(filename=os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"]).open_by_key(sheet_id).worksheet("Queue")
        ws.append_rows([[str(r.get(f, "")) for f in FIELDS] for r in rows if r["status"] != "skipped"],
                       value_input_option="RAW")
    else:
        write_csv(QUEUE_CSV, read_csv(QUEUE_CSV) + rows, FIELDS)
