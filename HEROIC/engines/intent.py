"""Intent engine: fast, rule-based understanding of what the user actually wants.

One pass over the text finds: mission type, domains, entities, constraints, ambiguity, implicit
requirements, unverified user beliefs, emotional/crisis cues and multiple intents. Results are cached.
`clarity` is a heuristic measure of how strong the language evidence is. It is not a probability.
"""
from __future__ import annotations

import re
from functools import lru_cache
from typing import Dict, List, Set, Tuple

from ..core.models import IntentProfile
from ..core.util import STOPWORDS, clip, tokens

_PHRASE_W, _WORD_W, _WEAK_W, _CONV_W = 2.0, 1.2, 0.5, 1.6

# mission type -> (phrases, strong words, weak words)
_TYPE_CUES: Dict[str, Tuple[str, str, str]] = {
    "EXPLANATION": (
        "what is|what are|what does|what do|what's|whats|who is|who are|who was|tell me about|describe|define|"
        "meaning of|how does|how do|how is|how are|what happened|what is happening|kya hai|kya hota hai|matlab kya",
        "explain|define|describe|meaning|introduce|overview|summarize|summarise|summary|eli5|teach|clarify|samjhao|batao|bataiye",
        "about|information|info|details"),
    "ANALYSIS": (
        "why is|why are|why did|why does|why do|is it true|check whether|find out why|what caused|what's causing|"
        "root cause|evidence for|evidence that|tell me whether|does the evidence|whether the evidence|supports that",
        "analyze|analyse|analysis|evaluate|assess|examine|interpret|review|audit|study|breakdown|evidence|whether|"
        "verify|investigate",
        "why|cause|reason|trend|supports|conclusion"),
    "RESEARCH": (
        "look up|find out|search for|dig into|latest news|news about|sources for|deep dive|find information|"
        "find me|look into",
        "research|investigate|gather|explore|survey|lookup|sources|news|search|find",
        "latest|recent|update|updates"),
    "COMPARISON": (
        "difference between|differences between|better than|which is better|pros and cons|compared to|"
        "compare with|compare to",
        "compare|comparison|comparing|versus|vs|pros|cons|alternatives|alternative", ""),
    "DECISION_SUPPORT": (
        "should i|should we|is it safe to|is it good to|is it worth|worth it|which should i|what should i|"
        "do you recommend|would you recommend|is now a good time|good time to|can i afford|buy or sell|"
        "hold or sell|what do you think about|do you think i should|lena chahiye|kharidna chahiye|bechna chahiye|kya karun",
        "recommend|advice|advise|decide|decision", "worth|safe|risky|better"),
    "PLANNING": (
        "make a plan|create a plan|plan for|how to|how can i|how should i|how do i|steps to|roadmap|road map|"
        "game plan|strategy for|prepare for|step by step",
        "plan|roadmap|schedule|timeline|milestones|outline|organize|organise|prepare", "strategy|goal|goals|steps"),
    "CREATION": (
        "write a|write an|write me|draft a|draft me|compose a|create a|create an|generate a|generate an|make a|"
        "make an|make me|build a|build an|build me|help me write|message to|email to|email for|reply to|"
        "apologize to|apology to|letter to|caption for",
        "write|draft|compose|create|generate|make|build|design|code|implement|develop|produce|rewrite|translate|"
        "edit|improve|refine|likho|banao", "message|email|text|letter|post|story|poem"),
    "EXECUTION": (
        "do it|go ahead|place an order|place order|buy now|sell now|execute the|run the|deploy the|send the|"
        "send it|send this|book a|pay for|start the|stop the|restart the|delete the|install the",
        "run|execute|deploy|launch|restart|install|delete|send|transfer|pay|book", "order|place|start|stop"),
    "MONITORING": (
        "alert me|notify me|let me know when|remind me|keep an eye|keep track|watch for|every day|every hour|"
        "every week|every minute",
        "monitor|monitoring|watch|track|tracking|alert|alerts|notify|remind|observe", "daily|weekly|hourly"),
    "DIAGNOSTIC": (
        "are you working|is vale working|system check|health check|check the brain|check status|system status|"
        "what is wrong with|what's wrong with|why is vale|why isn't vale|not working|is broken|error in",
        "status|health|debug|diagnose|broken|error|bug|crash|crashed|failing|failed|diagnostics", "issue|problem"),
}
_STRONG_PHRASES = {
    "PLANNING": "make a plan|create a plan|build a plan|draft a plan|write a plan|make me a plan|give me a plan|roadmap for",
    "ANALYSIS": "confirm that|confirm this|prove that|prove it|am i right|am i correct|do you agree|is it true that",
}
_CONV_WORDS = frozenset("hi hello hey hii hiii yo sup thanks thank thx bye goodbye ok okay cool nice great lol haha wow hmm".split())
_CONV_PHRASES = ("how are you", "good morning", "good evening", "good night", "good afternoon", "what's up",
                 "whats up", "who are you", "are you there", "nice to meet", "thank you")

