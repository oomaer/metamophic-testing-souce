Mutation implementation review — 2026-10-01

The implementations do not all match their descriptions. Several mutants cause the wrong failure, duplicate another mutant, or affect operations outside their stated scope.

Review covered all **51 active mutants across MR1–MR8**, using the current runner descriptions, server implementations, grammar assertions, and installed library code. No mutation implementations were changed during this review.

**Confirmed findings, in priority order**

1. **MR5-M4: RNFR wrong-code mutation is broken.** At `ftp/mr/redundant_rnfr/mutations/mutant_server.py:124`, the handler runs `ftp2fs` on an already translated filesystem path. An existing source consequently produces 550. It also assigns `self.fs.rnfr`, whereas the installed pyftpdlib RNTO reads `self._rnfr`. Direct execution with real temporary files produced `550, 550, 503`, not the intended `250, 250, 250`. Preserve the base RNFR validation/state handling and substitute only its successful 350 response.

2. **MR1-M3 never accepts the third occurrence.** At `smtp/mr/repeated_recipient/mutations/mutant_server.py:68`, it tests the number of accepted recipients. Rejecting the second occurrence leaves that count at 1, so every following duplicate is also rejected. Observed sequence: `250, 550, 550, 550`, rather than `250, 550, 250, 250`. Track whether the first duplicate rejection already happened, independently of accepted recipients.

3. **MR7-M2 does not flush on re-SELECT.** At `imap/mr/append_search_inclusion/mutations/mutant_server.py:419`, `do_SELECT` tries to override a method the installed Twisted parent does not have. SELECT dispatch uses `_selectWork`; neither auth_SELECT nor select_SELECT invokes the custom method. After three APPENDs and a real SELECT dispatch, search still returned `[]` and all 3 entries remained pending. Hook successful selection in the actual Twisted dispatch path. Merely calling the custom `do_SELECT` would also raise AttributeError at `super().do_SELECT`.

4. **MR2-M1 and MR2-M5 are equivalent in the tested behavior; neither preserves the actual transaction.** `aiosmtpd.SMTP.smtp_RSET` clears the envelope before invoking `handle_RSET`. The mutation handlers at `smtp/mr/state_reset/mutations/mutant_server.py:108` preserve only `session.mutation_state['mail_from_set']`. Both leave actual sender `None` and recipients `[]`, then reject later MAIL with 503. M5 therefore is not a genuine no-op reset. M4 also changes only this shadow flag, though it does produce the advertised first-reset/second-reset MAIL difference. To model distinct buffer/reset faults, mutate the SMTP reset implementation or explicitly preserve/restore the intended envelope fields.

5. **MR6 upload hooks also affect STOR.** `ftp/mr/size_after_appe/mutations/mutant_server.py:113` applies append mutations from `on_file_received` without checking whether that transfer was APPE. M7 turns a fresh 100-byte STOR into 102 bytes; M4 reports 101 for that fresh 100-byte file. The current grammar performs STOR before its append sequence, so these are effects outside the intended APPE fault. M3 also retains append totals across replacement STOR: after two 20-byte appends, a fresh 100-byte STOR reports 140, and another 20-byte append reports 180 instead of the intended 140. Restrict APPE hooks and reset cached state on replacement STOR. Separately, M4's offset is consumed by the first SIZE, so its description should say "next SIZE only" if that is intentional.

6. **MR1-M2 has a threshold mismatch.** Its runner describes accepting the first 2 occurrences and rejecting the 3rd onward. `smtp/mr/repeated_recipient/mutations/mutant_server.py:61` uses 10: the probe accepted occurrences 1–10 and rejected 11–12. Choose the intended threshold and align both descriptions and implementation.

7. **Other labels/duplicates need clarification.** MR5-M3 restores the first RNFR source and therefore duplicates MR5-M1 for the valid repeated-RNFR case. Its current full description acknowledges this, but SILENT_STATE_CLEAR is misleading. MR5-M5 deliberately chooses a nonexistent source and fails, rather than renaming a random existing source. MR7-M3 indexes odd-numbered appends, although the runner says every second message. MR4-M3 returns an empty 206 response rather than dropping a request without response. DNS M6 keeps just one A record rather than necessarily removing exactly one.

