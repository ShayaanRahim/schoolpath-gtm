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
3. **The landing page is the weakest link for comparisons, and the catalog is the reason.** For "Founders vs Great Hearts," the right link is the two school profiles, not the search page. Profile URLs turned out to be uuids (`/en/marketplace/schools/<uuid>`), so they live in `data/verified_schools.yaml`. Of the 5 schools parents mention most, **only SST Sonterra has a SchoolPath page.** The two SST comparison drafts (8e5cfe, 366171) now link straight to its profile, use its Nov 1 – Jan 1 application window and book-a-tour button, and quote only operational review themes. The other comparisons still land on search, and each one is logged as a catalog gap (Great Hearts Live Oak 7 times in this log, Founders Schertz 4, BASIS North Central 3). Adding those schools is probably the single biggest conversion lever, and it's a product fix, not a GTM one.
4. **Geography keywords are noisy at the edges.** "1604" and citywide group names pulled in 8 posts from outside the target area (UTSA, Bandera, Alamo Ranch, Helotes, central SA). The LLM rejected all 8 correctly, but each one costs a scoring call. "Kinder" matched the school name Kinder Ranch. Fix: add northwest exclusions and "kinder ranch" to `config.yaml` before going live.
5. **Some real needs fall just under the threshold.** Three examples:
   - A new-to-area parent whose 3-year-old is aging out of ECI scored 53, because "near 1604" is unknown geography.
   - A PK3 parent with an autistic son scored 55.
   - An NEISD kinder open-enrollment question scored 55.
   
   I'd rather see these than miss them. In week 1, the ops person reviews everything scoring 50–59 for 2 days, and we lower the threshold if more than a third of those deserve replies.
6. **One reply per group per day was too strict.** On May 20, three qualifying parents posted in the same group, and a 1-per-day cap would have dropped the military-family post (priority 90). The cap is now 2 per group per day, and they must come from different accounts. Assignment also runs in priority order, so the best posts get the slots.
7. **The verified-facts list is thin**, so 9 of 23 drafts are "questions to ask" rather than recommendations. That's safe, but it might convert worse, which is hypothesis H4. Every confirmed tour or parent detail should go into `data/verified_schools.yaml` as it comes in.
8. **The review summaries need a safety filter before replies can use them.** SST Sonterra's AI summary leads with racial discrimination and violence concerns from 4 reviews. A reply that repeats that ("I heard...") from a SchoolPath-connected account is a legal and partner risk. School entries now carry `safe_review_themes` and a `never_repeat` list, and the draft prompt only paraphrases operational themes, credited to the reviews, with the review count.

## Live run

`python run.py discover` ran from a home network on Oct 27, 2026. **Reddit returned `403 Blocked` on every request** across 5 subreddits × 8 queries. Reddit now blocks unauthenticated search. Its developer page steers new apps to Devvit, which only runs inside subreddits you moderate, so it can't listen to r/sanantonio. That's why discovery now tries OAuth (if keys are approved), then public JSON, then RSS, and falls back to the human Capture path. The ops person does a 5-minute daily search of r/sanantonio and r/JBSA in a browser and pastes matches into the Capture form, where they go through the same scoring and drafting. Live posts captured that way are marked `source = capture` in `shadow/shadow_log.csv`.
