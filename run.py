"""
command line entry point.

  python run.py discover                                # raw discovery only, no llm
  python run.py discover-and-draft                      # daily run (shadow unless MODE=live in .env)
  python run.py discover-and-draft --sa-export fb_school_discussions.csv
  python run.py prefilter-stats --sa-export fb_school_discussions.csv
  python run.py catalog-gaps --sa-export fb_school_discussions.csv --input fb_comments.csv
  python run.py report --queue sheet/queue.csv --signups signups_week1.csv --spend 42
"""
import argparse

from sp.common import MODE


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["discover", "discover-and-draft", "prefilter-stats", "catalog-gaps", "report"])
    ap.add_argument("--sa-export")
    ap.add_argument("--limit", type=int)
    ap.add_argument("--input", help="score/draft an existing posts csv instead of discovering")
    ap.add_argument("--min-prefilter", type=int, default=0)
    ap.add_argument("--queue")
    ap.add_argument("--signups")
    ap.add_argument("--clicks")
    ap.add_argument("--spend", type=float, default=0)
    a = ap.parse_args()
    print(f"mode: {MODE.upper()}")

    if a.cmd == "discover":
        # discovery only, no llm: dumps raw candidate posts for inspection or a later --input run
        from sp.common import ROOT, write_csv
        from sp.discover import discover
        from sp.prefilter import prefilter
        posts = discover(a.sa_export)
        for p in posts:
            p["prefilter_score"], p["prefilter_reasons"], keep = prefilter(p)
            p["keep"] = keep
        write_csv(ROOT / "shadow" / "discovered.csv", posts)
        print(f"{len(posts)} posts, {sum(p['keep'] for p in posts)} pass the keyword filter -> shadow/discovered.csv")
    elif a.cmd == "discover-and-draft":
        from sp.pipeline import run
        run(sa_export=a.sa_export, limit=a.limit, input_csv=a.input, min_prefilter=a.min_prefilter)
    elif a.cmd == "catalog-gaps":
        # which schools parents talk about that have no schoolpath page yet, ranked. a weekly list for the product team.
        from sp.common import ROOT, read_csv, write_csv
        from sp.pipeline import load_schools
        texts = [p.get("post_text", "") for p in read_csv(a.sa_export)] if a.sa_export else []
        texts += [r.get("post_text", "") for r in read_csv(ROOT / "sheet" / "queue.csv")]
        if a.input:
            texts += [r.get("comment_text", "") or r.get("text", "") for r in read_csv(a.input)]
        rows = []
        for s in load_schools():
            n = sum(any(al in (t or "").lower() for al in s.get("aliases", [])) for t in texts)
            rows.append({"school": s["name"], "mentions": n, "has_schoolpath_page": bool(s.get("schoolpath_url"))})
        rows.sort(key=lambda r: -r["mentions"])
        write_csv(ROOT / "reports" / "catalog_gaps.csv", rows)
        for r in rows:
            print(f"{r['mentions']:5d}  {'page' if r['has_schoolpath_page'] else 'NO PAGE':8s} {r['school']}")
    elif a.cmd == "prefilter-stats":
        from sp.discover import from_sa_export
        from sp.prefilter import prefilter
        posts = from_sa_export(a.sa_export)
        kept = [p for p in posts if prefilter(p)[2]]
        high = [p for p in kept if prefilter(p)[0] >= 70]
        print(f"{len(posts)} posts -> {len(kept)} sent to llm -> {len(high)} with keyword score >= 70")
    else:
        from sp.report import scorecard
        for r in scorecard(a.queue, a.signups, a.spend, a.clicks):
            print(r)


if __name__ == "__main__":
    main()
