# IMAP Append+Search Metamorphic Relation

## Overview

This metamorphic relation tests that newly appended messages are immediately searchable.

## Metamorphic Relation

**Source Test Case**:
```
SEARCH FROM "unique-mr-test@example.com"
→ * SEARCH (0 results)
```

**Follow-up Test Case**:
```
APPEND INBOX message with From: unique-mr-test@example.com
SEARCH FROM "unique-mr-test@example.com"
→ * SEARCH 1 (1 result)
```

**Relation**: `|follow-up results| == |source results| + 1`

## Running the Test

```bash
# Run the full test (starts server automatically)
python run_test.py

# Or manually:
# Terminal 1: Start server
python imap_server.py

# Terminal 2: Run test
python script.py
```

## Files

- `grammar.fan` - Fandango grammar with MR validation constraint
- `grammar-utils.fan` - NetworkParty setup (Client/Server on port 1144)
- `imap_server.py` - Custom IMAP server with SEARCH support (based on Twisted)
- `script.py` - Fandango test runner
- `run_test.py` - Server lifecycle manager
- `test_output.log` - Test results

## Bugs Detected

This MR can detect:
- **M1**: Search index not updated after APPEND
- **M2**: APPEND returns OK but message not stored
- **M3**: Header parsing bugs (FROM field not indexed)
- **M4**: Race condition between APPEND and SEARCH
- **M5**: Case sensitivity bugs in FROM matching

## Server Credentials

- Username: `testuser`
- Password: `testpass`
- Port: `1144`
