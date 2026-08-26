from datetime import datetime


class VALECore:

    def __init__(self):

        self.name = "VALE AI"
        self.version = "3.0"
        self.status = "ONLINE"

        self.modules = {

            "market": True,
            "strategy": True,
            "risk": True,
            "learning": True,
            "memory": True,
            "knowledge": True,
            "conversation": True,
            "chief": True

        }


    # ==========================================
    # MAIN PROCESSOR
    # ==========================================

    def process(self, message):

        original_message = message.strip()
        message = original_message.lower()

        if not message:
            return "Please ask me something."


        # -------------------------------
        # GREETINGS
        # -------------------------------

        if any(word in message for word in [
            "hello",
            "hi",
            "hey",
            "good morning",
            "good afternoon",
            "good evening"
        ]):

            return self.greet()


        # -------------------------------
        # IDENTITY
        # -------------------------------

        if (
            "who are you" in message
            or "what are you" in message
            or "your name" in message
        ):

            return self.identity()


        # -------------------------------
        # ORIGIN
        # -------------------------------

        if (
            "where are you from" in message
            or "where are you from?" in message
            or "where do you live" in message
            or "where were you created" in message
        ):

            return self.origin()


        # -------------------------------
        # WORK / PURPOSE
        # -------------------------------

        if (
            "what is your work" in message
            or "what do you do" in message
            or "your work" in message
            or "what is your purpose" in message
        ):

            return self.work()


        # -------------------------------
        # STATUS
        # -------------------------------

        if (
            message == "status"
            or "system status" in message
            or "are you online" in message
            or "are you working" in message
        ):

            return self.system_status()


        # -------------------------------
        # TIME
        # -------------------------------

        if "time" in message:

            return datetime.now().strftime(
                "Current Time: %H:%M:%S"
            )


        # -------------------------------
        # DATE
        # -------------------------------

        if (
            "what date" in message
            or "today's date" in message
            or "todays date" in message
            or message == "date"
        ):

            return datetime.now().strftime(
                "Today's Date: %d %B %Y"
            )


        # -------------------------------
        # MARKET
        # -------------------------------

        if (
            "market" in message
            or "stock market" in message
        ):

            return self.market_ai()


        # -------------------------------
        # STRATEGY
        # -------------------------------

        if (
            "strategy" in message
            or "trading strategy" in message
        ):

            return self.strategy_ai()


        # -------------------------------
        # RISK
        # -------------------------------

        if (
            "risk" in message
            or "risk management" in message
        ):

            return self.risk_ai()


        # -------------------------------
        # LEARNING
        # -------------------------------

        if (
            "learn" in message
            or "learning" in message
        ):

            return self.learning_ai()


        # -------------------------------
        # GENERAL KNOWLEDGE
        # -------------------------------

        knowledge_answer = self.general_knowledge(message)

        if knowledge_answer:

            return knowledge_answer


        # -------------------------------
        # CHIEF AI FALLBACK
        # -------------------------------

        return self.chief_ai(original_message)


    # ==========================================
    # GREETING
    # ==========================================

    def greet(self):

        return (
            "Hello! I am VALE AI. "
            "My intelligence systems are online and ready."
        )


    # ==========================================
    # IDENTITY
    # ==========================================

    def identity(self):

        return (
            "I am VALE AI, an intelligent trading operating system "
            "designed to understand information, analyze markets, "
            "develop strategies and assist with intelligent decisions."
        )


    # ==========================================
    # ORIGIN
    # ==========================================

    def origin(self):

        return (
            "I am VALE AI, created as part of the VALE AI Trading "
            "intelligence platform. I run through the VALE backend "
            "and its intelligence modules."
        )


    # ==========================================
    # WORK
    # ==========================================

    def work(self):

        return (
            "My purpose is to become an intelligent trading system. "
            "I am designed to analyze market information, study "
            "strategies, understand risk, learn from information "
            "and assist with trading decisions."
        )


    # ==========================================
    # SYSTEM STATUS
    # ==========================================

    def system_status(self):

        active_modules = []

        for module, active in self.modules.items():

            if active:
                active_modules.append(module)

        return (
            f"VALE AI Status: {self.status}\n"
            f"Version: {self.version}\n"
            f"Active Modules: {', '.join(active_modules)}"
        )


    # ==========================================
    # MARKET AI
    # ==========================================

    def market_ai(self):

        return (
            "Market Intelligence Module is online. "
            "VALE is prepared to analyze market structure, "
            "price behaviour, trends and market information."
        )


    # ==========================================
    # STRATEGY AI
    # ==========================================

    def strategy_ai(self):

        return (
            "Strategy Intelligence Module is online. "
            "VALE can study trading concepts, strategy logic, "
            "backtesting ideas and decision frameworks."
        )


    # ==========================================
    # RISK AI
    # ==========================================

    def risk_ai(self):

        return (
            "Risk Management Module is online. "
            "Risk assessment, position sizing, uncertainty "
            "and capital protection are core parts of VALE."
        )


    # ==========================================
    # LEARNING AI
    # ==========================================

    def learning_ai(self):

        return (
            "Learning Engine is active. "
            "The current version uses structured knowledge and "
            "logic. A more advanced learning architecture will "
            "be added as VALE evolves."
        )


    # ==========================================
    # BASIC GENERAL KNOWLEDGE
    # ==========================================

    def general_knowledge(self, message):

        # Python
        if "what is python" in message:

            return (
                "Python is a high-level programming language "
                "widely used for software development, automation, "
                "data science, artificial intelligence and machine learning."
            )


        # AI
        if (
            "what is ai" in message
            or "what is artificial intelligence" in message
        ):

            return (
                "Artificial Intelligence, or AI, is technology that "
                "allows computer systems to perform tasks that normally "
                "require human intelligence, such as understanding "
                "language, recognizing patterns and making decisions."
            )


        # Machine Learning
        if (
            "what is machine learning" in message
            or "what is ml" in message
        ):

            return (
                "Machine learning is a branch of AI where computer "
                "systems learn patterns from data and use those patterns "
                "to make predictions or decisions."
            )


        # Internet
        if "what is internet" in message:

            return (
                "The Internet is a worldwide network of connected "
                "computer systems that communicate and exchange information."
            )


        # Computer
        if "what is a computer" in message:

            return (
                "A computer is an electronic system that processes "
                "data according to programmed instructions."
            )


        # India
        if (
            "capital of india" in message
            or "what is the capital of india" in message
        ):

            return "The capital of India is New Delhi."


        # Earth
        if "what is earth" in message:

            return (
                "Earth is the third planet from the Sun and the only "
                "planet currently known to support life."
            )


        # Sun
        if "what is the sun" in message:

            return (
                "The Sun is a star at the center of our Solar System. "
                "Its energy provides most of the light and heat received by Earth."
            )


        # Moon
        if "what is the moon" in message:

            return (
                "The Moon is Earth's natural satellite and orbits our planet."
            )


        # Trading
        if (
            "what is trading" in message
            or "what is stock trading" in message
        ):

            return (
                "Trading involves buying and selling financial assets "
                "such as stocks, currencies or other instruments with "
                "the goal of managing risk and potentially generating returns."
            )


        # Stock
        if "what is a stock" in message:

            return (
                "A stock represents a unit of ownership in a company. "
                "When you own shares, you own a small portion of that company."
            )


        # Bitcoin
        if "what is bitcoin" in message:

            return (
                "Bitcoin is a decentralized digital asset that uses "
                "blockchain technology to record transactions."
            )


        # Blockchain
        if "what is blockchain" in message:

            return (
                "A blockchain is a distributed digital ledger that "
                "records transactions in a way designed to be transparent "
                "and resistant to unauthorized changes."
            )


        # CEO
        if "what does ceo mean" in message:

            return (
                "CEO means Chief Executive Officer. "
                "The CEO is generally responsible for leading and managing a company."
            )


        # Database
        if "what is database" in message:

            return (
                "A database is an organized system for storing, "
                "managing and retrieving information."
            )


        return None


    # ==========================================
    # CHIEF AI
    # ==========================================

    def chief_ai(self, message):

        return (
            f'I understand that you asked: "{message}".\n\n'
            "I do not have enough built-in knowledge to answer that "
            "accurately yet. I will not invent an answer."
        )


# ==============================================
# VALE CORE INSTANCE
# ==============================================

vale = VALECore()
