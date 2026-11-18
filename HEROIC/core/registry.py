"""Bounded mission registry (LRU). Finished missions leave first; a compact summary is archived."""
from __future__ import annotations

import threading
from collections import OrderedDict
from typing import Callable, Dict, List, Optional

from .enums import TERMINAL_MISSION
from .models import Mission


class MissionRegistry:
    def __init__(self, max_missions: int = 256, on_evict: Optional[Callable[[Mission], None]] = None) -> None:
        self.max = max(8, int(max_missions))
        self._m: "OrderedDict[str, Mission]" = OrderedDict()
        self._lock = threading.RLock()
        self._on_evict = on_evict
        self.evicted = 0

    def get(self, mission_id: str, touch: bool = True) -> Optional[Mission]:
        with self._lock:
            m = self._m.get(mission_id)
            if m is not None and touch:
                self._m.move_to_end(mission_id)
            return m

    def put(self, m: Mission) -> None:
        with self._lock:
            self._m[m.id] = m
            self._m.move_to_end(m.id)
            over = len(self._m) - self.max
            if over > 0:
                self._evict(over, keep=m.id)

    def _evict(self, n: int, keep: str) -> None:
        victims: List[str] = []
        for mid, m in self._m.items():                       # oldest first
            if len(victims) >= n:
                break
            if mid != keep and m.state in TERMINAL_MISSION:
                victims.append(mid)
        if len(victims) < n:
            for mid in self._m:
                if len(victims) >= n:
                    break
                if mid != keep and mid not in victims:
                    victims.append(mid)
        for mid in victims:
            m = self._m.pop(mid)
            self.evicted += 1
            if self._on_evict is not None:
                try:
                    self._on_evict(m)
                except Exception:
                    pass

    def remove(self, mission_id: str) -> Optional[Mission]:
        with self._lock:
            return self._m.pop(mission_id, None)

    def clear(self) -> int:
        with self._lock:
            n = len(self._m)
            self._m.clear()
            return n

    def ids(self) -> List[str]:
        with self._lock:
            return list(self._m)

    def values(self) -> List[Mission]:
        with self._lock:
            return list(self._m.values())

    def __len__(self) -> int:
        return len(self._m)

    def __contains__(self, mission_id: str) -> bool:
        return mission_id in self._m

    def counts_by_state(self) -> Dict[str, int]:
        out: Dict[str, int] = {}
        with self._lock:
            for m in self._m.values():
                out[m.state.value] = out.get(m.state.value, 0) + 1
        return out
