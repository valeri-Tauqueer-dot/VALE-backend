from datetime import datetime


class VALECore:

    def __init__(self):

        self.name = "VALE AI"
        self.version = "3.0"
        self.status = "ONLINE"

        self.modules = {
            "conversation": True,
            "knowledge": True,
            "market": True,
            "strategy": True,
            "risk": True,
            "learning": True,
            "memory": True,
            "chief": True
        }

        # Basic conversational memory
        self.memory = []

        # ==========================
        # BASIC KNOWLEDGE BASE
        # ==========================

        self.knowledge = {

            "what is ai":
                "AI means Artificial Intelligence. It refers to computer systems designed to perform tasks that normally require human intelligence, such as understanding language, recognizing patterns, reasoning, and learning.",

            "what is artificial intelligence":
                "Artificial Intelligence is the field of creating computer systems that can perform tasks involving reasoning, perception, language understanding, decision-making, and learning.",

            "what is machine learning":
                "Machine learning is a branch of AI where systems learn patterns from data instead of relying only on explicitly programmed rules.",

            "what is trading":
                "Trading is the buying and selling of financial assets such as stocks, currencies, commodities, or other instruments with the goal of managing risk and potentially generating returns.",

            "what is stock market":
                "The stock market is a marketplace where shares of publicly traded companies can be bought and sold.",

            "what is risk management":
                "Risk management is the process of identifying, measuring, and controlling potential losses. In trading, it can include position sizing, stop-loss rules, diversification, and exposure limits.",

            "what is a strategy":
                "A trading strategy is a defined set of rules or processes used to analyze markets and make trading decisions.",

            "what is data":
                "Data is information collected for analysis, processing, learning, or decision-making.",

            "what is memory":
                "Memory allows an AI system to retain selected information so it can use relevant previous context in future interactions.",

            "what is vaIe":
                "VALE is an AI Trading intelligence platform designed to combine market analysis, strategy research, risk management, learning, and decision-support capabilities."

        }


    # =========================================================
    # MAIN AI PROCESSOR
    # =========================================================

    def process(self, message):

        original_message = message.strip()
        text = original_message.lower().strip()

        if not text:

            return "Please enter a message. VALE is ready."


        # Store conversation
        self.memory.append({
            "user": original_message,
            "time": datetime.now().strftime("%H:%M:%S")
        })


        # =====================================================
        # GREETINGS
        # =====================================================

        if self.is_greeting(text):

            return self.greet()


        # =====================================================
        # IDENTITY
        # =====================================================

        if (
            "who are you" in text
            or "what are you" in text
            or "your name" in text
            or "what is your name" in text
            or "who is vale" in text
            or "what is vale" in text
        ):

            return self.identity()


        # =====================================================
        # ORIGIN
        # =====================================================

        if (
            "where are you from" in text
            or "where do you come from" in text
            or "where were you created" in text
            or "who created you" in text
            or "who made you" in text
        ):

            return self.origin()


        # =====================================================
        # CAPABILITIES
        # =====================================================

        if (
            "what can you do" in text
            or "what do you do" in text
            or "your work" in text
            or "your job" in text
            or "your capabilities" in text
            or "your purpose" in text
        ):

            return self.capabilities()


        # =====================================================
        # HOW ARE YOU
        # =====================================================

        if (
            "how are you" in text
            or "are you okay" in text
            or "are you online" in text
        ):

            return (
                "I am ONLINE and operating normally. "
                "VALE Intelligence Systems are ready."
            )


        # =====================================================
        # HELP
        # =====================================================

        if (
            text == "help"
            or "what can i ask" in text
            or "help me" in text
        ):

            return self.help()


        # =====================================================
        # STATUS
        # =====================================================

        if (
            text == "status"
            or "system status" in text
            or "are you working" in text
        ):

            return self.system_status()


        # =====================================================
        # TIME
        # =====================================================

        if "time" in text:

            return datetime.now().strftime(
                "Current Time: %H:%M:%S"
            )


        # =====================================================
        # MARKET
        # =====================================================

        if (
            "market analysis" in text
            or "stock market" in text
            or text == "market"
            or "market intelligence" in text
        ):

            return self.market_ai()


        # =====================================================
        # STRATEGY
        # =====================================================

        if (
            "trading strategy" in text
            or "strategy" in text
            or "trading plan" in text
        ):

            return self.strategy_ai()


        # =====================================================
        # RISK
        # =====================================================

        if (
            "risk management" in text
            or "risk" in text
            or "protect my capital" in text
        ):

            return self.risk_ai()


        # =====================================================
        # LEARNING
        # =====================================================

        if (
            "learning" in text
            or "learn" in text
            or "how do you learn" in text
        ):

            return self.learning_ai()


        # =====================================================
        # MEMORY
        # =====================================================

        if (
            "remember" in text
            or "memory" in text
            or "do you remember" in text
        ):

            return self.memory_response()


        # =====================================================
        # THANK YOU
        # =====================================================

        if (
            "thank you" in text
            or "thanks" in text
        ):

            return (
                "You're welcome. VALE is ready for your next command."
            )


        # =====================================================
        # GOODBYE
        # =====================================================

        if (
            text == "bye"
            or "goodbye" in text
        ):

            return (
                "VALE remains online. I'll be ready when you return."
            )


        # =====================================================
        # KNOWLEDGE ENGINE
        # =====================================================

        knowledge_answer = self.search_knowledge(text)

        if knowledge_answer:

            return knowledge_answer


        # =====================================================
        # SIMPLE CONVERSATION
        # =====================================================

        if (
            "good morning" in text
            or "good afternoon" in text
            or "good evening" in text
        ):

            return (
                "Good to see you. VALE Intelligence Systems are online."
            )


        # =====================================================
        # CHIEF AI FALLBACK
        # =====================================================

        return self.chief_ai(original_message)


    # =========================================================
    # GREETING DETECTOR
    # =========================================================

    def is_greeting(self, text):

        greetings = [
            "hello",
            "hi",
            "hey",
            "hello vale",
            "hi vale",
            "hey vale"
        ]

        return text in greetings


    # =========================================================
    # GREETING
    # =========================================================

    def greet(self):

        return (
            "Hello. I am VALE AI. "
            "The VALE Intelligence System is online and ready."
        )


    # =========================================================
    # IDENTITY
    # =========================================================

    def identity(self):

        return (
            "I am VALE AI, the intelligence core of the "
            "VALE Trading System. I am being developed to "
            "understand information, reason about problems, "
            "analyze markets, evaluate strategies, manage risk, "
            "learn from information, and coordinate future "
            "intelligence modules."
        )


    # =========================================================
    # ORIGIN
    # =========================================================

    def origin(self):

        return (
            "I am VALE AI, developed as the intelligence core "
            "of the VALE AI Trading platform."
        )


    # =========================================================
    # CAPABILITIES
    # =========================================================

    def capabilities(self):

        return (
            "My current foundation includes conversation, "
            "basic knowledge, market intelligence, strategy "
            "intelligence, risk management, learning, memory, "
            "and Chief AI coordination. More advanced reasoning "
            "and knowledge capabilities can be added to this core."
        )


    # =========================================================
    # HELP
    # =========================================================

    def help(self):

        return (
            "You can ask me about AI, trading, markets, "
            "strategies, risk management, VALE, my capabilities, "
            "system status, or general topics contained in my "
            "current knowledge base."
        )


    # =========================================================
    # SYSTEM STATUS
    # =========================================================

    def system_status(self):

        active_modules = [
            name
            for name, enabled in self.modules.items()
            if enabled
        ]

        return (
            f"VALE System Status: {self.status}\n"
            f"Version: {self.version}\n"
            f"Active Modules: {', '.join(active_modules)}"
        )


    # =========================================================
    # MARKET AI
    # =========================================================

    def market_ai(self):

        return (
            "Market Intelligence Module is ONLINE. "
            "The current foundation can support market-related "
            "reasoning and future real-time market-data analysis."
        )


    # =========================================================
    # STRATEGY AI
    # =========================================================

    def strategy_ai(self):

        return (
            "Strategy Intelligence Module is ONLINE. "
            "It is designed for strategy research, evaluation, "
            "testing, and future strategy evolution."
        )


    # =========================================================
    # RISK AI
    # =========================================================

    def risk_ai(self):

        return (
            "Risk Management Module is ONLINE. "
            "Its purpose is to identify and evaluate trading "
            "risk before decisions are made."
        )


    # =========================================================
    # LEARNING AI
    # =========================================================

    def learning_ai(self):

        return (
            "Learning Engine is ONLINE. "
            "The current system provides the foundation for "
            "future learning and evolution capabilities."
        )


    # =========================================================
    # MEMORY
    # =========================================================

    def memory_response(self):

        count = len(self.memory)

        return (
            f"VALE conversation memory currently contains "
            f"{count} message(s) from this session."
        )


    # =========================================================
    # KNOWLEDGE SEARCH
    # =========================================================

    def search_knowledge(self, text):

        # Exact/phrase matching
        for question, answer in self.knowledge.items():

            if question in text:

                return answer


        # Keyword matching
        keywords = {

            "artificial intelligence":
                "what is artificial intelligence",

            "machine learning":
                "what is machine learning",

            "stock":
                "what is stock market",

            "stocks":
                "what is stock market",

            "trading":
                "what is trading",

            "risk":
                "what is risk management",

            "strategy":
                "what is a strategy",

            "data":
                "what is data"

        }


        for keyword, knowledge_key in keywords.items():

            if keyword in text:

                return self.knowledge[knowledge_key]


        return None


    # =========================================================
    # CHIEF AI FALLBACK
    # =========================================================

    def chief_ai(self, message):

        return (
            f'I received your request: "{message}". '
            "I don't have enough knowledge in my current "
            "knowledge base to give you a reliable answer yet. "
            "This is an area where the VALE knowledge and "
            "reasoning system can be expanded."
        )


# =============================================================
# VALE INSTANCE
# =============================================================

vale = VALECore()
