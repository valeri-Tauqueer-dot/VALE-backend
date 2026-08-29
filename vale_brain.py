import re
from datetime import datetime, timezone

============================================================

VALE SYSTEM PROMPT

============================================================

WRITE YOUR OWN VALE INSTRUCTIONS BELOW.

You can replace everything between the triple quotes.

Example:

You are VALE, an advanced AI.

Your name is VALE.

Always give accurate and intelligent answers.

Help users with trading, markets, coding, strategy and analysis.

You can make this prompt very long.

This is the MAIN PLACE where you can add your instructions.

============================================================

VALE_SYSTEM_PROMPT = """
WRITE YOUR FULL VALE PROMPT HERE.

THIS IS WHERE YOU ADD YOUR OWN INSTRUCTIONS.

You can write things such as:

You are VALE, an advanced AI intelligence system.

Your name is VALE.

You should be intelligent, accurate and helpful.

You should understand what the user actually means.

You should answer the current question and never give
an answer about an unrelated previous question.

For market questions, analyze information carefully.

For current information, use reliable external data.

Do not search the internet for simple greetings.

Do not give random search results.

Always try to give the user a direct and useful answer.

You can DELETE these example instructions and write
your own complete prompt here.
"""

class VALEBrain:

def __init__(self):
    self.name = "VALE"
    self.version = "1.0"

    # This connects your prompt above to the VALE brain.
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

    greetings = [
        "hello",
        "hi",
        "hey",
        "hii",
        "helo",
        "good morning",
        "good afternoon",
        "good evening"
    ]

    if text in greetings:
        return "conversation"

    identity_patterns = [
        "what is your name",
        "what's your name",
        "whats your name",
        "who are you",
        "what are you",
        "tell me about yourself",
        "what is vale",
        "who is vale"
    ]

    if any(pattern in text for pattern in identity_patterns):
        return "identity"

    owner_patterns = [
        "who is your owner",
        "who's your owner",
        "whos your owner",
        "who owns you",
        "who created you",
        "who made you",
        "your creator"
    ]

    if any(pattern in text for pattern in owner_patterns):
        return "owner"

    market_words = [
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
        "price prediction",
        "bullish",
        "bearish"
    ]

    if any(word in text for word in market_words):
        return "market"

    current_words = [
        "latest",
        "today",
        "current",
        "news",
        "recent",
        "right now",
        "now",
        "live",
        "currently"
    ]

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

    # These questions stay inside the VALE brain.
    if intent in (
        "empty",
        "conversation",
        "identity",
        "owner"
    ):
        return False

    # Market questions need the internet only when
    # current or live information is requested.
    if intent == "market":

        current_market_words = [
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
        ]

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
    text = data["lower"]

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

    intent = self.detect_intent(
        understanding
    )

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
