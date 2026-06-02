"""
DNS Protocol Grammar for Fandango
Adapted from the reference Fandango DNS implementation.
Uses dnslib server on port 5053.
"""

include ("dns-utils.fan")

from fandango.language.symbols import NonTerminal


# === Verification Functions ===

def verify_transitive(question, response):
    """
    Verify that a DNS response answers the corresponding question.
    Handles transitive responses (CNAME chains).
    """
    type_byte = bytes(question.find_direct_trees(NonTerminal("<q_type>"))[0])
    allowed_names = [bytes(question.find_direct_trees(NonTerminal("<q_name>"))[0])]

    # Collect CNAME targets
    for ans in response.find_all_trees(NonTerminal("<answer_an>")):
        if bytes(ans.children[1])[0:2] == pack('>H', 5) and bytes(ans.find_direct_trees(NonTerminal("<q_name_optional>"))[0]) in allowed_names:
            allowed_names.append(bytes(ans.children[1].children[0].children[4]))

    # Check if any answer matches the question type and name
    for ans in response.find_all_trees(NonTerminal("<answer_an>")):
        if bytes(ans.children[1])[0:2] == type_byte and bytes(ans.find_direct_trees(NonTerminal("<q_name_optional>"))[0]) in allowed_names:
            return True
    return False


# === Grammar Definition ===

<start> ::= <exchange>

# Each exchange consists of a request made by the client and a response from the server
<exchange> ::= <Client:dns_req> <Server:dns_resp>

# Request: header + questions
<dns_req> ::= <header_req> <question>{byte_to_int(<req_qd_count>)}

# Response: header + question section + answer sections
<dns_resp> ::= <header_resp> <question_section> <answer_an_section> <answer_au_section> <answer_opt_section>

<question_section> ::= <question>{byte_to_int(<header_req>.<req_qd_count>)}
<answer_an_section> ::= <answer_an>{byte_to_int(<resp_an_count>)}
<answer_au_section> ::= <answer_au>{byte_to_int(<resp_ns_count>)}
<answer_opt_section> ::= <answer_opt>{byte_to_int(<resp_ar_count>)}


# === DNS Header ===

# Request header:  ID | QR=0 | OPCODE | AA=0 | TC=0 | RD | RA=0 | Z | RCODE | QDCOUNT | ANCOUNT=0 | NSCOUNT=0 | ARCOUNT=0
<header_req> ::= <h_id> 0 <h_opcode_standard> 0 0 <h_rd> 0 0 <bit> 0 <h_rcode_noerror> <req_qd_count> 0{16} 0{16} 0{16}

# Response header: ID | QR=1 | OPCODE | AA | TC=0 | RD | RA | Z | AA | RCODE | QDCOUNT | ANCOUNT | NSCOUNT | ARCOUNT
<header_resp> ::= <h_id> 1 <h_opcode_standard> <bit> 0 <h_rd> <h_ra> 0 <h_aa> 0 (<h_rcode_noerror> | <h_rcode_nxdomain>) <resp_qd_count> <resp_an_count> <resp_ns_count> <resp_ar_count>


# === Header Fields ===

<h_id> ::= <byte><byte>
<h_opcode_standard> ::= 0 0 0 0
<h_rd> ::= 1  # Recursion Desired
<h_aa> ::= <bit>
<h_ra> ::= <bit>

# Response codes
<h_rcode> ::= <h_rcode_noerror> | <h_rcode_formerr> | <h_rcode_servfail> | <h_rcode_nxdomain> | <h_rcode_notimp> | <h_rcode_refused> | <h_rcode_other>
<h_rcode_noerror>  ::= 0 0 0 0  # NOERROR
<h_rcode_formerr>  ::= 0 0 0 1  # FORMERR
<h_rcode_servfail> ::= 0 0 1 0  # SERVFAIL
<h_rcode_nxdomain> ::= 0 0 1 1  # NXDOMAIN
<h_rcode_notimp>   ::= 0 1 0 0  # NOTIMP
<h_rcode_refused>  ::= 0 1 0 1  # REFUSED
<h_rcode_other> ::= (1 <bit>{3, 3}) | (0 1 1 <bit>)

# Counts
<req_qd_count> ::= <byte>{2} := pack(">H", 1)
<resp_qd_count> ::= <bit>{16} := pack(">H", 1)
<resp_an_count> ::= <bit>{16} := pack(">H", randint(1, 2))
<resp_ns_count> ::= <bit>{16} := pack(">H", randint(0, 2))
<resp_ar_count> ::= <bit>{16} := pack(">H", randint(0, 2))


