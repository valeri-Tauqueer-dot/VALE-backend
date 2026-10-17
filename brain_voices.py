"""
VALE BRAIN VOICES
=================

Lets EVERY brain speak, then puts the voices together into one reply.

Where a voice comes from
------------------------
1. KNOWLEDGE   Text files you drop into a brain's folder:
                   LEGEND/knowledge/*.txt
                   FEEL/knowledge/*.txt        (the FEELINGS brain)
                   HEROIC/knowledge/*.txt  ... and the same for every brain.
               Two formats:
                   Q: What is a stop loss?        (or  USER: / ASSISTANT:)
                   A: An order that closes a trade at a chosen price.

                   Risk only a small part of your account on one trade.   <- a quote
               Add a file, redeploy, and that brain answers.  No code, no retraining.

2. BRAIN       What a brain computed for this question.
                   FEELINGS -> notices the emotion in your message.
                   LEGEND   -> says what it is missing before it can give a market view.
                   Any brain can also speak by returning a short sentence in
                   result["voice"] (or result["message"]).

3. INTERNET    Exa (if EXA_API_KEY is set) or Wikipedia (free fallback).
               Used when nothing else knows the answer, when you ask for the
               latest / news / price / "search ...", or always if you set
               VALE_ALWAYS_SEARCH=1.

The general talking-brain model speaks the general knowledge it memorised;
everything is checked against the stored text first (see knowledge_gate.py).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

try:
    from talking_brain.knowledge_gate import (
        GENERAL_BRAIN,
        content_tokens,
    )
except Exception:  # knowledge_gate.py missing: voices still import
    GENERAL_BRAIN = "VALE"

    def content_tokens(text: str) -> List[str]:  # type: ignore
        return re.findall(r"[a-z0-9]+", (text or "").lower())


MEDIA_MARKER = "=== VALE MEDIA CONTEXT ==="

MEDIA_REPLY = (
    "I received your file, but I can't describe or discuss files yet - "
    "my talking brain is too small for that. "
    "Type a question and I will answer what I can."
)

# How a brain's name is shown to the person (VALE's own text calls it FEELING).
DISPLAY_NAMES = {"FEELINGS": "FEELING", "AI_OS": "AI OS"}


def display_name(brain: str) -> str:
    return DISPLAY_NAMES.get(brain, brain)


MAX_KNOWLEDGE_VOICES = 3
MAX_WEB_VOICES = 2
MAX_WEB_CHARS = 450


# ==========================================================================
# DATA
# ==========================================================================

@dataclass
class Voice:
    brain: str                      # "LEGEND", "FEELINGS", "VALE", "INTERNET" ...
    text: str
    kind: str                       # "knowledge" | "brain" | "internet"
    score: float = 1.0
    source: str = ""                # file name or URL
    spoken_by_model: bool = False
    provider: str = ""              # "exa" | "wikipedia" for internet voices


@dataclass
class Reply:
    text: str
    voices: List[Voice] = field(default_factory=list)
    used_internet: bool = False
    tried_internet: bool = False
    answered: bool = False          # False when only the fallback text was possible

    def brains(self) -> List[str]:
        seen: List[str] = []
        for voice in self.voices:
            if voice.brain not in seen:
                seen.append(voice.brain)
        return seen


# ==========================================================================
# SMALL HELPERS
# ==========================================================================

def question_from(message: str) -> Optional[str]:
    """
    The text the person typed.  /chat-media wraps uploads in a long
    "=== VALE MEDIA CONTEXT ===" block; None means "a file and no question".
    """
    text = str(message or "")
    if MEDIA_MARKER not in text:
        return text.strip()[:400]
    found = re.search(
        r"USER QUESTION:\s*(.+?)\s*(?:\n\s*\n|" + re.escape(MEDIA_MARKER) + r"|$)",
        text,
        re.S,
    )
    if found and found.group(1).strip():
        return found.group(1).strip()[:400]
    return None


_PLACEHOLDER = re.compile(
    r"connected to the unified vale brain network|brain foundation|"
    r"not yet implemented|placeholder|\bstub\b|status: (ready|online)",
    re.I,
)

_QUESTION_START = re.compile(
    r"^\s*(what|whats|what's|who|whom|whose|when|where|why|how|which|is|are|was|"
    r"were|does|do|did|can|could|should|will|would|explain|define|describe|"
    r"tell me|give me|show me|find|search|look up)\b",
    re.I,
)

_SEARCH_REQUEST = re.compile(
    r"\b(search|google|look\s*up|lookup|find out|on the (internet|web)|online|"
    r"latest|news|current|currently|today|right now|price of|how much is|"
    r"who won|score of|recent|update on)\b",
    re.I,
)

# Questions addressed to the assistant itself ("how many brains do you have")
# are about VALE, not the outside world.
_ABOUT_VALE = re.compile(r"\b(you|your|yours|yourself|vale)\b", re.I)

_LIVE_INFO = re.compile(
    r"\b(latest|news|today|current|currently|right now|price|recent|update)\b",
    re.I,
)

_DECISION_REQUEST = re.compile(
    r"\b(should i (buy|sell|short|trade|enter|exit|hold)|buy or sell|"
    r"good time to (buy|sell)|price (target|prediction)|predict|forecast|"
    r"will .{0,40}(go up|go down|rise|fall|pump|dump|moon|crash)|"
    r"trade setup|entry point|signal|analy[sz]e)\b",
    re.I,
)

_MISSING_LABELS = {
    "instrument": "which instrument you are asking about",
    "market_data": "current market data",
    "timeframe": "the timeframe",
    "data_timestamp": "when that data was taken",
}


def looks_factual(question: str) -> bool:
    q = (question or "").strip()
    return bool(_QUESTION_START.match(q)) or q.endswith("?")


def _trim_sentence(text: str, limit: int = MAX_WEB_CHARS) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    if end > limit * 0.5:
        return cut[: end + 1]
    return cut.rsplit(" ", 1)[0] + "..."


# ==========================================================================
# WHAT EACH BRAIN SAYS ABOUT THIS QUESTION
# ==========================================================================

_EMOTION_LINES = {
    "WORRIED": "worried",
    "FRUSTRATED": "frustrated",
    "SAD": "sad",
    "DISCOURAGED": "discouraged",
    "ANGRY": "angry",
    "CONFUSED": "confused",
    "EXCITED": "excited",
    "ENTHUSIASM": "enthusiastic",
    "HAPPY": "happy",
    "URGENT": "under time pressure",
    "RELIEVED": "relieved",
}

_NEGATIVE = {"WORRIED", "FRUSTRATED", "SAD", "DISCOURAGED", "ANGRY"}

_SINGLE_LINES = {
    "WORRIED": "It sounds like you might be feeling worried. That is a very human reaction, and it is okay to feel that way.",
    "FRUSTRATED": "It sounds frustrating. That is understandable, and it is okay to feel that way.",
    "SAD": "I am sorry you are going through this. It is okay to feel sad.",
    "DISCOURAGED": "It sounds discouraging. Setbacks are part of learning, and you are allowed to feel that way.",
    "ANGRY": "It sounds like you are feeling angry, and that is okay. A short pause can help before any big decision.",
    "CONFUSED": "It sounds like this is confusing right now. We can take it one step at a time.",
    "EXCITED": "That sounds exciting! It is good to enjoy a win.",
    "ENTHUSIASM": "I love the energy! Let's put it to good use.",
    "HAPPY": "That is great to hear!",
    "URGENT": "This sounds urgent. Let's slow down just enough to check the facts first.",
    "RELIEVED": "I am glad that feels like a relief.",
}


def _state_names(result: Dict[str, Any]) -> List[str]:
    context = result.get("emotional_context")
    if not isinstance(context, dict):
        return []
    names: List[str] = []
    for raw in context.get("possible_states") or []:
        name = str(getattr(raw, "name", raw)).split(".")[-1].upper()
        if name in _SINGLE_LINES and name not in names:
            names.append(name)
    return names


def feelings_voice(result: Dict[str, Any]) -> Optional[Voice]:
    """The FEELINGS brain noticing an emotion in the message."""
    names = _state_names(result)
    if not names:
        return None

    if len(names) >= 2:
        first, second = names[0], names[1]
        text = (
            "It sounds like you may be feeling a mix of "
            f"{_EMOTION_LINES[first]} and {_EMOTION_LINES[second]}. "
            "Both are normal, and it is okay to feel them together."
        )
    else:
        text = _SINGLE_LINES[names[0]]

    human = result.get("human_experience")
    inferences = " ".join(
        str(x) for x in ((human or {}).get("inferences") or [])
    ).lower() if isinstance(human, dict) else ""

    if "financial" in inferences and names[0] in _NEGATIVE:
        text += " Money decisions are usually easier after a short pause."

    return Voice(brain="FEELINGS", text=text, kind="brain", score=0.5)


def legend_voice(result: Dict[str, Any], question: str) -> Optional[Voice]:
    """LEGEND being honest: it will not invent a market view without data."""
    if not _DECISION_REQUEST.search(question or ""):
        return None
    if result.get("market_analysis_ready") is not False:
        return None
    missing = result.get("missing_information")
    if not isinstance(missing, list) or not missing:
        return None
    labels = [
        _MISSING_LABELS.get(str(m), str(m).replace("_", " "))
        for m in missing
    ]
    need = ", ".join(labels[:-1]) + (" and " if len(labels) > 1 else "") + labels[-1]
    text = (
        "I can't give a buy or sell view yet. To analyse this properly I would "
        f"need {need}. I won't invent a market conclusion without them."
    )
    return Voice(brain="LEGEND", text=text, kind="brain", score=0.5)


def extract_brain_voice(
    name: str,
    result: Any,
    question: str,
) -> Optional[Voice]:
    """Turn one brain's think() result into a spoken sentence (or nothing)."""
    if not isinstance(result, dict):
        return None
    name = str(name).upper()

    try:
        if name in {"FEELINGS", "FEELING", "FEEL"}:
            voice = feelings_voice(result)
            if voice:
                return voice
        if name == "LEGEND":
            voice = legend_voice(result, question)
            if voice:
                return voice
    except Exception as error:      # a brain bug must never break the reply
        print(f"VOICES: {name} voice error: {type(error).__name__}: {error}")

    # Any brain can speak by returning a sentence.
    for key in ("voice", "message"):
        value = result.get(key)
        if (
            isinstance(value, str)
            and 8 <= len(value.strip()) <= 600
            and not _PLACEHOLDER.search(value)
        ):
            return Voice(brain=name, text=value.strip(), kind="brain", score=0.4)
    return None


