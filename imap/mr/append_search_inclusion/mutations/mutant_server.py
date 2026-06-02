#!/usr/bin/env python3
"""
Mutated IMAP Server for Append+Search MR Testing

Mutations target the relationship between APPEND and SEARCH:
- M1: NO_INDEX_UPDATE - APPEND succeeds but search index not updated
- M2: DELAYED_INDEX_UPDATE - Index updates only after re-SELECT
- M3: PARTIAL_INDEX_UPDATE - Only indexes every 2nd message
- M4: WRONG_HEADER_PARSE - Parses FROM header incorrectly
- M5: DUPLICATE_INDEX_ENTRY - Creates 2 index entries per APPEND
- M6: CASE_SENSITIVE_SEARCH - SEARCH is case-sensitive (bug)

Real-World Examples

  These are actual bugs found in email servers:
  - Dovecot had index corruption bugs where APPEND succeeded but search failed
  - Gmail IMAP had delays where newly appended messages weren't immediately searchable
  - Exchange had case-sensitivity issues with certain international characters
  
Based on Twisted IMAP4 server.
"""

import argparse
import re
import time
from io import BytesIO
from typing import Optional

from zope.interface import implementer
from twisted.mail import imap4
from twisted.internet import reactor, defer, protocol
from twisted.cred import portal, checkers


# Global mutation setting
MUTATION_ID = 'BASELINE'


@implementer(imap4.IMessage)
class SimpleMessage:
    """A simple message implementation with header parsing."""

    def __init__(self, body: bytes, flags: list, uid: int, date: Optional[str] = None):
        self.body = body if isinstance(body, bytes) else body.encode('utf-8')
        self.flags = [f.decode('utf-8') if isinstance(f, bytes) else f for f in flags]
        self.uid = uid
        self.date = date or time.strftime("%d-%b-%Y %H:%M:%S +0000", time.gmtime())
        self._headers = self._parse_headers()

    def _parse_headers(self) -> dict:
        """Parse email headers from body."""
        headers = {}
        try:
            body_str = self.body.decode('utf-8', errors='replace')
            if '\r\n\r\n' in body_str:
                header_section = body_str.split('\r\n\r\n')[0]
            elif '\n\n' in body_str:
                header_section = body_str.split('\n\n')[0]
            else:
                header_section = body_str

            current_header = None
            current_value = []

            for line in header_section.split('\n'):
                line = line.rstrip('\r')
                if line.startswith((' ', '\t')) and current_header:
                    current_value.append(line.strip())
                elif ':' in line:
                    if current_header:
                        headers[current_header.upper()] = ' '.join(current_value)
                    current_header, value = line.split(':', 1)
                    current_value = [value.strip()]

            if current_header:
                headers[current_header.upper()] = ' '.join(current_value)

        except Exception as e:
            print(f"DEBUG: Header parsing error: {e}")

        return headers

    def getHeader(self, name: str) -> Optional[str]:
        return self._headers.get(name.upper())

    def getUID(self):
        return self.uid

    def getFlags(self):
        return self.flags

    def getInternalDate(self):
        return self.date

    def getHeaders(self, negate, *names):
        if not names:
            return self._headers
        if negate:
            return {k: v for k, v in self._headers.items() if k not in [n.upper() for n in names]}
        return {k: self._headers.get(k.upper(), '') for k in names}

    def getBodyFile(self):
        return BytesIO(self.body)

    def getSize(self):
        return len(self.body)

    def isMultipart(self):
        return False

    def getSubPart(self, part):
        return None


