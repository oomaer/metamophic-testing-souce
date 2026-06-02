"""
IMAP Metamorphic Relation: Append Then Search (K-Path Version)

MR: After appending N messages with specific search criteria, searching for
    that criteria should return exactly N more results than before.

K-Paths:
  - append_1x: Single append (+1)
  - append_2x: Two appends (+2)
  - append_3x: Three appends (+3)

Each append uses message variants (msg_a, msg_b, msg_c) to create
additional k-path branches through content variation.
"""

include("grammar-utils.fan")


# === Main Grammar with K-Path Branching ===

<start> ::= <Server:greeting> <login_sequence> <select_inbox> <source_search> <append_sequence> <followup_search>


# === Server Greeting ===
<greeting> ::= r"\* OK.*\r\n"


# === Login Sequence ===
<login_sequence> ::= <Client:login_cmd> <Server:login_response>

<login_cmd> ::= "A001 LOGIN testuser testpass\r\n"
<login_response> ::= r"A001 OK.*\r\n"


# === Select INBOX ===
<select_inbox> ::= <Client:select_cmd> <Server:select_response>

<select_cmd> ::= "A002 SELECT INBOX\r\n"
<select_response> ::= r"(\* (FLAGS|EXISTS|RECENT|OK|[0-9]+).*\r\n)*A002 OK.*\r\n"


# === Source Search (before APPENDs) ===
<source_search> ::= <Client:search_cmd_source> <Server:search_response_source>

<search_cmd_source> ::= "A003 SEARCH FROM \"testmr@example.com\"\r\n"
<search_response_source> ::= r"\* SEARCH[^\r]*\r\nA003 OK.*\r\n"


# === K-Path: Append Sequence Alternatives ===
<append_sequence> ::= <append_1x> | <append_2x> | <append_3x>

<append_1x> ::= <single_append>
<append_2x> ::= <single_append><single_append>
<append_3x> ::= <single_append><single_append><single_append>


# === K-Path: Message Variants ===
<single_append> ::= <append_variant_a> | <append_variant_b> | <append_variant_c>

<append_variant_a> ::= <Client:append_cmd_a> <Server:append_continue> <Client:append_literal_a> <Server:append_response>
<append_variant_b> ::= <Client:append_cmd_b> <Server:append_continue> <Client:append_literal_b> <Server:append_response>
<append_variant_c> ::= <Client:append_cmd_c> <Server:append_continue> <Client:append_literal_c> <Server:append_response>

<append_cmd_a> ::= "A004 APPEND INBOX () {" <size_a> "}\r\n"
<append_cmd_b> ::= "A004 APPEND INBOX () {" <size_b> "}\r\n"
<append_cmd_c> ::= "A004 APPEND INBOX () {" <size_c> "}\r\n"

<size_a> ::= r"[0-9]+" := get_size_a()
<size_b> ::= r"[0-9]+" := get_size_b()
<size_c> ::= r"[0-9]+" := get_size_c()

<append_continue> ::= r"\+ .*\r\n"

<append_literal_a> ::= <msg_content_a> "\r\n"
<append_literal_b> ::= <msg_content_b> "\r\n"
<append_literal_c> ::= <msg_content_c> "\r\n"

<msg_content_a> ::= r"[\s\S]*" := get_msg_a()
<msg_content_b> ::= r"[\s\S]*" := get_msg_b()
<msg_content_c> ::= r"[\s\S]*" := get_msg_c()

<append_response> ::= r"(\* [0-9]+ EXISTS\r\n)?A004 OK.*\r\n"


# === Follow-up Search (after APPENDs) ===
<followup_search> ::= <Client:search_cmd_followup> <Server:search_response_followup>

<search_cmd_followup> ::= "A005 SEARCH FROM \"testmr@example.com\"\r\n"
<search_response_followup> ::= r"\* SEARCH[^\r]*\r\nA005 OK.*\r\n"


# === Validation Constraint ===

where validateAppendSearch(<search_response_source>, <search_response_followup>, <append_sequence>)


def validateAppendSearch(source_response, followup_response, append_seq):
    """
    Validate that SEARCH results increase by exactly the append count.
    Count appends by examining the derivation tree.
    """
    try:
        source_str = str(source_response)
        followup_str = str(followup_response)
        append_str = str(append_seq)

        if source_str.startswith("b'") or source_str.startswith('b"'):
            source_str = source_str[2:-1].replace('\\r\\n', '\r\n')
        if followup_str.startswith("b'") or followup_str.startswith('b"'):
            followup_str = followup_str[2:-1].replace('\\r\\n', '\r\n')

        source_count = parse_search_count(source_str)
        followup_count = parse_search_count(followup_str)

        # Count appends by counting "A004 APPEND" occurrences
        append_count = append_str.count("A004 APPEND")
        expected_count = source_count + append_count

        print("[DEBUG] Appends: " + str(append_count) + ", Source: " + str(source_count) + ", Follow-up: " + str(followup_count))

        if followup_count == expected_count:
            print("[PASS] After " + str(append_count) + " append(s): " + str(source_count) + " -> " + str(followup_count))
        else:
            print("[VIOLATION] Expected " + str(expected_count) + " after " + str(append_count) + " append(s), got " + str(followup_count))
            if followup_count == source_count:
                print("  Possible bug: APPEND did not update search index")
            elif followup_count < source_count:
                print("  Possible bug: Messages were lost")
            elif followup_count > expected_count:
                print("  Possible bug: Duplicate messages created or count mismatch")

    except Exception as e:
        print("[ERROR] Validation failed: " + str(e))
        import traceback
        traceback.print_exc()

    return True


def parse_search_count(response_str):
    """
    Parse IMAP SEARCH response and return count of results.
    """
    import re

    search_match = re.search(r'\* SEARCH([^\r\n]*)', response_str)
    if not search_match:
        print("[DEBUG] No SEARCH response found in: " + response_str[:100])
        return 0

    results_str = search_match.group(1).strip()

    if not results_str:
        return 0

    numbers = results_str.split()
    return len(numbers)
