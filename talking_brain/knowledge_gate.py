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
import threading
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

BRAIN_DIR = Path(__file__).resolve().parent
ROOT_DIR = BRAIN_DIR.parent          # the folder that holds ai_core.py

# General VALE knowledge (the files the talking-brain model was trained on).
QA_DIRS = [BRAIN_DIR, BRAIN_DIR / "data"]

# Each brain can have its own knowledge.  Drop a .txt file into one of
#     <BRAIN>/knowledge/   <BRAIN>/data/   <BRAIN>/
# and that brain answers from it - no code changes, no retraining.
# folder name -> brain name
BRAIN_FOLDERS = {
    "ALPHA": "ALPHA",
    "COGNITIVE": "COGNITIVE",
    "FEEL": "FEELINGS",
    "FEELINGS": "FEELINGS",
    "HEROIC": "HEROIC",
    "LEGEND": "LEGEND",
    "MARCO": "MARCO",
    "SUPERVISOR": "SUPERVISOR",
    "UNITY": "UNITY",
    "AI_OS": "AI_OS",
}

GENERAL_BRAIN = "VALE"

# The talking-brain MODEL memorised these files (measured: 28 of 29 answers
# exact).  Anything else is not in the model, so it is answered straight from
# the stored text instead of wasting CPU on a model call that would be
# thrown away.  After you retrain the model, add the new file names here.
MODEL_TRAINED_FILES = frozenset(
    {
        "advanced_general_qa.txt",
        "qa_vale2.txt",
        "qa_safety.txt",
        "qa_strategy.txt",
    }
)


def default_sources() -> List[Tuple[Path, str]]:
    """(folder, brain) pairs scanned for .txt knowledge files."""
    sources: List[Tuple[Path, str]] = [(d, GENERAL_BRAIN) for d in QA_DIRS]
    for folder, brain in BRAIN_FOLDERS.items():
        base = ROOT_DIR / folder
        for sub in (base, base / "knowledge", base / "data"):
            sources.append((sub, brain))
    return sources

# --------------------------------------------------------------------------
# SETTINGS (all scores are between 0 and 1)
# --------------------------------------------------------------------------

# score >= KNOWN_SCORE  -> the question is one the model knows: answer it.
# score >= CLOSE_SCORE  -> "I'm not sure, did you mean ...?"
# below that            -> "I don't know that yet."
KNOWN_SCORE = 0.80
CLOSE_SCORE = 0.35

# Quotes are matched by how much of the QUESTION they cover (filler words in
# the question do not count against them), so they use a lower bar.
QUOTE_KNOWN_SCORE = 0.60

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
    than there here let know want need like u ur r pls plz much many per very really
    after before during while because one
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

# Words that mean the same thing for matching.  This is what lets "I'm scared"
# find a quote about fear.  Extend it freely - key = word you see, value = the
# word it should count as.
_SYNONYMS = {
    "afraid": "fear", "scared": "fear", "frightened": "fear", "terrified": "fear",
    "fearful": "fear", "fears": "fear",
    "anxious": "worry", "nervous": "worry", "worried": "worry", "uneasy": "worry",
    "panic": "worry", "panicking": "worry", "worries": "worry",
    "stressed": "stress", "overwhelmed": "stress",
    "angry": "anger", "furious": "anger", "mad": "anger", "irritated": "anger",
    "unhappy": "sad", "depressed": "sad", "miserable": "sad",
    "lose": "loss", "losing": "loss", "lost": "loss", "losses": "loss",
    "profits": "profit", "gains": "profit", "winning": "profit",
    "purchase": "buy", "buying": "buy", "selling": "sell",
}

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
    return [_stem(_SYNONYMS.get(w, w)) for w in kept]


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


def _clean_quote(raw: str) -> str:
    """Strip bullets / numbering / surrounding quote marks; '' if unusable."""
    line = raw.strip()
    if not line or line.startswith("#"):
        return ""
    line = re.sub(r"^(?:[-*\u2022]+|\d+[.)])\s+", "", line)      # bullets / 1.
    line = line.strip().strip('"\u201c\u201d').strip()
    return line if 12 <= len(line) <= 400 else ""             # a quote, not prose


def parse_quotes(text: str) -> List[str]:
    """A file with no "Q:" / "USER:" lines: every line is one quote."""
    return [q for q in (_clean_quote(line) for line in text.splitlines()) if q]


