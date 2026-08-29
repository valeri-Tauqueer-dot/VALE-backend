import re
from datetime import datetime

class VALEBrain:

def __init__(self):
    self.name = "VALE"
    self.version = "1.0"

def understand(self, message):
    text = message.strip()
    lower = text.lower()

    return {
        "original": text,
        "lower": lower,
        "words": re.findall(r"\b\w+\b", lower)
    }

def detect_intent(self, data):
    text = data["lower"]

    if any(word in text for word in [
        "latest", "today", "current",
        "news", "now", "recent", "price"
    ]):
        return "current_information"

    if text.startswith((
        "what is",
        "what are",
        "who is",
        "who are"
    )):
        return "definition"

    if text.startswith(("how", "why")):
        return "explanation"

    if text in ("hello", "hi", "hey"):
        return "conversation"

    return "general"

def needs_internet(self, data, intent):

    if intent == "conversation":
        return False

    if intent == "current_information":
        return True

    if intent in ("definition", "explanation"):
        return True

    return False

def create_response(self, data, intent):

    if intent == "conversation":
        return "Hello. I am VALE. I am online and ready to help."

    if intent == "definition":
        return (
            "I understand your question. "
            "I will use available knowledge to provide a reliable answer."
        )

    if intent == "explanation":
        return (
            "I understand that you want an explanation. "
            "I will analyze the question carefully."
        )

    return "I understand your message and I am analyzing it."

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
        "timestamp": datetime.utcnow().isoformat()
                    }
