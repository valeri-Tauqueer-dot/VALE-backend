"""
VALE TALKING BRAIN - KNOWLEDGE GATE
===================================

Small helper used by talking_brain_connector.py.  It does NOT need PyTorch.

WHY THIS FILE EXISTS
--------------------
The Talking Brain is a small character-level transformer.  It memorised the
question/answer pairs that were in its training files.  It does not understand
anything outside of them.  Your chat was full of nonsense for three reasons:

  1. WRONG PROMPT FORMAT.  The model was trained on text that looks like

         <USER>
         What is a market order?

         <CONTEXT>
         <NONE>

         <ASSISTANT>
         A market order requests an immediate trade ...
         <END>

     (every tag on its own line, no closing tags).  The old connector sent
     "<USER>text<CONTEXT><UNITY></UNITY><HEROIC></HEROIC><ASSISTANT>".
     The model has no "/" character, so "</UNITY>" silently became a second
     "<UNITY>".  The model did not recognise that prompt, so it recited
     random memorised sentences.

  2. NOTHING STOPPED IT FROM GUESSING.  When you asked something it never
     learned ("Dt", "What", "trading strategy framework") it still had to
     write something, so it recited whatever memorised sentence was closest.

  3. THE OTHER BRAINS GAVE IT NOTHING.  UNITY and HEROIC return status
     dictionaries with no "message" text, so the UNITY / HEROIC slots were
     always empty.

WHAT THIS FILE DOES
-------------------
  build_prompt()      -> the exact prompt format the model was trained on
  KnowledgeBase       -> decides whether a question is one the model knows
  extract_answer()    -> cuts the model output at the first tag (no run-on)
  KnowledgeBase.verify() -> compares the model text with the stored answer

Q&A files are read automatically from this folder and from data/ :
  "USER: ... / ASSISTANT: ..."   and   "Q: ... / A: ..."
"""

from __future__ import annotations

import difflib
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

BRAIN_DIR = Path(__file__).resolve().parent
QA_DIRS = [BRAIN_DIR, BRAIN_DIR / "data"]

# --------------------------------------------------------------------------
# SETTINGS (all scores are between 0 and 1)
# --------------------------------------------------------------------------

# score >= KNOWN_SCORE  -> the question is one the model knows: answer it.
# score >= CLOSE_SCORE  -> "I'm not sure, did you mean ...?"
# below that            -> "I don't know that yet."
KNOWN_SCORE = 0.80
CLOSE_SCORE = 0.35

# The model's text is used only when it matches a stored answer EXACTLY
# (1.0).  A one-word slip such as "can" instead of "cannot" would change the
# meaning, which is dangerous in trading advice.  Anything else -> the stored
# answer is used and the log says the model garbled it.
VERIFY_RATIO = 1.0

# Words that carry no topic information.
_STOPWORDS = frozenset(
    """
    a an the is are was were be been am do does did to of in on at for with and
    or it its this that these those i you your yours me my we our us they them
    their he she his her what whats which who whom how why when where can could
    would should will shall may might please tell explain describe define give
    show about mean means meaning definition some any just so as by from if then
    than there here let know want need like u ur r pls plz
    """.split()
)

# A few very common short messages -> the question in the Q&A files.
_ALIASES = {
    "hey": "hi",
    "hiya": "hi",
    "yo": "hi",
    "hello there": "hello",
    "hi there": "hi",
    "thanks": "thank you",
    "thank u": "thank you",
    "thx": "thank you",
    "bye": "goodbye",
    "see you": "goodbye",
    "who r u": "who are you",
    "whats your name": "what is your name",
    "good morning": "hello",
    "good afternoon": "hello",
    "good evening": "hello",
    "good night": "goodbye",
}

# Words that may be added in front of / behind a question without changing it
# ("how are you vale", "please what is a market order").
_FILLERS = frozenset({"vale", "please", "pls", "plz"})

_EXAMPLE_QUESTIONS = (
    "What is a market order?",
    "What is a rug pull?",
    "What is machine learning?",
)

_TAGS = r"<(?:END|USER|CONTEXT|UNITY|HEROIC|ASSISTANT|NONE)>"


# --------------------------------------------------------------------------
# TEXT HELPERS
# --------------------------------------------------------------------------

def normalize(text: str) -> str:
    """lower-case, drop apostrophes, keep only letters and digits."""
    text = (text or "").lower().replace("'", "").replace("\u2019", "")
    return " ".join(re.findall(r"[a-z0-9]+", text))


def _stem(word: str) -> str:
    """Very small stemmer so that trade/trading/trades and order/orders match."""
    w = word
    if len(w) > 4 and w.endswith("ies"):
        w = w[:-3] + "y"
    elif len(w) > 3 and w.endswith("s") and not w.endswith(("ss", "us", "is")):
        w = w[:-1]
    if len(w) > 5 and w.endswith("ing"):
        w = w[:-3]
    elif len(w) > 5 and w.endswith("ed"):
        w = w[:-2]
    if len(w) > 3 and w.endswith("e"):
        w = w[:-1]
    return w


