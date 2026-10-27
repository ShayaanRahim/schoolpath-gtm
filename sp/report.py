"""
weekly scorecard. joins the posted queue to schoolpath's weekly "signups by utm" export on
utm_content = reply_id, then reports activity separately from results.
"""
from collections import defaultdict

from .common import ROOT, read_csv, write_csv


def scorecard(queue_csv, signups_csv, spend_to_date: float, clicks_csv=None, out=ROOT / "reports" / "scorecard.csv"):
    """
    input: queue export (status, reply_id, channel, post_type, reply_style), signups export
    (one row per signup or a 'signups' count column, with utm_content), spend so far, optional click log.
    returns rows grouped by channel, post type, and reply style, and writes them to reports/.
    """
    queue = read_csv(queue_csv)
    signups = defaultdict(int)
    for s in read_csv(signups_csv):
        signups[s.get("utm_content", "")] += int(s.get("signups", 1) or 1)
    clicks = defaultdict(int)
    for c in read_csv(clicks_csv) if clicks_csv else []:
        clicks[c.get("code") or c.get("utm_content", "")] += 1

    rows = []
    total_signups = sum(signups.values())
    for dim in ("channel", "post_type", "reply_style", "account"):
        agg = defaultdict(lambda: {"found": 0, "drafted": 0, "posted": 0, "clicks": 0, "signups": 0})
        for q in queue:
            a = agg[q.get(dim) or "(blank)"]
            a["found"] += 1
            a["drafted"] += q.get("status") != "skipped"
            if q.get("status") == "posted":
                a["posted"] += 1
                rid = q["reply_id"]
                a["clicks"] += clicks[rid] + clicks[rid.split("-")[-1]]
                a["signups"] += signups[rid]
        for k, a in agg.items():
            rows.append({
                "dimension": dim, "value": k,
                # activity
                "posts_found": a["found"], "replies_drafted": a["drafted"], "replies_posted": a["posted"],
                # results
                "clicks": a["clicks"], "signups": a["signups"],
                "signups_per_reply": round(a["signups"] / a["posted"], 2) if a["posted"] else "",
                "decision_hint": _hint(a),
            })
    rows.append({"dimension": "TOTAL", "value": "", "signups": total_signups,
                 "decision_hint": f"cost per signup ${spend_to_date / total_signups:.2f}" if total_signups else "no signups yet"})
    write_csv(out, rows)
    return rows


def _hint(a):
    # mirrors the kill / double-down rules in docs/experiment-plan.md
    if a["posted"] >= 10 and a["signups"] == 0 and a["clicks"] <= 2:
        return "KILL: 10+ replies, no signups, almost no clicks"
    if a["posted"] >= 10 and a["clicks"] >= 10 and a["signups"] == 0:
        return "FIX LANDING: people click but don't sign up"
    if a["posted"] >= 5 and a["signups"] / a["posted"] >= 0.5:
        return "DOUBLE DOWN"
    return ""
