class VALECore:

    def __init__(self):
        self.name = "VALE AI"
        self.version = "1.0"
        self.status = "Online"

    def process(self, message):

        message = message.lower()

        if "hello" in message:
            return "Hello, I am VALE AI. System online."

        elif "trading" in message:
            return "Trading AI module is ready."

        elif "who are you" in message:
            return "I am VALE, Generation AI OS Core."

        else:
            return "VALE is processing your request."


vale = VALECore()