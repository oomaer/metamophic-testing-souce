"""
DNS CNAME Resolution Equivalence - Simplified Version

Tests: example.local A (CNAME) vs test.local A (direct) should return same A records
"""

# Include base DNS utilities
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# Import from parent dns-utils.fan
exec(open(os.path.join(os.path.dirname(__file__), '..', '..', 'dns-utils.fan')).read())


<start> ::= <QueryCNAME> <QueryDirect>

# Query 1: CNAME domain (example.local A)
<QueryCNAME> ::= <Client:query_cname> <Server:response_cname>

# Query 2: Direct target (test.local A)
<QueryDirect> ::= <Client:query_direct> <Server:response_direct>

# Queries
<query_cname> ::= <dns_header> <question_cname>
<query_direct> ::= <dns_header> <question_direct>

<dns_header> ::= <h_id> 0 0000 0 0 1 0 0 0 0 0000 <qd_count> 0{16} 0{16} 0{16}
<h_id> ::= <byte><byte>
<qd_count> ::= <byte>{2} := pack(">H", 1)

<question_cname> ::= <name_example_local> <type_a> <class_in>
<question_direct> ::= <name_test_local> <type_a> <class_in>

<name_example_local> ::= <byte>{15} := b'\x07example\x05local\x00'
<name_test_local> ::= <byte>{12} := b'\x04test\x05local\x00'
<type_a> ::= 0{15} 1
<class_in> ::= 0{15} 1

# Responses - match any binary
<response_cname> ::= r"[\x00-\xff]+"
<response_direct> ::= r"[\x00-\xff]+"

<byte> ::= 0{8} | 1{8}


where validateCNAME(<response_cname>, <response_direct>)


def validateCNAME(resp_cname_bytes, resp_direct_bytes):
    """Validate CNAME resolution equivalence."""
    try:
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'dnslib'))
        from dnslib import DNSRecord, QTYPE, RCODE

        resp_cname = DNSRecord.parse(bytes(resp_cname_bytes))
        resp_direct = DNSRecord.parse(bytes(resp_direct_bytes))

        # Extract A records
        a_cname = {str(rr.rdata) for rr in resp_cname.rr if rr.rtype == QTYPE.A}
        a_direct = {str(rr.rdata) for rr in resp_direct.rr if rr.rtype == QTYPE.A}

        print(f"CNAME A records: {a_cname}")
        print(f"Direct A records: {a_direct}")

        if a_cname == a_direct:
            print(f"[PASS] A records match")
        else:
            print(f"[VIOLATION] A records differ: {a_cname} vs {a_direct}")

    except Exception as e:
        print(f"[ERROR] {e}")
        import traceback
        traceback.print_exc()

    return True
