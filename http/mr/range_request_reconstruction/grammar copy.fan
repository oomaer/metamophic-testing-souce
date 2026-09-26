
include ("./http-utils.fan")

# Range Request Reconstruction Metamorphic Relation (RFC 7233)
#
# A: Full GET request (no Range header) - gets complete content
# B: Two partial GET requests with Range headers, responses concatenated
# Relation: Concatenated B must exactly equal A's body
#
# Content size is 998 bytes

<start> ::= <test_case>

# ============================================================================
# Shared Elements
# ============================================================================
<req_full> ::= "GET /large HTTP/1.1\r\nHost: localhost\r\nUser-Agent: Fandango/1.0\r\n\r\n"
<response_full> ::= "HTTP/1.1 200 OK" "\r\n" (r"[A-Za-z0-9-]+" ": " (r"[^\r\n]+")? "\r\n")* "\r\n" r"[\s\S]+"
<response_partial> ::= "HTTP/1.1 206 Partial Content" "\r\n" (r"[A-Za-z0-9-]+" ": " (r"[^\r\n]+")? "\r\n")* "\r\n" r"[\s\S]+"
<ChangeConnection> ::= r".*" := changeConnection()

# Common interaction pattern - A always gets full content
<InteractionA> ::= <ClientA:req_full><ServerA:response_full>

# ============================================================================
# Test Cases - 9 different split points for k-path coverage
# ============================================================================
<test_case> ::= <test_50> | <test_100> | <test_200> | <test_300> | <test_500> | <test_600> | <test_800> | <test_900> | <test_950>

# Split at byte 50 (very early)
<test_50> ::= <InteractionA> <ChangeConnection> <ClientB:req_p1_50><ServerB:resp_p1_50><ClientB:req_p2_50><ServerB:resp_p2_50>
<req_p1_50> ::= "GET /large HTTP/1.1\r\nHost: localhost\r\nUser-Agent: Fandango/1.0\r\nRange: bytes=0-49\r\n\r\n"
<req_p2_50> ::= "GET /large HTTP/1.1\r\nHost: localhost\r\nUser-Agent: Fandango/1.0\r\nRange: bytes=50-\r\n\r\n"
<resp_p1_50> ::= <response_partial>
<resp_p2_50> ::= <response_partial>

# Split at byte 100
<test_100> ::= <InteractionA> <ChangeConnection> <ClientB:req_p1_100><ServerB:resp_p1_100><ClientB:req_p2_100><ServerB:resp_p2_100>
<req_p1_100> ::= "GET /large HTTP/1.1\r\nHost: localhost\r\nUser-Agent: Fandango/1.0\r\nRange: bytes=0-99\r\n\r\n"
<req_p2_100> ::= "GET /large HTTP/1.1\r\nHost: localhost\r\nUser-Agent: Fandango/1.0\r\nRange: bytes=100-\r\n\r\n"
<resp_p1_100> ::= <response_partial>
<resp_p2_100> ::= <response_partial>

# Split at byte 200
<test_200> ::= <InteractionA> <ChangeConnection> <ClientB:req_p1_200><ServerB:resp_p1_200><ClientB:req_p2_200><ServerB:resp_p2_200>
<req_p1_200> ::= "GET /large HTTP/1.1\r\nHost: localhost\r\nUser-Agent: Fandango/1.0\r\nRange: bytes=0-199\r\n\r\n"
<req_p2_200> ::= "GET /large HTTP/1.1\r\nHost: localhost\r\nUser-Agent: Fandango/1.0\r\nRange: bytes=200-\r\n\r\n"
<resp_p1_200> ::= <response_partial>
<resp_p2_200> ::= <response_partial>

# Split at byte 300
<test_300> ::= <InteractionA> <ChangeConnection> <ClientB:req_p1_300><ServerB:resp_p1_300><ClientB:req_p2_300><ServerB:resp_p2_300>
<req_p1_300> ::= "GET /large HTTP/1.1\r\nHost: localhost\r\nUser-Agent: Fandango/1.0\r\nRange: bytes=0-299\r\n\r\n"
<req_p2_300> ::= "GET /large HTTP/1.1\r\nHost: localhost\r\nUser-Agent: Fandango/1.0\r\nRange: bytes=300-\r\n\r\n"
<resp_p1_300> ::= <response_partial>
<resp_p2_300> ::= <response_partial>

