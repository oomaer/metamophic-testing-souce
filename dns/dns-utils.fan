"""
DNS Utilities for Fandango - Compression/Decompression and NetworkParty definitions.
Adapted from the reference Fandango DNS implementation.
"""

from struct import unpack, pack
from random import randint

# Configuration
DNS_PORT = 5053
DNS_HOST = "127.0.0.1"


# === Utility Functions ===

def byte_to_int(byte_val):
    """Convert a 2-byte byte array to an integer."""
    return int(unpack('>H', bytes(byte_val))[0])


def gen_q_name():
    """
    Generate DNS name encoding for test domains.
    Uses domains configured in our dnslib server.
    """
    result = b''
    # Use domains from our test server
    domains = ['test.local', 'example.local']
    domain_name = domains[randint(0, len(domains) - 1)]

    domain_parts = domain_name.split('.')
    for part in domain_parts:
        result += len(part).to_bytes(1, 'big')
        result += part.encode('iso8859-1')

    return result


# === DNS Name Compression/Decompression ===

def msg_suffix(name):
    """
    Get list of tuples with offset and suffix for DNS name compression.
    Example: msg_suffix(b'\x04test\x05local\x00') returns offsets for each label.
    """
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
    """
    Compress a single name in a DNS message.
    """
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
    """
    Compress a full DNS message applying DNS name compression.
    """
    qd_count = byte_to_int(uncompressed[4:6])
    an_count = byte_to_int(uncompressed[6:8])
    ns_count = byte_to_int(uncompressed[8:10])
    ar_count = byte_to_int(uncompressed[10:12])
    compressed = uncompressed[0:12]
    curr_idx = 12

    suffix_dict = dict()
    len_reduction = 0

    # Compress questions
    for i in range(qd_count):
        name, decompressed_len, len_reduction = compress_name(uncompressed, curr_idx, len_reduction, suffix_dict)
        compressed = compressed + name
        curr_idx += decompressed_len
        compressed += uncompressed[curr_idx:curr_idx+4]
        curr_idx += 4

    # Compress resource records
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
    """
    Decompress a DNS name at the given index.
    """
    segment_len = compressed[name_idx]
    compressed_len = 0
    decompressed = b''

    while segment_len != 0:
        # Check for compression pointer (first two bits are 1)
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
    """
    Decompress a full DNS message.
    """
    count_header = compressed[4:12]
    qd_count = byte_to_int(count_header[:2])
    an_count = byte_to_int(count_header[2:4])
    ns_count = byte_to_int(count_header[4:6])
    ar_count = byte_to_int(count_header[6:8])
    decompressed = compressed[0:12]
    curr_idx = 12

    # Decompress questions
    for i in range(qd_count):
        name, compressed_len = decompress_name(compressed, curr_idx)
        decompressed = decompressed + name
        curr_idx += compressed_len
        decompressed += compressed[curr_idx:curr_idx+4]
        curr_idx += 4

    # Decompress resource records
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


# === Network Party Classes ===

class NetworkParty(NetworkParty):
    """
    Override NetworkParty to handle DNS compression.
    All sent messages are compressed, all received messages are decompressed.
    """
    def receive(self, message: str | bytes, sender: Optional[str]) -> None:
        super().receive(decompress_msg(message), sender)

    def send(self, message: str | bytes, recipient: Optional[str]) -> None:
        if isinstance(message, DerivationTree):
            message = message.to_bytes(encoding="utf-8")
        super().send(compress_msg(message), recipient)


class Client(NetworkParty):
    """DNS Client - sends queries to DNS server."""
    def __init__(self):
        super().__init__(
            connection_mode=ConnectionMode.CONNECT,
            uri=f"udp://{DNS_HOST}:{DNS_PORT}"
        )
        self.start()


class Server(NetworkParty):
    """DNS Server - external dnslib server."""
    def __init__(self):
        super().__init__(
            connection_mode=ConnectionMode.EXTERNAL,
            uri=f"udp://{DNS_HOST}:{DNS_PORT}"
        )
        self.start()
