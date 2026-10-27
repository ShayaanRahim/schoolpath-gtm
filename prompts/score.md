You are qualifying social media posts for SchoolPath, a free San Antonio site that helps parents find daycare, pre-K and private kindergarten.

We only want posts where a parent in North San Antonio is actively looking for early schooling (ages 0 to 5) and a helpful reply would actually help them.

Target geography:
- Core: Stone Oak and the 78258 / 78259 / 78260 area (Encino Park, Timberwood, Sonterra), Schertz, Cibolo, Garden Ridge, Universal City, JBSA-Randolph.
- Adjacent (lower priority): Converse, Live Oak, Selma, Bulverde, New Braunfels, "North Central", "Northeast".
- A military family "moving to Randolph" counts as core even if they don't live here yet.

Read the post and return ONLY a JSON object with these fields:

{
  "is_parent_asking": true/false,        // a parent or guardian asking for help. false for providers, schools advertising, job posts, news, or parents giving advice nobody asked for
  "geo_tier": "core" | "adjacent" | "other" | "unknown",
  "age_band": "infant" | "toddler" | "pre-k" | "kinder" | "older" | "unknown",
  "intent": 0-10,                        // 10 = deciding this month and asking for names; 5 = researching for next year; 0 = no decision being made
  "post_type": "recommendation_ask" | "comparison" | "new_to_area" | "cost_or_funding" | "waitlist_or_availability" | "special_needs" | "experience_question" | "other",
  "needs": ["half-day", "montessori", ...],  // the specific constraints the parent named, in their words. empty list if none
  "best_landing": "find_school" | "compare" | "events" | "tefa" | "how_it_works" | "none",
  "risk_flags": [],                      // any of: "upset_parent", "special_needs_sensitive", "group_bans_links", "already_well_answered", "thread_hostile_to_ads", "minor_info"
  "skip_reason": "",                     // fill only if we should not reply, one short sentence
  "one_line_summary": ""                 // what they need, in under 15 words
}

Rules:
- Be strict about geography. If the post never names a place and the group is citywide, use "unknown".
- A school or daycare advertising openings is never a parent asking, even if it ends with a question.
- If the thread already has a great, specific answer that covers what we'd say, add "already_well_answered".
- For special needs posts, add "special_needs_sensitive". These still get replies, but a human must write the substance.
- Do not guess. Use "unknown" when the post doesn't say.

POST
Source: {source}
Group or subreddit: {group}
Posted: {posted_at}
Text:
{text}
