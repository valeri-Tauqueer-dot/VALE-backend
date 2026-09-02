"""
VALE AI CORE — REAL INTERNET MODE

This file used to contain hardcoded answers like:

    if "what is python" in message:
        return "Python is a high-level programming language..."

That is gone. There is no list of pre-written answers anywhere in this
file, and no ChatGPT / Claude / any language model is called here.

Every message VALE receives is answered the same way: by searching the
real internet through Exa (via VALEConnector) and returning what Exa
found, organized into a readable reply. If Exa has nothing, VALE says
so honestly instead of guessing.

Requires the EXA_API_KEY environment variable to be set on Render.
Without it, every answer will say the internet connection isn't
configured — that's VALEConnector telling you the key is missing, not
a bug in this file.
"""

from datetime import datetime, timezone

from vale_connector import VALEConnector


class VALECore:

    def __init__(self):

        self.name = "VALE AI"
        self.version = "2.0"
        self.status = "ONLINE"

        # Single shared connector — this is the ONLY source of answers.
        self.connector = VALEConnector()

    # ==========================================
    # MAIN PROCESSOR
    # ==========================================

    def process(self, message: str) -> str:

        original_message = (message or "").strip()

        if not original_message:
            return "Please ask me something."

        # Handful of housekeeping questions that don't need a web
        # search at all — asking VALE what it is, or whether it's
        # online. Everything else goes straight to the internet.
        lower = original_message.lower()

        if lower in {"status", "system status", "are you online", "are you working"}:
            return self.system_status()

        if any(word in lower for word in ["who are you", "what are you", "your name"]):
            return (
                "I am VALE AI. I answer by searching the real internet "
                "through Exa — I don't have a built-in list of answers, "
                "so everything I tell you comes from a live web search."
            )

        # Everything else: real internet search, no exceptions.
        return self.answer_from_internet(original_message)

    # ==========================================
    # REAL INTERNET ANSWER
    # ==========================================

    def answer_from_internet(self, message: str) -> str:

        if not self.connector.internet_available():
            return (
                "VALE cannot reach the internet right now because the "
                "EXA_API_KEY environment variable is not set on the "
                "server. Add EXA_API_KEY in Render → Environment, then "
                "ask again — nothing else needs to change."
            )

        results = self.connector.search_web(message, num_results=5)

        if not results:
            return (
                "VALE searched the internet through Exa but found no "
                "usable results for that question. Try rephrasing it, "
                "or ask something more specific."
            )

        return self.format_search_results(message, results)

    # ==========================================
    # FORMAT RAW EXA RESULTS INTO A REPLY
    # ==========================================

    def format_search_results(self, message: str, results) -> str:
        """
        Turns VALEConnector.search_web()'s raw list of
        {title, url, highlights} into a plain-text reply.

        This is pure string formatting — no model, no rewriting,
        no interpretation. What Exa found is what you get.
        """

        lines = [f'Live internet results for: "{message}"', ""]

        shown = 0

        for item in results:

            title = (item.get("title") or "").strip()
            url = (item.get("url") or "").strip()
            highlights = item.get("highlights") or []

            if not title and not url:
                continue

            shown += 1

            lines.append(f"{shown}. {title or url}")

            if url:
                lines.append(f"   {url}")

            for highlight in highlights[:2]:

                highlight = (highlight or "").strip()

                if highlight:
                    lines.append(f"   \u2192 {highlight}")

            lines.append("")

        if shown == 0:
            return (
                "VALE searched the internet through Exa but the results "
                "didn't contain usable titles or links. Try rephrasing "
                "the question."
            )

        return "\n".join(lines).strip()

    # ==========================================
    # SYSTEM STATUS
    # ==========================================

    def system_status(self) -> str:

        internet_ok = self.connector.internet_available()

        return (
            f"VALE AI Status: {self.status}\n"
            f"Version: {self.version}\n"
            f"Internet (Exa) connected: {'YES' if internet_ok else 'NO — EXA_API_KEY not set'}\n"
            f"Checked: {datetime.now(timezone.utc).isoformat()}"
        )


# ==============================================
# VALE CORE INSTANCE
# ==============================================

vale = VALECore()
