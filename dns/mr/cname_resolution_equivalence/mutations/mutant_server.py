#!/usr/bin/env python3
"""
Mutated DNS Server for CNAME Resolution Equivalence MR Testing

Port 5053 (ServerA) - baseline behavior (correct CNAME chasing)
Port 5054 (ServerB) - with configurable mutations

Mutations:
- M1: NO_CNAME_CHASE - Don't follow CNAME, only return CNAME record
- M2: WRONG_TARGET_RECORDS - Return wrong records when following CNAME
- M3: MISSING_RECORD - Drop one record when following CNAME
- M4: EXTRA_RECORD - Add a fake extra record when following CNAME
"""

import sys
import os
import time
import argparse

# Add dnslib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'dnslib'))

from dnslib import DNSRecord, RR, QTYPE, RCODE, A, AAAA, CNAME, TXT
from dnslib.server import DNSServer, BaseResolver, DNSLogger


# Zone data - same for both servers
ZONE_DATA = {
    'test.local.': {
        'A': ['192.168.1.1', '192.168.1.2'],
        'AAAA': ['2001:db8::1'],
        'TXT': ['v=spf1 include:test.local ~all'],
    },
    'example.local.': {
        'CNAME': ['test.local.'],  # CNAME only
    },
}

DEFAULT_TTL = 300


class BaselineResolver(BaseResolver):
    """
    Correct DNS resolver for ServerA (port 5053).
    Properly follows CNAME chains and returns target records.
    """

    def __init__(self):
        self.query_count = 0

    def resolve(self, request, handler):
        self.query_count += 1
        reply = request.reply()
        qname = str(request.q.qname)
        qtype = QTYPE[request.q.qtype]

        if not qname.endswith('.'):
            qname += '.'

        print(f"[ServerA-5053] Query: {qname} {qtype}")

        if qname in ZONE_DATA:
            zone = ZONE_DATA[qname]

            # Handle CNAME chasing for non-CNAME queries
            if qtype != 'CNAME' and 'CNAME' in zone:
                # Add CNAME record
                for target in zone['CNAME']:
                    reply.add_answer(RR(
                        qname, QTYPE.CNAME,
                        rdata=CNAME(target),
                        ttl=DEFAULT_TTL
                    ))
                # Chase CNAME to get actual records
                target = zone['CNAME'][0]
                if target in ZONE_DATA and qtype in ZONE_DATA[target]:
                    self._add_records(reply, target, qtype, ZONE_DATA[target][qtype])
                    print(f"[ServerA-5053] ✓ CNAME chased: {qname} -> {target}, added {qtype} records")
            elif qtype in zone:
                self._add_records(reply, qname, qtype, zone[qtype])
                print(f"[ServerA-5053] ✓ Direct response: {qtype} records")
            else:
                reply.header.rcode = RCODE.NOERROR
                print(f"[ServerA-5053] No {qtype} records for {qname}")
        else:
            reply.header.rcode = RCODE.NXDOMAIN
            print(f"[ServerA-5053] NXDOMAIN: {qname}")

        return reply

    def _add_records(self, reply, qname, qtype, rdata_list):
        for rdata in rdata_list:
            if qtype == 'A':
                reply.add_answer(RR(qname, QTYPE.A, rdata=A(rdata), ttl=DEFAULT_TTL))
            elif qtype == 'AAAA':
                reply.add_answer(RR(qname, QTYPE.AAAA, rdata=AAAA(rdata), ttl=DEFAULT_TTL))
            elif qtype == 'TXT':
                reply.add_answer(RR(qname, QTYPE.TXT, rdata=TXT(rdata), ttl=DEFAULT_TTL))
            elif qtype == 'CNAME':
                reply.add_answer(RR(qname, QTYPE.CNAME, rdata=CNAME(rdata), ttl=DEFAULT_TTL))


