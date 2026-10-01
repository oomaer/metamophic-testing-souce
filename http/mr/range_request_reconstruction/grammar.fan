
include ("./http-utils.fan")

# Range Request Reconstruction Metamorphic Relation (RFC 7233)
#
# A: Full GET request (no Range header) - gets complete content
# B: Two partial GET requests with Range headers, responses concatenated
# Relation: Concatenated B must exactly equal A's body
#
# Content size is 998 bytes
content_size = 998
<start> ::= <test_case>

# ============================================================================
# Shared Elements
# ============================================================================
<req_full> ::= "GET /large HTTP/1.1\r\nHost: localhost\r\nUser-Agent: Fandango/1.0\r\n\r\n"
<response_full> ::= r"HTTP/1\.1 200 OK\r\n(?:[A-Za-z0-9-]+: [^\r\n]*\r\n)*\r\n[\s\S]+"
<response_partial> ::= r"HTTP/1\.1 206 Partial Content\r\n(?:[A-Za-z0-9-]+: [^\r\n]*\r\n)*\r\n[\s\S]+"
<ChangeConnection> ::= r".*" := changeConnection()

# Common interaction pattern - A always gets full content
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

# ============================================================================
# Validation
# ============================================================================
where validateRangeReconstruction(<response_full>, <resp_p1>, <resp_p2>)


def validateRangeReconstruction(response_full, response_part1, response_part2):
    def clean_str(s):
        s = str(s)
        if s.startswith("b'") or s.startswith('b"'):
            s = s[2:-1]
        return s.replace('\\r\\n', '\r\n')

    def extract_body(response):
        idx = response.find('\r\n\r\n')
        return response[idx + 4:] if idx >= 0 else ""

    full_body = extract_body(clean_str(response_full))
    part1_body = extract_body(clean_str(response_part1))
    part2_body = extract_body(clean_str(response_part2))
    reconstructed = part1_body + part2_body

    if full_body == reconstructed:
        print("[PASS] Range reconstruction: full=" + str(len(full_body)) + " bytes, part1=" + str(len(part1_body)) + ", part2=" + str(len(part2_body)))
    else:
        print("[VIOLATION] Range reconstruction FAILED")
        print("  Full: " + str(len(full_body)) + ", Part1: " + str(len(part1_body)) + ", Part2: " + str(len(part2_body)))
        print("  Reconstructed: " + str(len(reconstructed)) + " bytes")
    return True
