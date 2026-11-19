"""
VALE AI helper - batch 9 of the plan (free AI helpers).

Everything in search_engine/ so far either finds links (storage, live_fetch,
providers) or checks they still work (health_checker, wave_runner). None of
it actually reads and judges what it found. This file adds one small,
genuinely free AI step that can: given a question and the evidence DRIVER
already gathered, put the most relevant pieces first and drop anything
clearly off-topic.

Uses Groq (console.groq.com/keys) - a real, no-credit-card-needed free
tier, fast enough to use on every question without slowing VALE down.
Needs GROQ_API_KEY to do anything; with no key, every function here just
hands back exactly what it was given, unchanged - the same safe pattern
as every other optional piece of search_engine/.

This file only re-orders and trims. It never writes new evidence, never
invents a fact, and never decides bullish or bearish - that is LEGEND's
job, further down the line.
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List

import requests

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MODEL = "llama-3.1-8b-instant"  # small and fast - this is a ranking helper, not a deep thinker
TIMEOUT = (5.0, 15.0)
MAX_ITEMS_TO_RANK = 30  # keep the prompt small and fast


def is_configured() -> bool:
    return bool(os.getenv("GROQ_API_KEY", "").strip())


def ask(prompt: str, max_tokens: int = 200) -> str:
    """
    A plain question to the free model. Returns "" if no key is set, or
    if anything at all goes wrong - never raises, and never blocks the
    rest of VALE on a slow or failed AI call.
    """

    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key or not prompt:
        return ""

    try:
        response = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.0,
            },
            timeout=TIMEOUT,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()

    except Exception as error:
        print("AI HELPER: call failed:", type(error).__name__, flush=True)
        return ""


def _build_prompt(question: str, evidence: List[Dict[str, Any]]) -> str:
    lines = [
        "You are sorting search results by how useful they are for answering a question.",
        f'Question: "{question}"',
        "",
        "Results:",
    ]
    for index, item in enumerate(evidence):
        title = (item.get("title") or "").strip()[:120]
        snippet = (item.get("snippet") or "").strip()[:160]
        lines.append(f"{index}. {title} - {snippet}")

    lines += [
        "",
        "Reply with ONLY the result numbers, most useful first, separated by commas.",
        "Leave out any number that is not actually useful for the question.",
        "Example reply: 2,0,4",
    ]
    return "\n".join(lines)


def rank_evidence(question: str, evidence: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Put the most relevant items first, drop anything the model marks as
    unhelpful. On any problem at all - no key, a bad reply, a failed
    call, an empty list - this hands back the original list, in its
    original order, completely unchanged.
    """

    if not is_configured() or not evidence or len(evidence) < 2:
        return evidence

    work = evidence[:MAX_ITEMS_TO_RANK]
    reply = ask(_build_prompt(question, work), max_tokens=120)

    numbers = [int(n) for n in re.findall(r"\d+", reply)]
    valid = [n for n in dict.fromkeys(numbers) if 0 <= n < len(work)]  # dedupe, keep order, drop bad numbers

    if not valid:
        print("AI HELPER: ranking reply unusable, keeping original order", flush=True)
        return evidence

    ranked = [work[n] for n in valid]
    leftover = evidence[MAX_ITEMS_TO_RANK:]  # anything past the cap, unranked but not thrown away
    return ranked + leftover
