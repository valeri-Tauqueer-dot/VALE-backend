"""Capability registry and selector. HEROIC chooses the smallest sufficient set of capabilities."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Tuple

from ..core.models import Mission

PROVIDERS: Dict[str, Tuple[str, ...]] = {
    "integration": ("UNITY",), "objective_intelligence": ("HEROIC",),
    "orchestration": ("ALPHA",), "performance": ("ALPHA",),
    "market_intelligence": ("LEGEND",), "trading_intelligence": ("LEGEND",), "market_data": ("LEGEND",),
    "strategy_intelligence": ("LEGEND",),
    "general_reasoning": ("MARCO",), "cross_domain_reasoning": ("MARCO",),
    "human_understanding": ("FEELINGS",), "emotional_context": ("FEELINGS",), "human_perspective": ("FEELINGS",),
    "verification": ("COGNITIVE",), "cognitive_support": ("COGNITIVE",), "system_monitoring": ("SUPERVISOR",),
}
TOOLS: Dict[str, str] = {"external_information": "TOOL:web_search", "knowledge": "TOOL:knowledge_base",
                         "conversation": "TOOL:response_layer"}
FALLBACKS: Dict[str, Tuple[str, ...]] = {
    "market_intelligence": ("MARCO",), "trading_intelligence": ("MARCO",), "strategy_intelligence": ("MARCO",),
    "general_reasoning": ("COGNITIVE",), "cross_domain_reasoning": ("COGNITIVE",),
}
DEFAULT_BRAINS = frozenset({"UNITY", "HEROIC", "ALPHA", "LEGEND", "MARCO", "FEELINGS", "COGNITIVE", "SUPERVISOR"})
_ALIASES = {"FEELING": "FEELINGS", "FEEL": "FEELINGS"}
_CORE = frozenset({"HEROIC", "UNITY", "SUPERVISOR"})


@dataclass(slots=True, frozen=True)
class Resolution:
    capability: str
    provider: Optional[str]
    available: bool
    degraded: bool = False
    tool: bool = False
    reason: str = ""


class CapabilityRegistry:
    def __init__(self, brains: Optional[Iterable[str]] = None, internet: Optional[bool] = None,
                 exclude: Iterable[str] = ()) -> None:
        names = {_ALIASES.get(str(b).upper(), str(b).upper()) for b in (brains or ())}
        down = {_ALIASES.get(str(b).upper(), str(b).upper()) for b in exclude}
        self.assumed = not names
        self.brains: FrozenSet[str] = frozenset((names or DEFAULT_BRAINS) - down)
        self.internet = internet

    def has(self, brain: str) -> bool:
        return _ALIASES.get(brain.upper(), brain.upper()) in self.brains

    def resolve(self, cap: str) -> Resolution:
        if cap in TOOLS:
            ok = True if cap != "external_information" else self.internet is not False
            return Resolution(cap, TOOLS[cap], ok, False, True, "" if ok else "internet search is not available")
        provs = PROVIDERS.get(cap, ())
        for p in provs:
            if self.has(p):
                return Resolution(cap, p, True)
        for fb in FALLBACKS.get(cap, ()):
            if self.has(fb):
                return Resolution(cap, fb, True, degraded=True, reason=f"{provs[0] if provs else cap} is not registered")
        return Resolution(cap, provs[0] if provs else None, False, reason="no provider registered for this capability")


class CapabilitySelector:
    def select(self, m: Mission, net_plan: Optional[dict], caps: CapabilityRegistry) -> Dict[str, Any]:
        required: List[str] = []
        optional: List[str] = []
        tools: List[str] = []
        unavailable: List[Dict[str, Any]] = []
        degraded: List[Dict[str, Any]] = []
        for t in m.tasks.values():
            r = caps.resolve(t.capability)
            if r.tool:
                if r.available and t.capability not in tools:
                    tools.append(t.capability)
            elif r.provider and r.available:
                bucket = required if t.mandatory else optional
                if r.provider not in bucket:
                    bucket.append(r.provider)
            if not r.available:
                unavailable.append({"capability": t.capability, "task": t.id, "mandatory": t.mandatory, "reason": r.reason})
            elif r.degraded:
                degraded.append({"capability": t.capability, "task": t.id, "using": r.provider, "reason": r.reason})
        mand = [t for t in m.tasks.values() if t.mandatory]
        needs_alpha = bool(m.plan) and (any(t.capability == "orchestration" for t in mand)
                                        or m.plan.max_parallelism() >= 3 or len(mand) >= 6)
        if needs_alpha:
            if caps.has("ALPHA"):
                if "ALPHA" not in required:
                    required.append("ALPHA")
            else:
                unavailable.append({"capability": "orchestration", "task": None, "mandatory": False,
                                    "reason": "ALPHA is not registered; the network runs the plan step by step"})
        required = [b for b in required if b != "HEROIC"]
        optional = [b for b in optional if b not in required and b != "HEROIC"]
        not_needed = sorted(b for b in caps.brains if b not in required and b not in optional and b not in _CORE)
        out: Dict[str, Any] = {"required_brains": required, "optional_brains": optional, "tools": tools,
                               "unavailable": unavailable, "degraded": degraded, "not_needed": not_needed,
                               "assumed_registry": caps.assumed}
        if net_plan:
            net = {_ALIASES.get(str(b).upper(), str(b).upper())
                   for b in list(net_plan.get("required_brains", [])) + list(net_plan.get("optional_brains", []))}
            net -= {"HEROIC"}
            out["network_alignment"] = {"network_selected": sorted(net),
                                        "needed_but_not_selected": sorted(set(required) - net),
                                        "selected_but_not_needed": sorted(net - set(required) - set(optional) - {"UNITY"})}
        return out
