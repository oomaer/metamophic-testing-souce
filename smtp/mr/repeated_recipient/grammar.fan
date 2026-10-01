
include ("../../smtp-utils.fan")

# Repeated Recipient Invariance Test (RFC 5321)
# A: Normal flow - Send email with ONE RCPT TO (single recipient)
# B: Repeated flow - Send email with SAME RCPT TO repeated multiple times
# Relation: Both should succeed with identical response codes
# Per RFC 5321: Duplicate recipients should be handled gracefully (ignored or accepted)

<start> ::= <Interation1> <ConnectionControl:ChangeConnection> <Interation2>

# 1. Setup Phase: Connect and EHLO
<Interation1> ::= <ServerA:response_setup><ClientA:request_ehlo><ServerA:response_ehlo><state_logged_out_A>
<Interation2> ::= <ServerB:response_setup><ClientB:request_ehlo><ServerB:response_ehlo><state_logged_out_B>
<ChangeConnection> ::= "start connection B"

# 2. Login Phase: Move from Logged Out to Logged In
<state_logged_out_A> ::= <exchange_login_valid_A>
<state_logged_out_B> ::= <exchange_login_valid_B>

# 3. Logged In State: Send email then quit
# A: Single recipient
<state_logged_in_A> ::= <exchange_send_email_A><exchange_quit_A>
# B: Repeated recipient (same address multiple times)
<state_logged_in_B> ::= <exchange_send_email_B><exchange_quit_B>

# --- Detailed Exchanges for A (Single Recipient) ---

<exchange_login_valid_A> ::= <ClientA:request_auth><ServerA:response_auth_expect_user><ClientA:request_auth_user><ServerA:response_auth_expect_pass><ClientA:request_auth_pass><ServerA:response_auth_success><state_logged_in_A>

# Single RCPT TO command
<exchange_send_email_A> ::= <ClientA:request_mail_from><ServerA:response_mail_from><ClientA:request_rcpt_to><ServerA:response_rcpt_to><ClientA:request_data><ServerA:response_data><ClientA:email_content><ServerA:response_emailA_sent>

<exchange_quit_A> ::= <ClientA:request_quit><ServerA:response_quit>

# --- Detailed Exchanges for B (Repeated Recipient) ---

<exchange_login_valid_B> ::= <ClientB:request_auth><ServerB:response_auth_expect_user><ClientB:request_auth_user><ServerB:response_auth_expect_pass><ClientB:request_auth_pass><ServerB:response_auth_success><state_logged_in_B>

# Multiple RCPT TO commands with the SAME recipient
<exchange_send_email_B> ::= <ClientB:request_mail_from><ServerB:response_mail_from><rcpt_repeated_B><ClientB:request_data><ServerB:response_data><ClientB:email_content><ServerB:response_emailB_sent>

# Repeat the same recipient two or more times (rcpt{2,})
# Multiple alternatives for different k-paths
<rcpt_repeated_B> ::= <rcpt_2x> | <rcpt_3x> | <rcpt_n>

<rcpt_n> ::= <single_rcpt_B><rcpt_n> | <single_rcpt_B>
<rcpt_2x> ::= <single_rcpt_B><single_rcpt_B>
<rcpt_3x> ::= <single_rcpt_B><single_rcpt_B><single_rcpt_B>

<single_rcpt_B> ::= <ClientB:rcpt_simple><ServerB:response_rcpt_to_repeated>
<exchange_quit_B> ::= <ClientB:request_quit><ServerB:response_quit>

# --- Static Definitions ---

<request_ehlo> ::= 'EHLO localhost\r\n'
<response_ehlo> ::= <response_ehlo_continuation>+ "250 " r"[^\r\n]+" "\r\n"
<response_ehlo_continuation> ::= "250-" r"[^\r\n]+" "\r\n"
<response_setup> ::= "220 " r"\S+" " " r"[^\r\n]+" "\r\n"

<request_auth> ::= 'AUTH LOGIN\r\n'
<response_auth_expect_user> ::= "334 " r"[A-Za-z0-9+/=]+" "\r\n"  # Base64 encoded username prompt
<request_auth_user> ::= 'dGhlX3VzZXI=\r\n'             # "the_user"
<response_auth_expect_pass> ::= "334 " r"[A-Za-z0-9+/=]+" "\r\n"  # Base64 encoded password prompt
<request_auth_pass> ::= 'dGhlX3Bhc3N3b3Jk\r\n'         # "the_password"
<response_auth_success> ::= "235 " r"[^\r\n]+" "\r\n"