@implementer(imap4.IMailbox)
class MutatedMailbox:
    """IMAP mailbox with configurable mutations for testing."""

    def __init__(self, name: str = "INBOX", mutation_id: str = 'BASELINE'):
        self.name = name
        self.mutation_id = mutation_id
        self.messages: list[SimpleMessage] = []
        self.listeners = []
        self.uidvalidity = int(time.time())
        self.uidnext = 1

        # For mutations
        self.append_count = 0  # Track appends for M3
        self.pending_index: list[SimpleMessage] = []  # For M2: delayed indexing
        self.search_index: list[SimpleMessage] = []  # Separate search index

        print(f"[Mailbox] Created with mutation: {mutation_id}")

    def getHierarchicalDelimiter(self):
        return "/"

    def getFlags(self):
        return ['\\Seen', '\\Answered', '\\Flagged', '\\Deleted', '\\Draft', '\\Recent']

    def getMessageCount(self):
        return len(self.messages)

    def getRecentCount(self):
        return len([m for m in self.messages if '\\Recent' in m.flags])

    def getUnseenCount(self):
        return len([m for m in self.messages if '\\Seen' not in m.flags])

    def isWriteable(self):
        return True

    def getUIDValidity(self):
        return self.uidvalidity

    def getUID(self, messageNum):
        if 0 <= messageNum < len(self.messages):
            return self.messages[messageNum].uid
        return None

    def getUIDNext(self):
        return self.uidnext

    def fetch(self, messages, uid):
        result = []
        for seq_num, msg in enumerate(self.messages, 1):
            if uid:
                if msg.uid in messages:
                    result.append((seq_num, msg))
            else:
                if seq_num in messages:
                    result.append((seq_num, msg))
        return iter(result)

    def addMessage(self, message, flags=(), date=None):
        """Add a message - mutations affect index updates."""
        if hasattr(message, 'read'):
            message_data = message.read()
        else:
            message_data = message

        if not isinstance(message_data, bytes):
            message_data = message_data.encode('utf-8')

        str_flags = []
        for f in flags:
            if isinstance(f, bytes):
                str_flags.append(f.decode('utf-8'))
            else:
                str_flags.append(f)

        uid = self.uidnext
        self.uidnext += 1
        self.append_count += 1

        msg = SimpleMessage(message_data, str_flags, uid, date)
        self.messages.append(msg)

        # === MUTATION LOGIC FOR INDEX UPDATES ===

        if self.mutation_id == 'M1':
            # M1: NO_INDEX_UPDATE - Don't add to search index
            print(f"[M1] APPEND OK but NOT adding to search index: UID={uid}")
            # Don't add to search_index

        elif self.mutation_id == 'M2':
            # M2: DELAYED_INDEX_UPDATE - Add to pending, not active index
            print(f"[M2] APPEND OK, adding to PENDING index (needs re-SELECT): UID={uid}")
            self.pending_index.append(msg)

        elif self.mutation_id == 'M3':
            # M3: PARTIAL_INDEX_UPDATE - Only index odd-numbered appends
            if self.append_count % 2 == 1:
                print(f"[M3] APPEND #{self.append_count} - INDEXED: UID={uid}")
                self.search_index.append(msg)
            else:
                print(f"[M3] APPEND #{self.append_count} - SKIPPED (even): UID={uid}")

        elif self.mutation_id == 'M4':
            # M4: WRONG_HEADER_PARSE - Store corrupted FROM header
            # Create a copy with wrong header parsing
            corrupted_msg = SimpleMessage(message_data, str_flags, uid, date)
            original_from = corrupted_msg._headers.get('FROM', '')
            # Bug: Only store first word of FROM header
            if original_from:
                corrupted_from = original_from.split('@')[0] if '@' in original_from else original_from.split()[0]
                corrupted_msg._headers['FROM'] = corrupted_from
                print(f"[M4] APPEND with corrupted FROM: '{original_from}' -> '{corrupted_from}'")
            self.search_index.append(corrupted_msg)

        elif self.mutation_id == 'M5':
            # M5: DUPLICATE_INDEX_ENTRY - Add message twice to index
            print(f"[M5] APPEND adding DUPLICATE index entries: UID={uid}")
            self.search_index.append(msg)
            self.search_index.append(msg)  # Duplicate!

        elif self.mutation_id == 'M6':
            # M6: CASE_SENSITIVE_SEARCH - Index normally, but search will be case-sensitive
            print(f"[M6] APPEND OK (case-sensitive search active): UID={uid}")
            self.search_index.append(msg)

        else:
            # BASELINE: Normal behavior
            print(f"[BASELINE] APPEND OK, indexed: UID={uid}, FROM={msg.getHeader('FROM')}")
            self.search_index.append(msg)

        return defer.succeed(None)

    def _flush_pending_index(self):
        """For M2: Move pending messages to active index (called on SELECT)."""
        if self.mutation_id == 'M2' and self.pending_index:
            count = len(self.pending_index)
            self.search_index.extend(self.pending_index)
            self.pending_index = []
            print(f"[M2] Flushed {count} pending messages to search index")

    def search(self, query, uid=False):
        """Search with mutations applied."""
        results = []

        # Use search_index instead of messages for search
        search_source = self.search_index

        for msg in search_source:
            if self._matches_query(msg, query):
                if uid:
                    results.append(msg.uid)
                else:
                    # Find sequence number in messages list
                    for seq_num, m in enumerate(self.messages, 1):
                        if m.uid == msg.uid:
                            results.append(seq_num)
                            break

        print(f"[SEARCH] Query={query}, Results={results}, Index size={len(search_source)}")
        return results

    def _matches_query(self, msg: SimpleMessage, query) -> bool:
        """Check if message matches query - M6 affects this."""
        if isinstance(query, bytes):
            query = query.decode('utf-8')

        if isinstance(query, str):
            query = query.strip().upper()
            if query == 'ALL':
                return True
            elif query == 'SEEN':
                return '\\Seen' in msg.flags
            elif query == 'UNSEEN':
                return '\\Seen' not in msg.flags

        if isinstance(query, (list, tuple)):
            if len(query) >= 2:
                criterion = query[0]
                if isinstance(criterion, bytes):
                    criterion = criterion.decode('utf-8')
                criterion = criterion.upper()

                value = query[1]
                if isinstance(value, bytes):
                    value = value.decode('utf-8')

                if criterion == 'FROM':
                    from_header = msg.getHeader('FROM') or ''

                    if self.mutation_id == 'M6':
                        # M6: CASE_SENSITIVE_SEARCH - exact case match required
                        match = value in from_header
                        if not match:
                            print(f"[M6] Case-sensitive mismatch: '{value}' not in '{from_header}'")
                        return match
                    else:
                        # Normal: case-insensitive
                        return value.lower() in from_header.lower()

                elif criterion == 'SUBJECT':
                    subject = msg.getHeader('SUBJECT') or ''
                    if self.mutation_id == 'M6':
                        return value in subject
                    return value.lower() in subject.lower()

        return False

    def store(self, messages, flags, mode, uid):
        result = {}
        for seq_num, msg in enumerate(self.messages, 1):
            check_val = msg.uid if uid else seq_num
            if check_val in messages:
                if mode == 1:
                    for flag in flags:
                        if flag not in msg.flags:
                            msg.flags.append(flag)
                elif mode == -1:
                    for flag in flags:
                        if flag in msg.flags:
                            msg.flags.remove(flag)
                else:
                    msg.flags = list(flags)
                result[seq_num] = {'FLAGS': msg.flags}
        return defer.succeed(result)

    def expunge(self):
        deleted_uids = []
        self.messages = [m for m in self.messages if '\\Deleted' not in m.flags or (deleted_uids.append(m.uid) and False)]
        return deleted_uids

    def addListener(self, listener):
        self.listeners.append(listener)

    def removeListener(self, listener):
        if listener in self.listeners:
            self.listeners.remove(listener)

    def requestStatus(self, names):
        result = {}
        for name in names:
            name_str = name.decode('utf-8') if isinstance(name, bytes) else name
            if name_str == 'MESSAGES':
                result[name] = self.getMessageCount()
            elif name_str == 'RECENT':
                result[name] = self.getRecentCount()
            elif name_str == 'UIDNEXT':
                result[name] = self.getUIDNext()
            elif name_str == 'UIDVALIDITY':
                result[name] = self.getUIDValidity()
            elif name_str == 'UNSEEN':
                result[name] = self.getUnseenCount()
        return defer.succeed(result)

    def destroy(self):
        pass


