import os
import re
import requests

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class VALEBrain:
    """
    VALE AI CENTRAL BRAIN

    Responsibilities:
    - Understand user messages
    - Detect intent
    - Search internal knowledge
    - Decide when live internet information is needed
    - Search the web through Exa
    - Process and rank research
    - Generate a useful response
    - Maintain short-term conversation memory

    main.py only needs to call:

        result = brain.think(message)

    The result contains:

        result["response"]
        result["intent"]
        result["needs_internet"]
    """

    def __init__(self):
        self.name = "VALE"
        self.version = "1.0"
        self.creator = "Md Tauqueer"

        # ============================================================
        # VALE MASTER INSTRUCTIONS
        #
        # YOU CAN EDIT YOUR OWN VALE INSTRUCTIONS HERE.
        # ============================================================

        self.master_prompt = """
VALE is an advanced AI intelligence system.

VALE must understand the user's real intention before answering.

VALE should:
- Give direct answers instead of generic placeholder messages.
- Use internal knowledge when reliable knowledge is available.
- Use internet research for current, recent, live, market, price,
  prediction, news, or unknown factual information.
- Never show raw search results as the main answer unless requested.
- Analyze multiple sources before forming an answer.
- Clearly state uncertainty when information is uncertain.
- Avoid pretending to know something that is not supported by available data.
- For market questions, distinguish facts from predictions.
- Never guarantee that a financial asset will rise or fall.
- Keep answers useful, understandable, and relevant.
"""

        # ============================================================
        # INTERNAL KNOWLEDGE BASE
        #
        # We can keep expanding this later.
        # ============================================================

        self.knowledge: Dict[str, str] = {
            "car": (
                "A car is a road vehicle designed mainly to transport people. "
                "Cars commonly have four wheels and use an internal-combustion "
                "engine or an electric motor."
            ),

            "bitcoin": (
                "Bitcoin is a decentralized digital currency that operates on "
                "a blockchain network. Its market price can change significantly "
                "because of supply and demand, investor sentiment, liquidity, "
                "economic conditions, regulation, and other factors."
            ),

            "artificial intelligence": (
                "Artificial intelligence, commonly called AI, is technology "
                "designed to perform tasks involving capabilities such as "
                "language processing, pattern recognition, prediction, "
                "reasoning, and decision support."
            ),

            "vale": (
                "VALE is an AI intelligence system being developed as an "
                "expandable platform for knowledge, reasoning, internet "
                "research, market intelligence, strategy analysis, "
                "and risk analysis."
            ),
        }

        # ============================================================
        # SHORT-TERM MEMORY
        # ============================================================

        self.memory: List[Dict[str, Any]] = []
        self.max_memory = 50

        # ============================================================
        # INTERNET CONFIGURATION
        # ============================================================

        self.exa_api_url = "https://api.exa.ai/search"

    # ================================================================
    # TEXT UNDERSTANDING
    # ================================================================

    def normalize(self, message: str) -> str:
        """Clean user input."""

        if not isinstance(message, str):
            message = str(message)

        message = message.strip()
        message = re.sub(r"\s+", " ", message)

        return message

    def understand(self, message: str) -> Dict[str, Any]:
        """Create a structured representation of the message."""

        text = self.normalize(message)
        lower = text.lower()

        words = re.findall(r"\b[\w']+\b", lower)

        return {
            "original": text,
            "lower": lower,
            "words": words,
            "word_count": len(words),
        }

    # ================================================================
    # INTENT DETECTION
    # ================================================================

    def detect_intent(self, data: Dict[str, Any]) -> str:
        """Determine what the user wants."""

        text = data["lower"]

        # Greetings
        greetings = {
            "hi",
            "hello",
            "hey",
            "hii",
            "helo",
            "good morning",
            "good afternoon",
            "good evening",
        }

        if text in greetings:
            return "conversation"

        # VALE identity
        if any(
            phrase in text
            for phrase in [
                "who are you",
                "what are you",
                "what is vale",
                "who made you",
                "who created you",
                "who is your owner",
                "who is ur owner",
                "who owns you",
                "what is your name",
                "what ur name",
                "what's your name",
            ]
        ):
            return "vale_identity"

        # Market / finance
        market_words = [
            "bitcoin",
            "btc",
            "crypto",
            "ethereum",
            "eth",
            "stock",
            "market",
            "forex",
            "trading",
            "trade",
            "price",
            "buy",
            "sell",
            "bullish",
            "bearish",
            "entry",
            "target",
            "stop loss",
            "risk",
            "strategy",
            "investment",
        ]

        if any(word in text for word in market_words):
            return "market_analysis"

        # Explicit internet research
        if any(
            phrase in text
            for phrase in [
                "search",
                "google",
                "look up",
                "research",
                "find online",
                "on internet",
                "on the internet",
                "latest information",
            ]
        ):
            return "research"

        # Current information
        if any(
            phrase in text
            for phrase in [
                "latest",
                "today",
                "right now",
                "current",
                "recent",
                "live",
                "news",
                "this week",
                "this month",
                "now",
            ]
        ):
            return "current_information"

        # General questions
        if text.startswith(
            (
                "what",
                "who",
                "where",
                "when",
                "which",
            )
        ):
            return "knowledge_question"

        # Explanation
        if text.startswith(("how", "why")):
            return "explanation"

        return "general"

    # ================================================================
    # INTERNAL KNOWLEDGE
    # ================================================================

    def search_knowledge(
        self,
        data: Dict[str, Any]
    ) -> Optional[str]:
        """Search VALE's internal knowledge."""

        text = data["lower"]

        for topic, information in self.knowledge.items():

            if topic in text:
                return information

        return None

    # ================================================================
    # INTERNET DECISION
    # ================================================================

    def should_search_internet(
        self,
        data: Dict[str, Any],
        intent: str,
        knowledge_answer: Optional[str]
    ) -> bool:
        """
        Decide whether live internet research is useful.
        """

        text = data["lower"]

        # Greetings never need internet.
        if intent == "conversation":
            return False

        # VALE identity is internal.
        if intent == "vale_identity":
            return False

        # These categories should normally use current research.
        if intent in (
            "market_analysis",
            "research",
            "current_information",
        ):
            return True

        # Unknown knowledge questions can use the internet.
        if intent in (
            "knowledge_question",
            "explanation",
        ):
            if not knowledge_answer:
                return True

        # Explicitly current words.
        current_terms = [
            "latest",
            "today",
            "current",
            "recent",
            "live",
            "news",
            "price",
        ]

        if any(term in text for term in current_terms):
            return True

        return False

    # ================================================================
    # VALE IDENTITY ANSWERS
    # ================================================================

    def answer_identity(self, data: Dict[str, Any]) -> str:
        """Answer questions about VALE itself."""

        text = data["lower"]

        if (
            "owner" in text
            or "made you" in text
            or "created you" in text
            or "owns you" in text
        ):
            return (
                f"VALE is being developed by {self.creator}. "
                "I am an AI intelligence system being built and expanded "
                "for knowledge, research, market intelligence, strategy, "
                "and risk analysis."
            )

        if "name" in text:
            return (
                "My name is VALE. "
                "I am an AI intelligence system."
            )

        return self.knowledge["vale"]

    # ================================================================
    # INTERNET SEARCH
    # ================================================================

    def search_internet(
        self,
        query: str,
        num_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search the internet through Exa.

        Requires:
            EXA_API_KEY

        to be configured in Render environment variables.
        """

        api_key = os.environ.get("EXA_API_KEY")

        if not api_key:
            print("VALE INTERNET: EXA_API_KEY is not configured.")
            return []

        try:
            response = requests.post(
                self.exa_api_url,
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": api_key,
                },
                json={
                    "query": query,
                    "type": "auto",
                    "numResults": num_results,
                    "contents": {
                        "highlights": True,
                    },
                },
                timeout=25,
            )

            response.raise_for_status()

            payload = response.json()

            results = []

            for item in payload.get("results", []):

                title = item.get("title", "")
                url = item.get("url", "")
                highlights = item.get("highlights", [])

                if not isinstance(highlights, list):
                    highlights = []

                cleaned_highlights = []

                for highlight in highlights:
                    if highlight:
                        cleaned = re.sub(
                            r"\s+",
                            " ",
                            str(highlight)
                        ).strip()

                        if cleaned:
                            cleaned_highlights.append(cleaned)

                results.append(
                    {
                        "title": title,
                        "url": url,
                        "highlights": cleaned_highlights,
                    }
                )

            return results

        except Exception as error:

            print(
                "VALE INTERNET SEARCH ERROR:",
                str(error)
            )

            return []

    # ================================================================
    # INTERNET RESULT ANALYSIS
    # ================================================================

    def clean_research_results(
        self,
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Remove weak or empty results.
        """

        cleaned_results = []

        for result in results:

            title = str(
                result.get("title", "")
            ).strip()

            url = str(
                result.get("url", "")
            ).strip()

            highlights = result.get(
                "highlights",
                []
            )

            if not isinstance(highlights, list):
                highlights = []

            useful_highlights = []

            for highlight in highlights:

                if not highlight:
                    continue

                text = re.sub(
                    r"\s+",
                    " ",
                    str(highlight)
                ).strip()

                if len(text) > 20:
                    useful_highlights.append(text)

            if title or useful_highlights:

                cleaned_results.append(
                    {
                        "title": title,
                        "url": url,
                        "highlights": useful_highlights,
                    }
                )

        return cleaned_results

    # ================================================================
    # RESEARCH-BASED RESPONSE
    # ================================================================

    def build_research_answer(
        self,
        question: str,
        intent: str,
        results: List[Dict[str, Any]]
    ) -> str:
        """
        Convert internet research into a useful VALE answer.

        This does NOT simply dump the raw search results.
        """

        results = self.clean_research_results(results)

        if not results:

            return (
                "I searched for current information but I could not retrieve "
                "reliable results at the moment. Please try again."
            )

        # ------------------------------------------------------------
        # Collect the strongest available research information.
        # ------------------------------------------------------------

        research_points = []

        for result in results[:5]:

            title = result.get("title", "").strip()

            highlights = result.get(
                "highlights",
                []
            )

            if highlights:

                point = highlights[0]

                if len(point) > 900:
                    point = point[:900].rsplit(
                        " ",
                        1
                    )[0] + "."

                research_points.append(
                    {
                        "title": title,
                        "text": point,
                        "url": result.get("url", ""),
                    }
                )

        if not research_points:

            return (
                "I found internet results for your question, but the returned "
                "sources did not contain enough usable information to produce "
                "a reliable answer."
            )

        # ------------------------------------------------------------
        # MARKET RESPONSE
        # ------------------------------------------------------------

        if intent == "market_analysis":

            answer = (
                "Based on the current information I found, here is VALE's "
                "research summary:\n\n"
            )

            for point in research_points[:3]:

                if point["text"]:
                    answer += (
                        f"{point['text']}\n\n"
                    )

            answer += (
                "VALE assessment: Market direction cannot be guaranteed. "
                "Internet research can show current information and market "
                "signals, but Bitcoin and other assets can move rapidly. "
                "A reliable trading decision should consider price trend, "
                "volume, liquidity, volatility, risk, and current news."
            )

            return answer

        # ------------------------------------------------------------
        # GENERAL RESEARCH RESPONSE
        # ------------------------------------------------------------

        answer = ""

        if len(research_points) == 1:

            answer += (
                research_points[0]["text"]
            )

        else:

            answer += (
                "Based on the information VALE found, the most relevant "
                "answer is:\n\n"
            )

            answer += research_points[0]["text"]

            if len(research_points) > 1:

                answer += (
                    "\n\nAdditional information found during research:\n"
                )

                for point in research_points[1:3]:

                    answer += (
                        f"\n• {point['text']}"
                    )

        answer += (
            "\n\nThis answer is based on information retrieved during "
            "VALE's current web research."
        )

        return answer

    # ================================================================
    # LOCAL RESPONSE
    # ================================================================

    def build_local_answer(
        self,
        data: Dict[str, Any],
        intent: str,
        knowledge_answer: Optional[str]
    ) -> str:
        """
        Generate an answer without internet research.
        """

        if intent == "conversation":

            return (
                "Hello. I am VALE. "
                "What would you like me to help you with?"
            )

        if intent == "vale_identity":

            return self.answer_identity(data)

        if knowledge_answer:

            return knowledge_answer

        return (
            "I do not yet have enough internal knowledge to answer this "
            "accurately. I will need to expand VALE's knowledge system "
            "or research reliable external information."
        )

    # ================================================================
    # MEMORY
    # ================================================================

    def remember(
        self,
        message: str,
        response: str,
        intent: str
    ) -> None:
        """Store recent conversation information."""

        memory_item = {
            "message": message,
            "response": response,
            "intent": intent,
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
        }

        self.memory.append(memory_item)

        if len(self.memory) > self.max_memory:

            self.memory = self.memory[
                -self.max_memory:
            ]

# ================================================================
    # MAIN VALE BRAIN
    # ================================================================

    def think(
        self,
        message: str
    ) -> Dict[str, Any]:
        """
        MAIN ENTRY POINT.

        main.py sends the user message here.

        The brain:
        1. Understands
        2. Detects intent
        3. Checks knowledge
        4. Decides whether to research
        5. Searches internet when necessary
        6. Builds a response
        7. Stores memory
        """

        # Step 1: Understand
        data = self.understand(message)

        # Step 2: Detect intent
        intent = self.detect_intent(data)

        # Step 3: Search VALE knowledge
        knowledge_answer = self.search_knowledge(data)

        # Step 4: Decide about internet
        use_internet = self.should_search_internet(
            data,
            intent,
            knowledge_answer,
        )

        web_results: List[Dict[str, Any]] = []

        # Step 5: Research internet
        if use_internet:

            web_results = self.search_internet(
                data["original"],
                num_results=5,
            )

            # Step 6: Build research answer
            response = self.build_research_answer(
                data["original"],
                intent,
                web_results,
            )

        else:

            # Step 6: Build local answer
            response = self.build_local_answer(
                data,
                intent,
                knowledge_answer,
            )

        # Step 7: Remember
        self.remember(
            data["original"],
            response,
            intent,
        )

        # IMPORTANT:
        #
        # needs_internet is False here because THIS brain has already
        # performed the internet search itself.
        #
        # This prevents main.py from performing the old duplicate search.
        #
        return {
            "response": response,
            "intent": intent,
            "needs_internet": False,
            "internet_used": use_internet,
            "knowledge_found": knowledge_answer is not None,
            "web_results": web_results,
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
        }

    # ================================================================
    # ADD KNOWLEDGE
    # ================================================================

    def add_knowledge(
        self,
        topic: str,
        information: str
    ) -> None:
        """
        Add information to VALE's internal knowledge.
        """

        topic = self.normalize(topic).lower()
        information = self.normalize(information)

        if topic and information:

            self.knowledge[topic] = information

    # ================================================================
    # READ MEMORY
    # ================================================================

    def get_memory(
        self
    ) -> List[Dict[str, Any]]:
        """
        Return VALE's current short-term memory.
        """

        return self.memory.copy()

    # ================================================================
    # BRAIN STATUS
    # ================================================================

    def status(
        self
    ) -> Dict[str, Any]:
        """
        Return information about VALE's brain.
        """

        api_key = os.environ.get(
            "EXA_API_KEY"
        )

        return {
            "name": self.name,
            "version": self.version,
            "creator": self.creator,
            "knowledge_topics": len(
                self.knowledge
            ),
            "memory_items": len(
                self.memory
            ),
            "internet_search_available": bool(
                api_key
            ),
        }