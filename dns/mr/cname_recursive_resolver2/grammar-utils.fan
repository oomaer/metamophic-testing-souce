
import sys
import os

# Add dnslib path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'dnslib'))

from struct import pack, unpack
from random import randint

# DNS Configuration
DNS_HOST = "127.0.0.1"
DNS_PORT_TARGET = 5053  # ServerA - authoritative for test.local. (target zone)
DNS_PORT_ALIAS = 5055   # ServerB - authoritative for example.local. (alias zone)
DNS_PORT_RECURSIVE = 5054  # ServerA - Recursive resolver (test subject)
# Hardcoded target the chase resolves to. Used as a fallback if we can't
# parse a CNAME target out of ServerB's response.
TARGET_DOMAIN = 'test.local'


# === Utility Functions ===

def byte_to_int(byte_val):
    """Convert 2-byte value to integer."""
    return int(unpack('>H', bytes(byte_val))[0])


def encode_qname(domain: str) -> bytes:
    """Encode a dotted name into DNS wire label format, terminated with \\x00."""
    out = b''
    for part in domain.split('.'):
        if not part:
            continue
        out += bytes([len(part)]) + part.encode('iso8859-1')
    return out + b'\x00'


def gen_cname_domain():
    """Generate the alias qname in DNS wire format: example.local -> \\x07example\\x05local\\x00."""
    return encode_qname('example.local')


def gen_target_domain():
    """Generate the target qname in DNS wire format: test.local -> \\x04test\\x05local\\x00."""
    return encode_qname(TARGET_DOMAIN)


def changeConnection():
    """Legacy hook — not used in Architecture 1 (each client owns one connection)."""
    print(f"[CONNECTION] changeConnection called (no-op in Architecture 1)")
    return "Connection change"


# === Query construction from a forwarded CNAME response ===

def extract_cname_target(response_bytes: bytes) -> bytes:
    """
    Walk a DNS response and return the CNAME target name (wire-encoded, ending
    with 0x00) from the first CNAME record found in the answer section. Returns
    None if no CNAME is present.

    Layout after the 12-byte header:
        for each question: qname + qtype(2) + qclass(2)
        for each answer:   name + type(2) + class(2) + ttl(4) + rdlen(2) + rdata(rdlen)
    Type CNAME = 5; rdata IS the wire-encoded target name (may use compression).
    """
    if len(response_bytes) < 12:
        return None
    qd_count = byte_to_int(response_bytes[4:6])
    an_count = byte_to_int(response_bytes[6:8])
    idx = 12

    for _ in range(qd_count):
        idx = _skip_name(response_bytes, idx)
        idx += 4  # qtype + qclass

    for _ in range(an_count):
        idx = _skip_name(response_bytes, idx)
        rr_type = byte_to_int(response_bytes[idx:idx+2])
        idx += 2
        idx += 2 + 4  # class + ttl
        rdlen = byte_to_int(response_bytes[idx:idx+2])
        idx += 2
        if rr_type == 5:  # CNAME
            # rdata is a wire-encoded name; return exactly rdlen bytes.
            return response_bytes[idx:idx+rdlen]
        idx += rdlen
    return None


def build_query_from_cname_response(response_bytes: bytes) -> bytes:
    """
    Given ServerB's response to ClientB's alias query (which contains a CNAME
    answer), build a fresh A-record query for the CNAME target.

    ClientC uses this to turn a *forwarded response* into a *valid query* for
    ServerA. This is the on-the-wire CNAME chase: the grammar's forwarding
    constraint plumbs response bytes into ClientC's send slot; ClientC
    materialises them into a real DNS query pointed at the chased name.
    """
    target = extract_cname_target(response_bytes)
    if target is None:
        # Fallback for malformed / empty responses so we still emit *something*
        # rather than hang. This should not fire in the happy path.
        target = encode_qname(TARGET_DOMAIN)

    # Fresh 12-byte header: standard A/IN query, 1 question, no answers.
    # ID is copied from the response (helps correlate logs) but harmless if not.
    txn_id = response_bytes[0:2] if len(response_bytes) >= 2 else b'\x12\x34'
    flags = b'\x01\x00'   # standard query, RD=1
    header = txn_id + flags + b'\x00\x01' + b'\x00\x00' + b'\x00\x00' + b'\x00\x00'

    question = target + b'\x00\x01' + b'\x00\x01'  # qtype A, qclass IN
    return header + question


