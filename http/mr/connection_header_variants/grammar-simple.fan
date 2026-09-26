<start> ::= <test_case>
<response> ::= "HTTP/1.1 " r"[0-9]{3}" " " (r"[^\r\n]+")? "\r\n" (r"[^\r\n]+" "\r\n")* "\r\n" (r"[0-9a-fA-F]+" "\r\n" r"[\s\S]"* "0\r\n\r\n" | (r"[^\r\n]+")?)?
<ChangeConnection> ::= r".*" := changeConnection()

# Request templates - only Connection header differs between A and B
<req_prefix_root> ::= "GET / HTTP/1.1\r\nHost: localhost\r\n"
<req_prefix_data> ::= "GET /data HTTP/1.1\r\nHost: localhost\r\n"

# User-Agent variants
<ua_fandango> ::= "User-Agent: Fandango/1.0\r\n"
<ua_testclient> ::= "User-Agent: TestClient/2.0\r\n"
<ua_mozilla> ::= "User-Agent: Mozilla/5.0\r\n"

# Accept variants
<accept_any> ::= "Accept: */*\r\n"
<accept_json> ::= "Accept: application/json\r\n"
<accept_html> ::= "Accept: text/html\r\n"

# Connection variants
<conn_keepalive> ::= "Connection: keep-alive\r\n\r\n"
<conn_close> ::= "Connection: close\r\n\r\n"

<test_case> ::= <test_root> | <test_data> | <test_root_json> | <test_data_json> | <test_root_html> | <test_data_html>

# Test / with Accept: */*
<test_root> ::= <ClientA:req_root_ka><ServerA:resp_A> <ChangeConnection> <ClientB:req_root_cl><ServerB:resp_B>
<req_root_ka> ::= <req_prefix_root> <ua_fandango> <accept_any> <conn_keepalive>
<req_root_cl> ::= <req_prefix_root> <ua_fandango> <accept_any> <conn_close>
<resp_A> ::= <response>
<resp_B> ::= <response>

# Test /data with Accept: */*
<test_data> ::= <ClientA:req_data_ka><ServerA:resp_A_data> <ChangeConnection> <ClientB:req_data_cl><ServerB:resp_B_data>
<req_data_ka> ::= <req_prefix_data> <ua_fandango> <accept_any> <conn_keepalive>
<req_data_cl> ::= <req_prefix_data> <ua_fandango> <accept_any> <conn_close>
<resp_A_data> ::= <response>
<resp_B_data> ::= <response>

# Test / with Accept: application/json
<test_root_json> ::= <ClientA:req_root_json_ka><ServerA:resp_A_rj> <ChangeConnection> <ClientB:req_root_json_cl><ServerB:resp_B_rj>
<req_root_json_ka> ::= <req_prefix_root> <ua_testclient> <accept_json> <conn_keepalive>
<req_root_json_cl> ::= <req_prefix_root> <ua_testclient> <accept_json> <conn_close>
<resp_A_rj> ::= <response>
<resp_B_rj> ::= <response>

# Test /data with Accept: application/json
<test_data_json> ::= <ClientA:req_data_json_ka><ServerA:resp_A_dj> <ChangeConnection> <ClientB:req_data_json_cl><ServerB:resp_B_dj>
<req_data_json_ka> ::= <req_prefix_data> <ua_testclient> <accept_json> <conn_keepalive>
<req_data_json_cl> ::= <req_prefix_data> <ua_testclient> <accept_json> <conn_close>
<resp_A_dj> ::= <response>
<resp_B_dj> ::= <response>

# Test / with Accept: text/html
<test_root_html> ::= <ClientA:req_root_html_ka><ServerA:resp_A_rh> <ChangeConnection> <ClientB:req_root_html_cl><ServerB:resp_B_rh>
<req_root_html_ka> ::= <req_prefix_root> <ua_mozilla> <accept_html> <conn_keepalive>
<req_root_html_cl> ::= <req_prefix_root> <ua_mozilla> <accept_html> <conn_close>
<resp_A_rh> ::= <response>
<resp_B_rh> ::= <response>

# Test /data with Accept: text/html
<test_data_html> ::= <ClientA:req_data_html_ka><ServerA:resp_A_dh> <ChangeConnection> <ClientB:req_data_html_cl><ServerB:resp_B_dh>
<req_data_html_ka> ::= <req_prefix_data> <ua_mozilla> <accept_html> <conn_keepalive>
<req_data_html_cl> ::= <req_prefix_data> <ua_mozilla> <accept_html> <conn_close>
<resp_A_dh> ::= <response>
<resp_B_dh> ::= <response>
where validateConnectionInvariance(<resp_A>, <resp_B>)
where validateConnectionInvariance(<resp_A_data>, <resp_B_data>)
where validateConnectionInvariance(<resp_A_rj>, <resp_B_rj>)
where validateConnectionInvariance(<resp_A_dj>, <resp_B_dj>)
where validateConnectionInvariance(<resp_A_rh>, <resp_B_rh>)
where validateConnectionInvariance(<resp_A_dh>, <resp_B_dh>)
