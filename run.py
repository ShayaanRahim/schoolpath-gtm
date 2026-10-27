"""
command line entry point.

  python run.py discover                                # raw discovery only, no llm
  python run.py discover-and-draft                      # daily run (shadow unless MODE=live in .env)
  python run.py discover-and-draft --sa-export fb_school_discussions.csv
  python run.py prefilter-stats --sa-export fb_school_discussions.csv
  python run.py report --queue sheet/queue.csv --signups signups_week1.csv --spend 42
"""
import argparse

from sp.common import MODE


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["discover", "discover-and-draft", "prefilter-stats", "report"])
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
