from typing import Optional
from fandango.io import ConnectionMode


class ClientA(NetworkParty):
    def __init__(self):
        super().__init__(
            connection_mode=ConnectionMode.CONNECT,
            uri=f"tcp://localhost:8080"
        )
        self.start()

    def receive(self, message: str | bytes, sender: Optional[str]) -> None:
        super().receive(message, "ServerA")


class ServerA(NetworkParty):
    def __init__(self):
        super().__init__(
            connection_mode=ConnectionMode.EXTERNAL,
            uri=f"tcp://localhost:8080"
        )
        self.start()

    def receive(self, message: str | bytes, sender: Optional[str]) -> None:
        super().receive(message, "ClientA")


class ClientB(NetworkParty):
    def __init__(self):
        super().__init__(
            connection_mode=ConnectionMode.CONNECT,
            uri=f"tcp://localhost:8081"
        )

    def receive(self, message: str | bytes, sender: Optional[str]) -> None:
        super().receive(message, "ServerB")


class ServerB(NetworkParty):
    def __init__(self):
        super().__init__(
            connection_mode=ConnectionMode.EXTERNAL,
            uri=f"tcp://localhost:8081"
        )

    def receive(self, message: str | bytes, sender: Optional[str]) -> None:
        super().receive(message, "ClientB")


def changeConnection():
    """Stop connection A and start connection B"""
    clientA = ClientA.instance()
    serverA = ServerA.instance()
    clientA.stop()
    serverA.stop()
    clientB = ClientB.instance()
    serverB = ServerB.instance()
    clientB.start()
    serverB.start()
    return "Switching from connection A to connection B"


def resetConnection():
    """Stop connection B and start connection A"""
    clientB = ClientB.instance()
    serverB = ServerB.instance()
    clientB.stop()
    serverB.stop()
    clientA = ClientA.instance()
    serverA = ServerA.instance()
    clientA.start()
    serverA.start()
    return "Resetting to connection A"
