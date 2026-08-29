import re
from datetime import datetime


class VALEBrain:
    """
    VALE's central intelligence layer.

    Future reasoning, knowledge, market analysis, memory,
    strategy logic, risk analysis, and other intelligence
    can be added here without changing the basic connector
    in main.py.
    """

    def __init__(self):
        self.name = "VALE"
        self.version = "1.0"

    def understand(self, message):
        text = str(message).strip()
        lower = text.lower()

        return {
            "original": text,
            "lower": lower,
            "words": re.findall(r"\b\w+\b", lower)
        }

    def detect_intent(self, data):
        text = data["lower"]

        # Normal conversation
        greetings = [
            "hello",
            "hi",
            "hey",
            "good morning",
            "good afternoon",
            "good evening"
        ]

        if text in greetings:
            return "conversation"

        # VALE identity
        if any(phrase in text for phrase in [
            "your name",
            "ur name",
            "what is your name",
            "who are you",
            "what are you"
        ]):
            return "identity"

        # Owner / creator
        if any(phrase in text for phrase in [
            "your owner",
            "ur owner",
            "who owns you",
            "who created you",
            "your creator"
        ]):
            return "owner"

        # Current or changing information
        if any(word in text for word in [
            "latest",
            "today",
            "current",
            "news",
            "recent",
            "live",
            "price",
            "market price"
        ]):
            return "current_information"

        # Cryptocurrency / market questions
        if any(word in text for word in [
            "bitcoin",
            "btc",
            "crypto",
            "ethereum",
            "eth",
            "stock",
            "market",
            "forex",
            "trading"
        ]):
            return "market_analysis"

        # Questions
        if text.startswith((
            "what is",
            "what are",
            "who is",
            "who are"
        )):
            return "definition"

        if text.startswith((
            "how",
            "why",
            "when",
            "where",
            "will",
            "can",
            "should"
        )):
            return "explanation"

        return "general"

    def needs_internet(self, data, intent):
        """
        Decides whether external information is useful.
        """

        if intent in (
            "conversation",
            "identity",
            "owner"
        ):
            return False

        if intent in (
            "current_information",
            "market_analysis",
            "definition",
            "explanation"
        ):
            return True

        return False

    def create_local_response(self, data, intent):
        """
        Handles information VALE already knows locally.
        """

        if intent == "conversation":
            return (
                "Hello. I am VALE, your AI trading intelligence system. "
                "I am online and ready to help."
            )

        if intent == "identity":
            return (
                "My name is VALE. I am an AI intelligence system "
                "designed for market analysis, strategy, risk awareness "
                "and intelligent decision-making."
            )

        if intent == "owner":
            return (
                "I am VALE, a custom AI intelligence system. "
                "My purpose is to provide intelligent market, strategy "
                "and risk analysis."
            )

        if intent == "general":
            return (
                "I understand your message. "
                "I am analyzing it and preparing the best response."
            )

        return (
            "I understand your question and I am analyzing it."
        )

    def process_web_results(self, data, intent, results):
        """
        Converts web search results into a response.

        Future versions can replace this simple method with
        advanced reasoning and source analysis.
        """

        if not results:
            return (
                "I could not retrieve reliable external information "
                "for that question right now."
            )

        question = data["original"]

        response = (
            f"I researched your question: {question}\n\n"
        )

        response += "Here is the information I found:\n\n"

        for index, result in enumerate(results[:3], start=1):
            title = result.get("title", "Source")
            highlights = result.get("highlights", [])

            response += f"{index}. {title}\n"

            if highlights:
                text = str(highlights[0]).replace("\n", " ").strip()
                response += text[:600]

            response += "\n\n"

        response += (
            "This information was retrieved through VALE's "
            "web intelligence system."
        )

        return response

    def think(self, message, web_results=None):
        """
        Main permanent interface used by main.py.

        main.py only needs to call:

            brain.think(message)

        or, after web search:

            brain.think(message, web_results=results)
        """

        understanding = self.understand(message)

        intent = self.detect_intent(understanding)

        internet_needed = self.needs_internet(
            understanding,
            intent
        )

        # If main.py has already supplied web results,
        # let the brain process them.
        if web_results is not None:
            response = self.process_web_results(
                understanding,
                intent,
                web_results
            )

            return {
                "response": response,
                "intent": intent,
                "needs_internet": internet_needed,
                "internet_used": True,
                "timestamp": datetime.utcnow().isoformat()
            }

        # Local answer
        response = self.create_local_response(
            understanding,
            intent
        )

        return {
            "response": response,
            "intent": intent,
            "needs_internet": internet_needed,
            "internet_used": False,
            "timestamp": datetime.utcnow().isoformat()
            }
