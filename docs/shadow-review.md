# Shadow run: what the log shows

**File:** `shadow/shadow_log.csv`. Each row is one detected post: source, link, text, keyword score, LLM intent score, priority, the drafted reply, the exact link it would use, the account and posting window it would get, and the reviewer note.

**What was run:**
- **SA School Analytics export (real local Facebook posts, May 2025 – Aug 2026).** 3,282 posts went through the keyword gate. 330 were early-ed, and 56 of those named a place in or near our geography. All 56 were scored and 23 were drafted.
- **Live sources:** see "Live run" at the bottom. My build environment's network can't reach Reddit, so live discovery (`python run.py discover`) runs from a normal machine and feeds the same pipeline with `--input`.
- **The LLM step** used the repo's file backend: each prompt in `prompts/` was answered by Claude and stored in `shadow/llm_responses.jsonl`, so the run reproduces exactly with no API key. With a key, the same prompts run through the API.

## Funnel inside the run

| Stage | Count |
|---|---|
| Posts in | 3,282 |
| Pass keyword gate (ages 0–5, not an ad) | 330 |
| ...and name a place in or near North SA | 56 |
| LLM says: a parent actually asking, ages 0–5, not outside geography | 36 |
| Priority ≥ 60, drafted | 23 |
| Assigned to an account within cadence caps | 21 (2 held by the 2-per-group-per-day cap) |

## My read of the 23 drafts

| Verdict | Count | Reply ids | Why |
|---|---|---|---|
| **Send as-is** (after a 1-line voice edit) | 10 | 415b6b, 8e5cfe, be2d7a, 0823fc, 821aa7, 919af7, 74abd7, af69eb, 890d85, 32042a | Answer first, specific to what they named, no unverified claims. The Randolph military reply (415b6b) is the best one in the log: concrete ("get on the CDC waitlist the day you have orders"), sourced, and it lands on the zip search they need. |
| **Send after a fact check** | 3 | f8c3ae, 8c746d, 8931d6 | They rely on time-sensitive facts: the Founders half-day hybrid still being offered, the Bezos Academy window, NEISD choice dates. The reviewer note says exactly what to check. |
| **Human rewrites part of it** | 7 | a58de3, 366171, 30506a, fdb1a7, b2f63c, 43d92c, 7c42e4 | 5 are special-needs posts (autism, ADHD, non-speaking). The structure is right, but a parent should write the first lines, and 2 should go out with no link at all. 366171's source post is mostly an image, so the human must read the thread. 30506a points to Bezos Academy, whose application window is seasonal, so check it's open first. |
| **Don't send** | 2 | 591528, 19304b | 591528 is a false positive: "Kinder Ranch" is an elementary school's name, not kindergarten. 19304b asks for Founders parents' first-hand experience. Unless the ambassador actually has a kid there, any reply is filler. |
| **Held by cadence** | 1 | 181268 | A third qualifying post in the same group that day. Post it the next day if the thread is still under 72 hours old. |

So **13 of 23 (57%) are sendable with light edits, 7 need a human, 2 shouldn't go out, and 1 waits a day.** That's the split I designed for. The ops hour goes to the 7, not the 13.

## What the misses tell me

1. **I caught the system's own bot pattern.** In the first pass, 19 of 22 drafts used the same disclosure line, "(full disclosure, I help out with SchoolPath)". A parent who saw two of them would call it a bot, and they'd be right. I added a repeated-phrase detector (`flag_repeats` in `sp/pipeline.py`): any 5-word phrase in 3+ recent replies gets a REWORD note. I also changed the draft prompt to receive recently used disclosure lines and avoid them. The log shows the second pass, with 0 flags. **Takeaway: "human-ness" has to be checked across replies, not just within one.**
2. **The data is skewed toward kindergarten comparisons, not daycare.** Of the 23 drafts, 14 are about kinder, 7 pre-K, and 1 is about a daycare. The sample comes mostly from a charter-school parents group. Parents of 0–3 year olds ask somewhere else (subdivision groups, Nextdoor, military spouse groups), which is why the Capture form and ambassadors are the main discovery path for closed groups, not a nice-to-have.
3. **The landing page is the weakest link for comparisons.** For "Founders vs Great Hearts," the right link is the two school profiles, not `/en/pre-k`. The site blocks crawlers, so I couldn't confirm profile URL patterns, and search filters don't appear in the URL. `docs/offshore-dev-spec.md` asks for shareable filter links. I'd expect this to matter more for conversion than anything in the drafts.
4. **Geography keywords are noisy at the edges.** "1604" and citywide group names pulled in 8 posts from outside the target area (UTSA, Bandera, Alamo Ranch, Helotes, central SA). The LLM rejected all 8 correctly, but each one costs a scoring call. "Kinder" matched the school name Kinder Ranch. Fix: add northwest exclusions and "kinder ranch" to `config.yaml` before going live.
5. **Some real needs fall just under the threshold.** Three examples:
   - A new-to-area parent whose 3-year-old is aging out of ECI scored 53, because "near 1604" is unknown geography.
   - A PK3 parent with an autistic son scored 55.
   - An NEISD kinder open-enrollment question scored 55.
   
   I'd rather see these than miss them. In week 1, the ops person reviews everything scoring 50–59 for 2 days, and we lower the threshold if more than a third of those deserve replies.
6. **One reply per group per day was too strict.** On May 20, three qualifying parents posted in the same group, and a 1-per-day cap would have dropped the military-family post (priority 90). The cap is now 2 per group per day, and they must come from different accounts. Assignment also runs in priority order, so the best posts get the slots.
7. **The verified-facts list is thin**, so 9 of 23 drafts are "questions to ask" rather than recommendations. That's safe, but it might convert worse, which is hypothesis H2. Every confirmed tour or parent detail should go into `data/verified_schools.yaml` as it comes in.

## Live run

_Filled in from `python run.py discover` on a normal network. See the rows with source `reddit` in `shadow/shadow_log.csv`._
