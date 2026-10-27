# Deploy runbook and daily ops playbook

Part A takes a teammate from this repo to live in under 60 minutes. Part B is what the offshore ops person does every day. Part C covers recruiting ambassadors and group admins, which is the only part that takes longer than an hour, so it starts on day 1 in parallel.

---

## Part A: Go live in under 60 minutes

### Accounts, keys, and config values

| # | Item | Where | Cost / month | Needed for |
|---|---|---|---|---|
| 1 | GitHub repo (this one) + Actions | github.com | $0 (well within free minutes) | Scheduled runs |
| 2 | Anthropic API key | console.anthropic.com | about $5–15 at our volume (budget line: $20 for 4 weeks) | Scoring + drafting |
| 3 | Google account for ops | google.com | $0 | Sheet, Form |
| 4 | Google Sheet "SchoolPath Community Queue" with tabs `Queue`, `Capture`, `Accounts`, `Results` | Google Drive | $0 | Ops interface |
| 5 | Google Cloud service account + JSON key, shared as Editor on the sheet | console.cloud.google.com → IAM → Service accounts | $0 | Pipeline writes to the sheet |
| 6 | Google Programmable Search key + engine ID (optional) | programmablesearchengine.google.com | $0 on the free daily quota | The Bump / indexed Nextdoor |
| 7 | Google Form "Saw a parent asking?" writing to the `Capture` tab | forms.google.com | $0 | Ambassadors paste closed-group posts |
| 8 | Reddit helper account, disclosed (e.g. `u/Maria_at_SchoolPath`) + a "script" app on it (`REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET`) | reddit.com/prefs/apps | $0 | Reddit replies + discovery (Reddit blocks unauthenticated search, so discovery needs the app keys) |
| 9 | `/r/<code>` redirect route on schoolpath.co | offshore dev, see `offshore-dev-spec.md` | $0 cash, about 2 dev hours | Clean links. Until it ships, leave `SHORTLINK_BASE` blank and full UTM links are used. |

There are no proxies, no phone numbers, and no extra Facebook or Nextdoor accounts. That's deliberate.

### Steps

1. **(5 min)** Fork or clone the repo. `pip install -r requirements.txt`. `cp .env.example .env`.
2. **(10 min)** Create the Google Sheet with the four tabs. Paste the headers from `sheet/queue.csv` (the `FIELDS` list in `sp/pipeline.py`), `sheet/capture.csv`, and `sheet/accounts.csv`. In `Queue`, add a dropdown on `status`: `ready_for_review, sent_to_ambassador, posted, skipped_by_human, held`.
3. **(10 min)** Create the service account, download its JSON, and share the sheet with its email as Editor.
4. **(5 min)** Create the Google Form with fields `source`, `group`, `url`, `posted_at`, `text`. Link its responses to the `Capture` tab.
5. **(5 min)** Fill `.env`: `ANTHROPIC_API_KEY`, `GOOGLE_SHEET_ID`, `GOOGLE_SERVICE_ACCOUNT_JSON`, optional CSE keys.
6. **(5 min)** Dry run in shadow: `python run.py discover-and-draft`. Open `shadow/shadow_log.csv` and check a few drafts read well.
7. **(5 min)** In GitHub → Settings → Secrets and variables → Actions, add the same secrets. Set variable `MODE=shadow`. Run the `daily-run` workflow once by hand.
8. **(2 min) THE SWITCH:** set the repository variable `MODE=live` (or `MODE=live` in `.env` for local runs). New drafts now land in the sheet's `Queue` tab. Nothing ever posts automatically. A human always does.
9. **(5 min)** Fill the `Accounts` tab with real people only: the helper plus each recruited ambassador (Part C). Delete the example rows.
10. **(3 min)** Share the sheet with the ops person and the ambassador-facing WhatsApp/text template (Part B, step 4).

---

## Part B: Daily playbook for the ops person (about 1 hour)

Work from the `Queue` tab, sorted by `priority` (highest first). Everything you need is in the row.

