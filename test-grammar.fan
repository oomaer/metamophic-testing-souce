<start> ::= <Interaction_A> <Interaction_B>
<Interaction_A> ::= <request_a> <response_a>
<Interaction_B> ::= <request_b> <response_b>
<request_a> ::= "GET " ("first_name" | "last_name") "\r\n"
<request_b> ::= r"GET [A-Z_]+\r\n" := str(<request_a>).upper()
<response_a> ::= "OK " (r"[^\r\n]+")? "\r\n"
<response_b> ::= ("OK" | "ERR") " " (r"[^\r\n]+")? "\r\n"
# where same_result(<response_a>, <response_b>)