#!/usr/bin/env python3
"""
IMAP Server for Append+Search Metamorphic Relation Testing

A simple IMAP server with SEARCH support for testing the MR:
- Source: SEARCH FROM "unique@test.com" returns 0 results
- Follow-up: After APPEND, SEARCH returns 1 result

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
            # Split headers from body (empty line separates them)
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
                    # Continuation of previous header
                    current_value.append(line.strip())
                elif ':' in line:
                    # Save previous header
                    if current_header:
                        headers[current_header.upper()] = ' '.join(current_value)
                    # Start new header
                    current_header, value = line.split(':', 1)
                    current_value = [value.strip()]

            # Save last header
            if current_header:
                headers[current_header.upper()] = ' '.join(current_value)

        except Exception as e:
            print(f"DEBUG: Header parsing error: {e}")

        return headers

    def getHeader(self, name: str) -> Optional[str]:
        """Get a header value by name (case-insensitive)."""
        return self._headers.get(name.upper())

    def getUID(self):
        return self.uid

    def getFlags(self):
        return self.flags

    def getInternalDate(self):
        return self.date

    def getHeaders(self, negate, *names):
        """Get headers. If negate is True, return all headers NOT in names."""
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
class SimpleMailbox:
    """A simple in-memory IMAP mailbox with SEARCH support."""

    def __init__(self, name: str = "INBOX"):
        self.name = name
        self.messages: list[SimpleMessage] = []
        self.listeners = []
        self.uidvalidity = int(time.time())
        self.uidnext = 1

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
        """Fetch messages - returns iterator of (seq, message) tuples."""
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
        """Add a message to the mailbox."""
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

        msg = SimpleMessage(message_data, str_flags, uid, date)
        self.messages.append(msg)

        print(f"DEBUG: Added message UID={uid}, FROM={msg.getHeader('FROM')}")
        return defer.succeed(None)

    def search(self, query, uid=False):
        """
        Search messages matching the query.

        Supports: ALL, FROM <string>, SUBJECT <string>, SEEN, UNSEEN, etc.
        Returns list of sequence numbers (or UIDs if uid=True).
        """
        results = []

        for seq_num, msg in enumerate(self.messages, 1):
            if self._matches_query(msg, query):
                if uid:
                    results.append(msg.uid)
                else:
                    results.append(seq_num)

        return results

    def _matches_query(self, msg: SimpleMessage, query) -> bool:
        """Check if a message matches the search query."""
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
            elif query == 'FLAGGED':
                return '\\Flagged' in msg.flags
            elif query == 'UNFLAGGED':
                return '\\Flagged' not in msg.flags
            elif query == 'DELETED':
                return '\\Deleted' in msg.flags
            elif query == 'UNDELETED':
                return '\\Deleted' not in msg.flags

        # Handle tuple/list queries like ('FROM', 'address')
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
                    # Case-insensitive substring match
                    return value.lower() in from_header.lower()
                elif criterion == 'SUBJECT':
                    subject = msg.getHeader('SUBJECT') or ''
                    return value.lower() in subject.lower()
                elif criterion == 'TO':
                    to_header = msg.getHeader('TO') or ''
                    return value.lower() in to_header.lower()
                elif criterion == 'BODY':
                    body = msg.body.decode('utf-8', errors='replace')
                    return value.lower() in body.lower()
                elif criterion == 'TEXT':
                    # Search both headers and body
                    text = msg.body.decode('utf-8', errors='replace')
                    return value.lower() in text.lower()

        return False

    def store(self, messages, flags, mode, uid):
        """Store flags for messages."""
        result = {}
        for seq_num, msg in enumerate(self.messages, 1):
            check_val = msg.uid if uid else seq_num
            if check_val in messages:
                if mode == 1:  # +FLAGS
                    for flag in flags:
                        if flag not in msg.flags:
                            msg.flags.append(flag)
                elif mode == -1:  # -FLAGS
                    for flag in flags:
                        if flag in msg.flags:
                            msg.flags.remove(flag)
                else:  # FLAGS (replace)
                    msg.flags = list(flags)
                result[seq_num] = {'FLAGS': msg.flags}
        return defer.succeed(result)

    def expunge(self):
        """Remove messages marked as deleted."""
        deleted_uids = []
        self.messages = [m for m in self.messages if '\\Deleted' not in m.flags or (deleted_uids.append(m.uid) and False)]
        return deleted_uids

    def addListener(self, listener):
        self.listeners.append(listener)

    def removeListener(self, listener):
        if listener in self.listeners:
            self.listeners.remove(listener)

    def requestStatus(self, names):
        """Request mailbox status."""
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


class SimpleAccount(imap4.MemoryAccount):
    """A simple IMAP account."""

    def _emptyMailbox(self, name, id):
        return SimpleMailbox(name=name)

    def __init__(self, username):
        super().__init__(username)
        # Create INBOX by default
        try:
            self.addMailbox(b"INBOX")
        except:
            pass


@implementer(portal.IRealm)
class IMAPRealm:
    """Realm for IMAP authentication."""

    def requestAvatar(self, avatarId, mind, *interfaces):
        if imap4.IAccount in interfaces:
            account = SimpleAccount(avatarId.decode('utf-8') if isinstance(avatarId, bytes) else avatarId)
            return imap4.IAccount, account, lambda: None
        raise NotImplementedError("No supported interfaces")


class CustomIMAP4Server(imap4.IMAP4Server):
    """Custom IMAP4 Server with SEARCH support."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.selected_mailbox = None

    def lineReceived(self, line):
        print(f">>> {line.decode('utf-8', errors='replace')}")
        super().lineReceived(line)

    def sendLine(self, line):
        print(f"<<< {line.decode('utf-8', errors='replace') if isinstance(line, bytes) else line}")
        super().sendLine(line)

    def do_SEARCH(self, tag, query, uid=False):
        """Handle SEARCH command."""
        if self.mbox is None:
            self.sendNegativeResponse(tag, b'No mailbox selected')
            return

        # Parse the query
        query_parts = self._parse_search_query(query)
        print(f"DEBUG: SEARCH query={query}, parsed={query_parts}")

        # Perform search
        if hasattr(self.mbox, 'search'):
            results = self.mbox.search(query_parts, uid=uid)
        else:
            results = []

        # Send results
        if results:
            result_str = ' '.join(str(r) for r in results)
            self.sendUntaggedResponse(f'SEARCH {result_str}'.encode('utf-8'))
        else:
            self.sendUntaggedResponse(b'SEARCH')

        self.sendPositiveResponse(tag, b'SEARCH completed')

    def _parse_search_query(self, query):
        """Parse SEARCH query string into structured format."""
        # Twisted's arg_searchkeys returns a list of tokens
        if isinstance(query, list):
            # Join list back to string for parsing, or handle directly
            if len(query) >= 2:
                criterion = query[0]
                if isinstance(criterion, bytes):
                    criterion = criterion.decode('utf-8')
                criterion = criterion.upper()

                if criterion == 'FROM':
                    value = query[1]
                    if isinstance(value, bytes):
                        value = value.decode('utf-8')
                    return ('FROM', value)
                elif criterion == 'SUBJECT':
                    value = query[1]
                    if isinstance(value, bytes):
                        value = value.decode('utf-8')
                    return ('SUBJECT', value)
                elif criterion == 'TO':
                    value = query[1]
                    if isinstance(value, bytes):
                        value = value.decode('utf-8')
                    return ('TO', value)
            elif len(query) == 1:
                item = query[0]
                if isinstance(item, bytes):
                    item = item.decode('utf-8')
                return item.upper()

            # Fallback: join and parse as string
            query = ' '.join(q.decode('utf-8') if isinstance(q, bytes) else str(q) for q in query)

        if isinstance(query, bytes):
            query = query.decode('utf-8')

        query = query.strip()

        # Handle FROM "string" pattern
        from_match = re.match(r'FROM\s+"([^"]+)"', query, re.IGNORECASE)
        if from_match:
            return ('FROM', from_match.group(1))

        from_match = re.match(r'FROM\s+(\S+)', query, re.IGNORECASE)
        if from_match:
            return ('FROM', from_match.group(1))

        # Handle SUBJECT "string" pattern
        subj_match = re.match(r'SUBJECT\s+"([^"]+)"', query, re.IGNORECASE)
        if subj_match:
            return ('SUBJECT', subj_match.group(1))

        # Handle simple keywords
        if query.upper() in ['ALL', 'SEEN', 'UNSEEN', 'FLAGGED', 'UNFLAGGED', 'DELETED', 'UNDELETED']:
            return query.upper()

        return query

    # Make SEARCH available in select state
    select_SEARCH = (do_SEARCH, imap4.IMAP4Server.arg_searchkeys)
    auth_SEARCH = (do_SEARCH, imap4.IMAP4Server.arg_searchkeys)


class IMAP4ServerFactory(protocol.ServerFactory):
    """Factory for IMAP4 server."""
    protocol = CustomIMAP4Server

    def __init__(self, portal):
        self.portal = portal

    def buildProtocol(self, addr):
        p = self.protocol()
        p.portal = self.portal
        p.factory = self
        return p


def main():
    parser = argparse.ArgumentParser(description='IMAP Server for MR Testing')
    parser.add_argument('-p', '--port', type=int, default=1144, help='Port to listen on')
    args = parser.parse_args()

    # Create realm and portal
    realm = IMAPRealm()
    p = portal.Portal(realm)

    # Add credentials checker
    checker = checkers.InMemoryUsernamePasswordDatabaseDontUse()
    checker.addUser(b"testuser", b"testpass")
    p.registerChecker(checker)

    # Create factory
    factory = IMAP4ServerFactory(p)

    # Listen
    reactor.listenTCP(args.port, factory)

    print(f"IMAP Server started on port {args.port}")
    print("Credentials: testuser / testpass")
    print("Press Ctrl+C to stop")

    reactor.run()


if __name__ == "__main__":
    main()