# === Basic Types ===

<bit> ::= 0 | 1
<byte> ::= <bit>{8}
<label_len_octet> ::= <byte>


# === Question Section ===

<question> ::= <q_name> <q_type> <rr_class>
<q_name_optional> ::= <q_name_written>? 0{8}
<q_name> ::= <q_name_written> 0{8}
<q_name_written> ::= (<label_len_octet> <byte>{byte_to_int(b'\x00' + bytes(<label_len_octet>))})+ := gen_q_name()
<q_type> ::= <type_id_cname> | <type_id_a> | <type_id_ns>
<rr_class> ::= 0{15} 1  # IN (Internet) class


# === Answer Sections ===

<answer_au> ::= <q_name_optional> <type_soa>
<answer_opt> ::= <q_name_optional> (<type_opt>|<type_a>|<type_aaaa>)
<answer_an> ::= <q_name_optional> <answer_an_type>
<answer_an_type> ::= (<type_a> | <type_cname> | <type_ns>)


# === Resource Record Types ===

<a_ttl> ::= 0 <bit>{7} <byte>{3}
<a_rd_length> ::= <byte>{2} := pack(">H", randint(0, 0))
<a_rdata> ::= <byte>

# Type IDs (16-bit)
<type_id_a> ::= 0{15} 1           # A = 1
<type_id_ns> ::= 0{14} 1 0        # NS = 2
<type_id_cname> ::= 0{13} 1 0 1   # CNAME = 5
<type_id_soa> ::= 0{13} 1 1 0     # SOA = 6
<type_id_opt> ::= 0{10} 1 0 1 0 0 1   # OPT = 41
<type_id_aaaa> ::= 0{11} 1 1 1 0 0    # AAAA = 28

# Record types with data
<type_a> ::= <type_id_a> <rr_class> <a_ttl> 0{13} 1 0 0 <ip_address>
<type_aaaa> ::= <type_id_aaaa> <rr_class> <a_ttl> 0{11} 1 0 0 0 0 <ip_address_v6>
<type_ns> ::= <type_id_ns> <rr_class> <a_ttl> <a_rd_length> <a_rdata>{int(unpack('>H', bytes(<a_rd_length>))[0])}
<type_soa> ::= <type_id_soa> <rr_class> <a_ttl> <a_rd_length> <a_rdata>{int(unpack('>H', bytes(<a_rd_length>))[0])}
<type_opt> ::= <type_id_opt> <udp_payload_size> <a_ttl> <a_rd_length> <a_rdata>{int(unpack('>H', bytes(<a_rd_length>))[0])}
<type_cname> ::= <type_id_cname> <rr_class> <a_ttl> <a_rd_length> <q_name>

<ip_address> ::= <byte>{4}
<ip_address_v6> ::= <byte>{16}
<udp_payload_size> ::= <bit>{16}


# === Constraints ===

# Request/Response matching constraints:
# 1. RD flag must match
# 2. Transaction ID must match
# 3. Question in response must match question in request
# 4. Question count must match
where forall <ex> in <start>.<exchange>:
    <ex>.<dns_resp>.<header_resp>.<h_rd> == <ex>.<dns_req>.<header_req>.<h_rd> and \
    <ex>.<dns_resp>.<header_resp>.<h_id> == <ex>.<dns_req>.<header_req>.<h_id> and \
    <ex>.<dns_resp>.<question_section>.<question> == <ex>.<dns_req>.<question> and \
    bytes(<ex>.<dns_resp>.<header_resp>.<resp_qd_count>) == bytes(<ex>.<dns_req>.<header_req>.<req_qd_count>)

# Answer must correspond to question (supports transitive CNAME chains)
where forall <ex> in <start>.<exchange>:
    forall <a> in <ex>.<dns_resp>.<answer_an_section>.<answer_an>:
        exists <q> in <ex>.<dns_req>.<question>:
            verify_transitive(<q>, <ex>.<dns_resp>) or \
            bytes(<a>.<answer_an_type>)[0:2] == bytes(<q>.<q_type>) and \
            bytes(<a>.<q_name_optional>) == bytes(<q>.<q_name>)

# CNAME rdlength must match the q_name length
where forall <t> in <type_cname>:
    bytes(<t>.<a_rd_length>) == pack('>H', len(bytes(<t>.<q_name>)))
