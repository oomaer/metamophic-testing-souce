"""
IMAP Append+Search MR - Network Party Utilities

Single connection setup for testing APPEND then SEARCH metamorphic relation.
"""

from typing import Optional


# === Message Content Definitions ===
MSG_A = b"From: testmr@example.com\r\nTo: test@example.com\r\nSubject: Test A\r\n\r\nBody A.\r\n"
MSG_B = b"From: testmr@example.com\r\nTo: test@example.com\r\nSubject: Test B\r\n\r\nBody B.\r\n"
MSG_C = b"From: testmr@example.com\r\nTo: test@example.com\r\nSubject: Test C\r\n\r\nBody C.\r\n"


def get_msg_a():
    return MSG_A


def get_msg_b():
    return MSG_B


def get_msg_c():
    return MSG_C


def get_size_a():
    return str(len(MSG_A))


def get_size_b():
    return str(len(MSG_B))


def get_size_c():
    return str(len(MSG_C))

class Client(NetworkParty):
    """IMAP Client connecting to server on port 1144."""

    def __init__(self):
        super().__init__(
            connection_mode=ConnectionMode.CONNECT,
            uri="tcp://localhost:1144"
        )
        self.start()

    def receive(self, message: str | bytes, sender: Optional[str]) -> None:
        super().receive(message, "Server")


class Server(NetworkParty):
    """IMAP Server (external) on port 1144."""

    def __init__(self):
        super().__init__(
            connection_mode=ConnectionMode.EXTERNAL,
            uri="tcp://localhost:1144"
        )
        self.start()

    def receive(self, message: str | bytes, sender: Optional[str]) -> None:
        super().receive(message, "Client")
