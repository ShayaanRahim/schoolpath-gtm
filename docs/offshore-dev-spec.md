# Offshore dev spec: first-party short links (about 2 hours, one-time)

**Why:** a reply with `schoolpath.co/en/pre-k?utm_source=facebook&utm_medium=community&utm_campaign=...` looks like an ad. Bitly-style shorteners look like spam. A short link on our own domain looks like a normal link, and it lets us count clicks ourselves, which matters because some platforms strip query strings.

**Build:**
1. Route `GET /r/:code` on schoolpath.co.
2. Look up `code` in a `redirects` table. Columns: `code` (text, primary key), `target` (text), `created_at`.
   - Seed and update the table from `sheet/redirects.csv`, which the pipeline writes in live mode. A nightly import, or a Google Sheet tab synced daily, is fine.
3. Log the click: `code`, timestamp, referrer, user agent, and a hashed IP for de-duplication only.
4. Respond `302` to `target`. The target already carries `utm_source / utm_medium / utm_campaign / utm_content / utm_term`.
5. Unknown code: `302` to `/en/pre-k?utm_source=community&utm_content=unknown`.
6. Make sure the UTM values survive into signup attribution (stored on the session or first-touch cookie), even when the parent browses a few pages before signing up.
7. Weekly: export clicks per `code` as CSV. `python run.py report --clicks clicks.csv` reads it.

**Optional (only if there's time left, since it lifts conversion on every reply):**
- Shareable filter URLs on the school search: `/en/marketplace/schools?zip=78108&age=pk3&schedule=half_day`. Today filters don't appear in the URL, so a reply can't link to "half-day pre-K near Cibolo," only to the general search.
- `og:title` / `og:description` on school profile pages, so link previews in Facebook show the school name instead of a generic card.

**Acceptance:**
- `schoolpath.co/r/test01` redirects to the stored target with UTMs intact.
- A signup after clicking it appears in the weekly export with `utm_content=<reply id>`.
