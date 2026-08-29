import re
from datetime import datetime, timezone

============================================================

VALE SYSTEM PROMPT

============================================================

VALE_SYSTEM_PROMPT = """
WRITE YOUR FULL VALE PROMPT HERE.

This is the exact place where you can add your own instructions.

You are VALE, an advanced AI intelligence system.

Your name is VALE.

Understand what the user is actually asking.

Answer the current user message.

Do not give unrelated answers.

Do not search the internet for simple greetings.

Do not search the internet for questions about VALE itself.

For current information, prices, latest news, and live markets,
use external information when needed.

For market questions, analyze carefully and do not claim that
an uncertain prediction is guaranteed.

Always give clear, useful, and relevant answers.
"""

class VALEBrain:

def __init__(self):
    self.name = "VALE"
    self.version = "1.0"
    self.system_prompt = VALE_SYSTEM_PROMPT

    self.owner_response = (
        "VALE is an AI intelligence system created and configured "
        "by its developer."
    )

def understand(self, message):
    text = str(message).strip()
    lower = text.lower()

    words = re.findall(
        r"\b[\w'-]+\b",
        lower
    )

    return {
        "original": text,
        "lower": lower,
        "words": words,
        "length": len(text)
    }

def detect_intent(self, data):
    text = data["lower"]

    if not text:
        return "empty"

    greetings = (
        "hello",
        "hi",
        "hey",
        "hii",
        "helo",
        "good morning",
        "good afternoon",
        "good evening"
    )

    if text in greetings:
        return "conversation"

    identity_patterns = (
        "what is your name",
        "what's your name",
        "whats your name",
        "who are you",
        "what are you",
        "tell me about yourself",
        "what is vale",
        "who is vale"
    )

    if any(pattern in text for pattern in identity_patterns):
        return "identity"

    owner_patterns = (
        "who is your owner",
        "who's your owner",
        "whos your owner",
        "who owns you",
        "who created you",
        "who made you",
        "your creator"
    )

    if any(pattern in text for pattern in owner_patterns):
        return "owner"

    market_words = (
        "bitcoin",
        "btc",
        "ethereum",
        "eth",
        "crypto",
        "cryptocurrency",
        "stock",
        "stocks",
        "forex",
        "trading",
        "market",
        "share price",
        "bullish",
        "bearish"
    )

    if any(word in text for word in market_words):
        return "market"

    current_words = (
        "latest",
        "today",
        "current",
        "news",
        "recent",
        "right now",
        "live",
        "currently"
    )

    if any(word in text for word in current_words):
        return "current_information"

    if text.startswith((
        "what is ",
        "what are ",
        "who is ",
        "who are "
    )):
        return "definition"

    if text.startswith((
        "how ",
        "why ",
        "explain ",
        "tell me how"
    )):
        return "explanation"

    return "general"

def needs_internet(self, data, intent):
    text = data["lower"]

    if intent in (
        "empty",
        "conversation",
        "identity",
        "owner"
    ):
        return False

    if intent == "market":

        current_market_words = (
            "today",
            "now",
            "current",
            "latest",
            "live",
            "price",
            "go up",
            "go down",
            "up or down",
            "prediction"
        )

        if any(
            word in text
            for word in current_market_words
        ):
            return True

        return False

    if intent == "current_information":
        return True

    return False

def create_response(self, data, intent):
    if intent == "empty":
        return (
            "Please ask me something. "
            "I am VALE and I am ready to help."
        )

    if intent == "conversation":
        return (
            "Hello. I am VALE. "
            "How can I help you?"
        )

    if intent == "identity":
        return (
            "My name is VALE. "
            "I am an AI intelligence system designed "
            "to analyze information and help users."
        )

    if intent == "owner":
        return self.owner_response

    if intent == "market":
        return (
            "I understand this is a market-related question. "
            "I will analyze the available information carefully."
        )

    if intent == "definition":
        return (
            "I understand your question and will provide "
            "a clear explanation."
        )

    if intent == "explanation":
        return (
            "I understand that you want an explanation. "
            "I will analyze the question carefully."
        )

    return (
        "I understand your message and I am analyzing it."
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
        "timestamp": datetime.now(
            timezone.utc
        ).isoformat()
    }