def parse_mixed(text: str) -> Tuple[List[Tuple[str, str]], List[str]]:
    """
    Parse a brain's knowledge file that may contain BOTH formats.

    * "Q:" / "A:" (or USER: / ASSISTANT:) start a question and its answer.
    * A blank line ends the answer.
    * Any other line outside a Q&A pair is a quote.
    * Lines starting with # are comments.
    """
    pairs: List[Tuple[str, str]] = []
    quotes: List[str] = []
    q: Optional[str] = None
    a: Optional[str] = None
    mode: Optional[str] = None

    def commit() -> None:
        nonlocal q, a, mode
        if q and q.strip() and a and a.strip():
            pairs.append((q.strip(), a.strip()))
        q, a, mode = None, None, None

    for raw in text.splitlines():
        line = raw.rstrip()
        mq = re.match(r"^(USER|Q):\s*(.*)$", line)
        ma = re.match(r"^(ASSISTANT|A):\s*(.*)$", line)
        if mq:
            commit()
            q, mode = mq.group(2), "q"
        elif ma and q is not None:
            a, mode = ma.group(2), "a"
        elif not line.strip():
            if mode == "a":
                commit()                      # blank line ends the answer
        elif line.strip().startswith("#"):
            continue
        elif mode == "q" and q is not None:
            q += " " + line.strip()
        elif mode == "a" and a is not None:
            a += " " + line.strip()
        else:
            quote = _clean_quote(line)
            if quote:
                quotes.append(quote)
    commit()
    return pairs, quotes


def has_qa_markers(text: str) -> bool:
    return bool(re.search(r"^(?:USER|Q):", text, re.M))


# --------------------------------------------------------------------------
# KNOWLEDGE BASE
# --------------------------------------------------------------------------

@dataclass
class Entry:
    question: str                       # exactly as written in the file
    answers: List[str] = field(default_factory=list)
    tokens: List[str] = field(default_factory=list)
    vector: Dict[str, float] = field(default_factory=dict)
    norm: float = 1.0
    brain: str = GENERAL_BRAIN          # which brain owns this knowledge
    kind: str = "qa"                    # "qa" (question+answer) or "quote"
    source: str = ""                    # file name it came from

    @property
    def longest_answer(self) -> int:
        return max((len(a) for a in self.answers), default=0)

    @property
    def model_trained(self) -> bool:
        """True when the talking-brain model memorised this entry."""
        return (
            self.brain == GENERAL_BRAIN
            and self.kind == "qa"
            and self.source in MODEL_TRAINED_FILES
        )


@dataclass
class Match:
    kind: str                           # "known" | "close" | "unknown"
    score: float
    entry: Optional[Entry] = None
    suggestions: List[str] = field(default_factory=list)

    @property
    def brain(self) -> str:
        return self.entry.brain if self.entry else ""


