#!/usr/bin/env python3
"""
Mutated SMTP Server for State Reset MR Testing
Port 8027 (ServerB) - with configurable mutations
Port 8026 (ServerA) - baseline behavior

Mutations target RSET command behavior:
- M1: INCOMPLETE_SENDER_RESET - RSET doesn't clear MAIL FROM buffer
- M2: RSET_CLEARS_AUTH - RSET incorrectly clears authentication
- M3: RSET_RETURNS_ERROR - RSET returns 500 error
- M4: RSET_PARTIAL_STATE_CLEAR - Only first RSET works
- M5: RSET_NOOP - RSET returns 250 but does nothing
"""

import argparse
import asyncio
from aiosmtpd.controller import Controller
from aiosmtpd.smtp import AuthResult


def easy_authenticator(server, session, envelope, mechanism, auth_data):
    """Accept any authentication and mark session as authenticated."""
    session.authenticated = True
    return AuthResult(success=True)


class BaselineHandler:
    """Clean baseline handler for ServerA (port 8026)"""

    async def handle_MAIL(self, server, session, envelope, address, mail_options):
        """Accept MAIL FROM."""
        envelope.mail_from = address
        print(f"[ServerA-8026] MAIL FROM: {address}")
        return '250 OK'

    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
        """Accept RCPT TO."""
        envelope.rcpt_tos.append(address)
        print(f"[ServerA-8026] RCPT TO: {address}")
        return '250 OK'

    async def handle_DATA(self, server, session, envelope):
        """Accept DATA."""
        print(f"[ServerA-8026] DATA from {envelope.mail_from} to {envelope.rcpt_tos}")
        return f"250 OK {envelope.mail_from} {envelope.rcpt_tos}"

    async def handle_RSET(self, server, session, envelope):
        """RFC-compliant RSET - clears transaction state, keeps auth."""
        print(f"[ServerA-8026] RSET: State cleared (auth preserved)")
        return '250 OK'


