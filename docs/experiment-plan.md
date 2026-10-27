# 4-week experiment plan, scorecard, and budget

## Funnel math (what gets us to 50)

| Lane | Volume | Click step | Signup step | Signups |
|---|---|---|---|---|
| A. Reactive replies (all channels) | 8–15 qualifying posts/week → ~40 replies posted in 4 weeks (about 20% skipped by humans) | ~3 clicks per reply (the asker plus a few readers) → ~120 clicks | 20% → | **~24** |
| B. Admin-approved proactive posts, alternating the **deadlines roundup** ("North SA pre-K & kinder open houses + deadlines": SST Sonterra's window opens Nov 1) and the **pre-K fit quiz** (`quiz/index.html`) | 2 groups say yes × 3 posts = 6 posts, ~2,000 views each | 1% click → ~120 clicks | 20% → | **~24** |
| C. Ambassador personal referrals (their own feeds, playgroups, texts) | 3 ambassadors | n/a | ~4 each | **~12** |
| **Total** | | | | **~60 vs. target 50** |

- **Least sure of:** the 20% click-to-signup rate. Nobody has measured it for this traffic, and it depends on what counts as a signup (email vs. account vs. finished quiz). At 10%, lanes A and B halve and the total is about 36. The plan misses.
- **Second least sure:** whether 2 of 6 admins say yes. Without lane B we're at about 36.
- **Lane A alone gets about 24.** The honest headline: replying to posts can't hit 50 by itself in this geography. In 15 months of the sample, only 23 posts were both ages 0–5 and in target geography, and November is the seasonal low for "recommend a daycare" posts (`data-findings.md`). Lane B is designed for exactly that: November–January is application and open-house season.

## Hypotheses

| # | Hypothesis | Metric | Decision rule |
|---|---|---|---|
| H1 | Ambassador replies in FB groups / Nextdoor convert at least 2× better per reply than the helper's Reddit replies | signups per reply posted (clicks per reply as the early read) | After ≥10 replies in each: if FB/ND ≥ 2× Reddit, cut Reddit to 1 reply/day and move the time to capture + ambassador support. If Reddit ≥ FB/ND, recruit fewer ambassadors and give Reddit a second disclosed account. |
| H2 | Replies that link to the **specific school's SchoolPath page** (when the parent names a school that has one) convert better than replies linking to the general search | signups per click | After 30 clicks each: if profile links win, prioritize school-mention posts in the queue and give the product team the catalog-gap list (`python run.py catalog-gaps`) to add the most-discussed schools first. If search wins, the profile pages need work before we drive traffic to them. |
| H3 | The **fit quiz** post brings more signups per post than the **deadlines roundup** | signups per proactive post | Alternate formats in each approved group. After 2 of each: the winner gets the remaining slots. If both get <1 signup, stop proactive posts and put the time into lane A. |
| H4 | "Questions to ask" replies beat "direct answer" replies | clicks per reply, then signups per reply | The drafter alternates styles where both fit. After 15 replies each, the loser becomes the exception: set the default in `prompts/draft.md`. |

## Week by week

| Week | Do | Decide at the end of the week, and what data triggers it |
|---|---|---|
| 0 (2 days before launch) | Deploy (runbook Part A). Offshore dev hosts the quiz at schoolpath.co/fit and builds `/r/<code>`. Message 6 admins. Recruit ambassadors from SchoolPath's existing parent reviewers + one JBSA spouse. Reddit helper starts link-free warm-up. Draft the special-needs guide (ECI-at-3 transition, how to request a free district evaluation, what to ask private programs about on-site therapy). 7 of 23 shadow drafts were special-needs posts, so this is the reply asset for them. | Go/no-go: ≥1 ambassador live, or start Reddit + Capture only and keep recruiting. |
| 1 | Lane A on all channels. Ops 1 hr/day. First proactive post (the deadlines roundup, since SST Sonterra's window opens Nov 1) if an admin has said yes. | **Kill** any source with 0 qualifying posts all week (remove it from `config.yaml`). **If <2 ambassadors**, move bounty money to admin thank-yous and push lane B. **If any reply gets called out**, review that account's last 5 replies and tighten `draft.md`. |
| 2 | Keep A + B running. Start H2 alternation. | **H1 call** (≥10 replies per side). **H3 first read.** **Kill** any channel with ≥10 replies, 0 signups, and ≤2 clicks. **Fix landing** for any channel with ≥10 clicks and 0 signups. |
| 3 | Double down on the winning channel and style. A second roundup in each approved group. | **H2 call. H4 call.** If cumulative signups < 20, ask the founders to flex the target or approve one paid boost of the best roundup post (≤$30 from contingency). |
| 4 | Run the winners only. Write the final report. | What to keep running in month 2, with each channel's cost per signup. |

## Weekly scorecard (template: `reports/scorecard_template.csv`)

`python run.py report` fills the results columns from the UTM export. Activity and results are kept apart deliberately, so a busy week with no signups can't look like a good week.

| | Week 1 | Week 2 | Week 3 | Week 4 |
|---|---|---|---|---|
| **ACTIVITY** | | | | |
| Posts discovered (all sources) | | | | |
| Posts qualified (priority ≥ 60) | | | | |
| Replies drafted | | | | |
| Replies posted (helper / ambassadors) | | | | |
| Roundups posted | | | | |
| Ops minutes spent | | | | |
| Call-outs ("ad" / "bot") | | | | |
| **RESULTS** | | | | |
| Clicks (redirect log) | | | | |
| Signups (UTM export) | | | | |
| Signups per reply | | | | |
| Spend this week ($) | | | | |
| Cost per signup (cumulative) | | | | |
| **BY CHANNEL** (signups / replies): Reddit · FB groups · Nextdoor · Roundups · Referrals | | | | |
| **DECISIONS MADE** | | | | |

## Budget: 4 weeks, $250 all-in

| Item | Cost | Notes |
|---|---|---|
| LLM tokens (Anthropic API) | $20 | Keyword gate first. Cheap model scores, stronger model drafts only posts with priority ≥ 60. Expected spend is lower. |
| Ambassador bounties | $150 cap | $5 per attributed signup, max $50 per ambassador. This scales with results, so if signups don't come, the money isn't spent. |
| Admin thank-yous | $50 | 2 × $25 disclosed group giveaways ("courtesy of SchoolPath") for groups that host roundups |
| Contingency | $30 | Week-3 boost of the best roundup, or a third admin |
| Reddit, Google Sheets/Forms, GitHub Actions, Programmable Search (free tier) | $0 | |
| Proxies, phone numbers, extra accounts | $0 | Deliberately none. Sockpuppets are the ban risk. |
| **Total** | **$250** | At 50 signups, the worst case is $5.00 per signup. At the projected ~60, about $4.20. |

## Constraint I'd push back on

$5 per signup is a fine ceiling. But **50 signups from replies alone isn't realistic in this geography in November**, and the data shows it (23 qualifying posts in 15 months across 9 groups). I'd rather be held to "50 signups across replies + roundups + referrals, with a cost-per-signup breakdown by lane" than have the team chase reply volume. That chase is what pushes people toward the fake accounts that get the brand screenshotted.
