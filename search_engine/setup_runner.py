"""
VALE setup runner - runs wikidata_import, api_directory_import, and
link_finder, one after another, in the background - so they can be
triggered from a phone browser instead of needing Colab.

Kept deliberately simple: one run at a time (starting a second one while
the first is still going is refused, not queued), with a small shared
status dict so main.py's /run-setup and /setup-status routes can both
read it. This is for the occasional, one-time-ish work of actually
creating candidate sources in the first place - the ongoing, scheduled
checking of what already exists is wave_runner.py's job, not this file's.
"""
from __future__ import annotations

import importlib
import threading
import time
from typing import Any, Dict

_status: Dict[str, Any] = {"running": False, "started_at": None, "last_result": None}
_lock = threading.Lock()

STEPS = [
    ("wikidata_import", "search_engine.wikidata_import"),
    ("api_directory_import", "search_engine.api_directory_import"),
    ("link_finder", "search_engine.link_finder"),
]


def status() -> Dict[str, Any]:
    """A safe copy of the current status - never the live dict itself."""
    with _lock:
        return dict(_status)


def _run_all() -> None:
    result: Dict[str, Any] = {}

    for name, module_path in STEPS:
        started = time.time()
        try:
            module = importlib.import_module(module_path)
            outcome = module.run()
            result[name] = {"ok": True, "result": outcome, "took_s": round(time.time() - started, 1)}
        except Exception as error:
            result[name] = {"ok": False, "error": type(error).__name__, "took_s": round(time.time() - started, 1)}
            print(f"SETUP RUNNER: {name} failed:", type(error).__name__, flush=True)

    with _lock:
        _status["running"] = False
        _status["last_result"] = result


def start() -> Dict[str, Any]:
    """
    Start the full setup run in the background, unless one is already
    going. Returns immediately either way - call status() to check on it.
    """
    with _lock:
        if _status["running"]:
            return {"started": False, "reason": "a run is already in progress"}
        _status["running"] = True
        _status["started_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    thread = threading.Thread(target=_run_all, name="vale-setup-runner", daemon=True)
    thread.start()
    return {"started": True}
