
<start> ::= <Server:greeting> <login_sequence> <select_inbox> <source_search> <append_sequence> <followup_search>
<greeting> ::= r"\* OK.*\r\n"
<login_sequence> ::= <Client:login_cmd> <Server:login_response>
<login_cmd> ::= "A001 LOGIN testuser testpass\r\n"
<login_response> ::= r"A001 OK.*\r\n"

<select_inbox> ::= <Client:select_cmd> <Server:select_response>
<select_cmd> ::= "A002 SELECT INBOX\r\n"
<select_response> ::= r"(\* (FLAGS|EXISTS|RECENT|OK|[0-9]+).*\r\n)*A002 OK.*\r\n"

<source_search> ::= <Client:search_cmd_source> <Server:search_response_source>
<search_cmd_source> ::= "A003 SEARCH FROM \"testmr@example.com\"\r\n"
<search_response_source> ::= r"\* SEARCH[^\r]*\r\nA003 OK.*\r\n"

<append_sequence> ::= <append_1x> | <append_2x> | <append_3x>
<append_1x> ::= <single_append>
<append_2x> ::= <single_append><single_append>
<append_3x> ::= <single_append><single_append><single_append>
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

<followup_search> ::= <Client:search_cmd_followup> <Server:search_response_followup>

<search_cmd_followup> ::= "A005 SEARCH FROM \"testmr@example.com\"\r\n"
<search_response_followup> ::= r"\* SEARCH[^\r]*\r\nA005 OK.*\r\n"


where validateAppendSearch(<search_response_source>, <search_response_followup>, <append_sequence>)