class MutatedResolver(BaseResolver):
    """
    Mutated DNS resolver for ServerB (port 5054).
    Contains configurable mutations for testing.
    """

    def __init__(self, mutation_id='BASELINE'):
        self.mutation_id = mutation_id
        self.query_count = 0
        print(f"[ServerB-5054] 🧬 Mutation: {mutation_id}")

    def resolve(self, request, handler):
        self.query_count += 1
        reply = request.reply()
        qname = str(request.q.qname)
        qtype = QTYPE[request.q.qtype]

        if not qname.endswith('.'):
            qname += '.'

        print(f"[ServerB-5054] Query: {qname} {qtype} (Mutation: {self.mutation_id})")

        if qname in ZONE_DATA:
            zone = ZONE_DATA[qname]

            # Handle CNAME chasing with mutations
            if qtype != 'CNAME' and 'CNAME' in zone:
                # Add CNAME record (always)
                for target in zone['CNAME']:
                    reply.add_answer(RR(
                        qname, QTYPE.CNAME,
                        rdata=CNAME(target),
                        ttl=DEFAULT_TTL
                    ))

                target = zone['CNAME'][0]

                # M1: NO_CNAME_CHASE - Don't add target records
                if self.mutation_id == 'M1':
                    print(f"[ServerB-5054] ✗ M1: NOT chasing CNAME, returning only CNAME record")
                    # Skip adding target records - bug!
                    return reply

                # M2: WRONG_TARGET_RECORDS - Return wrong records
                elif self.mutation_id == 'M2':
                    print(f"[ServerB-5054] ✗ M2: Returning WRONG target records")
                    wrong_records = {
                        'A': ['10.10.10.10'],  # Wrong IP
                        'AAAA': ['2001:db8::99'],  # Wrong IPv6
                        'TXT': ['WRONG TXT RECORD'],
                    }
                    if qtype in wrong_records:
                        self._add_records(reply, target, qtype, wrong_records[qtype])
                    return reply

                # M3: MISSING_RECORD - Only return first record
                elif self.mutation_id == 'M3':
                    if target in ZONE_DATA and qtype in ZONE_DATA[target]:
                        records = ZONE_DATA[target][qtype]
                        if len(records) > 1:
                            print(f"[ServerB-5054] ✗ M3: Dropping records, returning only first")
                            self._add_records(reply, target, qtype, records[:1])
                        else:
                            self._add_records(reply, target, qtype, records)
                    return reply

                # M4: EXTRA_RECORD - Add fake extra record
                elif self.mutation_id == 'M4':
                    if target in ZONE_DATA and qtype in ZONE_DATA[target]:
                        # Add real records
                        self._add_records(reply, target, qtype, ZONE_DATA[target][qtype])
                        # Add fake extra record
                        print(f"[ServerB-5054] ✗ M4: Adding EXTRA fake record")
                        if qtype == 'A':
                            reply.add_answer(RR(target, QTYPE.A, rdata=A('192.168.1.99'), ttl=DEFAULT_TTL))
                        elif qtype == 'AAAA':
                            reply.add_answer(RR(target, QTYPE.AAAA, rdata=AAAA('2001:db8::99'), ttl=DEFAULT_TTL))
                        elif qtype == 'TXT':
                            reply.add_answer(RR(target, QTYPE.TXT, rdata=TXT('EXTRA FAKE RECORD'), ttl=DEFAULT_TTL))
                    return reply

                # BASELINE: Correct behavior
                else:
                    if target in ZONE_DATA and qtype in ZONE_DATA[target]:
                        self._add_records(reply, target, qtype, ZONE_DATA[target][qtype])
                        print(f"[ServerB-5054] ✓ CNAME chased correctly")

            elif qtype in zone:
                self._add_records(reply, qname, qtype, zone[qtype])
                print(f"[ServerB-5054] ✓ Direct response: {qtype} records")
            else:
                reply.header.rcode = RCODE.NOERROR
                print(f"[ServerB-5054] No {qtype} records for {qname}")
        else:
            reply.header.rcode = RCODE.NXDOMAIN
            print(f"[ServerB-5054] NXDOMAIN: {qname}")

        return reply

    def _add_records(self, reply, qname, qtype, rdata_list):
        for rdata in rdata_list:
            if qtype == 'A':
                reply.add_answer(RR(qname, QTYPE.A, rdata=A(rdata), ttl=DEFAULT_TTL))
            elif qtype == 'AAAA':
                reply.add_answer(RR(qname, QTYPE.AAAA, rdata=AAAA(rdata), ttl=DEFAULT_TTL))
            elif qtype == 'TXT':
                reply.add_answer(RR(qname, QTYPE.TXT, rdata=TXT(rdata), ttl=DEFAULT_TTL))
            elif qtype == 'CNAME':
                reply.add_answer(RR(qname, QTYPE.CNAME, rdata=CNAME(rdata), ttl=DEFAULT_TTL))


def start_servers(mutation_id='BASELINE', port_a=5053, port_b=5054):
    """Start both DNS servers with the same mutation."""
    # Both servers run the same resolver (mutated or baseline)
    # This ensures both CNAME query and direct query hit the same implementation

    # ServerA - Mutated (for CNAME query: example.local)
    resolver_a = MutatedResolver(mutation_id)
    logger_a = DNSLogger(prefix=False)
    server_a = DNSServer(resolver_a, port=port_a, address="127.0.0.1", logger=logger_a)

    # ServerB - Mutated (for direct query: test.local)
    resolver_b = MutatedResolver(mutation_id)
    logger_b = DNSLogger(prefix=False)
    server_b = DNSServer(resolver_b, port=port_b, address="127.0.0.1", logger=logger_b)

    server_a.start_thread()
    server_b.start_thread()

    return server_a, server_b


def main():
    parser = argparse.ArgumentParser(description='DNS Mutation Testing Server')
    parser.add_argument('--mutation', type=str, default='BASELINE',
                        choices=['BASELINE', 'M1', 'M2', 'M3', 'M4'],
                        help='Mutation to apply to ServerB')
    parser.add_argument('--port-a', type=int, default=5053, help='ServerA port (baseline)')
    parser.add_argument('--port-b', type=int, default=5054, help='ServerB port (mutated)')
    args = parser.parse_args()

    mutation_descriptions = {
        'BASELINE': 'Clean baseline - correct CNAME chasing',
        'M1': 'NO_CNAME_CHASE - Only return CNAME record, skip target records',
        'M2': 'WRONG_TARGET_RECORDS - Return wrong records when following CNAME',
        'M3': 'MISSING_RECORD - Drop records when following CNAME (return only first)',
        'M4': 'EXTRA_RECORD - Add fake extra record when following CNAME',
    }

    print("=" * 80)
    print("DNS MUTATION TESTING - CNAME Resolution Equivalence MR")
    print("=" * 80)
    print(f"ServerA (Mutated): localhost:{args.port_a}")
    print(f"ServerB (Mutated): localhost:{args.port_b}")
    print(f"Mutation: {args.mutation} - {mutation_descriptions[args.mutation]}")
    print("=" * 80)
    print()

    server_a, server_b = start_servers(args.mutation, args.port_a, args.port_b)

    print("✓ Both servers running. Press Ctrl+C to stop.")
    print()
    print(f"Test with: dig @127.0.0.1 -p {args.port_a} example.local A")
    print(f"           dig @127.0.0.1 -p {args.port_b} example.local A")
    print()

    try:
        while server_a.isAlive() and server_b.isAlive():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping servers...")
        server_a.stop()
        server_b.stop()
        print("Done.")


if __name__ == '__main__':
    main()
