"""
ALPHA instrument auto-registry.

Drop a new file into this folder (e.g. brains/alpha/instruments/example.py)
and it is picked up automatically the next time this package is
imported. Nothing else needs to be edited.

Contract each instrument file must follow:

    INSTRUMENT_ID = \"EXAMPLE\"          # required, a short unique string

    def fetch_market_data() -> dict | None:
        \"\"\"Return live data, or None if it cannot be fetched.
        Never fabricate data -- returning None on failure is the
        correct behavior, not an error to hide.\"\"\"
        ...

A file that does not define both INSTRUMENT_ID and fetch_market_data
is skipped and logged, not silently ignored and not fatal to the rest
of the app.
"""
from __future__ import annotations

import importlib
import logging
import pkgutil
from typing import Callable, Dict, Optional

logger = logging.getLogger(__name__)

REGISTRY: Dict[str, Callable[[], Optional[dict]]] = {}
_LOAD_ERRORS: Dict[str, str] = {}


def _discover() -> None:
    """Scan this package folder for instrument modules and register them."""
    package_name = __name__

    for _, module_name, is_pkg in pkgutil.iter_modules(__path__):
        if is_pkg or module_name.startswith("_"):
            continue

        full_name = f"{package_name}.{module_name}"

        try:
            module = importlib.import_module(full_name)
        except Exception as exc:
            _LOAD_ERRORS[module_name] = f"import failed: {exc}"
            logger.warning("Instrument \x27%s\x27 failed to import: %s", module_name, exc)
            continue

        instrument_id = getattr(module, "INSTRUMENT_ID", None)
        fetch_fn = getattr(module, "fetch_market_data", None)

        if not instrument_id or not callable(fetch_fn):
            _LOAD_ERRORS[module_name] = "missing INSTRUMENT_ID or fetch_market_data()"
            logger.warning(
                "Instrument file \x27%s\x27 skipped: must define INSTRUMENT_ID and fetch_market_data()",
                module_name,
            )
            continue

        key = str(instrument_id).upper()

        if key in REGISTRY:
            logger.warning(
                "Instrument id \x27%s\x27 from \x27%s\x27 overwrites an existing registration",
                key,
                module_name,
            )

        REGISTRY[key] = fetch_fn


def get_instrument_data(instrument_id: str) -> Optional[dict]:
    """Fetch live data for one instrument, or None if unknown/unavailable."""
    if not instrument_id:
        return None
    fetcher = REGISTRY.get(str(instrument_id).upper())
    if fetcher is None:
        return None
    try:
        return fetcher()
    except Exception as exc:
        logger.warning("Instrument \x27%s\x27 fetch failed: %s", instrument_id, exc)
        return None


def available_instruments() -> list[str]:
    """List every instrument id currently registered."""
    return sorted(REGISTRY.keys())


def load_errors() -> Dict[str, str]:
    """Instrument files that were skipped, and why."""
    return dict(_LOAD_ERRORS)


_discover()
