from vale_connector import VALEConnector
from vale_brain_interface import VALEBrainInterface


class HeroicBrain(VALEBrainInterface):

    def __init__(self, connector):
        super().__init__(
            brain_name="HEROIC",
            connector=connector
        )
