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


<start> ::= <Interation1> <ChangeConnection> <Interation2> 

# 1. Setup Phase: Connect and EHLO
<Interation1> ::= <ServerA:response_setup><ClientA:request_ehlo><ServerA:response_ehlo><state_logged_out_A>
<Interation2> ::= <ServerB:response_setup><ClientB:request_ehlo><ServerB:response_ehlo><state_logged_out_B>
<ChangeConnection> ::= <DummyParty:change_conn>
<change_conn> ::= "changing connection\r\n"

<state_logged_out_A> ::= <exchange_login_valid_A>
<state_logged_out_B> ::= <exchange_login_valid_B>

# 3. Logged In State: Send email then quit
<state_logged_in_A> ::= <exchange_send_email_A><exchange_quit_A>
<state_logged_in_B> ::= <exchange_send_email_B><exchange_quit_B>

# --- Detailed Exchanges for A ---

<exchange_login_valid_A> ::=  <ClientA:request_auth><ServerA:response_auth_expect_user><ClientA:request_auth_user><ServerA:response_auth_expect_pass><ClientA:request_auth_pass><ServerA:response_auth_success><state_logged_in_A>

<exchange_send_email_A> ::= <ClientA:request_mail_from><ServerA:response_mail_from><rcpt_sequence_A><ClientA:request_data><ServerA:response_data><ClientA:email_content><ServerA:response_emailA_sent>

<rcpt_sequence_A> ::= ->Generated from fuzzer and replaced here with python script->

<exchange_quit_A> ::= <ClientA:request_quit><ServerA:response_quit>

# --- Detailed Exchanges for B ---

<exchange_login_valid_B> ::=  <ClientB:request_auth><ServerB:response_auth_expect_user><ClientB:request_auth_user><ServerB:response_auth_expect_pass><ClientB:request_auth_pass><ServerB:response_auth_success><state_logged_in_B>

<exchange_send_email_B> ::= <ClientB:request_mail_from><ServerB:response_mail_from><rcpt_sequence_B><ClientB:request_data><ServerB:response_data><ClientB:email_content><ServerB:response_emailB_sent>

<rcpt_sequence_B> ::= ->Generated from fuzzer and replaced here with python script->

<exchange_quit_B> ::= <ClientB:request_quit><ServerB:response_quit>

# --- Static Definitions ---

<request_ehlo> ::= 'EHLO localhost\r\n'
<response_ehlo> ::= r"250-.+\r\n(250-.+\r\n)*250 .+\r\n"
<response_setup> ::= r"220 .+\r\n"

<request_auth> ::= 'AUTH LOGIN\r\n'
<response_auth_expect_user> ::= '334 VXNlcm5hbWU6\r\n'  # "Username:" in base64
<request_auth_user> ::= 'dGhlX3VzZXI=\r\n'             # "the_user"
<response_auth_expect_pass> ::= '334 UGFzc3dvcmQ6\r\n'  # "Password:" in base64
<request_auth_pass> ::= 'dGhlX3Bhc3N3b3Jk\r\n'         # "the_password"
<response_auth_success> ::= r"235 .+\r\n"

# Email sending commands
<request_mail_from> ::= 'MAIL FROM:<sender@example.com>\r\n'
<response_mail_from> ::= r"250 .+\r\n"

<response_rcpt_to> ::= r"250 .+\r\n"

<request_data> ::= 'DATA\r\n'
<response_data> ::= r"354 .+\r\n"

<email_content> ::= 'Subject: Test Email\r\n\r\nThis is a test email to multiple recipients.\r\n.\r\n'
<response_emailA_sent> ::= r"250 .+\r\n"
<response_emailB_sent> ::= r"250 .+\r\n"

<request_quit> ::= 'QUIT\r\n'
<response_quit> ::= r"221 .+\r\n"


# where validateResponse(<response_emailA_sent>, <response_emailB_sent>)

