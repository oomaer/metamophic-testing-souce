#!/usr/bin/env python3
"""
DNS Server using dnslib for metamorphic testing.
This server can be mutated for mutation testing.

Usage:
    python dns_server.py [-p PORT] [-a ADDRESS]
"""

import sys
import os
import time
import argparse

# Add dnslib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'dnslib'))

from dnslib import DNSRecord, RR, QTYPE, RCODE, A, AAAA, CNAME, MX, TXT, NS
from dnslib.server import DNSServer, BaseResolver, DNSLogger


class TestResolver(BaseResolver):
    """
    Simple DNS resolver for metamorphic testing.
    Returns predictable responses based on query type and domain.

    Zone data can be mutated for mutation testing.
    """

    # Zone data - can be mutated for mutation testing
    ZONE_DATA = {
        'test.local.': {
            'A': ['192.168.1.1', '192.168.1.2'],
            'AAAA': ['2001:db8::1'],
            'MX': [(10, 'mail.test.local.')],
            'TXT': ['v=spf1 include:test.local ~all'],
            'NS': ['ns1.test.local.', 'ns2.test.local.'],
        },
        'example.local.': {
            'A': ['10.0.0.1'],
            'CNAME': ['test.local.'],
        },
        'ns1.test.local.': {
            'A': ['192.168.1.10'],
        },
        'ns2.test.local.': {
            'A': ['192.168.1.11'],
        },
        'mail.test.local.': {
            'A': ['192.168.1.20'],
        },
    }

    DEFAULT_TTL = 300

    def __init__(self):
        self.query_count = 0

    def resolve(self, request, handler):
        """Resolve DNS query and return response."""
        self.query_count += 1
        reply = request.reply()
        qname = str(request.q.qname)
        qtype = QTYPE[request.q.qtype]

        # Normalize domain name (ensure trailing dot)
        if not qname.endswith('.'):
            qname += '.'

        # Look up in zone data
        if qname in self.ZONE_DATA:
            zone = self.ZONE_DATA[qname]

            # Handle CNAME chasing for non-CNAME queries
            if qtype != 'CNAME' and 'CNAME' in zone:
                # Add CNAME record
                for target in zone['CNAME']:
                    reply.add_answer(RR(
                        qname,
                        QTYPE.CNAME,
                        rdata=CNAME(target),
                        ttl=self.DEFAULT_TTL
                    ))
                # Chase CNAME to get actual record
                target = zone['CNAME'][0]
                if target in self.ZONE_DATA and qtype in self.ZONE_DATA[target]:
                    self._add_records(reply, target, qtype, self.ZONE_DATA[target][qtype])
            elif qtype in zone:
                self._add_records(reply, qname, qtype, zone[qtype])
            elif qtype == 'ANY':
                # Return all records for ANY query
                for rtype, rdata_list in zone.items():
                    self._add_records(reply, qname, rtype, rdata_list)
            else:
                # No record of requested type, but domain exists
                reply.header.rcode = RCODE.NOERROR
        else:
            # Domain not found
            reply.header.rcode = RCODE.NXDOMAIN

        return reply

    def _add_records(self, reply, qname, qtype, rdata_list):
        """Add records to reply based on type."""
        for rdata in rdata_list:
            if qtype == 'A':
                reply.add_answer(RR(qname, QTYPE.A, rdata=A(rdata), ttl=self.DEFAULT_TTL))
            elif qtype == 'AAAA':
                reply.add_answer(RR(qname, QTYPE.AAAA, rdata=AAAA(rdata), ttl=self.DEFAULT_TTL))
            elif qtype == 'CNAME':
                reply.add_answer(RR(qname, QTYPE.CNAME, rdata=CNAME(rdata), ttl=self.DEFAULT_TTL))
            elif qtype == 'MX':
                priority, exchange = rdata
                reply.add_answer(RR(qname, QTYPE.MX, rdata=MX(exchange, priority), ttl=self.DEFAULT_TTL))
            elif qtype == 'TXT':
                reply.add_answer(RR(qname, QTYPE.TXT, rdata=TXT(rdata), ttl=self.DEFAULT_TTL))
            elif qtype == 'NS':
                reply.add_answer(RR(qname, QTYPE.NS, rdata=NS(rdata), ttl=self.DEFAULT_TTL))


def start_server(port=5053, address="127.0.0.1"):
    """Start the DNS server."""
    resolver = TestResolver()
    logger = DNSLogger(prefix=True)

    print(f"Starting DNS Server on {address}:{port} (UDP)")
    print("Zone data:")
    for domain, records in resolver.ZONE_DATA.items():
        print(f"  {domain}")
        for rtype, rdata in records.items():
            print(f"    {rtype}: {rdata}")
    print()

    server = DNSServer(resolver, port=port, address=address, logger=logger)
    server.start_thread()

    return server, resolver


def main():
    parser = argparse.ArgumentParser(description="DNS Test Server for Metamorphic Testing")
    parser.add_argument("-p", "--port", type=int, default=5053, help="Port (default: 5053)")
    parser.add_argument("-a", "--address", default="127.0.0.1", help="Address (default: 127.0.0.1)")
    args = parser.parse_args()

    server, resolver = start_server(args.port, args.address)

    print("Server running. Press Ctrl+C to stop.")
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