class KnowledgeBase:
    """
    Knowledge of every brain, searchable.

    Two kinds of knowledge files (both plain .txt):

      Q&A      Q: What is a stop loss?          (or USER: / ASSISTANT:)
               A: An order that closes a trade at a chosen price.

      Quotes   one quote per line, no "Q:" markers:
               Risk only a small part of your account on a single trade.

    Where they go:
      talking_brain/*.txt, talking_brain/data/*.txt   -> general VALE knowledge
      <BRAIN>/knowledge/*.txt  (also <BRAIN>/*.txt and <BRAIN>/data/*.txt)
                                                       -> that brain's knowledge
    """

    def __init__(
        self,
        directories: Optional[Sequence[Path]] = None,
        sources: Optional[Sequence[Tuple[Path, str]]] = None,
    ):
        self.entries: List[Entry] = []
        self.by_key: Dict[Tuple[str, str], Entry] = {}
        self.idf: Dict[str, float] = {}
        self.max_idf = 1.0
        self.postings: Dict[str, List[int]] = defaultdict(list)
        self.vocabulary: List[str] = []
        self._phrase_index: Dict[str, List[Entry]] = {}
        self._signature: Tuple = ()
        self._last_check = 0.0

        # The server answers several requests at once; a reload must never be
        # visible half-finished to another request.
        self._lock = threading.RLock()

        if sources is not None:
            self.sources = [(Path(p), b) for p, b in sources]
        elif directories is not None:
            self.sources = [(Path(d), GENERAL_BRAIN) for d in directories]
        else:
            self.sources = default_sources()

        self.load()

    # ---- loading -----------------------------------------------------
    def _files(self) -> List[Tuple[Path, str]]:
        seen = set()
        files: List[Tuple[Path, str]] = []
        for folder, brain in self.sources:
            if not folder.is_dir():
                continue
            for path in sorted(folder.glob("*.txt")):
                real = path.resolve()
                if real in seen:
                    continue
                seen.add(real)
                files.append((path, brain))
        return files

    def load(self) -> None:
        with self._lock:
            return self._load_unlocked()

    def _load_unlocked(self) -> None:
        self.entries, self.by_key = [], {}
        self.idf, self.postings, self._phrase_index = {}, defaultdict(list), {}

        files = self._files()
        signature = []
        for path, brain in files:
            try:
                text = path.read_text(encoding="utf-8", errors="ignore")
                stat = path.stat()
            except OSError:
                continue
            signature.append((str(path), stat.st_mtime_ns, stat.st_size))

            if brain == GENERAL_BRAIN:
                # The general talking_brain/ folders hold the files the model
                # was trained on, plus plain training prose (data/sample.txt)
                # that must NOT be read as quotes.  Q&A only.
                if has_qa_markers(text):
                    for question, answer in parse_qa_text(text):
                        self._add(brain, "qa", question, answer, path.name)
            else:
                # A brain's own folders accept Q&A pairs and quotes, even in
                # the same file.
                pairs, quotes = parse_mixed(text)
                for question, answer in pairs:
                    self._add(brain, "qa", question, answer, path.name)
                for quote in quotes:
                    self._add(brain, "quote", quote, quote, path.name)

        self._signature = tuple(signature)
        self._last_check = time.time()
        self._build_index()

    def _add(self, brain: str, kind: str, question: str, answer: str, source: str) -> None:
        key = (brain, normalize(question))
        if not key[1]:
            return
        entry = self.by_key.get(key)
        if entry is None:
            entry = Entry(
                question=question,
                tokens=content_tokens(question),
                brain=brain,
                kind=kind,
                source=source,
            )
            self.by_key[key] = entry
            self.entries.append(entry)
        if answer not in entry.answers:
            entry.answers.append(answer)

    def _build_index(self) -> None:
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

        # whole-question phrases, used for "how are you vale" style matching
        for (brain, key), entry in self.by_key.items():
            self._phrase_index.setdefault(key, []).append(entry)

    def refresh_if_changed(self, min_interval: float = 30.0) -> bool:
        with self._lock:
            return self._refresh_if_changed_unlocked(min_interval=min_interval)

    def _refresh_if_changed_unlocked(self, min_interval: float = 30.0) -> bool:
        """Re-read the files when any of them changed (checked at most
        every ``min_interval`` seconds).  Returns True when it reloaded."""
        now = time.time()
        if now - self._last_check < min_interval:
            return False
        self._last_check = now
        current = []
        for path, _brain in self._files():
            try:
                stat = path.stat()
            except OSError:
                continue
            current.append((str(path), stat.st_mtime_ns, stat.st_size))
        if tuple(current) != self._signature:
            self.load()
            return True
        return False

    def __len__(self) -> int:
        return len(self.entries)

    def brain_counts(self) -> Dict[str, int]:
        with self._lock:
            return self._brain_counts_unlocked()

    def _brain_counts_unlocked(self) -> Dict[str, int]:
        counts: Dict[str, int] = defaultdict(int)
        for e in self.entries:
            counts[e.brain] += 1
        return dict(counts)

    # ---- scoring -----------------------------------------------------
    @staticmethod
    def _strip_fillers(key: str) -> str:
        words = key.split()
        while words and words[0] in _FILLERS:
            words = words[1:]
        while words and words[-1] in _FILLERS:
            words = words[:-1]
        return " ".join(words)

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

    def _rank(self, message: str) -> List[Tuple[float, Entry]]:
        tokens = self._fix_typos(content_tokens(message))
        if not tokens or not self.entries:
            return []
        counts = Counter(tokens)
        # words the knowledge base has never seen count AGAINST the match
        qvec = {t: c * self.idf.get(t, self.max_idf) for t, c in counts.items()}
        qnorm = math.sqrt(sum(v * v for v in qvec.values())) or 1.0
        # For quotes, a word that appears nowhere in the knowledge counts only
        # PARTLY against the match (35%): enough that "list your brains" does
        # not match a quote on the single word "brain", but not so much that
        # a harmless extra word ("advice") hides a good quote.
        qtotal = sum(
            (w if t in self.idf else 0.35 * w) for t, w in qvec.items()
        ) or 1.0

        candidates = set()
        for t in qvec:
            candidates.update(self.postings.get(t, ()))

        scored = []
        for index in candidates:
            entry = self.entries[index]
            if entry.kind == "quote":
                # quotes are long: score by how much of the QUESTION they cover
                matched = sum(w for t, w in qvec.items() if t in entry.vector)
                focus = 1.0 - 0.1 * min(len(entry.tokens), 30) / 30.0   # shorter = better
                scored.append(((matched / qtotal) * focus, entry))
            else:
                dot = sum(w * entry.vector.get(t, 0.0) for t, w in qvec.items())
                scored.append((dot / (qnorm * entry.norm), entry))
        scored.sort(key=lambda item: -item[0])
        return scored

    def _exact(self, key: str) -> List[Entry]:
        """Entries whose whole question equals ``key`` (one per brain)."""
        return list(self._phrase_index.get(key, []))

    # ---- public API --------------------------------------------------
    def lookup_all(self, message: str, max_brains: int = 8) -> List[Match]:
        with self._lock:
            return self._lookup_all_unlocked(message=message, max_brains=max_brains)

    def _lookup_all_unlocked(self, message: str, max_brains: int = 8) -> List[Match]:
        """
        The best match for EACH brain, best first.  Only "known" and
        "close" matches are returned.
        """
        key = normalize(message)
        if not key:
            return []

        best: Dict[str, Match] = {}

        def offer(match: Match) -> None:
            brain = match.entry.brain
            current = best.get(brain)
            if current is None or match.score > current.score:
                best[brain] = match

        # 1. exact / alias / "how are you vale"
        exact_keys = [key]
        alias = _ALIASES.get(key)
        if alias:
            exact_keys.append(alias)
        core = self._strip_fillers(key)
        if core and core != key:
            exact_keys.append(core)
            if _ALIASES.get(core):
                exact_keys.append(_ALIASES[core])
        for k in exact_keys:
            for entry in self._exact(k):
                offer(Match("known", 1.0, entry))

        # 2. similarity (skipped for a lone stop-word such as "What")
        words = key.split()
        has_topic_word = any(w not in _STOPWORDS for w in words)
        if has_topic_word or len(words) >= 2:
            for score, entry in self._rank(message)[:200]:
                if entry.kind == "quote":
                    if score >= QUOTE_KNOWN_SCORE:
                        offer(Match("known", score, entry))
                    continue
                if score < CLOSE_SCORE:
                    continue
                kind = "known" if score >= KNOWN_SCORE else "close"
                offer(Match(kind, score, entry))

        matches = sorted(best.values(), key=lambda m: (-m.score, m.entry.brain != GENERAL_BRAIN))
        suggestions = self._suggestions(message)
        for m in matches:
            if m.kind == "close":
                m.suggestions = suggestions
        return matches[:max_brains]

    def _suggestions(self, message: str) -> List[str]:
        """Up to two Q&A questions to offer when nothing matched well."""
        out: List[str] = []
        best = 0.0
        for score, entry in self._rank(message):
            if entry.kind != "qa":
                continue
            best = best or score
            # stop at weak matches and at anything far below the best one
            if score < CLOSE_SCORE or score < 0.7 * best or len(out) == 2:
                break
            if entry.question not in out:
                out.append(entry.question)
        return out

    def lookup(self, message: str) -> Match:
        with self._lock:
            return self._lookup_unlocked(message=message)

    def _lookup_unlocked(self, message: str) -> Match:
        """The single best match over all brains (known > close > unknown)."""
        matches = self.lookup_all(message)
        if not matches:
            return Match("unknown", 0.0)
        known = [m for m in matches if m.kind == "known"]
        if known:
            return known[0]
        top = matches[0]
        return Match("close", top.score, top.entry, top.suggestions or self._suggestions(message))

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

    # ---- friendly replies when nothing is known ----------------------
    def examples(self) -> List[str]:
        with self._lock:
            return self._examples_unlocked()

    def _examples_unlocked(self) -> List[str]:
        found = [
            e.question for q in _EXAMPLE_QUESTIONS
            for e in self._exact(normalize(q))
        ]
        if not found:
            found = [e.question for e in self.entries if e.kind == "qa"][:3]
        return list(dict.fromkeys(found))[:3]

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
