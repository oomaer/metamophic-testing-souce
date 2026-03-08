from typing import Optional

from fandango.io import ConnectionMode


class ClientA(NetworkParty):
    def __init__(self):
        self.serverName = "ServerA"
        super().__init__(
            connection_mode=ConnectionMode.CONNECT,
            uri=f"tcp://localhost:{8026}"
        )
        self.start()

    def receive(self, message: str | bytes, sender: Optional[str]) -> None:
        super().receive(message, self.serverName)

class ServerA(NetworkParty):
    def __init__(self):
        super().__init__(
            connection_mode=ConnectionMode.EXTERNAL,
            uri=f"tcp://localhost:{8026}"
        )
        self.start()

    def receive(self, message: str | bytes, sender: Optional[str]) -> None:
        super().receive(message, "ClientA")
    

class ClientB(NetworkParty):
    def __init__(self):
        super().__init__(
            connection_mode=ConnectionMode.CONNECT,
            uri=f"tcp://127.0.0.1:{8027}"
        )

    def receive(self, message: str | bytes, sender: Optional[str]) -> None:
        super().receive(message, "ServerB")

class ServerB(NetworkParty):
    def __init__(self):
        super().__init__(
            connection_mode=ConnectionMode.EXTERNAL,
            uri=f"tcp://127.0.0.1:{8028}"
        )

    def receive(self, message: str | bytes, sender: Optional[str]) -> None:
        super().receive(message, "ClientB")


class DummyParty(NetworkParty):
    def __init__(self):
        super().__init__(
            connection_mode=ConnectionMode.OPEN,
            uri=f"tcp://127.0.0.1:{8028}"
        )


    def send(self, message: str | bytes, recipient: Optional[str]) -> None:
        if message == "changing connection\r\n":
            print("changing connection")
            ClientA.instance().stop()
            ServerA.instance().stop()
            ClientB.instance().start()
            ServerB.instance().start()


    def start(self):
        pass

    def stop(self):
        pass


def changeConnection():
    # stop ClientA and ServerA and start ClientB and ServerB
    clientA = ClientA.instance()
    serverA = ServerA.instance()
    clientA.stop()
    serverA.stop()
    clientB = ClientB.instance()
    serverB = ServerB.instance()
    clientB.start()
    serverB.start()
    return "Stopping connection 1 and starting connection 2"


def resetConnection():
    # stop ClientA and ServerA and start ClientB and ServerB
    clientB = ClientB.instance()
    serverB = ServerB.instance()
    clientB.stop()
    serverB.stop()
    clientA = ClientA.instance()
    serverA = ServerA.instance()
    clientA.start()
    serverA.start()
    return "Resetting Connection"


def validateResponse(responseA: str, responseB: str) -> bool:
    # Extract response codes (first 3 digits) and compare
    # Extract the SMTP response code (e.g., "250")
    codeA = responseA.strip().split()[0] if responseA.strip() else ""
    codeB = responseB.strip().split()[0] if responseB.strip() else ""
    
    # Extract the extended status code (e.g., "2.0.0")
    partsA = responseA.strip().split()
    partsB = responseB.strip().split()
    
    extendedCodeA = partsA[1] if len(partsA) > 1 else ""
    extendedCodeB = partsB[1] if len(partsB) > 1 else ""
    
    # Check if both codes match (ignoring the message ID)
    if codeA == codeB and extendedCodeA == extendedCodeB:
        print(f"✓ Responses are equivalent: {codeA} {extendedCodeA}")
        return True
    else:
        print(f"✗ Responses differ: {codeA} {extendedCodeA} vs {codeB} {extendedCodeB}")
        return False