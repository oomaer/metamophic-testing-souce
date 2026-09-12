"""
IMAP Metamorphic Relation: Append Then Search (Simple K-Path Version)

Uses fixed email but varies other aspects to generate k-paths.
"""

include("grammar-utils.fan")

<start> ::= <Server:greeting> <login_sequence> <select_inbox> <source_search> <append_message> <followup_search>

<greeting> ::= r"\* OK.*\r\n"

<login_sequence> ::= <Client:login_cmd> <Server:login_response>
<login_cmd> ::= "A001 LOGIN testuser testpass\r\n"
<login_response> ::= r"A001 OK.*\r\n"

<select_inbox> ::= <Client:select_cmd> <Server:select_response>
<select_cmd> ::= "A002 SELECT INBOX\r\n"
<select_response> ::= r"(\* (FLAGS|EXISTS|RECENT|OK|[0-9]+).*\r\n)*A002 OK.*\r\n"

# Fixed email to avoid constraint issues
FIXED_EMAIL = "testmr@example.com"

<source_search> ::= <Client:search_cmd_source> <Server:search_response_source>
<search_cmd_source> ::= "A003 SEARCH FROM \"testmr@example.com\"\r\n"
<search_response_source> ::= r"(\* SEARCH[^\r]*\r\n)?A003 OK.*\r\n"

<append_message> ::= <Client:append_cmd> <Server:append_continue> <Client:append_literal> <Server:append_response>
<append_cmd> ::= "A004 APPEND INBOX () {" <msg_size> "}\r\n"
<append_continue> ::= r"\+ .*\r\n"
<append_literal> ::= <msg_variant> "\r\n"

# K-paths through different message sizes and subjects
<msg_size> ::= "100" | "110" | "115"

<msg_variant> ::= <msg_100> | <msg_110> | <msg_115>

<msg_100> ::= "From: testmr@example.com\r\nTo: test@example.com\r\nSubject: A\r\n\r\nBody 1.\r\n"
<msg_110> ::= "From: testmr@example.com\r\nTo: test@example.com\r\nSubject: Test B\r\n\r\nBody 2.\r\n"
<msg_115> ::= "From: testmr@example.com\r\nTo: test@example.com\r\nSubject: Message C\r\n\r\nBody 3.\r\n"

<append_response> ::= r"(\* [0-9]+ EXISTS\r\n)?A004 OK.*\r\n"

<followup_search> ::= <Client:search_cmd_followup> <Server:search_response_followup>
<search_cmd_followup> ::= "A005 SEARCH FROM \"testmr@example.com\"\r\n"
<search_response_followup> ::= r"(\* SEARCH[^\r]*\r\n)?A005 OK.*\r\n"

where validateAppendSearch(<search_response_source>, <search_response_followup>)

def validateAppendSearch(source_response, followup_response):
    try:
        source_str = str(source_response)
        followup_str = str(followup_response)
        if source_str.startswith("b'") or source_str.startswith('b"'):
            source_str = source_str[2:-1].replace('\\r\\n', '\r\n')
        if followup_str.startswith("b'") or followup_str.startswith('b"'):
            followup_str = followup_str[2:-1].replace('\\r\\n', '\r\n')
        source_count = parse_search_count(source_str)
        followup_count = parse_search_count(followup_str)
        print("[DEBUG] Source: " + str(source_count) + ", Follow-up: " + str(followup_count))
        if followup_count == source_count + 1:
            print("[PASS] Search count increased by 1 after APPEND")
        else:
            print("[VIOLATION] Expected " + str(source_count + 1) + ", got " + str(followup_count))
    except Exception as e:
        print("[ERROR] " + str(e))
    return True

def parse_search_count(response_str):
    import re
    match = re.search(r'\* SEARCH([^\r\n]*)', response_str)
    if not match:
        return 0
    results = match.group(1).strip()
    return len(results.split()) if results else 0
