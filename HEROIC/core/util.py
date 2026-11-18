"""Small, fast helpers shared by every HEROIC engine."""
from __future__ import annotations

import hashlib
import re
import time
from typing import List, Set

_TOKEN = re.compile(r"[^\W_]+(?:['&.\-][^\W_]+)*")

STOPWORDS = frozenset(
    "a an the and or but if then so of to in on at by for from with about as is are was were be been being am "
    "do does did can could should would will shall may might must i me my mine we us our you your he she it its "
    "they them their this that these those there here what which who whom whose when where why how please just "
    "also very really quite some any all more most much many".split()
)


def now_ns() -> int:
    return time.time_ns()


def mono_ns() -> int:
    return time.perf_counter_ns()


def norm(text: str) -> str:
    return " ".join(text.lower().split())


def tokens(text: str) -> List[str]:
    return _TOKEN.findall(text.lower())


def content_tokens(text: str) -> List[str]:
    return [t for t in _TOKEN.findall(text.lower()) if t not in STOPWORDS]


def jaccard(a: Set[str], b: Set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def fingerprint(*parts: str) -> str:
    return hashlib.blake2b("\x1f".join(parts).encode("utf-8", "ignore"), digest_size=6).hexdigest()


def clip(text: str, n: int) -> str:
    return text if len(text) <= n else text[: n - 1].rstrip() + "…"