**1. Clear the queue (25 min).** For each `ready_for_review` row, in order:
- Open the `url`. If the thread is gone, closed, or already has a great specific answer, set `skipped_by_human` and move on.
- If it's more than 72 hours old, skip it. Late replies look like digging.
- Read `reviewer_note`. Do what it says (e.g. "confirm the deadline is still open").
- Edit the draft. Change at least one sentence so it sounds like the person posting. Check it:
  - It answers their question in the first sentence.
  - Every school fact is in `data/verified_schools.yaml`.
  - There's one link at most.
  - It includes the disclosure line.
  - No phrases like "seamless", "journey", or "hope this helps".
  - **If you'd be embarrassed to see it screenshotted, don't send it.**
- If `risk_flags` include `special_needs_sensitive` or `upset_parent`: rewrite the first two sentences yourself. Drop the link unless they asked where to look.

**2. Post the open-channel replies (10 min).** Reddit and The Bump rows assigned to the helper account:
- Post at or after `post_after`.
- Never more than 3 a day from this account, and never twice in the same thread.
- Set `status=posted` and paste the comment's URL into `url`.

**3. Hand off the closed-group replies (10 min).** Facebook and Nextdoor rows go to the assigned ambassador by text or WhatsApp. Use this exact template:

> "Hi {name}! A parent in {group} is asking: '{one-line summary}'. Here's a draft if it helps, please change anything so it sounds like you: {draft}. Your link: {link}. Only post if you agree with it. Thanks!"

Set `status=sent_to_ambassador`. When they confirm, set `posted`.

**4. Check replies to yesterday's posts (10 min).** Open each comment posted in the last 3 days.
- **Thanks:** like it. Reply only if it's natural.
- **Follow-up question:** run `prompts/followup.md` (or answer directly). No new link unless they ask where to look.
- **"Is this an ad?" / "Is this a bot?":** don't delete and don't deny. Within the hour, reply once:
  > "Fair question. Yes, I help out with SchoolPath, I said that up top. The [specific tip] is real though."
  
  Then stop. Log it in the `Results` tab with the screenshot. Pause that account for 48 hours.
- **Hostile or a mod removes it:** don't reply. Log it. If a group mod objects, that group is off the list until we've asked the admin directly.

**5. Capture (5 min).** Check the `Capture` tab for posts ambassadors sent in. Mark obvious junk as skipped. The next scheduled run scores and drafts the rest.

### Never

- Never create an account that pretends to be a local parent.
- Never post from an account in a group that person isn't really a member of.
- Never post the same wording twice.
- Never reply within 25 minutes of the original post.
- Never post more than 2 SchoolPath-connected replies in one group on one day.
- Never DM a parent first.
- Never mention a child's diagnosis back to the parent.

### Account setup and warm-up

- **Reddit helper:** a real person's first name plus "at SchoolPath" in the username, and a profile bio saying they work at SchoolPath.
  - Week 0: read the rules of r/sanantonio, r/JBSA, and r/MilitarySpouse. Message the mods once: "I work at SchoolPath, a free school-finder for SA families. OK if I answer daycare/pre-K questions with disclosure?"
  - First 7 days: about 10 genuinely helpful comments with **no links**.
  - Keep links in fewer than 1 in 3 of this account's comments (`link_in_every_nth_reply: 3` in config if needed).
- **Ambassadors:** use their existing real accounts, no warm-up needed. They post only in groups they already belong to, at most 3 replies a day across all groups.

---

## Part C: Ambassadors and admins (start day 1, runs in parallel)

**Who to recruit (target 3–5):**
- (1) Parents who have already written SchoolPath school reviews in the target zip codes. SchoolPath profiles are built on parent insight, so these people exist and already like the product.
- (2) A military spouse connected to the JBSA-Randolph spouse/PCS groups.
- (3) A parent active in a Schertz/Cibolo subdivision group.

**Offer:** $5 per signup from their links, capped at $50 per ambassador, plus early access to new features. The disclosure line is a condition of the deal.

**Admins (target: 6 contacted, 2 yes):** message the admins of the 6 biggest relevant groups from the helper's real account:

> "Hi! I work at SchoolPath (free school/daycare finder for SA). Twice a month we put together a list of North SA pre-K and kinder open houses and application deadlines. Would you be OK with us posting it in your group, clearly labeled as from SchoolPath? Happy to send a sample first."

Offer a small disclosed group giveaway as thanks (budget line in `experiment-plan.md`).
