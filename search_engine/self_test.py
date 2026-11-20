"""
VALE self-test - batch 5 of the plan.

Everything else in search_engine/ either does work quietly in the
background, or stays silent until something goes wrong. This file is
different on purpose: run it, and it actually TRIES each piece, right
now, live, and reports in plain words what worked and what didn't - so
checking on VALE never means digging through logs.

Checks, in order:
    1. storage      - can VALE read anything it has already saved?
    2. DRIVER        - does a real live search actually return something?
    3. source state  - how many sources are tracked, how many are due
    4. optional extras - providers (Brave/Tavily) and the AI helper
                         (Groq) - "off" is a normal, healthy answer here,
                         not a failure, since neither needs a key to be
                         safe; this just says whether a key is set.

Never raises - a piece that fails just gets its own entry so you know
which one.
"""
from __future__ import annotations

import time
from typing import Any, Dict


def _check_storage() -> Dict[str, Any]:
    try:
        from search_engine import storage
        total = storage.count()
        return {"ok": True, "total_saved": total}
    except Exception as error:
        return {"ok": False, "error": type(error).__name__}


def _check_driver() -> Dict[str, Any]:
    try:
        from DRIVER import driver_brain
        started = time.time()
        results = driver_brain.search_web("gold price today", 3)
        return {
            "ok": len(results) > 0,
            "results_found": len(results),
            "took_ms": int((time.time() - started) * 1000),
        }
    except Exception as error:
        return {"ok": False, "error": type(error).__name__}


def _check_source_state() -> Dict[str, Any]:
    try:
        from search_engine import source_state
        return {
            "ok": True,
            "known_sources": len(source_state.known_urls()),
            "due_for_check": len(source_state.due_for_check(max_age_hours=6, limit=2000)),
        }
    except Exception as error:
        return {"ok": False, "error": type(error).__name__}


def _check_extras() -> Dict[str, Any]:
    extras: Dict[str, Any] = {}

    try:
        from search_engine import providers
        extras["providers"] = "on" if providers.any_configured() else "off (no key set - this is fine)"
    except Exception as error:
        extras["providers"] = f"not loaded ({type(error).__name__})"

    try:
        from search_engine import ai_helper
        extras["ai_helper"] = "on" if ai_helper.is_configured() else "off (no key set - this is fine)"
    except Exception as error:
        extras["ai_helper"] = f"not loaded ({type(error).__name__})"

    try:
        from search_engine import meaning_search
        extras["meaning_search"] = "on" if meaning_search.score("test", "test") == 1.0 else "loaded but acting oddly"
    except Exception as error:
        extras["meaning_search"] = f"not loaded ({type(error).__name__})"

    try:
        from search_engine import source_reliability
        extras["source_reliability"] = {"ok": True, "most_seen": source_reliability.most_seen(limit=3)}
    except Exception as error:
        extras["source_reliability"] = f"not loaded ({type(error).__name__})"

    try:
        from DRIVER import bridge_to_legend  # noqa: F401 - only checking it loads; never called from here
        extras["bridge_to_legend"] = "loaded (call it yourself with a real LEGEND instance when ready)"
    except Exception as error:
        extras["bridge_to_legend"] = f"not loaded ({type(error).__name__})"

    return extras


def run() -> Dict[str, Any]:
    """The full self-test. Returns one plain, readable report."""

    storage_result = _check_storage()
    driver_result = _check_driver()
    state_result = _check_source_state()
    extras_result = _check_extras()

    all_core_ok = storage_result.get("ok") and driver_result.get("ok") and state_result.get("ok")

    return {
        "overall": "healthy" if all_core_ok else "needs attention",
        "storage": storage_result,
        "driver_live_search": driver_result,
        "source_state": state_result,
        "optional_extras": extras_result,
    }