_PH: List[Tuple[str, str, float]] = []
_WD: Dict[str, List[Tuple[str, float]]] = {}
_CUE_WORDS: Set[str] = set(_CONV_WORDS)
for _typ, _p in _STRONG_PHRASES.items():
    for _x in _p.split("|"):
        _PH.append((" " + _x + " ", _typ, 4.0))
        _CUE_WORDS.update(_x.split())
for _typ, (_p, _w, _k) in _TYPE_CUES.items():
    for _x in filter(None, _p.split("|")):
        _PH.append((" " + _x + " ", _typ, _PHRASE_W))
        _CUE_WORDS.update(_x.split())
    for _x in filter(None, _w.split("|")):
        _WD.setdefault(_x, []).append((_typ, _WORD_W))
        _CUE_WORDS.add(_x)
    for _x in filter(None, _k.split("|")):
        _WD.setdefault(_x, []).append((_typ, _WEAK_W))
        _CUE_WORDS.add(_x)

# ------------------------------------------------------------------ domains
_DOM_STRONG = {
    "MARKET": "btc bitcoin crypto cryptocurrency ethereum eth solana bnb xrp doge dogecoin stock stocks shares "
              "trading trade trader trades forex fx nifty banknifty sensex nasdaq nse bse sp500 etf futures candle "
              "candles candlestick rsi macd bullish bearish breakout portfolio drawdown leverage liquidity "
              "volatility regime backtest backtesting pnl stoploss altcoin altcoins defi market markets invest "
              "investing investment investor commodity commodities ipo dividend equity equities bonds hedge broker",
    "HUMAN": "girlfriend boyfriend wife husband friend friends family mother father mom dad brother sister parents "
             "relationship breakup apologize apology hurt lonely feelings emotion emotional empathy human",
    "VALE": "vale heroic supervisor unity mcvl brain brains",
}
_DOM_WEAK = {
    "MARKET": "price prices chart charts strategy risk short long buy sell entry exit pump dump crash rally trend "
              "support resistance options gold silver oil coin coins token",
    "HUMAN": "love romantic partner sorry trust argument fight perspective feel feeling worried stress stressed "
             "anxious sad angry",
    "VALE": "alpha legend marco cognitive feeling architecture backend frontend",
}
_DOM_PHRASES = {
    "MARKET": "stop loss|take profit|moving average|market structure|technical analysis|price action|order book|"
              "risk reward|s&p 500|s&p|market cap|open interest|funding rate",
    "HUMAN": "how do i feel|how would she feel|how would he feel|how will he feel|how will she feel|my feelings",
    "VALE": "brain network|ai os|your brain|your architecture|who built you|who made you|are you vale",
}
_DOM_W: Dict[str, Dict[str, float]] = {}
for _d, _s in _DOM_STRONG.items():
    for _x in _s.split():
        _DOM_W.setdefault(_x, {})[_d] = 1.0
for _d, _s in _DOM_WEAK.items():
    for _x in _s.split():
        _DOM_W.setdefault(_x, {})[_d] = 0.5
_DOM_PH = [(" " + p + " ", d) for d, s in _DOM_PHRASES.items() for p in s.split("|")]

_EMOTION = frozenset(
    "feel feeling feelings felt emotion emotional sad angry frustrated frustrating confused anxious anxiety scared "
    "afraid worried worry nervous fear stressed stress panic panicking overwhelmed upset disappointed discouraged "
    "excited happy hopeless depressed lonely ashamed guilty regret regretting".split())