# === A-record extraction and MR check ===

def extract_a_records(response_bytes: bytes) -> list:
    """
    Walk a decompressed DNS response and return the list of A-record rdata
    as dotted-quad strings, in the order they appear across the answer,
    authority, and additional sections. Non-A records are skipped.

    Why all three sections: dnslib's ZoneResolver, when serving a CNAME
    whose target is in the same zone, puts the CNAME in the *answer*
    section and the target's A records in the *additional* section (glue).
    A client — and this MR — should treat those glue A records as the
    real answer for the alias query.

    Response layout after the 12-byte header:
        for each question:  qname + qtype(2) + qclass(2)
        for each RR (an/ns/ar):
            name + type(2) + class(2) + ttl(4) + rdlen(2) + rdata(rdlen)

    Type A = 1; A rdata is 4 raw bytes (an IPv4 address).
    """
    if len(response_bytes) < 12:
        return []
    qd_count = byte_to_int(response_bytes[4:6])
    an_count = byte_to_int(response_bytes[6:8])
    ns_count = byte_to_int(response_bytes[8:10])
    ar_count = byte_to_int(response_bytes[10:12])
    idx = 12

    # Skip questions
    for _ in range(qd_count):
        idx = _skip_name(response_bytes, idx)
        idx += 4  # qtype + qclass

    a_records = []
    for _ in range(an_count + ns_count + ar_count):
        idx = _skip_name(response_bytes, idx)
        rr_type = byte_to_int(response_bytes[idx:idx+2])
        idx += 2
        idx += 2  # class
        idx += 4  # ttl
        rdlen = byte_to_int(response_bytes[idx:idx+2])
        idx += 2
        if rr_type == 1 and rdlen == 4:  # A record
            ip = '.'.join(str(b) for b in response_bytes[idx:idx+4])
            a_records.append(ip)
        idx += rdlen
    return a_records


def _skip_name(buf: bytes, idx: int) -> int:
    """Advance past a DNS name (labels or compression pointer). Returns new index."""
    while idx < len(buf):
        length = buf[idx]
        if length == 0:
            return idx + 1
        if (length & 0xC0) == 0xC0:
            return idx + 2  # compression pointer, 2 bytes
        idx += length + 1
    return idx


def extract_question(query_bytes: bytes) -> tuple:
    """
    Parse the question section of a DNS query and return (qname, qtype, qclass).

    qname is returned as the wire-encoded label sequence terminated by 0x00
    (compression pointers are followed if present). qtype and qclass are
    returned as ints. Returns (None, None, None) for malformed / too-short
    inputs so callers can distinguish "no question" from "empty match".

    Layout after the 12-byte header:
        qname (variable, terminated by 0x00 or compression pointer)
        qtype  (2 bytes)
        qclass (2 bytes)
    """
    if len(query_bytes) < 12:
        return (None, None, None)

    qd_count = byte_to_int(query_bytes[4:6])
    if qd_count < 1:
        return (None, None, None)

    # Decompress the qname so the comparison is compression-agnostic — the
    # client and the resolver may (re-)serialise the same name differently.
    qname, _ = decompress_name(query_bytes, 12)
    idx = _skip_name(query_bytes, 12)

    if idx + 4 > len(query_bytes):
        return (qname, None, None)

    qtype = byte_to_int(query_bytes[idx:idx+2])
    qclass = byte_to_int(query_bytes[idx+2:idx+4])
    return (qname, qtype, qclass)