**Per-mutant observations**

"Matches" means the stated behavior was observed in the bounded direct probes below; it is not a claim that every input or complete Fandango run is correct.

| Mutant | Assessment | Observed behavior |
| --- | --- | --- |
| MR1-M1 | Matches | First recipient accepted; repeated recipient rejected with 550. |
| MR1-M2 | Mismatch | Runner says accept first 2/reject 3rd+, but code accepts 10 and rejects 11th+. |
| MR1-M3 | Incorrect | Responses are 250, 550, 550, ...; third and later occurrences never recover. Same duplicate behavior as M1. |
| MR1-M4 | Matches | A duplicate inserts unexpected-recipient@example.com and returns 250. |
| MR1-M5 | Matches | A duplicate produces two separate 250 response lines. |
| MR1-M6 | Matches within one transaction | After a duplicate, a different recipient is also rejected. The poison flag is handler-wide, not per session. |
| MR2-M1 | Partial / duplicate | Sender envelope is actually cleared; a separate stale flag makes later MAIL return 503. Same tested behavior as M5. |
| MR2-M2 | Matches | RSET clears authenticated and later MAIL is rejected with 530. |
| MR2-M3 | Matches | RSET returns 500. Underlying envelope is still reset before that response. |
| MR2-M4 | Partial | MAIL succeeds after first RSET and fails after second. Actual envelope is reset on every RSET; only the separate flag stops clearing. |
| MR2-M5 | Incorrect as a full no-op | RSET clears the envelope and recipients in aiosmtpd. Only a stale flag remains, duplicating M1 rather than preserving the transaction. |
| MR3-M1 | Matches | Connection: close changes status to 201; keep-alive stays 200. |
| MR3-M2 | Matches | Connection: close changes status to 500; keep-alive stays 200. |
| MR3-M3 | Matches | Connection: close returns 204 with an empty body. |
| MR3-M4 | Matches | Connection: close returns 200 with an empty body. |
| MR3-M5 | Matches | Connection: close selects chunked encoding with the same JSON body. Expected survivor for the current status/body comparison. |
| MR4-M1 | Matches | Inclusive end is treated as exclusive; each partial body loses its final byte. |
| MR4-M2 | Matches | An open-ended range returns one byte instead of the remaining suffix. |
| MR4-M3 | Clarify description | For start > 512 it sends an empty 206 response. It does not drop the connection or omit a response; lower offsets are unchanged. |
| MR4-M4 | Matches | Case-sensitive header lookup misses Node-normalized range and returns the full body with 200. |
| MR4-M5 | Matches | Open-ended suffix omits the final file byte; closed ranges are unchanged. |
| MR4-M6 | Matches | Second range for the same URL returns the first cached range. |
| MR4-M7 | Matches | Each partial body receives two extra NUL bytes and a matching padded Content-Length. |
| MR4-M8 | Matches | Content-Range is false but body slices reconstruct correctly. Expected survivor for the current body comparison. |
| MR4-M9 | Matches | Correct partial body is returned with 200 rather than 206; current grammar requires 206. |
| MR5-M1 | Matches | After RNFR first, RNFR second, RNTO target, the FIRST content is renamed. |
| MR5-M2 | Matches | Second RNFR returns 503; first source remains pending. |
| MR5-M3 | Duplicate behavior | Matches the current description of restoring the first source, but duplicates M1 on valid repeated-RNFR sequences. It does not clear the pending source. |
| MR5-M4 | Incorrect | Existing sources return 550, then RNTO returns 503, instead of changing only RNFR success from 350 to 250. |
| MR5-M5 | Clarify description | Selects a deliberately nonexistent source, so RNTO fails with 550. It does not successfully rename another/random existing directory. |
| MR5-M6 | Matches | Rename succeeds using the last source, with a single 200 success response instead of 250. |
| MR6-M1 | Matches | Appended bytes are discarded; size remains at pre-append length. |
| MR6-M2 | Matches | Data is appended but SIZE returns the size before the latest append. |
| MR6-M3 | Extra state defect | Double-counts appended bytes, but the accumulated count survives a fresh STOR and contaminates later test cases. |
| MR6-M4 | Partial / extra effect | Adds 1 only to the next SIZE, then consumes the offset. Also installs the offset on STOR, not only APPE. |
| MR6-M5 | Matches | Only half of each appended payload is retained. |
| MR6-M6 | Matches | APPE truncates the previous content and stores only the new payload. |
| MR6-M7 | Extra effect | Adds CRLF after APPE as stated, but also after STOR, corrupting the initial test file before any append. |
| MR7-M1 | Matches | Messages are stored but absent from search results. |
| MR7-M2 | Incorrect | Messages remain pending even after actual Twisted SELECT dispatch; the supposed flush override is never called. |
| MR7-M3 | Description mismatch | Indexes appends 1, 3, 5, ...; runner says only every second message (normally 2, 4, 6, ...). Alternation is implemented, but the stated phase differs. |
| MR7-M4 | Matches | Search index stores a FROM header truncated before @; full-address searches fail. |
| MR7-M5 | Matches | Search index contains each message twice and search returns duplicate sequence numbers. |
| MR7-M6 | Matches | Uppercase address search misses lowercase stored address; same-case search succeeds. |
| MR8-M1 | Matches | Changes upstream qname to test.local.; naturally no change when that was already the requested name. |
| MR8-M2 | Matches | Changes upstream qtype from A (1) to AAAA (28). |
| MR8-M3 | Matches | Changes upstream qclass from IN (1) to CH (3). |
| MR8-M4 | Matches | Removes A records across answer, authority, and additional sections, retaining non-A records. |
| MR8-M5 | Matches | Replaces all A addresses with 10.10.10.10. |
| MR8-M6 | Matches description | Keeps only the first A across all sections. With 3 A records it removes 2, despite the MISSING_ONE_A_RECORD label. |
| MR8-M7 | Matches | Adds an answer A record containing 192.168.1.99. |

