include ("smtp-utils.fan")

<start> ::= <Interation1> <ChangeConnection> <Interation2> 

# 1. Setup Phase: Connect and EHLO
<Interation1> ::= <ServerA:response_setup><ClientA:request_ehlo><ServerA:response_ehlo><state_logged_out_A>
<Interation2> ::= <ServerB:response_setup><ClientB:request_ehlo><ServerB:response_ehlo><state_logged_out_B>
<ChangeConnection> ::= r".*" := changeConnection()

# 2. Login Phase: Move from Logged Out to Logged In
<state_logged_out_A> ::= <exchange_login_valid_A>
<state_logged_out_B> ::= <exchange_login_valid_B>

# 3. Logged In State: Send email then quit
<state_logged_in_A> ::= <exchange_send_email_A><exchange_quit_A>
<state_logged_in_B> ::= <exchange_send_email_B><exchange_quit_B>

# --- Detailed Exchanges for A ---

<exchange_login_valid_A> ::=  <ClientA:request_auth><ServerA:response_auth_expect_user><ClientA:request_auth_user><ServerA:response_auth_expect_pass><ClientA:request_auth_pass><ServerA:response_auth_success><state_logged_in_A>

<exchange_send_email_A> ::= <ClientA:request_mail_from><ServerA:response_mail_from><rcpt_sequence_A><ClientA:request_data><ServerA:response_data><ClientA:email_content><ServerA:response_emailA_sent>

# <rcpt_sequence_A> ::= <ClientA:request_rcpt_to_1><ServerA:response_rcpt_to><ClientA:request_rcpt_to_2><ServerA:response_rcpt_to><ClientA:request_rcpt_to_3><ServerA:response_rcpt_to>
<rcpt_sequence_A> ::= ->Generated from fuzzer and replaced here with python script->

<exchange_quit_A> ::= <ClientA:request_quit><ServerA:response_quit>

# --- Detailed Exchanges for B ---

<exchange_login_valid_B> ::=  <ClientB:request_auth><ServerB:response_auth_expect_user><ClientB:request_auth_user><ServerB:response_auth_expect_pass><ClientB:request_auth_pass><ServerB:response_auth_success><state_logged_in_B>

<exchange_send_email_B> ::= <ClientB:request_mail_from><ServerB:response_mail_from><rcpt_sequence_B><ClientB:request_data><ServerB:response_data><ClientB:email_content><ServerB:response_emailB_sent>

# <rcpt_sequence_B> ::= <ClientB:request_rcpt_to_2><ServerB:response_rcpt_to><ClientB:request_rcpt_to_1><ServerB:response_rcpt_to><ClientB:request_rcpt_to_3><ServerB:response_rcpt_to>
<rcpt_sequence_B> ::= ->Generated from fuzzer and replaced here with python script->

<exchange_quit_B> ::= <ClientB:request_quit><ServerB:response_quit>

# --- Static Definitions ---

<request_ehlo> ::= 'EHLO localhost\r\n'
<response_ehlo> ::= r"250-.+\r\n(250-.+\r\n)*250 .+\r\n"
<response_setup> ::= r"220 .+\r\n"

<request_auth> ::= 'AUTH LOGIN\r\n'
<response_auth_expect_user> ::= r"334 [A-Za-z0-9+/=]+\r\n"  # Base64 encoded username prompt
<request_auth_user> ::= 'dGhlX3VzZXI=\r\n'             # "the_user"
<response_auth_expect_pass> ::= r"334 [A-Za-z0-9+/=]+\r\n"  # Base64 encoded password prompt
<request_auth_pass> ::= 'dGhlX3Bhc3N3b3Jk\r\n'         # "the_password"
<response_auth_success> ::= r"235 .+\r\n"

# Email sending commands
<request_mail_from> ::= 'MAIL FROM:<sender@example.com>\r\n'
<response_mail_from> ::= r"250 .+\r\n"

# <request_rcpt_to_1> ::= 'RCPT TO:<recipient1@example.com>\r\n'
# <request_rcpt_to_2> ::= 'RCPT TO:<recipient2@example.com>\r\n'
# <request_rcpt_to_3> ::= 'RCPT TO:<recipient3@example.com>\r\n'
<response_rcpt_to> ::= r"250 .+\r\n"

<request_data> ::= 'DATA\r\n'
<response_data> ::= r"354 .+\r\n"

<email_content> ::= 'Subject: Test Email\r\n\r\nThis is a test email to multiple recipients.\r\n.\r\n'
<response_emailA_sent> ::= r"250 .+\r\n"
<response_emailB_sent> ::= r"250 .+\r\n"

<request_quit> ::= 'QUIT\r\n'
<response_quit> ::= r"221 .+\r\n"


where validateResponse(<response_emailA_sent>, <response_emailB_sent>)