_CRISIS = ("kill myself", "end my life", "want to die", "suicide", "suicidal", "self harm", "self-harm",
           "hurt myself", "don't want to live", "do not want to live", "no reason to live", "overdose",
           "can't breathe", "cant breathe", "chest pain", "heart attack", "being abused", "i am in danger")

# ------------------------------------------------------------------ entities / time / constraints
_ASSET = {"btc": "BTC", "bitcoin": "BTC", "eth": "ETH", "ethereum": "ETH", "sol": "SOL", "solana": "SOL",
          "bnb": "BNB", "xrp": "XRP", "doge": "DOGE", "dogecoin": "DOGE", "ada": "ADA", "cardano": "ADA",
          "nifty": "NIFTY", "nifty50": "NIFTY", "banknifty": "BANKNIFTY", "sensex": "SENSEX",
          "nasdaq": "NASDAQ", "sp500": "SP500", "s&p": "SP500", "dow": "DOW", "gold": "GOLD", "silver": "SILVER",
          "oil": "OIL", "eurusd": "EURUSD", "usdinr": "USDINR", "gbpusd": "GBPUSD", "usdjpy": "USDJPY"}
_BRAINS = frozenset("unity heroic alpha legend marco supervisor cognitive feelings feeling mcvl".split())
_TICKER = re.compile(r"\b[A-Z]{2,5}\b")
_NOT_TICKER = frozenset("AI OK US UK UN EU IT TV PC HR CEO CFO ETA FAQ API URL PDF USB SQL HTML CSS JSON VALE HEROIC "
                        "ALPHA LEGEND MARCO UNITY MCVL DO IS IF IN ON OR TO NO YES THE AND FOR NOT ARE BUT CAN WHY "
                        "HOW WHAT WHO WHEN".split())

_TS_HARD = frozenset("today now currently current latest recent recently yesterday tomorrow tonight live realtime "
                     "real-time breaking weather election outage aaj abhi".split())
_TS_SOFT = frozenset("price prices score scores news update updates trending".split())
_TS_PHRASES = (" right now ", " this week ", " this month ", " this year ", " real time ", " at the moment ",
               " as of ", " up to date ", " last week ", " last month ", " these days ")

_DEADLINE = re.compile(r"\b(?:within|in|by|before|under)\s+(\d+(?:\.\d+)?)\s*(seconds?|secs?|minutes?|mins?|hours?|hrs?|days?|weeks?)\b")
_DUE = re.compile(r"\b(?:by|before|until)\s+(today|tonight|tomorrow|monday|tuesday|wednesday|thursday|friday|saturday|sunday|end of (?:the )?(?:day|week|month))\b")
_TIMEFRAME = re.compile(r"\b(\d+)\s?(m|min|mins|minute|minutes|h|hr|hrs|hour|hours|d|day|days|w|week|weeks|mo|month|months|y|yr|year|years)\b(?=\s+(?:chart|candle|candles|timeframe|tf|interval|data|bars?))")
_TF_WORDS = frozenset("intraday scalp scalping swing daily weekly monthly hourly longterm long-term short-term".split())
_FMT_SHORT = frozenset("short brief briefly concise tldr".split())
_FMT_LONG = frozenset("detailed thorough comprehensive".split())
_FMT_OTHER = frozenset("simple simply beginner eli5 table bullets bullet".split())
_URGENCY = frozenset("asap urgent urgently immediately emergency hurry quickly fast".split())
_URGENCY_PHRASES = (" right away ", " at once ", " right now ")
_EXCLUDE = re.compile(r"\b(?:don't|dont|do not|never|without|avoid|no need to)\s+([a-z']+(?:\s+[a-z']+){0,3})")

_HYP = ("i think", "i believe", "i'm sure", "i am sure", "i'm convinced", "obviously", "clearly", "everyone knows",
        "isn't it", "isn't that", "confirm that", "confirm this", "prove that", "prove it", "agree that",
        "you agree", "it must be", "it has to be", "definitely", "for sure", "no doubt")
