
include("grammar-utils.fan")

from struct import pack


# =============================================================================
# CNAME Resolution Equivalence MR (Architecture 1)
# =============================================================================
#
# Two authoritative servers, three clients (roles):
#
#   ServerA (:5053) — authoritative for test.local.    (target zone)
#                     holds:  test.local.  A  192.168.1.1
#                             test.local.  A  192.168.1.2
#
#   ServerB (:5054) — authoritative for example.local. (alias zone)
#                     holds:  example.local. CNAME test.local.
#
#   ClientA — queries ServerA for A test.local.       → receives A records (direct baseline)
#   ClientB — queries ServerB for A example.local.    → receives CNAME response
#   ClientC — queries ServerA for A <chased target>   → receives A records (chased)
#
#             (grammar forwarding: <ClientC:forward_query> bytes are constrained
#              equal to <ServerB:response_alias> bytes; ClientC.send() extracts
#              the CNAME target from those bytes and builds a fresh A query.)
#
# Metamorphic relation:
#     A-records via ClientC (chased)  ==  A-records via ClientA (direct)
# Both should return {192.168.1.1, 192.168.1.2}.
#
# Constraints:
#   1. bytes(forward_query) == bytes(response_alias)         [forwarding fidelity]
#   2. validateResponses(response_chased, response_direct)   [A-record equivalence]
# =============================================================================


<start> ::=  <ClientA:query_direct_target> <ServerA:response_direct> <alias_query>
<alias_query> ::= <ClientB:query_alias> <request_forwarding> <ServerA:response_chased>
<request_forwarding> ::= <ServerB:response_alias> <ClientC:forward_query>

# ClientA's baseline query and ClientB's alias query share every rule except
# the qname bytes — that is the only piece that legitimately differs between
# the two legs. Everything else (header layout, qtype, qclass) is identical.

<query_direct_target> ::= <header> <question_of_target>
<query_alias>         ::= <header> <question_of_alias>

# Grammar-side view of every message on the wire — opaque bytes constrained by
# what real dnslib actually sends. Responses and forwarded slots share this.
<response_alias>   ::= <dns_message>
<response_chased>  ::= <dns_message>
<response_direct>  ::= <dns_message>
<forward_query>    ::= <dns_message>
<dns_message>      ::= rb"[\x00-\xff]+"

# DNS header (12 bytes): random ID, standard query, one question, no answers.
<header> ::= <byte>{2} 0 0{4} 0 0 1 0 0 0 0 0{4} <qd_count> 0{16} 0{16} 0{16}
<qd_count> ::= <byte>{2} := pack(">H", 1)

# Question section — differs only in which name-generator supplies the qname.
# gen_*_domain() already emits the trailing 0x00 terminator.
<question_of_alias>  ::= <qname_of_alias>  <qtype_a> <rr_class_in>
<question_of_target> ::= <qname_of_target> <qtype_a> <rr_class_in>

<qname_of_alias> ::= <qname_1> | <qname_2> | <qname_3> | <qname_4> | <qname_5>
<qname_1> ::= <byte>+ := encode_qname('example.local')
<qname_2> ::= <byte>+ := encode_qname('www.example.local')
<qname_3> ::= <byte>+ := encode_qname('mail.example.local')
<qname_4> ::= <byte>+ := encode_qname('ftp.example.local')
<qname_5> ::= <byte>+ := encode_qname('api.example.local')
<qname_of_target> ::= <byte>+ := encode_qname('test.local')

# QTYPE = A (1), QCLASS = IN (1). Only these are exercised in this MR.
<qtype_a>      ::= 0{15} 1
<rr_class_in>  ::= 0{15} 1

# Basic types
<bit>              ::= 0 | 1
<byte>             ::= <bit>{8}


# =============================================================================
# Metamorphic constraints
# =============================================================================
# 1. Forwarding fidelity: the bytes ServerB emits as its CNAME response must
#    equal the bytes ClientC emits as its outbound "forwarded" query at the
#    grammar layer. (ClientC.send() then transforms them into a real query for
#    the chased target — see grammar-utils.fan.)
where all(bytes(<i>.<forward_query>) == bytes(<i>.<response_alias>) for <i> in *<request_forwarding>)

# 2. A-record equivalence: chased response A-records must match the direct
#    response A-records. Violations print [VIOLATION]; the function always
#    returns True so Fandango keeps generating.
where validateResponses(<response_chased>, <response_direct>)
