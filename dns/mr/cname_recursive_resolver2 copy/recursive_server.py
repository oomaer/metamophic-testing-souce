#!/usr/bin/env python3
"""
DNS Recursive Resolver for Metamorphic Testing.

This server acts as a recursive resolver:
- Has local zone knowledge of ONLY the CNAME mapping (example.local -> test.local)
- When queried for example.local A, it:
  1. Adds the CNAME record to the response
  2. Forwards the query for test.local A to the upstream authoritative server
  3. Appends the A records from the upstream response

Usage:
    python recursive_server.py [-p PORT] [-a ADDRESS] [-u UPSTREAM_PORT]
"""

import sys
import os
import time
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', 'dnslib'))

from dnslib import DNSRecord, RR, QTYPE, RCODE, CNAME
from dnslib.server import DNSServer, BaseResolver, DNSLogger


class RecursiveResolver(BaseResolver):
    """
    Recursive DNS resolver that only knows CNAME mappings.
    Forwards target resolution to an upstream authoritative server.
    """

    LOCAL_ZONE = {
        'example.local.': {
            'CNAME': ['test.local.'],
        },
    }

    DEFAULT_TTL = 300

    def __init__(self, upstream_host="127.0.0.1", upstream_port=5053):
        self.upstream_host = upstream_host
        self.upstream_port = upstream_port
        self.query_count = 0

    def resolve(self, request, handler):
        self.query_count += 1
        reply = request.reply()
        qname = str(request.q.qname)
        qtype = QTYPE[request.q.qtype]

        if not qname.endswith('.'):
            qname += '.'

        if qname in self.LOCAL_ZONE:
            zone = self.LOCAL_ZONE[qname]

            if 'CNAME' in zone:
                target = zone['CNAME'][0]

                reply.add_answer(RR(
                    qname,
                    QTYPE.CNAME,
                    rdata=CNAME(target),
                    ttl=self.DEFAULT_TTL
                ))

                # Recursive resolution: query upstream for the target domain
                upstream_query = DNSRecord.question(target, qtype)
                try:
                    upstream_response_bytes = upstream_query.send(
                        self.upstream_host, self.upstream_port, timeout=5
                    )
                    upstream_response = DNSRecord.parse(upstream_response_bytes)

                    for rr in upstream_response.rr:
                        reply.add_answer(rr)
                except Exception as e:
                    print(f"[ERROR] Upstream query failed: {e}")
                    reply.header.rcode = RCODE.SERVFAIL
        else:
            reply.header.rcode = RCODE.NXDOMAIN

        return reply


def start_server(port=5054, address="127.0.0.1", upstream_port=5053):
    resolver = RecursiveResolver(upstream_host=address, upstream_port=upstream_port)
    logger = DNSLogger(prefix=True)

    print(f"Starting Recursive DNS Resolver on {address}:{port} (UDP)")
    print(f"Upstream authoritative server: {address}:{upstream_port}")
    print("Local zone (CNAME only):")
    for domain, records in resolver.LOCAL_ZONE.items():
        print(f"  {domain}")
        for rtype, rdata in records.items():
            print(f"    {rtype}: {rdata}")
    print()

    server = DNSServer(resolver, port=port, address=address, logger=logger)
    server.start_thread()

    return server, resolver


def main():
    parser = argparse.ArgumentParser(description="DNS Recursive Resolver for Metamorphic Testing")
    parser.add_argument("-p", "--port", type=int, default=5054, help="Port (default: 5054)")
    parser.add_argument("-a", "--address", default="127.0.0.1", help="Address (default: 127.0.0.1)")
    parser.add_argument("-u", "--upstream-port", type=int, default=5053, help="Upstream port (default: 5053)")
    args = parser.parse_args()

    server, resolver = start_server(args.port, args.address, args.upstream_port)

    print("Recursive resolver running. Press Ctrl+C to stop.")
    print(f"Test with: dig @{args.address} -p {args.port} example.local A")
    print()

    try:
        while server.isAlive():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.stop()


if __name__ == '__main__':
    main()
