
include("grammar-utils.fan")

from struct import pack


<start> ::= <ClientA:query_direct><request_forwarding><AuthoritativeServer:auth_response><MimClient:receive_response> 

<request_forwarding> ::= <MimServer:upstream_query> <MimClient:forward_query>
# DNS message patterns
<upstream_query> ::= <dns_message>
<forward_query> ::= <dns_message>
<auth_response> ::= <dns_message>
<receive_response> ::= <dns_message>
<forward_response> ::= <dns_message>
<final_response> ::= <dns_message>
<dns_message> ::= r"[\x00-\xff]+"



<query_direct> ::= <header_req_direct> <question_direct>

# Header
<header_req_direct> ::= <h_id_direct> 0 <h_opcode_standard> 0 0 1 0 0 0 0 <h_rcode_noerror> <qd_count> 0{16} 0{16} 0{16}

<h_id_direct> ::= <byte><byte>
<h_opcode_standard> ::= 0 0 0 0
<h_rcode_noerror> ::= 0 0 0 0
<qd_count> ::= <byte>{2} := pack(">H", 1)

# Question
<question_direct> ::= <q_name_direct> <q_type_direct> <rr_class>

<q_name_direct> ::= <q_name_written_direct> 0{8}
<q_name_written_direct> ::= (<label_len_octet> <byte>{byte_to_int(b'\x00' + bytes(<label_len_octet>))})+ := gen_cname_domain()

# Query types
<q_type_direct> ::= <q_type_a>
<q_type_a> ::= 0{15} 1                    # A = 1
<q_type_aaaa> ::= 0{11} 1 1 1 0 0         # AAAA = 28
<q_type_txt> ::= 0{11} 1 0 0 0 0          # TXT = 16
<rr_class> ::= 0{15} 1  # IN class


# === Basic Types ===

<bit> ::= 0 | 1
<byte> ::= <bit>{8}
<label_len_octet> ::= <byte>


where all(bytes(<i>.<upstream_query>) == bytes(<i>.<forward_query>) for <i> in *<request_forwarding>)