def validateUpstreamRequestEqual(query_client, query_upstream):
    """
    Metamorphic relation:
        The question the client sent to the recursive resolver
            ==
        The question the recursive resolver forwarded upstream.

    A forwarding recursive resolver must not rewrite the client's question
    when it forwards the query upstream. Transaction ID and flags are allowed
    to differ (the resolver may re-mint an ID and set/clear RD, RA, etc.);
    only the (qname, qtype, qclass) triple in the question section is
    compared.

    query_client   — bytes ClientA sent to the recursive resolver
    query_upstream — bytes the recursive resolver forwarded (intercepted
                     by MimServer on its way to ServerB)

    Always returns True so Fandango keeps generating; mismatches are surfaced
    via [VIOLATION] prints and picked up by script.py.
    """
    qname_c, qtype_c, qclass_c = extract_question(bytes(query_client))
    qname_u, qtype_u, qclass_u = extract_question(bytes(query_upstream))

    print(f"[DEBUG] client   question: qname={qname_c!r} qtype={qtype_c} qclass={qclass_c}")
    print(f"[DEBUG] upstream question: qname={qname_u!r} qtype={qtype_u} qclass={qclass_u}")

    if qname_c is None or qname_u is None:
        print(f"[VIOLATION] Upstream-request equality: one side has no parseable question")
        print(f"  client   bytes: {bytes(query_client)!r}")
        print(f"  upstream bytes: {bytes(query_upstream)!r}")
        return True

    if (qname_c, qtype_c, qclass_c) == (qname_u, qtype_u, qclass_u):
        print(f"[PASS] Upstream-request equality: question preserved on forward")
    else:
        print(f"[VIOLATION] Upstream-request equality: resolver rewrote the question")
        print(f"  client   : qname={qname_c!r} qtype={qtype_c} qclass={qclass_c}")
        print(f"  upstream : qname={qname_u!r} qtype={qtype_u} qclass={qclass_u}")

    return True


def validateResponses(response_chased, response_direct):
    """
    Metamorphic relation:
        A-records via CNAME chase == A-records via direct query.

    response_chased  — what ServerA returned to ClientC (chased via CNAME)
    response_direct  — what ServerA returned to ClientA (direct baseline)

    Both must yield the same set of A-record IPs. Returns True always so
    Fandango keeps generating; violations are surfaced via [VIOLATION] prints.
    """
    a_chased = sorted(extract_a_records(bytes(response_chased)))
    a_direct = sorted(extract_a_records(bytes(response_direct)))

    print(f"[DEBUG] chased  A-records: {a_chased}")
    print(f"[DEBUG] direct  A-records: {a_direct}")

    if a_chased and a_chased == a_direct:
        print(f"[PASS] CNAME equivalence: A records match {a_chased}")
    elif not a_chased and not a_direct:
        print(f"[VIOLATION] Both responses have no A records — chase and direct query both failed")
    else:
        print(f"[VIOLATION] CNAME equivalence broken")
        print(f"  Via chase  (ClientC → ServerA): {a_chased}")
        print(f"  Direct     (ClientA → ServerA): {a_direct}")

    return True


# === DNS Compression Functions ===

def msg_suffix(name):
    """Get DNS name suffixes for compression."""
    suffixes = []
    len_idx = 0
    prefix_len = name[len_idx]
    while prefix_len != 0:
        suffixes.append((len_idx, name[len_idx:]))
        len_idx = len_idx + prefix_len + 1
        prefix_len = name[len_idx]
    return suffixes


def compress_name(uncompressed: bytes, curr_idx: int,
                  len_reduction: int, suffix_dict: dict) -> tuple:
    """Compress a single DNS name."""
    name_len = 0
    while uncompressed[curr_idx + name_len] != 0:
        name_len += uncompressed[curr_idx + name_len] + 1
    name_len += 1
    b_name = uncompressed[curr_idx:(curr_idx+name_len)]

    if name_len == 1:
        return b_name, name_len, len_reduction

    for n_offset, suffix in msg_suffix(b_name):
        if suffix in suffix_dict:
            cpr_ptr = suffix_dict[suffix]
            bin_ptr = pack('>H', (192 << 8) | cpr_ptr)
            new_name = b_name[:n_offset] + bin_ptr
            len_reduction += len(b_name) - len(new_name)
            return new_name, name_len, len_reduction
        else:
            offset_name_start = curr_idx
            suffix_dict[suffix] = offset_name_start + n_offset - len_reduction
            return b_name, name_len, len_reduction


