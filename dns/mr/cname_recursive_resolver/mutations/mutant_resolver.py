#!/usr/bin/env python3
"""Mutated recursive resolver for cname_recursive_resolver2 mutation tests."""

import argparse
import os
import socket
import sys
import time
from copy import deepcopy


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "dnslib"))

from dnslib import A, CLASS, DNSLabel, DNSRecord, QTYPE, RCODE, RR
from dnslib.server import BaseResolver, DNSServer, DNSLogger


MUTATIONS = ["BASELINE", "M1", "M2", "M3", "M4", "M5", "M6", "M7"]

MUTATION_DESCRIPTIONS = {
    "BASELINE": "Clean baseline - forward request and response unchanged",
    "M1": "REWRITE_QNAME_TO_TARGET - Forward test.local. instead of client qname",
    "M2": "REWRITE_QTYPE_AAAA - Forward AAAA instead of A",
    "M3": "REWRITE_QCLASS_CH - Forward CH instead of IN",
    "M4": "DROP_A_RECORDS - Remove all A records from recursive response",
    "M5": "WRONG_A_RECORDS - Replace A records with 10.10.10.10",
    "M6": "MISSING_ONE_A_RECORD - Keep only the first A record",
    "M7": "EXTRA_A_RECORD - Add fake A record 192.168.1.99",
}


class MutatedRecursiveResolver(BaseResolver):
    """Proxy-style recursive resolver with targeted DNS mutation hooks."""

    def __init__(self, upstream_host, upstream_port, mutation_id="BASELINE", timeout=10):
        self.upstream_host = upstream_host
        self.upstream_port = upstream_port
        self.mutation_id = mutation_id
        self.timeout = timeout
        self.query_count = 0

    def resolve(self, request, handler):
        self.query_count += 1
        upstream_request = self._mutate_request(deepcopy(request))

        print(
            f"[resolver] #{self.query_count} {self.mutation_id}: "
            f"client={self._question_summary(request)} upstream={self._question_summary(upstream_request)}"
        )

        try:
            proxy_response = upstream_request.send(
                self.upstream_host,
                self.upstream_port,
                tcp=(handler.protocol != "udp"),
                timeout=self.timeout,
            )
            reply = DNSRecord.parse(proxy_response)
        except socket.timeout:
            print("[resolver] Upstream timeout")
            reply = request.reply()
            reply.header.rcode = RCODE.NXDOMAIN

        reply = self._mutate_response(reply)
        print(f"[resolver] response A records: {self._a_records(reply)}")
        return reply

    def _mutate_request(self, request):
        if not request.questions:
            return request

        question = request.q

        if self.mutation_id == "M1":
            question.qname = DNSLabel("test.local.")
            print("[M1] Rewrote upstream qname to test.local.")
        elif self.mutation_id == "M2":
            question.qtype = QTYPE.AAAA
            print("[M2] Rewrote upstream qtype to AAAA")
        elif self.mutation_id == "M3":
            question.qclass = CLASS.CH
            print("[M3] Rewrote upstream qclass to CH")

        return request

    def _mutate_response(self, reply):
        if self.mutation_id == "M4":
            print("[M4] Dropping all A records from response")
            self._drop_a_records(reply)
        elif self.mutation_id == "M5":
            print("[M5] Replacing all A records with 10.10.10.10")
            self._replace_a_records(reply, "10.10.10.10")
        elif self.mutation_id == "M6":
            print("[M6] Keeping only the first A record")
            self._keep_first_a_record(reply)
        elif self.mutation_id == "M7":
            print("[M7] Adding extra fake A record 192.168.1.99")
            self._add_extra_a_record(reply, "192.168.1.99")

        return reply

    @staticmethod
    def _drop_a_records(reply):
        reply.rr = [rr for rr in reply.rr if rr.rtype != QTYPE.A]
        reply.auth = [rr for rr in reply.auth if rr.rtype != QTYPE.A]
        reply.ar = [rr for rr in reply.ar if rr.rtype != QTYPE.A]
        reply.set_header_qa()

    @staticmethod
    def _replace_a_records(reply, ip_address):
        for section in (reply.rr, reply.auth, reply.ar):
            for rr in section:
                if rr.rtype == QTYPE.A:
                    rr.rdata = A(ip_address)
        reply.set_header_qa()

    @staticmethod
    def _keep_first_a_record(reply):
        seen_first = False
        for attr in ("rr", "auth", "ar"):
            kept = []
            for rr in getattr(reply, attr):
                if rr.rtype != QTYPE.A:
                    kept.append(rr)
                    continue
                if not seen_first:
                    kept.append(rr)
                    seen_first = True
            setattr(reply, attr, kept)
        reply.set_header_qa()

    @staticmethod
    def _add_extra_a_record(reply, ip_address):
        owner = str(reply.q.qname) if reply.questions else "test.local."
        reply.add_answer(RR(owner, QTYPE.A, rdata=A(ip_address), ttl=300))

    @staticmethod
    def _question_summary(record):
        if not record.questions:
            return "<no question>"
        q = record.q
        return f"{q.qname}/{QTYPE.get(q.qtype)}/{CLASS.get(q.qclass)}"

    @staticmethod
    def _a_records(record):
        values = []
        for section in (record.rr, record.auth, record.ar):
            for rr in section:
                if rr.rtype == QTYPE.A:
                    values.append(str(rr.rdata))
        return values


def parse_upstream(spec):
    host, _, port = spec.partition(":")
    if not host:
        raise ValueError(f"Invalid upstream {spec!r}: missing host")
    return host, int(port) if port else 53


def start_server(address, port, upstream, mutation_id, timeout):
    upstream_host, upstream_port = parse_upstream(upstream)
    resolver = MutatedRecursiveResolver(upstream_host, upstream_port, mutation_id, timeout)
    logger = DNSLogger(prefix=True)
    server = DNSServer(resolver, port=port, address=address, logger=logger)

    print("=" * 80)
    print("DNS CNAME Recursive Resolver 2 - Mutant Resolver")
    print("=" * 80)
    print(f"Mutation: {mutation_id} - {MUTATION_DESCRIPTIONS[mutation_id]}")
    print(f"Listen:   {address}:{port}")
    print(f"Upstream: {upstream_host}:{upstream_port}")
    print("=" * 80)
    print()

    server.start_thread()
    return server


def main():
    parser = argparse.ArgumentParser(description="Mutated recursive DNS resolver")
    parser.add_argument("--mutation", default="BASELINE", choices=MUTATIONS)
    parser.add_argument("-p", "--port", type=int, default=5055)
    parser.add_argument("-a", "--address", default="127.0.0.1")
    parser.add_argument("-u", "--upstream", default="127.0.0.1:5054")
    parser.add_argument("-o", "--timeout", type=float, default=10)
    args = parser.parse_args()

    server = start_server(args.address, args.port, args.upstream, args.mutation, args.timeout)

    try:
        while server.isAlive():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping mutant resolver...")
        server.stop()


if __name__ == "__main__":
    main()
