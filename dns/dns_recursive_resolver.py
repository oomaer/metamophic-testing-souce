#!/usr/bin/env python3
"""
DNS Recursive Resolver using dnslib.proxy.ProxyResolver for metamorphic testing.

This is the "system under test" recursive resolver: it holds no zone data of
its own. Every incoming query is decoded, re-encoded, and forwarded to an
upstream DNS server (typically an authoritative server like dns_server.py).
The upstream reply is parsed and returned to the client.

It is the sibling of dns_server.py:

    dns_server.py             -- authoritative (ZoneResolver over a zone file)
    dns_recursive_resolver.py -- recursive    (ProxyResolver forwarding upstream)

Because dnslib's ProxyResolver decodes and re-encodes packets end-to-end (see
dnslib/dnslib/proxy.py), it behaves like a real recursive resolver rather than
a byte-transparent proxy. That's what we want for mutation testing: mutants
planted in this file (cache handling, CNAME chasing, upstream selection, etc.)
will show up as observable behavioural differences.

Usage:
    python dns_recursive_resolver.py -p 5055 -u 127.0.0.1:5053
    python dns_recursive_resolver.py -p 5055 -u 127.0.0.1:5053 -o 3
"""

import sys
import os
import time
import argparse

from dnslib.server import DNSServer, DNSLogger
from dnslib.proxy import ProxyResolver


def start_server(listen_addr="127.0.0.1", listen_port=5055,
                 upstream_host="127.0.0.1", upstream_port=5054,
                 timeout=10):
    """Start a dnslib ProxyResolver-backed recursive DNS server.

    Every query received on (listen_addr, listen_port) is forwarded to
    (upstream_host, upstream_port). Returns (server, resolver) so callers
    can inspect or stop them.
    """
    resolver = ProxyResolver(upstream_host, upstream_port, timeout=timeout)
    logger = DNSLogger(prefix=True)

    print(f"Starting DNS Recursive Resolver on {listen_addr}:{listen_port} (UDP)")
    print(f"  Upstream: {upstream_host}:{upstream_port} (timeout={timeout}s)")
    print()

    server = DNSServer(resolver, port=listen_port, address=listen_addr,
                       logger=logger)
    server.start_thread()
    return server, resolver


def _parse_upstream(spec: str) -> tuple[str, int]:
    """Parse a "host:port" upstream spec. Port defaults to 53 if omitted."""
    host, _, port = spec.partition(':')
    if not host:
        raise ValueError(f"Invalid upstream {spec!r}: missing host")
    return host, int(port) if port else 53


def main():
    parser = argparse.ArgumentParser(
        description="DNS Recursive Resolver for Metamorphic Testing"
    )
    parser.add_argument("-p", "--port", type=int, default=5055,
                        help="Local listen port (default: 5055)")
    parser.add_argument("-a", "--address", default="127.0.0.1",
                        help="Local listen address (default: 127.0.0.1)")
    parser.add_argument("-u", "--upstream", default="127.0.0.1:5054",
                        metavar="<host:port>",
                        help="Upstream DNS server (default: 127.0.0.1:5054)")
    parser.add_argument("-o", "--timeout", type=float, default=10,
                        help="Upstream query timeout in seconds (default: 50)")
    args = parser.parse_args()

    upstream_host, upstream_port = _parse_upstream(args.upstream)

    server, _ = start_server(args.address, args.port,
                             upstream_host, upstream_port,
                             args.timeout)

    print("Recursive resolver running. Press Ctrl+C to stop.")
    print(f"Test with: dig @{args.address} -p {args.port} test.local A")
    print()

    try:
        while server.isAlive():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.stop()


if __name__ == '__main__':
    main()
