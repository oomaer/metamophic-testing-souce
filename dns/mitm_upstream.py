#!/usr/bin/env python3
"""
Tiny UDP DNS MITM for observing the recursive resolver's upstream traffic.

Sits between the recursive resolver and the authoritative server:

    dig ──> resolver (5055) ──> [ THIS MITM (5054) ] ──> authoritative (5053)
                                          │                          │
                                          └─── reply ────────────────┘

Every packet in both directions is timestamped and logged with a monotonic
delta from the first packet of that flow, so you can see whether the
resolver sends upstream immediately or after a delay.

Usage:
    python dns/mitm_upstream.py                       # listen 5054, upstream 5053
    python dns/mitm_upstream.py -p 5054 -u 127.0.0.1:5053

No dnslib dependency — pure stdlib UDP. Parses just enough of the DNS
header (id, qdcount, first QNAME) to make logs human-readable; if a
packet doesn't decode, it's still forwarded and logged as raw bytes.
"""

import argparse
import socket
import struct
import sys
import threading
import time


def decode_qname(data: bytes, offset: int) -> tuple[str, int]:
    """Decode a QNAME starting at offset. Returns (name, new_offset). Handles no compression."""
    labels = []
    while True:
        if offset >= len(data):
            return ("<truncated>", offset)
        length = data[offset]
        if length == 0:
            return (".".join(labels) + ".", offset + 1)
        if length & 0xC0:  # pointer — don't bother resolving, just stop
            return (".".join(labels) + ".<ptr>", offset + 2)
        offset += 1
        labels.append(data[offset:offset + length].decode("ascii", errors="replace"))
        offset += length


def summarize(pkt: bytes) -> str:
    """Return a short 'id=… qname=… qtype=…' string; falls back on raw len."""
    if len(pkt) < 12:
        return f"raw {len(pkt)}B"
    txid, flags, qd, an, ns, ar = struct.unpack("!HHHHHH", pkt[:12])
    is_response = bool(flags & 0x8000)
    rcode = flags & 0x000F
    try:
        qname, off = decode_qname(pkt, 12)
        qtype = struct.unpack("!H", pkt[off:off + 2])[0] if off + 2 <= len(pkt) else 0
    except Exception:
        qname, qtype = "<parse-err>", 0
    kind = "RESP" if is_response else "QUERY"
    return f"id=0x{txid:04x} {kind} qname={qname} qtype={qtype} an={an} rcode={rcode}"


class MITM:
    def __init__(self, listen_addr, listen_port, upstream_addr, upstream_port):
        self.listen = (listen_addr, listen_port)
        self.upstream = (upstream_addr, upstream_port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(self.listen)
        self.t0 = time.monotonic()
        self.lock = threading.Lock()

    def log(self, direction, peer, pkt):
        dt_ms = (time.monotonic() - self.t0) * 1000.0
        wall = time.strftime("%H:%M:%S")
        with self.lock:
            print(f"[{wall}] +{dt_ms:8.2f}ms  {direction:<20}  {peer[0]}:{peer[1]:<5}  "
                  f"{summarize(pkt)}", flush=True)

    def handle_upstream_reply(self, client_addr, upstream_sock):
        """Wait for one reply on upstream_sock and relay it back to the client."""
        try:
            data, _ = upstream_sock.recvfrom(65535)
        except socket.timeout:
            self.log("<< UPSTREAM TIMEOUT", self.upstream, b"\x00" * 12)
            return
        finally:
            pass
        self.log("<< upstream -> mitm", self.upstream, data)
        self.sock.sendto(data, client_addr)
        self.log(">> mitm -> client  ", client_addr, data)
        upstream_sock.close()

    def serve_forever(self):
        print(f"MITM UDP DNS proxy listening on {self.listen[0]}:{self.listen[1]}", flush=True)
        print(f"  forwarding to {self.upstream[0]}:{self.upstream[1]}", flush=True)
        print(f"  t0 = 0ms established at process start; all deltas are from t0", flush=True)
        print(flush=True)
        while True:
            data, client_addr = self.sock.recvfrom(65535)
            self.log(">> client -> mitm  ", client_addr, data)

            # Forward to upstream on a fresh ephemeral socket so its
            # reply comes back to us on a known socket we can select on.
            up_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            up_sock.settimeout(4.0)
            up_sock.sendto(data, self.upstream)
            self.log(">> mitm -> upstream", self.upstream, data)

            # Handle the reply on a background thread so we can keep
            # accepting new client queries meanwhile.
            t = threading.Thread(target=self.handle_upstream_reply,
                                 args=(client_addr, up_sock), daemon=True)
            t.start()


def _parse_hostport(spec: str, default_port: int) -> tuple[str, int]:
    host, _, port = spec.partition(":")
    if not host:
        raise ValueError(f"missing host in {spec!r}")
    return host, int(port) if port else default_port


def main():
    parser = argparse.ArgumentParser(description="Tiny UDP DNS MITM for observing upstream traffic")
    parser.add_argument("-p", "--port", type=int, default=5054,
                        help="local listen port (default: 5054)")
    parser.add_argument("-a", "--address", default="127.0.0.1",
                        help="local listen address (default: 127.0.0.1)")
    parser.add_argument("-u", "--upstream", default="127.0.0.1:5053",
                        metavar="<host:port>",
                        help="upstream DNS server (default: 127.0.0.1:5053)")
    args = parser.parse_args()

    up_host, up_port = _parse_hostport(args.upstream, 53)
    mitm = MITM(args.address, args.port, up_host, up_port)
    try:
        mitm.serve_forever()
    except KeyboardInterrupt:
        print("\nMITM shutting down.", flush=True)
        sys.exit(0)


if __name__ == "__main__":
    main()
