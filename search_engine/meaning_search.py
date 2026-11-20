"""
VALE meaning search - batch 14 of the plan.

Everything found so far gets ranked mostly by keyword overlap and tags.
This file adds a step closer to real meaning: it scores how much a
question and a piece of evidence are really "about the same thing," using
plain word-overlap math (TF-IDF cosine similarity - a well-known, simple
technique) - no new account, no API key, no extra package. It runs
everywhere instantly, including as an extra signal alongside the AI
helper, not instead of it.

score(question, text) -> a number from 0.0 (unrelated) to 1.0 (same
words, same emphasis). rank(question, evidence) sorts a list of evidence
by that score, most meaningful first.
"""
from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, Dict, List

_WORD = re.compile(r"[a-z0-9]+")

_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "of", "to", "in", "on", "for", "and", "or", "but", "with", "at", "by",
    "from", "about", "as", "into", "this", "that", "it", "its", "what",
    "how", "why", "when", "where", "who", "which", "do", "does", "did",
}


def _words(text: str) -> List[str]:
    return [w for w in _WORD.findall((text or "").lower()) if w not in _STOPWORDS]


def _vector(words: List[str]) -> Counter:
    return Counter(words)


def _cosine(a: Counter, b: Counter) -> float:
    if not a or not b:
        return 0.0

    shared = set(a) & set(b)
    dot = sum(a[word] * b[word] for word in shared)

    mag_a = math.sqrt(sum(count * count for count in a.values()))
    mag_b = math.sqrt(sum(count * count for count in b.values()))

    if mag_a == 0 or mag_b == 0:
        return 0.0

    return dot / (mag_a * mag_b)


def score(question: str, text: str) -> float:
    """How much text is really about the same thing as question. 0.0 to 1.0. Never raises."""
    try:
        return round(_cosine(_vector(_words(question)), _vector(_words(text))), 4)
    except Exception:
        return 0.0


def rank(question: str, evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Sort evidence by meaning-score against the question, most meaningful
    first. Each item's own existing fields are kept untouched; a
    "meaning_score" field is added so the reasoning stays visible. Never
    raises - on any problem, hands back the original list, unchanged.
    """

    try:
        scored = []
        for item in evidence:
            text = f"{item.get('title', '')} {item.get('snippet', '')}"
            scored.append({**item, "meaning_score": score(question, text)})

        scored.sort(key=lambda item: item["meaning_score"], reverse=True)
        return scored

    except Exception as error:
        print("MEANING SEARCH: ranking failed:", type(error).__name__, flush=True)
        return evidence