# Email sending commands - use SAME recipient address for both A and B
<request_mail_from> ::= 'MAIL FROM:<sender@example.com>\r\n'
<response_mail_from> ::= "250 " r"[^\r\n]+" "\r\n"

# Same recipient used by both A (once) and B (multiple times)
# Multiple variants to test different address formats
<request_rcpt_to> ::= <rcpt_simple>
<rcpt_simple> ::= 'RCPT TO:<recipient@example.com>\r\n'

<response_rcpt_to> ::= "250 " r"[^\r\n]+" "\r\n"

# For repeated RCPT TO, server may respond with:
# - 250 (accepted) - server allows duplicates
# - 550 (rejected) - server rejects duplicates
# - 452 (too many recipients)
# - 421 (temporary error)
# - Any other SMTP response code
# <response_rcpt_to_repeated> ::= (r"[2-5][0-9]{2}" " " r"[^\r\n]+" "\r\n")+
<response_rcpt_to_repeated> ::= "250 " r"[^\r\n]+" "\r\n"

<request_data> ::= 'DATA\r\n'
<response_data> ::= r"[2-5][0-9]{2}" " " r"[^\r\n]+" "\r\n"

<email_content> ::= 'Subject: Metamorphic Test\r\n\r\nTesting repeated recipient behavior.\r\n.\r\n'
<response_emailA_sent> ::= "250 " r"[^\r\n]+" "\r\n"
<response_emailB_sent> ::= r"[2-5][0-9]{2}" " " r"[^\r\n]+" "\r\n"

<request_quit> ::= 'QUIT\r\n'
<response_quit> ::= "221 " r"[^\r\n]+" "\r\n"


where validateResponses(<response_emailA_sent>, <response_emailB_sent>) and validateRcptResponse(<response_rcpt_to>) and validateRcptResponse(<response_rcpt_to_repeated>)


def normalizeResponse(response):
    response = str(response)
    if response.startswith("b'") or response.startswith('b"'):
        response = response[2:-1]
    return response.replace("\\r", "\r").replace("\\n", "\n").strip()


def validateRcptResponse(response):
    # Special keyword
    """Verify each RCPT TO was accepted (250)"""
    # Convert to string first (handles DerivationTree, bytes, etc.)
    response = normalizeResponse(response)
    code = response[:3]
    if code != '250':
        print(f"[VIOLATION] RCPT TO rejected: {response.strip()}")
    return True


def validateResponses(responseA, responseB):
    responseA = normalizeResponse(responseA)
    responseB = normalizeResponse(responseB)

    codeA = responseA[:3]
    codeB = responseB[:3]
    
    # Both must be success codes (250)
    a_success = codeA == '250'
    b_success = codeB == '250'
    
    if a_success and b_success and codeA == codeB:
        detailsA = responseA[7:].strip()
        detailsB = responseB[7:].strip()
        senderA = detailsA.split("[")[0].strip()
        senderB = detailsB.split("[")[0].strip()
        recipientsA = detailsA[detailsA.find("[") + 1:detailsA.rfind("]")]
        recipientsB = detailsB[detailsB.find("[") + 1:detailsB.rfind("]")]

        if "[" not in detailsA or "[" not in detailsB:
            print(f"[VIOLATION] Missing sender/recipient metadata: A={responseA}, B={responseB}")
        elif senderA != senderB:
            print(f"[VIOLATION] Sender mismatch: A={senderA}, B={senderB}")
        else:
            recipientA = recipientsA.split(",")[0].strip()
            same_recipients = True
            for recipientB in recipientsB.split(","):
                if recipientB.strip() != recipientA:
                    same_recipients = False

            if not same_recipients:
                print(f"[VIOLATION] Recipient mismatch: A=[{recipientsA}], B=[{recipientsB}]")
            else:
                print(f"[PASS] Both succeeded with 250 and same sender/recipients")
    elif a_success and not b_success:
        print(f"[VIOLATION] Single recipient succeeded but repeated recipient failed: {responseB.strip()}")
    elif not a_success and b_success:
        print(f"[VIOLATION] Single recipient failed but repeated recipient succeeded: {responseA.strip()}")
    else:
        # Both failed - check if same error
        print(f"[VIOLATION] Both failed: A={codeA}, B={codeB}")
    return True
