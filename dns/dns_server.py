#!/usr/bin/env python3
"""
DNS Server using dnslib.zoneresolver.ZoneResolver for metamorphic testing.

Two zones are defined, each served by a *separate* process (multi-zone / two
authoritative servers). Select which zone this instance is authoritative for
with --zone:

    --zone alias   -> serves example.local. (holds only the CNAME to test.local.)
    --zone target  -> serves test.local.    (holds A/AAAA/MX/TXT/NS records)
    --zone all     -> serves both (legacy single-zone mode; used by other MRs)

The alias server only knows about example.local. and returns NXDOMAIN /
just-a-CNAME for anything else — no cross-zone chasing. That is the correct
authoritative behaviour when the target lives on a different server, and it is
what our Architecture 1 CNAME-equivalence MR relies on.

For mutation testing, mutate the ZONE_TEXT strings below or swap ZoneResolver
for a hand-written BaseResolver.

Usage:
    python dns_server.py --zone alias  -p 5053
    python dns_server.py --zone target -p 5054
"""

import sys
import os
import time
import argparse

# Add dnslib to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'dnslib'))

from dnslib.server import DNSServer, DNSLogger
from dnslib.zoneresolver import ZoneResolver


# Zone data as RFC 1035 zone-file lines.
# One process serves exactly one entry (or 'all' for legacy single-zone mode).
#
# Every alias in the 'alias' zone points at the SAME target (test.local.).
# This gives the MR grammar freedom to pick any alias name while keeping the
# expected A-record set constant — the CNAME chase and the direct query on
# test.local. always yield the same records by construction.
ZONE_TEXT = {
    # 'alias' zone: authoritative for example.local. and its subdomains.
    # Five aliases, all CNAME'd to the single canonical target test.local.
    'alias': """
example.local.        300 IN CNAME  test.local.
example1.local.    300 IN CNAME  test.local.
example2.local.   300 IN CNAME  test.local.
example3.local.    300 IN CNAME  test.local.
example4.local.    300 IN CNAME  test.local.
""",
    # 'target' zone: authoritative for test.local. and its subdomains.
    # test.local. is the single A/AAAA target that every alias resolves to.
    'target': """
test.local.       300 IN A     192.168.1.1
test.local.       300 IN A     192.168.1.2
test.local.       300 IN AAAA  2001:db8::1
test.local.       300 IN MX    10 mail.test.local.
test.local.       300 IN TXT   "v=spf1 include:test.local ~all"
test.local.       300 IN NS    ns1.test.local.
test.local.       300 IN NS    ns2.test.local.
ns1.test.local.   300 IN A     192.168.1.10
ns2.test.local.   300 IN A     192.168.1.11
mail.test.local.  300 IN A     192.168.1.20
""",
}
# Legacy single-zone mode: concatenation of both zones (backwards-compatible
# with other MRs that still expect one process to know both).
ZONE_TEXT['all'] = ZONE_TEXT['alias'] + ZONE_TEXT['target']


def start_server(zone='all', port=5053, address="127.0.0.1"):
    """Start a dnslib ZoneResolver-backed authoritative DNS server."""
    if zone not in ZONE_TEXT:
        raise ValueError(f"Unknown zone {zone!r}; choose from {list(ZONE_TEXT)}")

    resolver = ZoneResolver(ZONE_TEXT[zone])
    logger = DNSLogger(prefix=True)

    print(f"Starting DNS Server on {address}:{port} (UDP) — zone={zone}")
    print("Zone data:")
    for line in ZONE_TEXT[zone].strip().splitlines():
        print(f"  {line}")
    print()

    server = DNSServer(resolver, port=port, address=address, logger=logger)
    server.start_thread()
    return server, resolver


def main():
    parser = argparse.ArgumentParser(description="DNS Test Server for Metamorphic Testing")
    parser.add_argument("--zone", choices=sorted(ZONE_TEXT), default='all',
                        help="Which zone this process is authoritative for")
    parser.add_argument("-p", "--port", type=int, default=5053, help="Port (default: 5053)")
    parser.add_argument("-a", "--address", default="127.0.0.1", help="Address (default: 127.0.0.1)")
    args = parser.parse_args()

    server, _ = start_server(args.zone, args.port, args.address)

    print("Server running. Press Ctrl+C to stop.")
    hint = "example.local A" if args.zone == 'alias' else "test.local A"
    print(f"Test with: dig @{args.address} -p {args.port} {hint}")
    print()

    try:
        while server.isAlive():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        server.stop()


if __name__ == '__main__':
    main()