class MutatedAccount(imap4.MemoryAccount):
    """IMAP account with mutated mailboxes."""

    def __init__(self, username, mutation_id='BASELINE'):
        self.mutation_id = mutation_id
        super().__init__(username)
        try:
            self.addMailbox(b"INBOX")
        except:
            pass

    def _emptyMailbox(self, name, id):
        return MutatedMailbox(name=name, mutation_id=self.mutation_id)


@implementer(portal.IRealm)
class MutatedIMAPRealm:
    """Realm with mutation support."""

    def __init__(self, mutation_id='BASELINE'):
        self.mutation_id = mutation_id

    def requestAvatar(self, avatarId, mind, *interfaces):
        if imap4.IAccount in interfaces:
            username = avatarId.decode('utf-8') if isinstance(avatarId, bytes) else avatarId
            account = MutatedAccount(username, self.mutation_id)
            return imap4.IAccount, account, lambda: None
        raise NotImplementedError("No supported interfaces")


class MutatedIMAP4Server(imap4.IMAP4Server):
    """Custom IMAP4 Server with SEARCH support and mutation awareness."""

    def __init__(self, *args, mutation_id='BASELINE', **kwargs):
        super().__init__(*args, **kwargs)
        self.mutation_id = mutation_id
        self.selected_mailbox = None

    def lineReceived(self, line):
        print(f">>> {line.decode('utf-8', errors='replace')}")
        super().lineReceived(line)

    def sendLine(self, line):
        print(f"<<< {line.decode('utf-8', errors='replace') if isinstance(line, bytes) else line}")
        super().sendLine(line)

    def do_SELECT(self, tag, mailbox):
        """Override SELECT to trigger M2 index flush."""
        # Call parent SELECT first
        d = super().do_SELECT(tag, mailbox)

        # For M2: flush pending index when mailbox is selected
        if self.mutation_id == 'M2' and self.mbox:
            if hasattr(self.mbox, '_flush_pending_index'):
                self.mbox._flush_pending_index()

        return d

    def do_SEARCH(self, tag, query, uid=False):
        """Handle SEARCH command."""
        if self.mbox is None:
            self.sendNegativeResponse(tag, b'No mailbox selected')
            return

        query_parts = self._parse_search_query(query)
        print(f"DEBUG: SEARCH query={query}, parsed={query_parts}")

        if hasattr(self.mbox, 'search'):
            results = self.mbox.search(query_parts, uid=uid)
        else:
            results = []

        if results:
            result_str = ' '.join(str(r) for r in results)
            self.sendUntaggedResponse(f'SEARCH {result_str}'.encode('utf-8'))
        else:
            self.sendUntaggedResponse(b'SEARCH')

        self.sendPositiveResponse(tag, b'SEARCH completed')

    def _parse_search_query(self, query):
        """Parse SEARCH query string."""
        if isinstance(query, list):
            if len(query) >= 2:
                criterion = query[0]
                if isinstance(criterion, bytes):
                    criterion = criterion.decode('utf-8')
                criterion = criterion.upper()

                if criterion in ('FROM', 'SUBJECT', 'TO'):
                    value = query[1]
                    if isinstance(value, bytes):
                        value = value.decode('utf-8')
                    return (criterion, value)
            elif len(query) == 1:
                item = query[0]
                if isinstance(item, bytes):
                    item = item.decode('utf-8')
                return item.upper()

            query = ' '.join(q.decode('utf-8') if isinstance(q, bytes) else str(q) for q in query)

        if isinstance(query, bytes):
            query = query.decode('utf-8')

        query = query.strip()

        from_match = re.match(r'FROM\s+"([^"]+)"', query, re.IGNORECASE)
        if from_match:
            return ('FROM', from_match.group(1))

        from_match = re.match(r'FROM\s+(\S+)', query, re.IGNORECASE)
        if from_match:
            return ('FROM', from_match.group(1))

        if query.upper() in ['ALL', 'SEEN', 'UNSEEN', 'FLAGGED', 'UNFLAGGED', 'DELETED', 'UNDELETED']:
            return query.upper()

        return query

    select_SEARCH = (do_SEARCH, imap4.IMAP4Server.arg_searchkeys)
    auth_SEARCH = (do_SEARCH, imap4.IMAP4Server.arg_searchkeys)