def compress_msg(uncompressed: bytes) -> bytes:
    """Compress full DNS message."""
    qd_count = byte_to_int(uncompressed[4:6])
    an_count = byte_to_int(uncompressed[6:8])
    ns_count = byte_to_int(uncompressed[8:10])
    ar_count = byte_to_int(uncompressed[10:12])
    compressed = uncompressed[0:12]
    curr_idx = 12

    suffix_dict = dict()
    len_reduction = 0

    for i in range(qd_count):
        name, decompressed_len, len_reduction = compress_name(uncompressed, curr_idx, len_reduction, suffix_dict)
        compressed = compressed + name
        curr_idx += decompressed_len
        compressed += uncompressed[curr_idx:curr_idx+4]
        curr_idx += 4

    for i in range(an_count + ns_count + ar_count):
        name, decompressed_len, len_reduction = compress_name(uncompressed, curr_idx, len_reduction, suffix_dict)
        compressed = compressed + name
        curr_idx += decompressed_len
        rr_type = uncompressed[curr_idx:curr_idx+2]
        compressed += rr_type
        rr_type = byte_to_int(rr_type)
        curr_idx += 2
        compressed += uncompressed[curr_idx:curr_idx+6]
        curr_idx += 6
        r_data_len = byte_to_int(uncompressed[curr_idx:curr_idx+2])
        curr_idx += 2

        if rr_type == 5:  # CNAME
            name, decompressed_len, len_reduction = compress_name(uncompressed, curr_idx, len_reduction, suffix_dict)
            compressed += pack('>H', len(name))
            compressed = compressed + name
            curr_idx += decompressed_len
        else:
            compressed += uncompressed[curr_idx-2:curr_idx]
            compressed += uncompressed[curr_idx:curr_idx+r_data_len]
            curr_idx += r_data_len

    return compressed


def decompress_name(compressed: bytes, name_idx: int) -> tuple:
    """Decompress DNS name."""
    segment_len = compressed[name_idx]
    compressed_len = 0
    decompressed = b''

    while segment_len != 0:
        if (segment_len & 192) == 192:
            name_ptr = (segment_len & 63) << 8
            name_ptr += compressed[name_idx+1]
            decompressed = decompressed + decompress_name(compressed, name_ptr)[0]
            return decompressed, compressed_len + 2

        decompressed = decompressed + bytes([segment_len])
        decompressed = decompressed + compressed[name_idx + 1 : name_idx + 1 + segment_len]
        compressed_len = compressed_len + segment_len + 1
        name_idx = name_idx + segment_len + 1
        segment_len = compressed[name_idx]

    decompressed = decompressed + bytes([0])
    return decompressed, compressed_len + 1


def decompress_msg(compressed: bytes) -> bytes:
    """Decompress full DNS message."""
    count_header = compressed[4:12]
    qd_count = byte_to_int(count_header[:2])
    an_count = byte_to_int(count_header[2:4])
    ns_count = byte_to_int(count_header[4:6])
    ar_count = byte_to_int(count_header[6:8])
    decompressed = compressed[0:12]
    curr_idx = 12

    for i in range(qd_count):
        name, compressed_len = decompress_name(compressed, curr_idx)
        decompressed = decompressed + name
        curr_idx += compressed_len
        decompressed += compressed[curr_idx:curr_idx+4]
        curr_idx += 4

    for i in range(an_count + ns_count + ar_count):
        name, compressed_len = decompress_name(compressed, curr_idx)
        decompressed = decompressed + name
        curr_idx += compressed_len
        rr_type = compressed[curr_idx:curr_idx+2]
        decompressed += rr_type
        rr_type = byte_to_int(rr_type)
        curr_idx += 2
        decompressed += compressed[curr_idx:curr_idx+6]
        curr_idx += 6
        r_data_len = byte_to_int(compressed[curr_idx:curr_idx+2])
        curr_idx += 2

        if rr_type == 5:  # CNAME
            c_name, compressed_len = decompress_name(compressed, curr_idx)
            decompressed += pack('>H', len(c_name))
            decompressed += c_name
            curr_idx += compressed_len
        else:
            decompressed += compressed[curr_idx-2:curr_idx]
            decompressed += compressed[curr_idx:curr_idx+r_data_len]
            curr_idx += r_data_len

    return decompressed