class MutatedHandler:
    """Mutated handler for ServerB (port 8027) with configurable RSET behavior.

    State is tracked per-session to handle multiple connections correctly.
    """

    def __init__(self, mutation_id='BASELINE'):
        self.mutation_id = mutation_id
        print(f"[ServerB-8027] Mutation: {mutation_id}")

    def _get_session_state(self, session):
        """Get or initialize per-session mutation state."""
        if not hasattr(session, 'mutation_state'):
            session.mutation_state = {
                'mail_from_set': False,
                'rset_count': 0,
            }
        return session.mutation_state

    async def handle_MAIL(self, server, session, envelope, address, mail_options):
        """MAIL FROM with mutation-aware state checking."""
        state = self._get_session_state(session)

        # M2: Check if auth was incorrectly cleared by RSET
        if self.mutation_id == 'M2':
            if not getattr(session, 'authenticated', False):
                print(f"[ServerB-8027] M2: MAIL rejected - not authenticated")
                return '530 5.7.1 Authentication required'

        # M1, M4, and M5: Check for nested MAIL command (sender not cleared by RSET)
        # M4 relies on the same guard because the 2nd+ RSET no-ops and leaves mail_from_set=True.
        if self.mutation_id in ('M1', 'M4', 'M5'):
            if state['mail_from_set']:
                print(f"[ServerB-8027] {self.mutation_id}: MAIL rejected - sender already specified")
                return '503 5.5.1 Sender already specified'

        envelope.mail_from = address
        state['mail_from_set'] = True
        print(f"[ServerB-8027] MAIL FROM: {address}")
        return '250 OK'

    async def handle_RCPT(self, server, session, envelope, address, rcpt_options):
        """Accept RCPT TO."""
        envelope.rcpt_tos.append(address)
        print(f"[ServerB-8027] RCPT TO: {address}")
        return '250 OK'

    async def handle_DATA(self, server, session, envelope):
        """Accept DATA."""
        state = self._get_session_state(session)
        # Reset mail_from_set after DATA completes (transaction finished)
        state['mail_from_set'] = False
        print(f"[ServerB-8027] DATA from {envelope.mail_from} to {envelope.rcpt_tos}")
        return f"250 OK {envelope.mail_from} {envelope.rcpt_tos}"

    async def handle_RSET(self, server, session, envelope):
        """RSET with mutations applied."""
        state = self._get_session_state(session)

        # M3: RSET_RETURNS_ERROR - Return error instead of 250
        if self.mutation_id == 'M3':
            print(f"[ServerB-8027] M3: RSET returning error")
            return '500 5.5.1 Command not recognized'

        # M4: RSET_PARTIAL_STATE_CLEAR - Only first RSET works
        if self.mutation_id == 'M4':
            state['rset_count'] += 1
            if state['rset_count'] == 1:
                # First RSET works
                state['mail_from_set'] = False
                print(f"[ServerB-8027] M4: First RSET - state cleared")
            else:
                # Subsequent RSETs are no-ops
                print(f"[ServerB-8027] M4: RSET #{state['rset_count']} - NO-OP (state NOT cleared)")
            return '250 OK'

        # M5: RSET_NOOP - Return 250 but don't reset anything
        if self.mutation_id == 'M5':
            print(f"[ServerB-8027] M5: RSET NO-OP (returning 250 but not clearing state)")
            # Don't clear mail_from_set
            return '250 OK'

        # M1: INCOMPLETE_SENDER_RESET - Don't clear mail_from_set flag
        if self.mutation_id == 'M1':
            # Don't clear the mail_from_set flag
            print(f"[ServerB-8027] M1: RSET - NOT clearing mail_from_set flag")
            return '250 OK'

        # M2: RSET_CLEARS_AUTH - Incorrectly clear authentication
        if self.mutation_id == 'M2':
            state['mail_from_set'] = False
            session.authenticated = False  # BUG: Should not clear auth
            print(f"[ServerB-8027] M2: RSET - incorrectly cleared authentication")
            return '250 OK'

        # BASELINE: Normal RSET behavior
        state['mail_from_set'] = False
        print(f"[ServerB-8027] RSET: State cleared normally")
        return '250 OK'


def start_server(port, handler_class, mutation_id=None):
    """Start SMTP server with given handler."""
    if mutation_id:
        handler = handler_class(mutation_id)
    else:
        handler = handler_class()

    controller = Controller(
        handler,
        hostname='127.0.0.1',
        port=port,
        authenticator=easy_authenticator,
        auth_required=True,
        auth_require_tls=False
    )
    controller.start()
    return controller


def main():
    parser = argparse.ArgumentParser(description='Run mutated SMTP servers for State Reset MR testing')
    parser.add_argument('--mutation', type=str, default='BASELINE',
                       choices=['BASELINE', 'M1', 'M2', 'M3', 'M4', 'M5'],
                       help='Mutation to apply to ServerB')
    parser.add_argument('--port-a', type=int, default=8026, help='ServerA port (baseline)')
    parser.add_argument('--port-b', type=int, default=8027, help='ServerB port (mutated)')
    args = parser.parse_args()

    print("=" * 80)
    print("SMTP MUTATION TESTING - State Reset MR")
    print("=" * 80)
    print(f"ServerA (Baseline): localhost:{args.port_a}")
    print(f"ServerB (Mutated):  localhost:{args.port_b} - Mutation: {args.mutation}")
    print("=" * 80)
    print()

    # Start both servers
    server_a = start_server(args.port_a, BaselineHandler)
    server_b = start_server(args.port_b, MutatedHandler, args.mutation)

    print(f"Both servers running. Press Ctrl+C to stop.")
    print()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        print("\n\nStopping servers...")
        server_a.stop()
        server_b.stop()
        print("Done.")


if __name__ == '__main__':
    main()
