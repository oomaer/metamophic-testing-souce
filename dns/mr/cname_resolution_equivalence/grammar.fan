"""
DNS Metamorphic Relation: CNAME Resolution Equivalence

MR: Querying a CNAME domain for a record type should return the same final records
    as directly querying the target domain for that type.

Example:
  - example.local has CNAME → test.local
  - test.local has A → 192.168.1.1, 192.168.1.2

  Query A: "example.local A" should return:
    - CNAME: example.local → test.local
    - A: test.local → 192.168.1.1, 192.168.1.2

  Query B: "test.local A" should return:
    - A: test.local → 192.168.1.1, 192.168.1.2

  Relation: The A records in both responses should be identical.

//wildcard entry point: any domain with a CNAME pointing to another domain, and the target domain having A/AAAA/TXT records

This tests:
- CNAME chain following
- Transitive resolution
- Correct target record retrieval
"""

include("grammar-utils.fan")

from struct import pack


# === Grammar Definition ===

<start> ::= <Interaction1> <ChangeConnection> <Interaction2>

# Interaction 1: Query CNAME domain on Server A
<Interaction1> ::= <ClientA:query_cname><ServerA:response_cname>

# Switch connections
<ChangeConnection> ::= r".*" := changeConnection()

# Interaction 2: Query target domain on Server B
<Interaction2> ::= <ClientB:query_target><ServerB:response_target>


# === DNS Queries ===

<query_cname> ::= <header_req_cname> <question_cname>
<query_target> ::= <header_req_target> <question_target>

# Headers
<header_req_cname> ::= <h_id_cname> 0 <h_opcode_standard> 0 0 1 0 0 0 0 <h_rcode_noerror> <qd_count> 0{16} 0{16} 0{16}
<header_req_target> ::= <h_id_target> 0 <h_opcode_standard> 0 0 1 0 0 0 0 <h_rcode_noerror> <qd_count> 0{16} 0{16} 0{16}

<h_id_cname> ::= <byte><byte>
<h_id_target> ::= <byte><byte>
<h_opcode_standard> ::= 0 0 0 0
<h_rcode_noerror> ::= 0 0 0 0
<qd_count> ::= <byte>{2} := pack(">H", 1)

# Questions - both use <q_type> which will be constrained to match
<question_cname> ::= <q_name_cname> <q_type_cname> <rr_class>
<question_target> ::= <q_name_target> <q_type_target> <rr_class>

<q_name_cname> ::= <q_name_written_cname> 0{8}
<q_name_target> ::= <q_name_written_target> 0{8}

<q_name_written_cname> ::= (<label_len_octet> <byte>{byte_to_int(b'\x00' + bytes(<label_len_octet>))})+ := gen_cname_domain()
<q_name_written_target> ::= (<label_len_octet> <byte>{byte_to_int(b'\x00' + bytes(<label_len_octet>))})+ := gen_target_domain()

# Query types - creates k-path variations for multiple test cases
<q_type_cname> ::= <q_type_a> | <q_type_aaaa> | <q_type_txt>
<q_type_target> ::= <q_type_a> | <q_type_aaaa> | <q_type_txt>
<q_type_a> ::= 0{15} 1                    # A = 1
<q_type_aaaa> ::= 0{11} 1 1 1 0 0         # AAAA = 28 (0b11100)
<q_type_txt> ::= 0{11} 1 0 0 0 0          # TXT = 16 (0b10000)
<rr_class> ::= 0{15} 1  # IN class


# === DNS Responses (from server) ===
# Use regex to match any binary data (DNS responses are variable length)
<response_cname> ::= r"[\x00-\xff]+"
<response_target> ::= r"[\x00-\xff]+"


# === Basic Types ===

<bit> ::= 0 | 1
<byte> ::= <bit>{8}
<label_len_octet> ::= <byte>


# === Validation Constraint ===

# Ensure both queries use the same type AND validate CNAME resolution
where str(<q_type_cname>) == str(<q_type_target>) and validateCNAMEResolution(<response_cname>, <response_target>)


def validateCNAMEResolution(response_cname_bytes, response_target_bytes):
    """
    Validate CNAME resolution equivalence.

    The records returned for the CNAME query should match
    the records returned for the direct target query (for any query type: A, AAAA, TXT).
    """
    try:
        # Import dnslib here (already in path from grammar-utils.fan)
        from dnslib import DNSRecord, QTYPE, RCODE

        # Parse responses
        resp_cname = DNSRecord.parse(bytes(response_cname_bytes))
        resp_target = DNSRecord.parse(bytes(response_target_bytes))

        # Get response codes
        rcode_cname = RCODE[resp_cname.header.rcode]
        rcode_target = RCODE[resp_target.header.rcode]

        # Get query type from target response (same for both)
        qtype = resp_target.q.qtype
        qtype_name = QTYPE[qtype]

        print(f"[DEBUG] Query type: {qtype_name}")
        print(f"[DEBUG] CNAME query RCODE: {rcode_cname}")
        print(f"[DEBUG] Target query RCODE: {rcode_target}")

        # Both should succeed
        if rcode_cname != 'NOERROR' or rcode_target != 'NOERROR':
            print(f"[VIOLATION] Non-NOERROR response: CNAME={rcode_cname}, Target={rcode_target}")
            return True  # Continue execution

        # Extract records of the queried type from CNAME response (skip CNAME records themselves)
        records_cname = set()
        for rr in resp_cname.rr:
            if rr.rtype == qtype:
                records_cname.add(str(rr.rdata))
                print(f"[DEBUG] CNAME response {qtype_name} record: {rr.rdata}")

        # Extract records from direct target response
        records_target = set()
        for rr in resp_target.rr:
            if rr.rtype == qtype:
                records_target.add(str(rr.rdata))
                print(f"[DEBUG] Target response {qtype_name} record: {rr.rdata}")

        # Compare records
        if records_cname == records_target:
            print(f"[PASS] CNAME resolution equivalence holds for {qtype_name}: {records_cname}")
        else:
            print(f"[VIOLATION] {qtype_name} records differ!")
            print(f"  CNAME query returned: {records_cname}")
            print(f"  Target query returned: {records_target}")
            if records_cname - records_target:
                print(f"  Extra in CNAME: {records_cname - records_target}")
            if records_target - records_cname:
                print(f"  Missing in CNAME: {records_target - records_cname}")

    except Exception as e:
        print(f"[ERROR] Failed to validate: {e}")
        import traceback
        traceback.print_exc()

    return True  # Always return True to continue