_ANAPHORA = frozenset("it this that them those these same above previous there".split())
_FOLLOW_START = frozenset("and also then so but next another continue again more".split())
_FOLLOW_PHRASES = ("what about", "how about", "go on", "tell me more")

_SPLIT = re.compile(
    r"\s*(?:;|\n+)\s*|\b(?:and then|after that|then|also|plus|as well as)\b|"
    r"\band\s+(?=(?:tell|show|give|explain|write|make|create|check|find|analyze|analyse|compare|plan|send|build|help)\b)|"
    r"(?<=[.?!])\s+(?=[A-Za-z])")
_POLITE = re.compile(r"^(?:(?:hey|hi|hello|ok|okay|so|please|kindly|vale|can you|could you|would you|will you|"
                     r"i want to|i need to|i'd like to|i would like to|let's|lets|i want you to|i need you to|just)\s+)+")
_SUBJ_STRIP = sorted(
    ("tell me about", "tell me whether", "tell me", "what is the", "what is a", "what is", "what are the", "what are",
     "what does", "who is", "explain", "describe", "define", "investigate", "analyze", "analyse", "compare",
     "write a", "write me", "draft a", "make a plan for", "make a plan", "create a plan for", "plan for", "how to",
     "how can i", "how do i", "should i", "find out", "look up", "research", "show me", "give me"),
    key=len, reverse=True)
_SUBJ_CUT = re.compile(r"\s+(?:and then|and tell me|and also|and explain|and show|and give me|and let me know|then|also|plus)\s+|;|\.\s")
_CMP_SPLIT = re.compile(r"\s+(?:vs\.?|versus|compared to|compare to|compared with|or|and)\s+|,\s*")
_CMP_BODY = re.compile(r"(?:compare|comparison of|comparing|difference between|differences between|between|which is better,?|better:?)\s+(.+)")


def comparison_subjects(text: str) -> List[str]:
    t = text.lower().replace("pros and cons", "pros_cons")
    m = _CMP_BODY.search(t)
    body = re.sub(r"[?.!]+$", "", m.group(1) if m else t)
    parts = [p.strip() for p in _CMP_SPLIT.split(body)]
    return [clip(p, 40) for p in parts if p and any(w not in STOPWORDS for w in tokens(p))][:5]


def _score_types(toks: List[str], joined: str, tset: Set[str]) -> Dict[str, float]:
    s: Dict[str, float] = {}
    for ph, typ, w in _PH:
        if ph in joined:
            s[typ] = s.get(typ, 0.0) + w
    for t in tset:
        lst = _WD.get(t)
        if lst:
            for typ, w in lst:
                s[typ] = s.get(typ, 0.0) + w
    if toks:
        for typ, w in _WD.get(toks[0], ()):
            if w >= _WORD_W:
                s[typ] = s.get(typ, 0.0) + 0.8          # an imperative opening verb is a strong signal
    return s


def _subject(text: str) -> str:
    t = " ".join(text.lower().split())
    t = _POLITE.sub("", t)
    for p in _SUBJ_STRIP:
        if t.startswith(p + " "):
            t = t[len(p) + 1:]
            break
    t = _SUBJ_CUT.split(t, 1)[0]
    for lead in ("whether ", "if ", "that "):
        if t.startswith(lead):
            t = t[len(lead):]
    t = t.strip(" ?!.,;:\"'")
    return clip(t or " ".join(text.lower().split()), 90)