# ==========================================================================
# THE VOICE BOX
# ==========================================================================

class VoiceBox:
    """Collects what every brain has to say and builds the final reply."""

    def __init__(
        self,
        knowledge=None,
        talking_brain=None,
        brain_network=None,
        connector=None,
    ):
        self.knowledge = knowledge
        self.talking_brain = talking_brain
        self.brain_network = brain_network
        self.connector = connector

    # ---- public ------------------------------------------------------
    def respond(
        self,
        message: str,
        network_result: Optional[Dict[str, Any]] = None,
    ) -> Reply:
        question = question_from(message)

        if question is None:
            return Reply(MEDIA_REPLY, answered=True)
        if not question:
            return Reply("")

        kb = self.knowledge
        if kb is not None:
            try:
                kb.refresh_if_changed()
            except Exception as error:
                print("VOICES: knowledge refresh failed:", error)

        matches = kb.lookup_all(question) if kb is not None else []
        known = [m for m in matches if m.kind == "known"]
        close = [m for m in matches if m.kind == "close"]

        voices: List[Voice] = []

        # 1) knowledge voices (every brain that knows something)
        for match in known[:MAX_KNOWLEDGE_VOICES]:
            text, spoken = self._say(match.entry)
            if text:
                voices.append(
                    Voice(
                        brain=match.entry.brain,
                        text=text,
                        kind="knowledge",
                        score=match.score,
                        source=match.entry.source,
                        spoken_by_model=spoken,
                    )
                )

        # 2) what the brains computed
        results = (network_result or {}).get("results") or {}
        for name, envelope in results.items():
            result = envelope.get("result") if isinstance(envelope, dict) else None
            voice = extract_brain_voice(name, result, question)
            if voice:
                voices.append(voice)

        # a FEELINGS quote you wrote beats the built-in empathy sentence
        if any(v.brain == "FEELINGS" and v.kind == "knowledge" for v in voices):
            voices = [
                v for v in voices
                if not (v.brain == "FEELINGS" and v.kind == "brain")
            ]

        # 3) the internet
        web_voices, tried = self._internet(
            question,
            network_result,
            has_knowledge=any(v.kind == "knowledge" for v in voices),
            emotional=any(v.brain == "FEELINGS" and v.kind == "brain" for v in voices),
        )
        voices.extend(web_voices)

        reply = self._compose(question, voices, close, tried)
        print(
            "🗣️ VOICES |",
            "knowledge=" + str([(v.brain, round(v.score, 2)) for v in voices if v.kind == "knowledge"]),
            "brain=" + str([v.brain for v in voices if v.kind == "brain"]),
            f"web={len(web_voices)}",
            f"tried_web={tried}",
            flush=True,
        )
        return reply

    # ---- knowledge ---------------------------------------------------
    def _say(self, entry) -> Tuple[str, bool]:
        """The model speaks what it memorised; otherwise the stored text."""
        stored = entry.answers[0] if entry.answers else ""
        speak = getattr(self.talking_brain, "speak", None)
        if callable(speak):
            try:
                text, spoken = speak(entry)
                if text:
                    return text, bool(spoken)
            except Exception as error:
                print(f"VOICES: talking brain failed ({type(error).__name__}: {error}); using stored text")
        return stored, False

    # ---- internet ----------------------------------------------------
    def _internet(
        self,
        question: str,
        network_result: Optional[Dict[str, Any]],
        has_knowledge: bool,
        emotional: bool,
    ) -> Tuple[List[Voice], bool]:
        """Returns (web voices, whether a search was attempted)."""
        raw = list((network_result or {}).get("internet_results") or [])
        tried = bool(raw)

        # The planner may already have searched (and found nothing).
        state = (network_result or {}).get("state")
        try:
            planner_searched = bool(
                state is not None and state.get("internet_research_performed")
            )
        except Exception:
            planner_searched = False
        if planner_searched:
            tried = True

        if not raw and not planner_searched:
            tokens = content_tokens(question)
            asked_to_search = bool(_SEARCH_REQUEST.search(question))
            always = os.environ.get("VALE_ALWAYS_SEARCH", "0").strip() == "1"
            about_vale = bool(_ABOUT_VALE.search(question)) and not asked_to_search
            wants = (not about_vale) and (
                (
                    len(tokens) >= 2
                    and looks_factual(question)
                    and (asked_to_search or always or (not has_knowledge and not emotional))
                )
                or (asked_to_search and len(tokens) >= 1 and not emotional)
            )

            if wants:
                raw, tried = self._search(question, network_result)

        return self._web_voices(question, raw), tried

    def _search(
        self,
        question: str,
        network_result: Optional[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], bool]:
        try:
            network = self.brain_network
            state = (network_result or {}).get("state")
            if network is not None and state is not None:
                return list(network.research_web(state, question, num_results=5) or []), True
            if self.connector is not None and self.connector.internet_available():
                return list(self.connector.search_web(question, num_results=5) or []), True
        except Exception as error:
            print(f"VOICES: internet search failed ({type(error).__name__}: {error})")
        return [], False

    def _web_voices(
        self,
        question: str,
        raw: List[Dict[str, Any]],
    ) -> List[Voice]:
        wanted = set(content_tokens(question))
        voices: List[Voice] = []
        for item in raw:
            if not isinstance(item, dict):
                continue
            highlights = item.get("highlights") or []
            snippet = next(
                (str(h).strip() for h in highlights if str(h).strip()),
                "",
            )
            title = str(item.get("title") or "").strip()
            url = str(item.get("url") or "").strip()
            if not snippet:
                continue

            # keep only results that really mention what was asked
            have = set(content_tokens(f"{title} {snippet}"))
            if wanted and not (wanted & have):
                continue

            label = title or url or "web"
            where = f"{label}, {url}" if url and url != label else label
            voices.append(
                Voice(
                    brain="INTERNET",
                    text=f"{_trim_sentence(snippet)} (Source: {where})",
                    kind="internet",
                    source=url,
                    provider=str(item.get("source") or ""),
                )
            )
            if len(voices) >= MAX_WEB_VOICES:
                break
        return voices

    # ---- composing ---------------------------------------------------
    def _compose(
        self,
        question: str,
        voices: List[Voice],
        close: List[Any],
        tried_internet: bool,
    ) -> Reply:
        knowledge = sorted(
            (v for v in voices if v.kind == "knowledge"),
            key=lambda v: (-v.score, v.brain != GENERAL_BRAIN),
        )
        brain = [v for v in voices if v.kind == "brain"]
        web = [v for v in voices if v.kind == "internet"]
        feelings = [v for v in brain if v.brain == "FEELINGS"]
        others = [v for v in brain if v.brain != "FEELINGS"]

        parts: List[str] = []
        seen: set = set()

        def add(text: str) -> None:
            key = re.sub(r"\W+", " ", text.lower()).strip()
            if key and key not in seen:
                seen.add(key)
                parts.append(text)

        for voice in feelings:
            add(voice.text)

        for index, voice in enumerate(knowledge):
            if voice.brain == GENERAL_BRAIN and index == 0:
                add(voice.text)                       # VALE's own voice: no label
            else:
                add(f"{display_name(voice.brain)}: {voice.text}")

        for voice in others:
            add(f"{display_name(voice.brain)}: {voice.text}")

        if web:
            lines = "\n".join(f"- {v.text}" for v in web)
            note = ""
            if (
                all(v.provider == "wikipedia" for v in web)
                and _LIVE_INFO.search(question)
            ):
                note = (
                    "\n(This came from Wikipedia, which is not a live source. "
                    "For current news and prices, set EXA_API_KEY on the server.)"
                )
            add("From the internet (not verified):\n" + lines + note)

        answered = bool(knowledge or web or others)

        if not parts:
            return Reply(
                self._fallback(question, close, tried_internet),
                voices=[],
                tried_internet=tried_internet,
                answered=False,
            )

        if feelings and not (knowledge or web or others):
            add(self._follow_up(close))

        return Reply(
            "\n\n".join(parts),
            voices=voices,
            used_internet=bool(web),
            tried_internet=tried_internet,
            answered=answered or bool(feelings),
        )

    def _fallback(self, question: str, close: List[Any], tried_internet: bool) -> str:
        kb = self.knowledge
        if kb is None:
            return "I don't know that yet."
        match = close[0] if close else None
        if match is None:
            from_gate = kb.fallback_text(_unknown())
        else:
            from_gate = kb.fallback_text(match)
        if tried_internet:
            from_gate += "\nI also searched the internet but found nothing useful."
        return from_gate

    def _follow_up(self, close: List[Any]) -> str:
        return (
            "If you would like to talk it through, tell me more. "
            "You can also ask me something specific about trading, "
            "crypto safety or how VALE works."
        )


def _unknown():
    """A 'nothing matched' Match without importing at module load time."""
    from talking_brain.knowledge_gate import Match
    return Match("unknown", 0.0)
