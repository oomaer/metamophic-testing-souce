include("imap-utils.fan")

# --- IMAP Handshake ---
<start> ::= <imap_session>

<imap_session> ::= <server_greeting> <login_sequence> <create_mailbox> <m> <select_mailbox>

# Server initiates with * OK
<server_greeting> ::= <Server:Client:GREETING_DATA><Server:lastbit>
<GREETING_DATA>   ::= r".*"
<lastbit> ::= "\n"

# --- The Tagged Interaction ---
<login_sequence> ::= <Client:Server:LOGIN_CMD><Server:Client:LOGIN_RESPONSE>

<LOGIN_CMD>      ::= <tag> " LOGIN " <user> " " <password> "\r\n"
<LOGIN_RESPONSE> ::= <tag> " OK LOGIN succeeded\r\n"

# --- Terminals ---
<tag>  ::= "A001" | "A002" | r"A[0-9]{3}"
<user> ::= "testuser"
<password> ::= "testpass"

<create_mailbox> ::= <Client:Server:CREATE_CMD><Server:Client:CREATE_RESPONSE>
<CREATE_CMD>      ::= <tag> " CREATE testmailbox\r\n"
<CREATE_RESPONSE> ::= <tag> " OK Mailbox created\r\n"

<select_mailbox> ::= <Client:Server:SELECT_CMD><Server:Client:SELECT_RESPONSE>

<SELECT_CMD>      ::= <tag> " SELECT testmailbox\r\n"
<SELECT_RESPONSE> ::= ("* " r"."+ "\r\n")* "A" r"[0-9]{3}" " OK " r"."+ "\r\n"