class IntentEngine:
    def __init__(self, cache_size: int = 1024, max_chars: int = 4000) -> None:
        self._max = max_chars
        self._cached = lru_cache(maxsize=cache_size)(self._analyze)

    def analyze(self, text: str, has_history: bool = False) -> IntentProfile:
        return self._cached((text or "")[: self._max].strip(), bool(has_history))

    # ------------------------------------------------------------------
    def _analyze(self, text: str, has_history: bool) -> IntentProfile:
        toks = tokens(text)
        n = len(toks)
        tset = set(toks)
        joined = " " + " ".join(toks) + " "

        scores = _score_types(toks, joined, tset)
        crisis = any(p in joined for p in _CRISIS)
        emotional = bool(tset & _EMOTION) or crisis
        conv = 0.0
        if n <= 7:
            conv = sum(_CONV_W for t in tset if t in _CONV_WORDS) + sum(_PHRASE_W for p in _CONV_PHRASES if p in joined)
        top_other = max(scores.values(), default=0.0)

        implicit: List[str] = []
        if crisis and top_other < 4.0:
            mission_type, clarity, secondary = "CONVERSATION", 0.85, ()
        elif conv >= _CONV_W and top_other < 2.0:
            mission_type, clarity, secondary = "CONVERSATION", 0.9, ()
        elif top_other >= 0.9:
            ranked = sorted(scores.items(), key=lambda kv: -kv[1])
            mission_type = ranked[0][0]
            second = ranked[1][1] if len(ranked) > 1 else 0.0
            clarity = top_other / (top_other + second + 1.0)
            secondary = tuple(t for t, v in ranked[1:4] if v >= 1.2 and v >= 0.5 * top_other)
        elif emotional:
            mission_type, clarity, secondary = "CONVERSATION", (0.85 if crisis else 0.55), ()
        else:
            clarity, secondary = 0.35, ()
            bare_q = n >= 2 or "?" in text
            if bare_q:
                implicit.append("no_explicit_intent_cue")
                live = bool(tset & _TS_HARD) or bool(tset & _TS_SOFT) or any(p in joined for p in _TS_PHRASES)
                mission_type = "RESEARCH" if (live or any(t in _DOM_W and "MARKET" in _DOM_W[t] for t in tset)) else "EXPLANATION"
            else:
                mission_type, clarity = "OTHER", 0.2

        # domains
        dscore: Dict[str, float] = {}
        for t in tset:
            for d, w in _DOM_W.get(t, {}).items():
                dscore[d] = dscore.get(d, 0.0) + w
        for ph, d in _DOM_PH:
            if ph in joined:
                dscore[d] = dscore.get(d, 0.0) + 1.5
        domains = tuple(d for d, v in sorted(dscore.items(), key=lambda kv: -kv[1]) if v >= 1.0) or ("GENERAL",)
        if emotional and "HUMAN" not in domains:
            domains = ("HUMAN",) + tuple(d for d in domains if d != "GENERAL")
        market = "MARKET" in domains

        # entities
        entities: List[Tuple[str, str]] = []
        seen: Set[str] = set()
        for t in toks:
            a = _ASSET.get(t)
            if a and a not in seen:
                seen.add(a)
                entities.append(("ASSET", a))
            elif t in _BRAINS and t.upper() not in seen:
                seen.add(t.upper())
                entities.append(("BRAIN", "FEELINGS" if t == "feeling" else t.upper()))
        if market and sum(1 for c in text if c.isupper()) < 0.6 * max(1, sum(1 for c in text if c.isalpha())):
            for tk in _TICKER.findall(text):
                if tk not in _NOT_TICKER and tk not in seen and len(seen) < 6:
                    seen.add(tk)
                    entities.append(("ASSET", tk))

        if mission_type == "OTHER" and entities:
            mission_type, clarity = "RESEARCH", 0.3
            implicit.append("no_explicit_intent_cue")

        # time sensitivity
        hard = bool(tset & _TS_HARD) or any(p in joined for p in _TS_PHRASES)
        soft = bool(tset & _TS_SOFT)
        has_asset = any(k == "ASSET" for k, _ in entities)
        time_sensitive = hard or (soft and (has_asset or mission_type != "EXPLANATION"))

        # constraints
        cons: List[Tuple[str, str]] = []
        low = text.lower()
        deadline_spans = []
        for m in _DEADLINE.finditer(low):
            cons.append(("deadline", f"{m.group(1)} {m.group(2)}"))
            deadline_spans.append(m.span())
        for m in _DUE.finditer(low):
            cons.append(("deadline", m.group(1)))
        tf_text = low
        for a, b in deadline_spans:
            tf_text = tf_text[:a] + " " * (b - a) + tf_text[b:]
        for m in _TIMEFRAME.finditer(tf_text):
            cons.append(("timeframe", f"{m.group(1)}{m.group(2)}"))
        for t in tset & _TF_WORDS:
            cons.append(("timeframe", t))
        fmts = []
        for t in toks:
            if t in _FMT_SHORT or t in _FMT_LONG or t in _FMT_OTHER:
                fmts.append(t)
        for p in ("in detail", "step by step", "in simple english", "one line"):
            if " " + p + " " in joined:
                fmts.append(p)
        for f in fmts[:4]:
            cons.append(("format", f))
        for t in tset & _URGENCY:
            cons.append(("urgency", t))
        for p in _URGENCY_PHRASES:
            if p in joined:
                cons.append(("urgency", p.strip()))
        for m in _EXCLUDE.finditer(low):
            cons.append(("exclude", m.group(1)))
        constraints = tuple(cons[:12])

        conflicts: List[str] = []
        if any(f in _FMT_SHORT or f == "one line" for f in fmts) and any(f in _FMT_LONG or f == "in detail" for f in fmts):
            conflicts.append("short_vs_detailed")

        # hypotheses (user beliefs that must not be assumed true)
        hyps = []
        for p in _HYP:
            i = joined.find(" " + p + " ")
            if i >= 0 and len(joined[i + len(p) + 2:].split()) >= 3:
                hyps.append(p)
        hypotheses = tuple(hyps[:3])

        # topic tokens (what is left once cue words and stopwords are removed)
        topic = [t for t in toks if t not in STOPWORDS and t not in _CUE_WORDS]
        ambiguity: List[str] = []
        content_count = sum(1 for t in toks if t not in STOPWORDS)
        if mission_type not in ("CONVERSATION", "DIAGNOSTIC", "MONITORING") and content_count <= 1 and not entities:
            ambiguity.append("no_subject")
        if (tset & _ANAPHORA) and len(topic) <= 1 and not has_history and mission_type != "CONVERSATION":
            ambiguity.append("referential_without_antecedent")
        if mission_type == "OTHER" and n <= 3 and not entities:
            ambiguity.append("no_clear_request")
        follow_up = bool(has_history and (
            (toks and toks[0] in _FOLLOW_START) or any(p in joined for p in _FOLLOW_PHRASES)
            or ((tset & _ANAPHORA) and len(topic) <= 2)))

        # sub-intents
        subs: List[Tuple[str, str]] = []
        if n >= 6:
            segs = [s.strip() for s in _SPLIT.split(text) if s and len(s.split()) >= 2]
            if len(segs) >= 2:
                for seg in segs[:6]:
                    st = tokens(seg)
                    sc = _score_types(st, " " + " ".join(st) + " ", set(st))
                    if sc:
                        subs.append((max(sc.items(), key=lambda kv: kv[1])[0], clip(seg, 140)))
                if len(subs) < 2:
                    subs = []

        # implicit requirements
        if time_sensitive:
            implicit.append("fresh_information")
        if mission_type in ("ANALYSIS", "RESEARCH", "DECISION_SUPPORT", "COMPARISON") or (market and time_sensitive):
            implicit.append("evidence_for_claims")
        if mission_type == "DECISION_SUPPORT" and market:
            implicit.append("risk_disclosure")
        if mission_type == "COMPARISON" and (tset & {"compare", "versus", "vs", "vs.", "comparing"}
                                             or " difference between " in joined or " better than " in joined
                                             or " compared to " in joined):
            implicit.append("needs_two_subjects")
        if emotional or "HUMAN" in domains:
            implicit.append("human_sensitivity")
        if mission_type == "EXECUTION":
            implicit.append("execution_authorization")
        if hypotheses:
            implicit.append("unverified_user_belief")
        if mission_type in ("ANALYSIS", "DECISION_SUPPORT", "RESEARCH"):
            implicit.append("state_limitations")

        return IntentProfile(
            text=text, subject=_subject(text), mission_type=mission_type, domains=domains,
            secondary_types=secondary, clarity=clarity, ambiguity=tuple(ambiguity), implicit=tuple(implicit),
            time_sensitive=time_sensitive, entities=tuple(entities), constraints=constraints,
            hypotheses=hypotheses, sub_intents=tuple(subs), emotional=emotional, crisis=crisis,
            follow_up=follow_up, conflicts=tuple(conflicts), token_count=n, tokens=frozenset(tset))
