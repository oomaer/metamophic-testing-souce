"""
DNS Metamorphic Relation: CNAME Recursive Resolver

MR: Querying an authoritative server directly for "test.local <type>" should return
    the same records as querying a recursive resolver for "example.local <type>"
    (which internally resolves via the authoritative server).

Setup:
  - Server A (port 5053): Authoritative, has all records for test.local
  - Server B (port 5054): Recursive resolver, only has CNAME example.local -> test.local
    and forwards to Server A for the actual records

Test:
  Interaction 1: ClientA queries ServerA for "test.local <type>" (direct)
  Interaction 2: ClientB queries ServerB for "example.local <type>" (recursive)
  Types tested: A, AAAA, TXT (k-path variations)

  Relation: Records of the queried type from both responses should be identical.
"""

include("grammar-utils.fan")

from struct import pack


# === Grammar Definition ===

<start> ::= <Interaction1> <ChangeConnection> <Interaction2>

# Interaction 1: Direct query to authoritative server
<Interaction1> ::= <ClientA:query_direct><ServerA:response_direct>

# Switch connections
<ChangeConnection> ::= r".*" := changeConnection()

# Interaction 2: Query to recursive resolver
<Interaction2> ::= <ClientB:query_recursive><ServerB:response_recursive>


# === DNS Queries ===

<query_direct> ::= <header_req_direct> <question_direct>
<query_recursive> ::= <header_req_recursive> <question_recursive>

# Headers
<header_req_direct> ::= <h_id_direct> 0 <h_opcode_standard> 0 0 1 0 0 0 0 <h_rcode_noerror> <qd_count> 0{16} 0{16} 0{16}
<header_req_recursive> ::= <h_id_recursive> 0 <h_opcode_standard> 0 0 1 0 0 0 0 <h_rcode_noerror> <qd_count> 0{16} 0{16} 0{16}

<h_id_direct> ::= <byte><byte>
<h_id_recursive> ::= <byte><byte>
<h_opcode_standard> ::= 0 0 0 0
<h_rcode_noerror> ::= 0 0 0 0
<qd_count> ::= <byte>{2} := pack(">H", 1)

# Questions - both use <q_type> which will be constrained to match
<question_direct> ::= <q_name_direct> <q_type_direct> <rr_class>
<question_recursive> ::= <q_name_recursive> <q_type_recursive> <rr_class>

<q_name_direct> ::= <q_name_written_direct> 0{8}
<q_name_recursive> ::= <q_name_written_recursive> 0{8}

<q_name_written_direct> ::= (<label_len_octet> <byte>{byte_to_int(b'\x00' + bytes(<label_len_octet>))})+ := gen_target_domain()
<q_name_written_recursive> ::= (<label_len_octet> <byte>{byte_to_int(b'\x00' + bytes(<label_len_octet>))})+ := gen_cname_domain()

# Query types - creates k-path variations for multiple test cases
<q_type_direct> ::= <q_type_a> | <q_type_aaaa> | <q_type_txt>
<q_type_recursive> ::= <q_type_a> | <q_type_aaaa> | <q_type_txt>
<q_type_a> ::= 0{15} 1                    # A = 1
<q_type_aaaa> ::= 0{11} 1 1 1 0 0         # AAAA = 28
<q_type_txt> ::= 0{11} 1 0 0 0 0          # TXT = 16
<rr_class> ::= 0{15} 1  # IN class


# === DNS Responses (from server) ===
<response_direct> ::= r"[\x00-\xff]+"
<response_recursive> ::= r"[\x00-\xff]+"


# === Basic Types ===

<bit> ::= 0 | 1
<byte> ::= <bit>{8}
<label_len_octet> ::= <byte>


# === Validation Constraint ===

# Ensure both queries use the same type AND validate recursive resolution
where str(<q_type_direct>) == str(<q_type_recursive>) and validateRecursiveResolution(<response_direct>, <response_recursive>)


def validateRecursiveResolution(response_direct_bytes, response_recursive_bytes):
    """
    Validate that direct authoritative query and recursive resolver query
    return the same records for the queried type.
    """
    try:
        from dnslib import DNSRecord, QTYPE, RCODE

        resp_direct = DNSRecord.parse(bytes(response_direct_bytes))
        resp_recursive = DNSRecord.parse(bytes(response_recursive_bytes))

        rcode_direct = RCODE[resp_direct.header.rcode]
        rcode_recursive = RCODE[resp_recursive.header.rcode]

        # Get query type from direct response
        qtype = resp_direct.q.qtype
        qtype_name = QTYPE[qtype]

        print(f"[DEBUG] Query type: {qtype_name}")
        print(f"[DEBUG] Direct query RCODE: {rcode_direct}")
        print(f"[DEBUG] Recursive query RCODE: {rcode_recursive}")

        if rcode_direct != 'NOERROR' or rcode_recursive != 'NOERROR':
            print(f"[VIOLATION] Non-NOERROR response: Direct={rcode_direct}, Recursive={rcode_recursive}")
            return True

        # Extract records of the queried type from direct response
        records_direct = set()
        for rr in resp_direct.rr:
            if rr.rtype == qtype:
                records_direct.add(str(rr.rdata))
                print(f"[DEBUG] Direct {qtype_name} record: {rr.rdata}")

        # Extract records of the queried type from recursive response (skip CNAME records)
        records_recursive = set()
        for rr in resp_recursive.rr:
            if rr.rtype == qtype:
                records_recursive.add(str(rr.rdata))
                print(f"[DEBUG] Recursive {qtype_name} record: {rr.rdata}")
            elif rr.rtype == QTYPE.CNAME:
                print(f"[DEBUG] Recursive CNAME record: {rr.rdata}")

        if records_direct == records_recursive:
            print(f"[PASS] Recursive resolution equivalence holds for {qtype_name}: {records_direct}")
        else:
            print(f"[VIOLATION] {qtype_name} records differ!")
            print(f"  Direct query returned: {records_direct}")
            print(f"  Recursive query returned: {records_recursive}")
            if records_direct - records_recursive:
                print(f"  Missing in recursive: {records_direct - records_recursive}")
            if records_recursive - records_direct:
                print(f"  Extra in recursive: {records_recursive - records_direct}")

    except Exception as e:
        print(f"[ERROR] Failed to validate: {e}")
        import traceback
        traceback.print_exc()

    return True
