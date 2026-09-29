<start> ::= <Server:greeting> <login_sequence> <Interaction1> <Interaction2>
<Interaction1> ::= <select_inbox> <source_search> 
<Interaction2> ::= <append_sequence> <followup_search>
<greeting> ::= r"\* OK[^\r\n]*" "\r\n"
<login_sequence> ::= <Client:login_cmd> <Server:login_response>
<login_cmd> ::= "A001 LOGIN testuser testpass\r\n"
<login_response> ::= r"A001 OK[^\r\n]*" "\r\n"

<select_inbox> ::= <Client:select_cmd> <Server:select_response>
<select_cmd> ::= "A002 SELECT INBOX\r\n"
<select_response> ::= r"(\* (FLAGS|EXISTS|RECENT|OK|[0-9]+).*\r\n)*A002 OK[^\r\n]*" "\r\n"
<source_search> ::= <Client:search_cmd_source> <Server:search_response_source>
<search_cmd_source> ::= "A003 SEARCH FROM \"testmr@example.com\"\r\n"
<search_response_source> ::= r"(\* SEARCH[^\r]*\r\n)?A003 OK[^\r\n]*" "\r\n"

<append_sequence> ::= <append_1x> | <append_2x> | <append_3x>
<append_1x> ::= <append_variant_test>
<append_2x> ::= <append_variant_test><append_variant_test>
<append_3x> ::= <append_variant_test><append_variant_test><append_variant_test>
<append_variant_test> ::= <StdOut:message_wrapper><Client:append_cmd><Server:append_continue><Client:append_literal><Server:append_response>
<append_cmd> ::=  "A004 APPEND INBOX () {" <size> "}\r\n"
<message_wrapper> ::= <message>
<message> ::= b"From: testmr@example.com\r\nTo: test@example.com\r\nSubject: Test "<random_number>"\r\n\r\nBody "<random_number>".\r\n"
<size> ::= r"\d+"
<append_literal> ::= <message> "\r\n"
<random_number> ::= <digit>
<digit> ::= '1' | '2' | '3' 
where int(<size>) == len(str(<message>))

<append_continue> ::= r"\+ [^\r\n]*" "\r\n"
<append_response> ::= r"(\* [0-9]+ EXISTS\r\n)?A004 OK[^\r\n]*" "\r\n"

<followup_search> ::= <Client:search_cmd_followup> <Server:search_response_followup>
<search_cmd_followup> ::= "A005 SEARCH FROM \"testmr@example.com\"\r\n"
<search_response_followup> ::= r"(\* SEARCH[^\r]*\r\n)?A005 OK[^\r\n]*" "\r\n"

where validateAppendSearch(<search_response_source>, <search_response_followup>, <append_sequence>)
