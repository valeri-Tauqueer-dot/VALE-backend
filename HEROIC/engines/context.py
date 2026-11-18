"""Context controller: turns VALE's shared brain state into one small, typed Context."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, FrozenSet, Optional, Tuple

from ..core.util import clip, now_ns

MEDIA_MARKER = "=== VALE MEDIA CONTEXT ==="
_USER_Q = "USER QUESTION:"
_KEYS = ("user_request", "user_input", "message", "request", "query")
_ALIASES = {"FEELING": "FEELINGS", "FEEL": "FEELINGS"}


@dataclass(slots=True)
class Context:
    request: str
    media: bool
    history: Tuple[str, ...]
    network_plan: Optional[dict]
    registered: FrozenSet[str]
    internet_results: int
    internet_performed: bool
    internet_available: Optional[bool]
    external_required: bool
    now_ns: int
    sig: str

    @property
    def has_history(self) -> bool:
        return bool(self.history)


def _get(state: Any, key: str, default: Any = None) -> Any:
    getter = getattr(state, "get", None)
    if callable(getter):
        try:
            return getter(key, default)
        except Exception:
            return default
    return default


def split_media(raw: str) -> Tuple[str, bool]:
    """Return (the user's own words, whether a media block was attached). Never scans the whole block."""
    i = raw.find(MEDIA_MARKER)
    if i < 0:
        return raw, False
    head = raw[:i].strip()
    if head.startswith(_USER_Q):
        head = head[len(_USER_Q):].strip()
    return head, True


class ContextController:
    @staticmethod
    def extract_request(state: Any) -> str:
        for key in _KEYS:
            v = _get(state, key)
            if isinstance(v, str) and v.strip():
                return v.strip()
        v = getattr(state, "user_message", "")
        return v.strip() if isinstance(v, str) else ""

    def from_text(self, text: str) -> Context:
        """A Context for programmatic use, when there is no brain state."""
        t, media = split_media(text or "")
        return Context(request=t, media=media, history=(), network_plan=None, registered=frozenset(),
                       internet_results=0, internet_performed=False, internet_available=None,
                       external_required=False, now_ns=now_ns(), sig="text")

    def build(self, state: Any, request_override: Optional[str] = None) -> Context:
        raw = request_override if request_override is not None else self.extract_request(state)
        text, media = split_media(raw)
        if media and not text:
            text = "Understand the attached file"

        history = []
        conv = getattr(state, "conversation", None)
        if isinstance(conv, list):
            for item in conv[-10:]:
                if isinstance(item, dict) and item.get("role") == "user":
                    c = item.get("content")
                    if isinstance(c, str) and c.strip():
                        c, _ = split_media(c.strip())
                        if c and c != text:
                            history.append(clip(c, 200))
        history = history[-4:]

        plan = _get(state, "task_plan")
        regs = _get(state, "registered_brains") or ()
        registered = frozenset(_ALIASES.get(str(b).upper(), str(b).upper()) for b in regs)
        results = _get(state, "internet_results") or ()
        n_results = len(results) if hasattr(results, "__len__") else 0
        performed = bool(_get(state, "internet_research_performed", False))
        available = _get(state, "internet_available")
        external = bool(_get(state, "external_information_required", False))
        sig = f"{n_results}|{int(performed)}|{available}|{int(external)}|{len(registered)}"
        return Context(request=text, media=media, history=tuple(history),
                       network_plan=plan if isinstance(plan, dict) else None, registered=registered,
                       internet_results=n_results, internet_performed=performed,
                       internet_available=available if isinstance(available, bool) else None,
                       external_required=external, now_ns=now_ns(), sig=sig)