# Split at byte 500 (middle)
<test_500> ::= <InteractionA> <ChangeConnection> <ClientB:req_p1_500><ServerB:resp_p1_500><ClientB:req_p2_500><ServerB:resp_p2_500>
<req_p1_500> ::= "GET /large HTTP/1.1\r\nHost: localhost\r\nUser-Agent: Fandango/1.0\r\nRange: bytes=0-499\r\n\r\n"
<req_p2_500> ::= "GET /large HTTP/1.1\r\nHost: localhost\r\nUser-Agent: Fandango/1.0\r\nRange: bytes=500-\r\n\r\n"
<resp_p1_500> ::= <response_partial>
<resp_p2_500> ::= <response_partial>

# Split at byte 600
<test_600> ::= <InteractionA> <ChangeConnection> <ClientB:req_p1_600><ServerB:resp_p1_600><ClientB:req_p2_600><ServerB:resp_p2_600>
<req_p1_600> ::= "GET /large HTTP/1.1\r\nHost: localhost\r\nUser-Agent: Fandango/1.0\r\nRange: bytes=0-599\r\n\r\n"
<req_p2_600> ::= "GET /large HTTP/1.1\r\nHost: localhost\r\nUser-Agent: Fandango/1.0\r\nRange: bytes=600-\r\n\r\n"
<resp_p1_600> ::= <response_partial>
<resp_p2_600> ::= <response_partial>

# Split at byte 800
<test_800> ::= <InteractionA> <ChangeConnection> <ClientB:req_p1_800><ServerB:resp_p1_800><ClientB:req_p2_800><ServerB:resp_p2_800>
<req_p1_800> ::= "GET /large HTTP/1.1\r\nHost: localhost\r\nUser-Agent: Fandango/1.0\r\nRange: bytes=0-799\r\n\r\n"
<req_p2_800> ::= "GET /large HTTP/1.1\r\nHost: localhost\r\nUser-Agent: Fandango/1.0\r\nRange: bytes=800-\r\n\r\n"
<resp_p1_800> ::= <response_partial>
<resp_p2_800> ::= <response_partial>

# Split at byte 900
<test_900> ::= <InteractionA> <ChangeConnection> <ClientB:req_p1_900><ServerB:resp_p1_900><ClientB:req_p2_900><ServerB:resp_p2_900>
<req_p1_900> ::= "GET /large HTTP/1.1\r\nHost: localhost\r\nUser-Agent: Fandango/1.0\r\nRange: bytes=0-899\r\n\r\n"
<req_p2_900> ::= "GET /large HTTP/1.1\r\nHost: localhost\r\nUser-Agent: Fandango/1.0\r\nRange: bytes=900-\r\n\r\n"
<resp_p1_900> ::= <response_partial>
<resp_p2_900> ::= <response_partial>

# Split at byte 950 (very late)
<test_950> ::= <InteractionA> <ChangeConnection> <ClientB:req_p1_950><ServerB:resp_p1_950><ClientB:req_p2_950><ServerB:resp_p2_950>
<req_p1_950> ::= "GET /large HTTP/1.1\r\nHost: localhost\r\nUser-Agent: Fandango/1.0\r\nRange: bytes=0-949\r\n\r\n"
<req_p2_950> ::= "GET /large HTTP/1.1\r\nHost: localhost\r\nUser-Agent: Fandango/1.0\r\nRange: bytes=950-\r\n\r\n"
<resp_p1_950> ::= <response_partial>
<resp_p2_950> ::= <response_partial>

# ============================================================================
# Validation
# ============================================================================
where validateRangeReconstruction(<response_full>, <resp_p1_50>, <resp_p2_50>)
where validateRangeReconstruction(<response_full>, <resp_p1_100>, <resp_p2_100>)
where validateRangeReconstruction(<response_full>, <resp_p1_200>, <resp_p2_200>)
where validateRangeReconstruction(<response_full>, <resp_p1_300>, <resp_p2_300>)
where validateRangeReconstruction(<response_full>, <resp_p1_500>, <resp_p2_500>)
where validateRangeReconstruction(<response_full>, <resp_p1_600>, <resp_p2_600>)
where validateRangeReconstruction(<response_full>, <resp_p1_800>, <resp_p2_800>)
where validateRangeReconstruction(<response_full>, <resp_p1_900>, <resp_p2_900>)
where validateRangeReconstruction(<response_full>, <resp_p1_950>, <resp_p2_950>)


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
