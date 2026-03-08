
include ("/Users/i7949486/Downloads/docker/metamorphic-testing/mt-smtp/smtp-utils.fan")

# State Reset Invariance Test (RFC 5321)
# A: Normal flow - EHLO → AUTH → MAIL FROM → RCPT TO → DATA → QUIT
# B: Reset flow  - Can RSET at any state and continue from MAIL FROM
# Relation: Outcome of B's final MAIL FROM sequence must match A's outcome

<start> ::= <Interation1> <ChangeConnection> <Interation2> 

# 1. Setup Phase: Connect and EHLO
<Interation1> ::= <ServerA:response_setup><ClientA:request_ehlo><ServerA:response_ehlo><state_logged_out_A>
<Interation2> ::= <ServerB:response_setup><ClientB:request_ehlo><ServerB:response_ehlo><state_logged_out_B>
<ChangeConnection> ::= r".*" := changeConnection()

# 2. Login Phase: Move from Logged Out to Logged In
<state_logged_out_A> ::= <exchange_login_valid_A>
<state_logged_out_B> ::= <exchange_login_valid_B>

# 3. Logged In State: Send email then quit
# A: Normal flow
<state_logged_in_A> ::= <exchange_send_email_A><exchange_quit_A>
# B: Reset flow - can reset at any point, then complete transaction
<state_logged_in_B> ::= <reset_path_B><exchange_send_email_B><exchange_quit_B>

# --- Detailed Exchanges for A (Normal Flow) ---

<exchange_login_valid_A> ::= <ClientA:request_auth><ServerA:response_auth_expect_user><ClientA:request_auth_user><ServerA:response_auth_expect_pass><ClientA:request_auth_pass><ServerA:response_auth_success><state_logged_in_A>

<exchange_send_email_A> ::= <ClientA:request_mail_from><ServerA:response_mail_from><ClientA:request_rcpt_to><ServerA:response_rcpt_to><ClientA:request_data><ServerA:response_data><ClientA:email_content><ServerA:response_emailA_sent>

<exchange_quit_A> ::= <ClientA:request_quit><ServerA:response_quit>

# --- Detailed Exchanges for B (Reset Flow) ---

<exchange_login_valid_B> ::= <ClientB:request_auth><ServerB:response_auth_expect_user><ClientB:request_auth_user><ServerB:response_auth_expect_pass><ClientB:request_auth_pass><ServerB:response_auth_success><state_logged_in_B>

# Reset can happen at different points in the transaction
<reset_path_B> ::= <reset_after_mail_from_B> | <reset_after_rcpt_to_B> | <reset_after_invalid_mail_from_B> | <reset_after_invalid_rcpt_to_B>

# Path 1: Reset immediately after MAIL FROM
<reset_after_mail_from_B> ::= <ClientB:request_mail_from><ServerB:response_mail_from><exchange_reset_B>

# Path 2: Reset after RCPT TO
<reset_after_rcpt_to_B> ::= <ClientB:request_mail_from><ServerB:response_mail_from><ClientB:request_rcpt_to><ServerB:response_rcpt_to><exchange_reset_B>

# Path 3: Reset after invalid MAIL FROM (error recovery)
<reset_after_invalid_mail_from_B> ::= <ClientB:request_invalid_mail_from><ServerB:response_invalid_mail_from><exchange_reset_B>

# Path 4: Reset after invalid RCPT TO (error recovery)
<reset_after_invalid_rcpt_to_B> ::= <ClientB:request_mail_from><ServerB:response_mail_from><ClientB:request_invalid_rcpt_to><ServerB:response_invalid_rcpt_to><exchange_reset_B>

# Note: Cannot RSET after DATA's 354 response - server is in "data receiving mode" expecting email content

# RSET command to clear buffers and reset state
<exchange_reset_B> ::= <ClientB:request_rset><ServerB:response_rset>

# Complete mail transaction after reset (should work identically to A)
<exchange_send_email_B> ::= <ClientB:request_mail_from><ServerB:response_mail_from><ClientB:request_rcpt_to><ServerB:response_rcpt_to><ClientB:request_data><ServerB:response_data><ClientB:email_content><ServerB:response_emailB_sent>

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

<request_rcpt_to> ::= 'RCPT TO:<recipient@example.com>\r\n'
<response_rcpt_to> ::= r"250 .+\r\n"

# Invalid email commands (for error recovery testing)
<request_invalid_mail_from> ::= 'MAIL FROM:<invalid@>\r\n'
<response_invalid_mail_from> ::= r"[45][0-9]{2} .+\r\n"  # Accepts 4xx or 5xx error codes

<request_invalid_rcpt_to> ::= 'RCPT TO:<invalid@>\r\n'
<response_invalid_rcpt_to> ::= r"[45][0-9]{2} .+\r\n"  # Accepts 4xx or 5xx error codes

<request_data> ::= 'DATA\r\n'
<response_data> ::= r"354 .+\r\n"

<email_content> ::= 'Subject: Test Email\r\n\r\nThis is a test email.\r\n.\r\n'
<response_emailA_sent> ::= r"250 .+\r\n"
<response_emailB_sent> ::= r"250 .+\r\n"

# RSET command
<request_rset> ::= 'RSET\r\n'
<response_rset> ::= r"250 .+\r\n"

<request_quit> ::= 'QUIT\r\n'
<response_quit> ::= r"221 .+\r\n"


where validateResponses(<response_emailA_sent>, <response_emailB_sent>)


def validateResponses(responseA, responseB):
    """
    Validate that RSET properly resets server state.
    After RSET, the server should behave identically to a fresh connection.

    Returns True always to continue execution (violations are logged via print).
    """
    # Extract response codes (first 3 digits) and compare
    codeA = str(responseA)[:3]
    codeB = str(responseB)[:3]

    if codeA == codeB:
        print("[PASS] State reset successful: Response codes match (A: " + codeA + ", B: " + codeB + ")")
    else:
        print("[VIOLATION] State reset failed: Response code mismatch")
        print("  Connection A (normal): " + codeA + " - " + str(responseA).strip())
        print("  Connection B (after RSET): " + codeB + " - " + str(responseB).strip())
        print("  Expected: Server should respond identically after RSET")

    # Always return True so Fandango continues to next solution
    return True