def content_tokens(text: str) -> List[str]:
    """Topic words of a sentence (stop-words removed, stemmed)."""
    words = normalize(text).split()
    kept = [w for w in words if w not in _STOPWORDS]
    if not kept:          # e.g. "who are you" -> keep everything
        kept = words
    return [_stem(w) for w in kept]


def _squash(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


# --------------------------------------------------------------------------
# PROMPT FORMAT THE MODEL WAS TRAINED ON
# --------------------------------------------------------------------------

def build_prompt(question: str) -> str:
    """
    The exact prompt format found in the trained checkpoint.

    The model's own samples show it was trained on:

        <USER>\\n{question}\\n\\n<CONTEXT>\\n<NONE>\\n\\n<ASSISTANT>\\n{answer}\\n<END>
    """
    question = _squash(question)
    return f"<USER>\n{question}\n\n<CONTEXT>\n<NONE>\n\n<ASSISTANT>\n"


def extract_answer(raw: str) -> str:
    """
    Take the text the model wrote after <ASSISTANT> and cut it at the FIRST
    tag.  (The old code kept text after a stray tag, which created the
    "answer ... \\n\\n\\n second unrelated answer" run-on in the chat.)
    """
    if not raw:
        return ""
    text = raw.split("<ASSISTANT>", 1)[1] if "<ASSISTANT>" in raw else raw
    text = re.split(_TAGS, text, maxsplit=1)[0]
    return text.strip()


def parse_qa_text(text: str) -> List[Tuple[str, str]]:
    """Read 'USER:/ASSISTANT:' and 'Q:/A:' blocks."""
    pairs: List[Tuple[str, str]] = []
    q: Optional[str] = None
    a: Optional[str] = None
    mode = None
    for raw in text.splitlines():
        line = raw.rstrip()
        mq = re.match(r"^(USER|Q):\s*(.*)$", line)
        ma = re.match(r"^(ASSISTANT|A):\s*(.*)$", line)
        if mq:
            if q is not None and a is not None:
                pairs.append((q.strip(), a.strip()))
            q, a, mode = mq.group(2), None, "q"
        elif ma and q is not None:
            a, mode = ma.group(2), "a"
        elif not line.strip():
            continue
        elif mode == "q" and q is not None:
            q += " " + line.strip()
        elif mode == "a" and a is not None:
            a += " " + line.strip()
    if q is not None and a is not None:
        pairs.append((q.strip(), a.strip()))
    return [(x, y) for x, y in pairs if x and y]


# --------------------------------------------------------------------------
# KNOWLEDGE BASE
# --------------------------------------------------------------------------

@dataclass
class Entry:
    question: str                       # exactly as written in the Q&A file
    answers: List[str] = field(default_factory=list)
    tokens: List[str] = field(default_factory=list)
    vector: Dict[str, float] = field(default_factory=dict)
    norm: float = 1.0

    @property
    def longest_answer(self) -> int:
        return max((len(a) for a in self.answers), default=0)


@dataclass
class Match:
    kind: str                           # "known" | "close" | "unknown"
    score: float
    entry: Optional[Entry] = None
    suggestions: List[str] = field(default_factory=list)


class KnowledgeBase:
    """TF-IDF lookup over the questions in your Q&A files."""

    def __init__(self, directories: Optional[Sequence[Path]] = None):
        self.entries: List[Entry] = []
        self.by_key: Dict[str, Entry] = {}
        self.idf: Dict[str, float] = {}
        self.max_idf = 1.0
        self.postings: Dict[str, List[int]] = defaultdict(list)
        self.vocabulary: List[str] = []
        self.load(directories or QA_DIRS)

    # ---- loading -----------------------------------------------------
    def load(self, directories: Sequence[Path]) -> None:
        pairs: List[Tuple[str, str]] = []
        for folder in directories:
            folder = Path(folder)
            if not folder.is_dir():
                continue
            for path in sorted(folder.glob("*.txt")):
                try:
                    pairs += parse_qa_text(path.read_text(encoding="utf-8", errors="ignore"))
                except OSError:
                    continue

        for question, answer in pairs:
            key = normalize(question)
            if not key:
                continue
            entry = self.by_key.get(key)
            if entry is None:
                entry = Entry(question=question, tokens=content_tokens(question))
                self.by_key[key] = entry
                self.entries.append(entry)
            if answer not in entry.answers:
                entry.answers.append(answer)

        # inverse document frequency
        n = len(self.entries)
        df: Counter = Counter()
        for entry in self.entries:
            df.update(set(entry.tokens))
        self.idf = {t: math.log((n + 1) / (c + 1)) + 1.0 for t, c in df.items()}
        self.max_idf = math.log(n + 1) + 1.0 if n else 1.0
        self.vocabulary = sorted(self.idf)

        for index, entry in enumerate(self.entries):
            counts = Counter(entry.tokens)
            entry.vector = {t: c * self.idf[t] for t, c in counts.items()}
            entry.norm = math.sqrt(sum(v * v for v in entry.vector.values())) or 1.0
            for t in entry.vector:
                self.postings[t].append(index)

    def __len__(self) -> int:
        return len(self.entries)

    # ---- scoring -----------------------------------------------------
    def _fix_typos(self, tokens: List[str]) -> List[str]:
        """Map an unknown word to the closest known word ('markt' -> 'market')."""
        fixed = []
        for t in tokens:
            if t in self.idf or len(t) < 5:
                fixed.append(t)
                continue
            close = difflib.get_close_matches(t, self.vocabulary, n=1, cutoff=0.80)
            fixed.append(close[0] if close else t)
        return fixed

    @staticmethod
    def _strip_fillers(key: str) -> str:
        words = key.split()
        while words and words[0] in _FILLERS:
            words = words[1:]
        while words and words[-1] in _FILLERS:
            words = words[:-1]
        return " ".join(words)

    def _rank(self, message: str) -> List[Tuple[float, Entry]]:
        tokens = self._fix_typos(content_tokens(message))
        if not tokens or not self.entries:
            return []
        counts = Counter(tokens)
        # words the knowledge base has never seen count AGAINST the match
        qvec = {t: c * self.idf.get(t, self.max_idf) for t, c in counts.items()}
        qnorm = math.sqrt(sum(v * v for v in qvec.values())) or 1.0

        candidates = set()
        for t in qvec:
            candidates.update(self.postings.get(t, ()))

        scored = []
        for index in candidates:
            entry = self.entries[index]
            dot = sum(w * entry.vector.get(t, 0.0) for t, w in qvec.items())
            scored.append((dot / (qnorm * entry.norm), entry))
        scored.sort(key=lambda item: -item[0])
        return scored

    # ---- public API --------------------------------------------------
    def lookup(self, message: str) -> Match:
        key = normalize(message)
        if not key:
            return Match("unknown", 0.0)

        if key in self.by_key:                               # exact
            return Match("known", 1.0, self.by_key[key])

        alias = _ALIASES.get(key)
        if alias and alias in self.by_key:                   # "hey" -> "hi"
            return Match("known", 1.0, self.by_key[alias])

        core = self._strip_fillers(key)                      # "how are you vale"
        if core and core != key:
            if core in self.by_key:
                return Match("known", 1.0, self.by_key[core])
            alias = _ALIASES.get(core)
            if alias and alias in self.by_key:
                return Match("known", 1.0, self.by_key[alias])

        words = key.split()
        has_topic_word = any(w not in _STOPWORDS for w in words)
        if not has_topic_word and len(words) < 2:           # e.g. just "What"
            return Match("unknown", 0.0)

        ranked = self._rank(message)
        if not ranked:
            return Match("unknown", 0.0)

        score, entry = ranked[0]
        if score >= KNOWN_SCORE:
            return Match("known", score, entry)
        if score >= CLOSE_SCORE:
            suggestions = []
            for s, e in ranked:
                if s < CLOSE_SCORE or len(suggestions) == 2:
                    break
                suggestions.append(e.question)
            return Match("close", score, entry, suggestions)
        return Match("unknown", score)

    def verify(self, candidate: str, entry: Entry) -> Tuple[bool, float, str]:
        """
        Compare what the model wrote with the stored answer(s).
        Returns (model_text_is_good, similarity, best_stored_answer).
        """
        cand = _squash(candidate).lower()
        best_ratio, best_answer = 0.0, (entry.answers[0] if entry.answers else "")
        for answer in entry.answers:
            ratio = difflib.SequenceMatcher(None, cand, _squash(answer).lower()).ratio()
            if ratio > best_ratio:
                best_ratio, best_answer = ratio, answer
        return best_ratio >= VERIFY_RATIO, best_ratio, best_answer

    # ---- friendly replies when the model should NOT answer -----------
    def examples(self) -> List[str]:
        found = [q for q in _EXAMPLE_QUESTIONS if normalize(q) in self.by_key]
        if not found:
            found = [e.question for e in self.entries[:3]]
        return found[:3]

    def fallback_text(self, match: Match) -> str:
        if match.kind == "close" and match.suggestions:
            options = match.suggestions[:2]
            lines = "\n".join(f"- {s}" for s in options)
            ask = "that" if len(options) == 1 else "one of those"
            return (
                "I'm not sure I understood that. Did you mean:\n"
                f"{lines}\n"
                f"Ask me {ask}, or rephrase your question."
            )
        lines = "\n".join(f"- {q}" for q in self.examples())
        return (
            "I don't know that yet. I'm a small model, so I only know what I was "
            "trained on: trading and crypto basics, scam safety, strategy ideas, "
            "simple science and AI concepts, and how VALE works.\n"
            "Try asking, for example:\n"
            f"{lines}"
        )