def startMimServer():
    """Start the MITM server and client."""
    mim_server = MimServer.instance()
    # mim_server.start()
    return "started"


class ClientA(NetworkParty):
    def __init__(self):
        self.serverName = "ServerA"
        super().__init__(
            connection_mode=ConnectionMode.CONNECT,
            uri=f"udp://{DNS_HOST}:{DNS_PORT_ALIAS}"
        )
        self.start()

    def receive(self, message: str | bytes, sender: Optional[str]) -> None:
        super().receive(decompress_msg(message), self.serverName)

    def send(self, message: str | bytes, recipient: Optional[str]) -> None:
        if isinstance(message, DerivationTree):
            message = message.to_bytes(encoding="utf-8")
        super().send(compress_msg(message), recipient)


class ServerA(NetworkParty):
    def __init__(self):
        super().__init__(
            connection_mode=ConnectionMode.EXTERNAL,
            uri=f"udp://{DNS_HOST}:{DNS_PORT_ALIAS}"
        )
        self.start()

    def receive(self, message: str | bytes, sender: Optional[str]) -> None:
        super().receive(decompress_msg(message), "ClientB")

    def send(self, message: str | bytes, recipient: Optional[str]) -> None:
        if isinstance(message, DerivationTree):
            message = message.to_bytes(encoding="utf-8")
        super().send(compress_msg(message), recipient)


class ServerB(NetworkParty):
    def __init__(self):
        super().__init__(
            connection_mode=ConnectionMode.EXTERNAL,
            uri=f"udp://{DNS_HOST}:{DNS_PORT_TARGET}"
        )
        self.start()

    def receive(self, message: str | bytes, sender: Optional[str]) -> None:
        super().receive(decompress_msg(message), "ClientB")

    def send(self, message: str | bytes, recipient: Optional[str]) -> None:
        if isinstance(message, DerivationTree):
            message = message.to_bytes(encoding="utf-8")
        super().send(compress_msg(message), recipient)



class MimServer(NetworkParty):
    """MITM Server - intercepts upstream queries from ServerA (recursive resolver)."""
    def __init__(self):
        super().__init__(
            connection_mode=ConnectionMode.OPEN,
            uri=f"udp://{DNS_HOST}:{DNS_PORT_RECURSIVE}"
        )
        self.start()

    def receive(self, message: str | bytes, sender: Optional[str]) -> None:
        print("reciveing", sender, bytes(message))
        super().receive(decompress_msg(message), 'ServerA')

    def send(self, message: str | bytes, recipient: Optional[str]) -> None:
        print("sendingggggg", recipient, bytes(message))
        if isinstance(message, DerivationTree):
            message = message.to_bytes(encoding="utf-8")
        super().send(compress_msg(message), "ServerA")


class MimClient(NetworkParty):
    """MITM Client - forwards requests to Target Server."""
    def __init__(self):
        super().__init__(
            connection_mode=ConnectionMode.CONNECT,
            uri=f"udp://{DNS_HOST}:{DNS_PORT_TARGET}"
        )
        self.start()

    def receive(self, message: str | bytes, sender: Optional[str]) -> None:
        super().receive(decompress_msg(message), "ServerB")

    def send(self, message: str | bytes, recipient: Optional[str]) -> None:
        if isinstance(message, DerivationTree):
            message = message.to_bytes(encoding="utf-8")
        super().send(compress_msg(message), recipient)

