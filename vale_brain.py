import re
from datetime import datetime, timezone


class VALEBrain:
    """
    VALE Core Brain

    This file is the central intelligence layer for VALE.

    main.py should send the user's message to:
        brain.think(message)

    This brain then returns structured information including:
        - intent
        - needs_internet
        - response
        - metadata
    """

    def __init__(self):
        self.name = "VALE"
        self.version = "1.0"

        # ============================================================
        # YOUR VALE INSTRUCTIONS / PROMPT
        #
        # WRITE YOUR OWN VALE PROMPT BETWEEN THE TRIPLE QUOTES BELOW.
        #
        # Example:
        #
        # You are VALE, an advanced AI trading intelligence system.
        # You should be accurate, helpful, analytical and honest.
        # Focus strongly on markets, trading, strategy and risk.
        # Never pretend to know information you do not know.
        #
        # You can replace or expand this prompt anytime.
        # ============================================================

        self.system_prompt = """
You are VALE, an AI intelligence system.

Your purpose is to help users understand information, analyze
questions and provide useful responses.

VALE should be helpful, clear, analytical and honest.

VALE specializes in:
- Market intelligence
- Trading concepts
- Strategy analysis
- Risk awareness
- General information analysis

VALE must not pretend that it knows something when it does not.
VALE should identify when current or external information is needed.

For greetings and simple conversation, VALE should respond naturally.

For questions about VALE itself, VALE should answer from its
configured identity instead of searching random websites.
"""

        # ============================================================
        # VALE'S INTERNAL IDENTITY KNOWLEDGE
        #
        # You can edit or expand these values.
        # ============================================================

        self.identity = {
            "name": "VALE",
            "version": "1.0",
            "description": (
                "VALE is an AI intelligence system designed to help "
                "with market intelligence, trading concepts, strategy, "
                "risk awareness and information analysis."
            ),
            "purpose": (
                "VALE analyzes questions and information to provide "
                "useful, structured and reliable assistance."
            ),
        }

        # ============================================================
        # SIMPLE INTERNAL KNOWLEDGE
        #
        # You can add your own permanent VALE knowledge here later.
        # ============================================================

        self.internal_knowledge = {
            "what is vale": self.identity["description"],
            "what is your name": (
                "My name is VALE. I am an AI intelligence system."
            ),
            "who are you": (
                "I am VALE, an AI intelligence system designed for "
                "market intelligence, trading concepts, strategy, "
                "risk awareness and information analysis."
            ),
            "what can you do": (
                "I can help analyze questions, explain concepts, "
                "assist with market and trading topics, consider "
                "strategy and risk, and identify when current "
                "external information is needed."
            ),
        }

    # ================================================================
    # TEXT UNDERSTANDING
    # ================================================================

    def understand(self, message):
        text = str(message).strip()
        lower = text.lower()

        words = re.findall(r"\b[\w'-]+\b", lower)

        return {
            "original": text,
            "lower": lower,
            "words": words,
            "word_count": len(words),
        }

    # ================================================================
    # NORMALIZE COMMON WORDING
    # ================================================================

    def normalize_question(self, text):
        normalized = text.lower().strip()

        replacements = {
            "ur": "your",
            "u ": "you ",
            "u?": "you?",
            "whats": "what is",
            "what's": "what is",
            "who's": "who is",
            "im": "i am",
            "dont": "do not",
            "doesnt": "does not",
            "cant": "cannot",
        }

        for old, new in replacements.items():
            normalized = normalized.replace(old, new)

        normalized = re.sub(
            r"\s+",
            " ",
            normalized
        ).strip()

        return normalized

    # ================================================================
    # DETECT INTENT
    # ================================================================

    def detect_intent(self, data):
        text = self.normalize_question(data["lower"])

        greetings = {
            "hello",
            "hi",
            "hey",
            "hello vale",
            "hi vale",
            "hey vale",
        }

        if text in greetings:
            return "conversation"

        if any(
            phrase in text
            for phrase in [
                "your name",
                "who are you",
                "what are you",
                "what is vale",
                "what can you do",
                "about vale",
            ]
        ):
            return "vale_identity"

        if any(
            word in text
            for word in [
                "bitcoin",
                "btc",
                "crypto",
                "market",
                "stock",
                "forex",
                "trade",
                "trading",
                "price",
                "strategy",
                "risk",
            ]
        ):
            return "market"

        if text.startswith(
            (
                "what is",
                "what are",
                "who is",
                "who are",
                "define",
            )
        ):
            return "definition"

        if text.startswith(
            (
                "how",
                "why",
                "explain",
            )
        ):
            return "explanation"

        return "general"

    # ================================================================
    # DECIDE WHETHER CURRENT INTERNET DATA IS REQUIRED
    # ================================================================

    def needs_internet(self, data, intent):
        text = self.normalize_question(data["lower"])

        if intent == "conversation":
            return False

        if intent == "vale_identity":
            return False

        current_keywords = [
            "latest",
            "today",
            "current",
            "currently",
            "right now",
            "now",
            "recent",
            "live",
            "news",
            "price",
            "forecast",
            "prediction",
            "will bitcoin",
            "go up",
            "go down",
        ]

        if any(keyword in text for keyword in current_keywords):
            return True

        if intent == "market":
            return True

        return False

    # ================================================================
    # ANSWER QUESTIONS ABOUT VALE
    # ================================================================

    def answer_about_vale(self, data):
        text = self.normalize_question(data["lower"])

        if "name" in text:
            return (
                f"My name is {self.identity['name']}. "
                f"I am an AI intelligence system."
            )

        if (
            "who are you" in text
            or "what are you" in text
        ):
            return self.identity["description"]

        if "what is vale" in text:
            return self.identity["description"]

        if "what can you do" in text:
            return (
                "I can help with market intelligence, trading concepts, "
                "strategy analysis, risk awareness and general "
                "information analysis. I can also determine when "
                "current external information should be researched."
            )

        return (
            f"I am {self.identity['name']}, version "
            f"{self.identity['version']}. "
            f"{self.identity['description']}"
        )

    # ================================================================
    # CHECK INTERNAL KNOWLEDGE
    # ================================================================

    def find_internal_answer(self, data):
        text = self.normalize_question(data["lower"])

        for question, answer in self.internal_knowledge.items():
            if question == text:
                return answer

        return None

    # ================================================================
    # CREATE LOCAL RESPONSE
    # ================================================================

    def create_response(self, data, intent):
        text = self.normalize_question(data["lower"])

        if intent == "conversation":
            return (
                "Hello. I am VALE. What would you like me to help "
                "you analyze?"
            )

        if intent == "vale_identity":
            return self.answer_about_vale(data)

        internal_answer = self.find_internal_answer(data)

        if internal_answer:
            return internal_answer

        if intent == "definition":
            return (
                "I understand your question. This requires knowledge "
                "or information that should be answered by VALE's "
                "knowledge system."
            )

        if intent == "explanation":
            return (
                "I understand that you want an explanation. "
                "I will analyze the question and provide a clear answer."
            )

        if intent == "market":
            return (
                "I recognize this as a market or trading-related "
                "question. Current market information may be required "
                "before giving a reliable answer."
            )

        return (
            "I understand your message. I will analyze the available "
            "information to provide the most useful answer I can."
        )

    # ================================================================
    # MAIN VALE THINKING FUNCTION
    #
    # main.py connects to this function.
    #
    # As we expand VALE, we can keep adding intelligence inside this
    # file while preserving the same connection:
    #
    # brain.think(message)
    # ================================================================

    def think(self, message):
        understanding = self.understand(message)

        intent = self.detect_intent(understanding)

        internet_needed = self.needs_internet(
            understanding,
            intent
        )

        response = self.create_response(
            understanding,
            intent
        )

        return {
            "success": True,
            "brain": self.name,
            "version": self.version,
            "intent": intent,
            "needs_internet": internet_needed,
            "response": response,
            "understanding": {
                "original": understanding["original"],
                "word_count": understanding["word_count"],
            },
            "timestamp": datetime.now(
                timezone.utc
            ).isoformat(),
        }
