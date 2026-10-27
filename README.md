# SchoolPath parent-acquisition system (North San Antonio, ages 0–5)

This finds parents in North San Antonio who are asking for daycare, pre-K, or kindergarten advice. It drafts a reply that actually answers the question, hands that draft to a person who reviews it and posts it under a real, disclosed identity, and tracks every reply through to a signup.

**Software finds and drafts. A trained human decides and posts. The weekly numbers decide what we keep.**

## Architecture

```
                         ┌──────────────────────── DISCOVERY ────────────────────────┐
  Reddit (r/sanantonio,  │  sp/discover.py                                            │
  r/JBSA, r/MilitarySp.) ├─► automated: reddit public json, google programmable search │
  The Bump, indexed      │                                                            │
  Nextdoor posts         │  Capture tab (Google Form → sheet)  ◄── ambassadors paste  │
  FB groups / Nextdoor ──┼─► human: posts from closed groups we can't (and shouldn't)  │
  (closed, login walls)  │          scrape                                            │
                         └───────────────────────────┬────────────────────────────────┘
                                                     ▼
                     sp/prefilter.py  keyword gate: age 0–5 terms, geo, ask, not an ad   ($0)
                                                     ▼  ~10% of posts survive
                     prompts/score.md  LLM qualifies: parent asking? geo tier? age? intent 0–10?
                                                     ▼  pipeline.priority() → 0–100
                     prompts/draft.md  LLM drafts: answer first, verified facts only,
                                       one tracked link, disclosure line, 40–110 words
                                                     ▼
                     sp/links.py       schoolpath.co/r/<code> → full UTM url (utm_content = reply id)
                     sp/accounts.py    who posts it, and when (daily caps, never instant, jitter)
                                                     ▼
          MODE=shadow → shadow/shadow_log.csv        MODE=live → Google Sheet "Queue" tab
                                                     ▼
          ┌──────────────── HUMAN IN THE LOOP (docs/runbook.md, 1 hr/day) ────────────────┐
          │ ops reviews/edits → Reddit & The Bump: posts as a disclosed SchoolPath helper  │
          │                   → FB groups & Nextdoor: sends draft to a local ambassador,   │
          │                     who edits it into their own voice and posts it             │
          │ follow-ups and call-outs: prompts/followup.md + escalation rules               │
          └───────────────────────────────────────┬───────────────────────────────────────┘
                                                  ▼
          weekly "signups by UTM" export ──► sp/report.py ──► scorecard by channel, post type,
                                                              reply style, account → kill / double down
```

## One page on how it works

**Where the parents are.** I started from the SA School Analytics export (3,282 posts, 9 groups). Only 23 posts in 15 months were both about ages 0–5 and inside our geography, and none of the 9 groups covers the Schertz / Cibolo / Garden Ridge corridor (details in `docs/data-findings.md`). So discovery is built around the places those parents actually ask: parent groups and Nextdoor in the Northeast, military spouse and PCS groups around JBSA-Randolph, SA Charter Moms Discussion, and r/sanantonio and r/JBSA.

**Why a human posts, and why the identity is disclosed.** Closed Facebook groups and Nextdoor screen members by address and won't let an offshore account in. Scraping them, or faking local accounts to get in, is exactly what gets accounts banned and gets screenshotted. So those channels run through 3 to 5 real local parents (ambassadors) who post from their own accounts and say they help SchoolPath. Open channels run through one named, disclosed SchoolPath helper. Disclosure is normal in these groups already ("I work for the enrollment office, feel free to contact me…"). A reply nobody could mistake for a bot is easier to build when nothing in it is fake.

**What makes a reply not look like a bot** (enforced in code, not left to discipline):
- The draft answers the actual question in the first sentence and only states school facts listed in `data/verified_schools.yaml`.
- It has at most one link, a clean `schoolpath.co/r/xxxx` instead of a UTM wall, and can be set to drop the link entirely on some replies.
- It never replies within 25 minutes of a post. Each account gets at most 3 replies a day, each group at most 2 a day, and posting times are jittered.
- A human edits every reply into their own voice before posting.

**Where the link goes.** `best_landing` picks the page that answers the question: the zip/age search and quiz for "find me a pre-K", events for deadline and open-house questions, the TEFA page for funding questions. Never the signup page.

**Tracking.** Every reply gets its own id, sent as `utm_content`, with the post type in `utm_term`. SchoolPath's weekly signups-by-UTM export joins back to the queue, so `python run.py report` shows results by channel, post type, reply style, and account, with kill and double-down hints that match `docs/experiment-plan.md`.

## Run it

```bash
pip install -r requirements.txt
cp .env.example .env            # MODE=shadow by default. MODE=live is the single switch to go live.
python run.py discover          # raw discovery, no LLM, writes shadow/discovered.csv
python run.py discover-and-draft                 # full daily run
python run.py discover-and-draft --input shadow/discovered.csv
python run.py report --queue sheet/queue.csv --signups week1.csv --spend 38
```

With no `ANTHROPIC_API_KEY`, the pipeline uses the **file backend**: it writes each prompt to `shadow/pending_prompts/` and reads the answers from `shadow/llm_responses.jsonl`. You can run the whole system by pasting prompts into any chat model. Going live with a key requires no code changes.

## Repo map

| Path | What it is |
|---|---|
| `config.yaml` | Everything tunable: geography, keywords, sources, landing pages, cadence caps, models |
| `prompts/` | `score.md`, `draft.md`, `followup.md`, plain text, edit freely |
| `data/verified_schools.yaml` | The only school facts a draft may state, each with a source |
| `sp/` | Pipeline code (discover, prefilter, llm, links, accounts, pipeline, report) |
| `sheet/` | Ops-sheet tab templates: accounts, capture, queue |
| `shadow/shadow_log.csv` | Shadow-mode run: every post detected, its scores, the draft, and the link |
| `docs/data-findings.md` | What the SA School Analytics sample says, and where it falls short |
| `docs/runbook.md` | Deploy in under 60 minutes + the daily ops playbook |
| `docs/experiment-plan.md` | Hypotheses, week-by-week plan, scorecard, $250 budget |
| `docs/offshore-dev-spec.md` | The one thing I'd ask the offshore dev to build (≈2 hrs) |
| `docs/shadow-review.md` | My honest read of the shadow log |

## Build vs. buy

| Need | Choice | Why |
|---|---|---|
| Listening | Built (≈300 lines) | Octolens ($199/mo) and ReplyGuy are built for brand mentions on global platforms and can't see closed local groups. Reddit's public search plus Google Programmable Search cover the open web for $0. |
| Closed groups | Humans (ambassadors + Capture form) | No tool can legitimately read them. |
| Qualify + draft | LLM, prompts as files | Cheap model for scoring, stronger model only for drafts. The keyword gate cuts LLM calls by about 90%. |
| Ops interface | Google Sheet | The offshore team already knows it, it's free, and it has filters and status dropdowns. A web app would be slower to change. |
| Posting | Never automated | Redreach deliberately doesn't auto-post because it gets accounts banned. Same call here. |
| Short links | `schoolpath.co/r/<code>` route (2 hrs of dev) | A first-party domain looks like a normal link. Bitly-style shorteners look like ads. |
| Scheduler | GitHub Actions cron | Free, no server. |

## AI tools used

- **Claude** (claude.ai): data analysis of the export, code scaffolding, prompt drafting, drafting the runbook and experiment-plan docs, and acting as the LLM for the shadow run through the file backend.
- The strategy memo is written by me.
