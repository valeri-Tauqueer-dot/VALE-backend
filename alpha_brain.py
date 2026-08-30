from vale_connector import VALEConnector
from vale_brain_interface import VALEBrainInterface


class AlphaBrain(VALEBrainInterface):

    def __init__(self, connector):
        super().__init__(
            brain_name="ALPHA",
            connector=connector
        )
