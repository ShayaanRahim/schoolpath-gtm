"""
cheap keyword pre-filter. runs before any llm call so we only pay to score posts that could matter.
on the SA School Analytics sample it cuts 3,282 posts to roughly 300 worth an llm look.
"""
import re

from .common import CONFIG


def _hits(text, terms):
    return [t for t in terms if t.lower() in text]


def prefilter(post):
    """
    scores a post 0-100 on keywords alone and says why.
    input: a post dict. returns (score, reasons, keep) where keep=False means don't send to the llm.
    """
    t = " " + re.sub(r"\s+", " ", post["text"].lower()) + " "
    geo1 = _hits(t, CONFIG["geo"]["tier1"])
    geo2 = _hits(t, CONFIG["geo"]["tier2"])
    age = _hits(t, CONFIG["age_terms"])
    intent = _hits(t, CONFIG["intent_terms"])
    promo = _hits(t, CONFIG["exclude_terms"])

    score = 0
    score += 40 if age else 0
    score += 30 if geo1 else (15 if geo2 else 0)
    score += 20 if intent else 0
    score += 10 if len(t) < 900 else 0          # short asks convert better than essays
    score -= 50 if len(promo) >= 2 else (20 if promo else 0)
    score = max(0, min(100, score))

    reasons = []
    if age: reasons.append("age:" + ",".join(age[:3]))
    if geo1: reasons.append("geo1:" + ",".join(geo1[:3]))
    elif geo2: reasons.append("geo2:" + ",".join(geo2[:3]))
    if intent: reasons.append("ask")
    if promo: reasons.append("promo:" + ",".join(promo[:2]))

    # an early-ed post with no place named can still be local (citywide groups), so keep it
    keep = bool(age) and len(promo) < 2
    return score, "; ".join(reasons), keep
