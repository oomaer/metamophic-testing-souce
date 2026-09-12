from typing import Optional
from fandango.io import ConnectionMode


class ClientA(NetworkParty):
    def __init__(self):
        super().__init__(
            connection_mode=ConnectionMode.CONNECT,
            uri=f"tcp://localhost:2121"
        )
        self.start()

    def receive(self, message: str | bytes, sender: Optional[str]) -> None:
        super().receive(message, "ServerA")


class ServerA(NetworkParty):
    def __init__(self):
        super().__init__(
            connection_mode=ConnectionMode.EXTERNAL,
            uri=f"tcp://localhost:2121"
        )
        self.start()

    def receive(self, message: str | bytes, sender: Optional[str]) -> None:
        super().receive(message, "ClientA")


class ClientDataA(NetworkParty):
    def __init__(self):
        super().__init__(
            connection_mode=ConnectionMode.CONNECT,
            uri=f"tcp://localhost:50100"
        )

    def receive(self, message: str | bytes, sender: Optional[str]) -> None:
        if message is None:
            super().receive("Data socket closed.\r\n", sender="SocketControlServerA")
            return
        if isinstance(message, bytes):
            message = message.decode("utf-8")
        super().receive(message, "ServerDataA")


class ServerDataA(NetworkParty):
    def __init__(self):
        super().__init__(
            connection_mode=ConnectionMode.EXTERNAL,
            uri=f"tcp://localhost:50100"
        )

    def receive(self, message: str | bytes, sender: Optional[str]) -> None:
        super().receive(message, "ClientDataA")


class ClientB(NetworkParty):
    def __init__(self):
        super().__init__(
            connection_mode=ConnectionMode.CONNECT,
            uri=f"tcp://localhost:2122"
        )

    def receive(self, message: str | bytes, sender: Optional[str]) -> None:
        super().receive(message, "ServerB")


class ServerB(NetworkParty):
    def __init__(self):
        super().__init__(
            connection_mode=ConnectionMode.EXTERNAL,
            uri=f"tcp://localhost:2122"
        )

    def receive(self, message: str | bytes, sender: Optional[str]) -> None:
        super().receive(message, "ClientB")


class ClientDataB(NetworkParty):
    def __init__(self):
        super().__init__(
            connection_mode=ConnectionMode.CONNECT,
            uri=f"tcp://localhost:50101"
        )

    def receive(self, message: str | bytes, sender: Optional[str]) -> None:
        if message is None:
            super().receive("Data socket closed.\r\n", sender="SocketControlServerB")
            return
        if isinstance(message, bytes):
            message = message.decode("utf-8")
        super().receive(message, "ServerDataB")


class ServerDataB(NetworkParty):
    def __init__(self):
        super().__init__(
            connection_mode=ConnectionMode.EXTERNAL,
            uri=f"tcp://localhost:50101"
        )

    def receive(self, message: str | bytes, sender: Optional[str]) -> None:
        super().receive(message, "ClientDataB")


class SocketControlServerA(FandangoParty):
    def __init__(self):
        super().__init__(connection_mode=ConnectionMode.EXTERNAL)

    def start(self):
        pass

    def stop(self):
        pass


class SocketControlServerB(FandangoParty):
    def __init__(self):
        super().__init__(connection_mode=ConnectionMode.EXTERNAL)

    def start(self):
        pass

    def stop(self):
        pass


class SocketControlClientA(FandangoParty):
    def __init__(self):
        super().__init__(connection_mode=ConnectionMode.CONNECT)

    def send(self, message: str | bytes, recipient: Optional[str]) -> None:
        if str(message).startswith("Data socket closed.\r\n"):
            ClientDataA.instance().stop()

    def start(self):
        pass

    def stop(self):
        pass


class SocketControlClientB(FandangoParty):
    def __init__(self):
        super().__init__(connection_mode=ConnectionMode.CONNECT)

    def send(self, message: str | bytes, recipient: Optional[str]) -> None:
        if str(message).startswith("Data socket closed.\r\n"):
            ClientDataB.instance().stop()

    def start(self):
        pass

    def stop(self):
        pass


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


def open_data_port_A(port) -> int:
    """Reconfigure data connection A to use the specified port"""
    try:
        client_data = ClientDataA.instance()
        server_data = ServerDataA.instance()
    except KeyError:
        # Party instances not created
        return port

    client_data.stop()
    server_data.stop()
    if client_data.port != port:
        client_data.port = port
    client_data.start()
    if server_data.port != port:
        server_data.port = port
    server_data.start()
    return port


def open_data_port_B(port) -> int:
    """Reconfigure data connection B to use the specified port"""
    try:
        client_data = ClientDataB.instance()
        server_data = ServerDataB.instance()
    except KeyError:
        # Party instances not created
        return port

    client_data.stop()
    server_data.stop()
    if client_data.port != port:
        client_data.port = port
    client_data.start()
    if server_data.port != port:
        server_data.port = port
    server_data.start()
    return port