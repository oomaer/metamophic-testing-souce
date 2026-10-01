#!/usr/bin/env python3
"""
Mutated SMTP Server for Repeated Recipient MR Testing
Port 8027 (ServerB) - with configurable mutations
Port 8026 (ServerA) - baseline behavior
"""

import argparse
import asyncio
import os
from aiosmtpd.controller import Controller
from aiosmtpd.smtp import AuthResult


def easy_authenticator(server, session, envelope, mechanism, auth_data):
    """Accept any authentication."""
    return AuthResult(success=True)


class BaselineHandler:
    """Clean baseline handler for ServerA (port 8026)"""

    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
        """RFC-compliant RCPT handler - accepts all including duplicates."""
        envelope.rcpt_tos.append(address)
        print(f"[ServerA-8026] ✓ Accepted: {address}")
        return '250 OK'

    async def handle_DATA(self, server, session, envelope):
        print(f"[ServerA-8026] 📧 Message from {envelope.mail_from} to {envelope.rcpt_tos}")
        return f"250 OK {envelope.mail_from} {envelope.rcpt_tos}"


class MutatedHandler:
    """Mutated handler for ServerB (port 8027)"""

    def __init__(self, mutation_id='BASELINE'):
        self.mutation_id = mutation_id
        self.duplicate_detected = False  # For M6
        print(f"[ServerB-8027] 🧬 Mutation: {mutation_id}")

    async def handle_MAIL(self, server, session, envelope, address, mail_options):
        """Reset per-transaction state on new MAIL FROM."""
        self.duplicate_detected = False
        envelope.mail_from = address
        return '250 OK'

    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
        """Handle RCPT with mutations."""

        # M1: STRICT_DUPLICATE_REJECT
        if self.mutation_id == 'M1':
            if address in envelope.rcpt_tos:
                print(f"[ServerB-8027] ✗ M1: Duplicate rejected: {address}")
                return '550 5.5.1 Duplicate recipient not allowed'

        # M2: ACCEPT_FIRST_N_DUPLICATES (N=10)
        elif self.mutation_id == 'M2':
            # Count how many times this address already exists
            count = envelope.rcpt_tos.count(address)
            if count >= 10:  # Already have 10 copies, reject 11th+
                print(f"[ServerB-8027] ✗ M2: Too many duplicates (>10): {address}")
                return '550 5.5.1 Too many duplicates of this recipient'

        # M3: REJECT_FIRST_DUPLICATE_ONLY
        elif self.mutation_id == 'M3':
            count = envelope.rcpt_tos.count(address)
            if count == 1:  # This is the SECOND occurrence (first duplicate)
                print(f"[ServerB-8027] ✗ M3: Rejecting first duplicate: {address}")
                return '550 5.5.1 Duplicate recipient not allowed'
            # 3rd, 4th, etc. are allowed (logic bug!)

        # M4: DUPLICATE_DELIVERS_TO_WRONG_RECIPIENT
        elif self.mutation_id == 'M4':
            if address in envelope.rcpt_tos:
                wrong_recipient = 'unexpected-recipient@example.com'
                envelope.rcpt_tos.append(wrong_recipient)
                print(f"[ServerB-8027] ✗ M4: Duplicate {address} recorded as {wrong_recipient}")
                return '250 OK'

        # M5: MULTIPLE_RESPONSE_LINES
        elif self.mutation_id == 'M5':
            if address in envelope.rcpt_tos:
                # Protocol violation: Send multiple 250 responses
                print(f"[ServerB-8027] ✗ M5: Sending multiple response lines")
                # Note: aiosmtpd might not allow this easily, so we simulate with enhanced response
                envelope.rcpt_tos.append(address)
                return '250 OK\r\n250 Duplicate accepted'

        # M6: REJECT_ALL_AFTER_DUPLICATE
        elif self.mutation_id == 'M6':
            # State corruption: Once a duplicate is detected, reject ALL subsequent RCPT
            if address in envelope.rcpt_tos:
                print(f"[ServerB-8027] ✗ M6: Duplicate detected, poisoning session: {address}")
                self.duplicate_detected = True
                return '550 5.5.1 Duplicate recipient not allowed'
            elif self.duplicate_detected:
                # Even unique addresses are rejected after duplicate was found
                print(f"[ServerB-8027] ✗ M6: Session poisoned, rejecting all: {address}")
                return '550 5.5.1 No more recipients allowed after duplicate'

        # BASELINE: Accept all (RFC-compliant)
        envelope.rcpt_tos.append(address)
        print(f"[ServerB-8027] ✓ Accepted: {address}")
        return '250 OK'

    async def handle_DATA(self, server, session, envelope):
        # For M6 and other mutations that reject recipients
        # If no recipients, still accept DATA content but return error at end
        if not envelope.rcpt_tos:
            print(f"[ServerB-8027] ✗ No recipients, but accepting email content anyway")
            # Accept the email content, return error after
            return f"554 5.5.1 Error: No valid recipients {envelope.mail_from} {envelope.rcpt_tos}"

        print(f"[ServerB-8027] 📧 Message from {envelope.mail_from} to {envelope.rcpt_tos}")
        return f"250 OK {envelope.mail_from} {envelope.rcpt_tos}"


def start_server(port, handler, mutation_id=None):
    """Start SMTP server with given handler."""
    if mutation_id:
        handler_instance = handler(mutation_id)
    else:
        handler_instance = handler()

    controller = Controller(
        handler_instance,
        hostname='127.0.0.1',
        port=port,
        authenticator=easy_authenticator,
        auth_required=True,
        auth_require_tls=False
    )
    controller.start()
    return controller


def main():
    parser = argparse.ArgumentParser(description='Run mutated SMTP servers for testing')
    parser.add_argument('--mutation', type=str, default='BASELINE',
                       choices=['BASELINE', 'M1', 'M2', 'M3', 'M4', 'M5', 'M6'],
                       help='Mutation to apply to ServerB')
    parser.add_argument('--port-a', type=int, default=8026, help='ServerA port (baseline)')
    parser.add_argument('--port-b', type=int, default=8027, help='ServerB port (mutated)')
    args = parser.parse_args()

    print("=" * 80)
    print("SMTP MUTATION TESTING - Repeated Recipient MR")
    print("=" * 80)
    print(f"ServerA (Baseline): localhost:{args.port_a}")
    print(f"ServerB (Mutated):  localhost:{args.port_b} - Mutation: {args.mutation}")
    print("=" * 80)
    print()

    # Start both servers
    server_a = start_server(args.port_a, BaselineHandler)
    server_b = start_server(args.port_b, MutatedHandler, args.mutation)

    print(f"✓ Both servers running. Press Ctrl+C to stop.")
    print()

    loop = asyncio.get_event_loop()
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print("\n\nStopping servers...")
        server_a.stop()
        server_b.stop()
        print("Done.")


if __name__ == '__main__':
    main()