**Validation method and limits**

- SMTP: called real asynchronous handler methods with real aiosmtpd envelopes; for MR2, invoked the installed SMTP RSET implementation. Checked 12 repeated recipient commands plus a new recipient, and two MAIL/RSET cycles.
- FTP RNFR: invoked actual mutant handlers and installed pyftpdlib filesystem/rename methods on temporary files; compared which source moved and every reply code.
- FTP SIZE: actual files and mutation methods, with the network transfer replaced by a deterministic 20-byte append followed by the real completion hook. Checked two appends, a fresh replacement STOR, and another append. These were callback-level probes, not socket-level transfers.
- IMAP: actual mailbox methods and installed Twisted SELECT dispatch, with protocol response output stubbed. Checked three APPENDs, mixed-case searches, and delayed-index re-selection.
- HTTP: executed actual JavaScript server request callbacks using Node VM and a fake HTTP transport. Checked both connection-header endpoints, keep-alive versus close, range reconstruction, and a high-offset range. Baseline range reconstruction matched the oracle's 998-byte body. These probes inspect response status/headers/body before Node wire serialization.
- DNS: exercised actual request/response mutation functions and serialized/parsed the resulting DNS packets, including A records in all three RR sections and a retained TXT record.
- The three disabled HTTP MR4 mutations M10–M12 were also probed: M10 prepends up to 8 stale bytes; M11 advertises full-file length for a partial body; M12 rounds the end to an 8-byte boundary. They are not in the active runner list.
- No protocol servers were launched, existing experiment logs were not overwritten, and no full Fandango campaign was run. Temporary probe scripts and machine-readable observations are at `/tmp/mutation_implementation_audit/`.

**Separate experiment-harness concerns**

The root analyzer treats generic FandangoError as detection. The recently observed internal grammar-navigation crash can therefore be counted as a killed mutant even when it is not evidence of the intended server fault. Also, several runners read child stdout with blocking `readline()` before reaching `wait(timeout=...)`; those per-mutant timeouts do not bound a child stuck before EOF. These are separate from the mutant semantics reviewed above and should be considered before interpreting mutation scores.

DNS forwarding through port 5054 is intentional in the current grammar: MimServer opens that port and forwards to the authoritative server at 5053. It is not a port mismatch in this architecture.
