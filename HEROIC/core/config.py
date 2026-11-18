"""HEROIC configuration. Every value can be overridden with a HEROIC_<NAME> environment variable."""
from __future__ import annotations

import os
from dataclasses import dataclass, fields


def _env(name: str, cast, default):
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        if cast is bool:
            return raw.strip().lower() in ("1", "true", "yes", "on")
        return cast(raw)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class HeroicConfig:
    max_missions: int = 256            # live missions kept in memory (oldest finished ones leave first)
    archive_size: int = 512            # compact summaries of missions that left memory
    max_tasks: int = 40                # hard cap on tasks in one plan
    max_replans: int = 3               # replans allowed before HEROIC escalates instead
    max_rounds: int = 3                # investigation rounds before HEROIC stops and states limits
    max_attempts: int = 2              # tries per task before it counts as failed
    intent_cache_size: int = 1024
    max_request_chars: int = 4000      # only this much of a request is analysed
    task_stall_s: float = 300.0        # a RUNNING task older than this is flagged as possibly stalled
    ttl_market_s: float = 120.0        # freshness limit for market data
    ttl_news_s: float = 21600.0
    ttl_general_s: float = 86400.0
    speak: bool = False                # False: HEROIC never adds text to the user's answer
    learning_buffer: int = 500

    @classmethod
    def from_env(cls) -> "HeroicConfig":
        kw = {f.name: _env("HEROIC_" + f.name.upper(), type(f.default), f.default) for f in fields(cls)}
        return cls(**kw)
