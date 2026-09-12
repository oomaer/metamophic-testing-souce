
<start> ::= <test_case>

<req_full> ::= "GET /large HTTP/1.1\r\nHost: localhost\r\nUser-Agent: Fandango/1.0\r\n\r\n"
<response_full> ::= r"HTTP/1\.1 200 OK\r\n(?:[A-Za-z0-9-]+: [^\r\n]*\r\n)*\r\n[\s\S]+"
<response_partial> ::= r"HTTP/1\.1 206 Partial Content\r\n(?:[A-Za-z0-9-]+: [^\r\n]*\r\n)*\r\n[\s\S]+"
<ChangeConnection> ::= r".*" := changeConnection()

<InteractionA> ::= <ClientA:req_full><ServerA:response_full>

<test_case> ::= <InteractionA> <ChangeConnection> <InteractionB>
<InteractionB> ::=  <ClientB:req_p1><ServerB:resp_p1><ClientB:req_p2><ServerB:resp_p2>
<req_p1> ::= "GET /large HTTP/1.1\r\nHost: localhost\r\nUser-Agent: Fandango/1.0\r\nRange: bytes=0-" <req_1_size> "\r\n\r\n"
<req_p2> ::= "GET /large HTTP/1.1\r\nHost: localhost\r\nUser-Agent: Fandango/1.0\r\nRange: bytes=" <req_2_size> "-\r\n\r\n"
<req_1_size> ::= <range_bound_digit>
<req_2_size> ::= r'\d+'
<range_bound_digit> ::= <digit_without_0> <range_bound_digit2> | <digit_without_0>
<range_bound_digit2> ::= <digit> <range_bound_digit3> | <digit>
<range_bound_digit3> ::= <digit>
<digit> ::= '0' | '1' | '2' | '3' | '4' | '5' | '6' | '7' |'8' | '9'
<digit_without_0> ::= '1' | '2' | '3' | '4' | '5' | '6' | '7' |'8' | '9'
<resp_p1> ::= <response_partial>
<resp_p2> ::= <response_partial>

where int(<req_2_size>) == int(<req_1_size>) + 1
where int(<req_1_size>) < content_size - 1

where validateRangeReconstruction(<response_full>, <resp_p1>, <resp_p2>)
