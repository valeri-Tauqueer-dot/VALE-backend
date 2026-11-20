"""
VALE DRIVER-to-LEGEND bridge - batches 11 and 12 of the plan (prices into
LEGEND, flows into LEGEND), combined into one honest piece.

A note on scope, worth reading before using this: the original plan
named these two batches "prices" and "flows" separately, as if they were
two different data types. DRIVER does not yet tell two kinds of evidence
apart that cleanly - today it gathers market-moving evidence in general
(news, central bank feeds, crypto news, and so on), not a dedicated price
feed or a dedicated money-flow feed. Rather than guess at a narrower
split that might be wrong, this file does the one thing that is
certainly correct either way: it takes whatever DRIVER found and hands
it to LEGEND through LEGEND's own existing add_evidence() method -
nothing invented, nothing skipped.

This file does NOT:
    - decide whether evidence is bullish or bearish (that is LEGEND's
      own job, through its own hypotheses and confidence assessment)
    - set "supports" on the evidence it adds (left as None - exactly
      what LEGEND's own add_evidence() does when it is not told)
    - touch LEGEND's thinking, confidence, or decision logic at all

It is a plain, explicit function, not something wired automatically into
any request - call it yourself, when you are ready, with a real LEGEND
instance and a real state (the same state object LEGEND's other methods
already expect from the brain network).
"""
from __future__ import annotations

from typing import Any, Dict, List


def feed_evidence(legend: Any, state: Any, question: str, n: int = 10) -> Dict[str, Any]:
    """
    Gather DRIVER's evidence for `question` and add every piece to
    `legend` as evidence, through LEGEND's own add_evidence(). Returns a
    small report of what happened - never raises, and never silently
    pretends evidence was added if it was not.

    legend: an already-created LegendBrain instance.
    state:  whatever state object you already pass to LEGEND's other
            methods (add_observation, create_hypothesis, and so on).
    """

    report: Dict[str, Any] = {"question": question, "added": 0, "failed": 0, "evidence_ids": []}

    try:
        from DRIVER import driver_brain
        found = driver_brain.gather_evidence(question, n=n)
    except Exception as error:
        report["error"] = f"could not gather evidence: {type(error).__name__}"
        return report

    for item in found.get("evidence", []):
        claim = (item.get("title") or item.get("url") or "").strip()
        source = (item.get("source") or item.get("via") or "DRIVER").strip()

        if not claim or not source:
            report["failed"] += 1
            continue

        try:
            result = legend.add_evidence(
                state,
                claim=claim,
                source=source,
                evidence=item,
                relevance=item.get("meaning_score") or item.get("score") or None,
            )
            if result.get("success"):
                report["added"] += 1
                report["evidence_ids"].append(result["evidence"]["id"])
            else:
                report["failed"] += 1
        except Exception as error:
            print("BRIDGE TO LEGEND: add_evidence failed:", type(error).__name__, flush=True)
            report["failed"] += 1

    try:
        from search_engine import source_reliability
        source_reliability.record_evidence_sources(found.get("evidence", []))
    except Exception:
        pass  # purely informational history - never worth failing the bridge over

    return report
