
include("grammar-utils.fan")

from struct import pack



<start> ::= <ClientA:query_recursive_server> <request_forwarding><response_forwarding><ServerA:recusrive_server_response>
<request_forwarding> ::= <ServerA:MimServer:intercept_upstream_request><MimClient:ServerB:forward_upstream_request>
<response_forwarding> ::= <ServerB:MimClient:response_chased><MimServer:ServerA:forward_response_chased>


<query_recursive_server> ::= <header><dns_question>

# Grammar-side view of every message on the wire — opaque bytes constrained by
# what real dnslib actually sends. Responses and forwarded slots share this.
<intercept_upstream_request>   ::= <dns_message>
<forward_response_chased>   ::= <dns_message>
<response_chased>  ::= <dns_message>
<recusrive_server_response>  ::= <dns_message>
<forward_upstream_request>    ::= <dns_message>
<dns_message>      ::= rb"[\x00-\xff]+"

# DNS header (12 bytes): random ID, standard query, one question, no answers.
<header> ::= <byte>{2} 0 0{4} 0 0 1 0 0 0 0 0{4} <qd_count> 0{16} 0{16} 0{16}
<qd_count> ::= <byte>{2} := pack(">H", 1)

# Question section — differs only in which name-generator supplies the qname.
<dns_question>  ::= <qname><qtype_a> <rr_class_in>

<qname> ::= <qname_1> | <qname_2> | <qname_3> | <qname_4> | <qname_5>
<qname_1> ::= <byte>+ := encode_qname('test.local')
<qname_2> ::= <byte>+ := encode_qname('example.local')
<qname_3> ::= <byte>+ := encode_qname('example2.local')
<qname_4> ::= <byte>+ := encode_qname('example3.local')
<qname_5> ::= <byte>+ := encode_qname('example4.local')

# QTYPE = A (1), QCLASS = IN (1). Only these are exercised in this MR.
<qtype_a>      ::= 0{15} 1
<rr_class_in>  ::= 0{15} 1

# Basic types
<bit>              ::= 0 | 1
<byte>             ::= <bit>{8}


where all(bytes(<i>.<forward_upstream_request>) == bytes(<i>.<intercept_upstream_request>) for <i> in *<request_forwarding>)
where all(bytes(<i>.<forward_response_chased>) == bytes(<i>.<response_chased>) for <i> in *<response_forwarding>)

where validateResponses(<response_chased>, <recusrive_server_response>)
where validateUpstreamRequestEqual(<query_recursive_server>, <intercept_upstream_request>)
