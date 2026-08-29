import re
from datetime import datetime


class VALEBrain:
    def __init__(self):
        self.name = "VALE"
        self.version = "1.0"

        # ==================================================
        # VALE CORE INSTRUCTIONS
        # WRITE OR PASTE YOUR OWN PROMPT BELOW
        # ==================================================
        self.system_prompt = """
You are VALE, an advanced AI intelligence system.

Your purpose is to help users analyze questions,
understand requests, reason carefully, and provide
clear and useful answers.

Always understand the user's actual question before responding.
Do not give unrelated information.
Be accurate, clear, intelligent, and honest.

When current or live information is required,
tell the main system that internet access is needed.

You can add your own VALE instructions here.
"""

    def understand(self, message):
        text = message.strip()
        lower = text.lower()

        words = re.findall(r"\b\w+\b", lower)

        return {
            "original": text,
            "lower": lower,
            "words": words
        }

    def detect_intent(self, data):
        text = data["lower"].strip()

        if text in ("hello", "hi", "hey", "hello vale", "hi vale"):
            return "conversation"

        current_words = [
            "latest",
            "today",
            "current",
            "now",
            "recent",
            "news",
            "live",
            "price",
            "market"
        ]

        if any(word in text for word in current_words):
            return "current_information"

        if any(
            phrase in text
            for phrase in (
                "will bitcoin",
                "bitcoin go up",
                "bitcoin go down",
                "btc go up",
                "btc go down",
                "stock go up",
                "stock go down",
                "crypto price"
            )
        ):
            return "current_information"

        if text.startswith(
            (
                "what is",
                "what are",
                "who is",
                "who are",
                "tell me about"
            )
        ):
            return "knowledge"

        if text.startswith(
            (
                "how",
                "why",
                "when",
                "where",
                "can you",
                "could you"
            )
        ):
            return "explanation"

        return "general"

    def needs_internet(self, data, intent):
        text = data["lower"]

        if intent == "conversation":
            return False

        if intent == "current_information":
            return True

        live_indicators = [
            "bitcoin",
            "btc",
            "crypto",
            "stock price",
            "market price",
            "weather",
            "latest",
            "news",
            "today"
        ]

        if any(indicator in text for indicator in live_indicators):
            return True

        return False

    def create_response(self, data, intent):
        text = data["lower"]

        if intent == "conversation":
            if text in ("hello", "hi", "hey", "hello vale", "hi vale"):
                return (
                    "Hello. I am VALE, your AI intelligence system. "
                    "I am online and ready to help."
                )

        if "your name" in text or "what is your name" in text:
            return (
                "My name is VALE. "
                "I am an AI intelligence system."
            )

        if "who is your owner" in text or "who is ur owner" in text:
            return (
                "I am VALE, an AI system created and developed "
                "for the VALE platform."
            )

        if intent == "knowledge":
            return (
                "I understand your question. "
                "I will analyze the available information and "
                "provide the most useful answer I can."
            )

        if intent == "explanation":
            return (
                "I understand that you want an explanation. "
                "I will analyze the question carefully and explain it clearly."
            )

        return (
            "I understand your message. "
            "I am analyzing your request."
        )

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
            "intent": intent,
            "needs_internet": internet_needed,
            "response": response,
            "system_prompt": self.system_prompt,
            "timestamp": datetime.utcnow().isoformat()
        }