class MutatedIMAP4Factory(protocol.ServerFactory):
    """Factory for mutated IMAP4 server."""

    def __init__(self, portal, mutation_id='BASELINE'):
        self.portal = portal
        self.mutation_id = mutation_id

    def buildProtocol(self, addr):
        p = MutatedIMAP4Server(mutation_id=self.mutation_id)
        p.portal = self.portal
        p.factory = self
        p.mutation_id = self.mutation_id
        return p


def main():
    parser = argparse.ArgumentParser(description='Mutated IMAP Server for MR Testing')
    parser.add_argument('-p', '--port', type=int, default=1144, help='Port to listen on')
    parser.add_argument('--mutation', type=str, default='BASELINE',
                       choices=['BASELINE', 'M1', 'M2', 'M3', 'M4', 'M5', 'M6'],
                       help='Mutation to apply')
    args = parser.parse_args()

    global MUTATION_ID
    MUTATION_ID = args.mutation

    print("=" * 80)
    print("IMAP MUTATION TESTING - Append+Search MR")
    print("=" * 80)
    print(f"Port: {args.port}")
    print(f"Mutation: {args.mutation}")
    print("=" * 80)

    mutation_descriptions = {
        'BASELINE': 'Clean baseline - normal index behavior',
        'M1': 'NO_INDEX_UPDATE - APPEND succeeds but search index not updated',
        'M2': 'DELAYED_INDEX_UPDATE - Index updates only after re-SELECT',
        'M3': 'PARTIAL_INDEX_UPDATE - Only indexes every 2nd message',
        'M4': 'WRONG_HEADER_PARSE - Parses FROM header incorrectly',
        'M5': 'DUPLICATE_INDEX_ENTRY - Creates 2 index entries per APPEND',
        'M6': 'CASE_SENSITIVE_SEARCH - SEARCH is case-sensitive',
    }
    print(f"Description: {mutation_descriptions.get(args.mutation, 'Unknown')}")
    print("=" * 80 + "\n")

    realm = MutatedIMAPRealm(mutation_id=args.mutation)
    p = portal.Portal(realm)

    checker = checkers.InMemoryUsernamePasswordDatabaseDontUse()
    checker.addUser(b"testuser", b"testpass")
    p.registerChecker(checker)

    factory = MutatedIMAP4Factory(p, mutation_id=args.mutation)
    reactor.listenTCP(args.port, factory)

    print(f"IMAP Server started on port {args.port}")
    print("Credentials: testuser / testpass")
    print("Press Ctrl+C to stop\n")

    reactor.run()


if __name__ == "__main__":
    main()
