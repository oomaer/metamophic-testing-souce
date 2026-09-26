# Mutation Testing for Range Request Reconstruction MR

## Metamorphic Relation

**Two partial `GET`s must reconstruct the full body.**

- **A**: `GET /large` (no `Range`) → `200 OK`, full body
- **B**: `GET /large  Range: bytes=0-(k-1)` → `206`, part 1
        `GET /large  Range: bytes=k-`       → `206`, part 2
- **Oracle**: `body(part1) + body(part2) == body(full)`

The validator only inspects **body-concat equality** — it ignores status codes
and headers. Mutations that only touch headers/status should therefore NOT be
detected; that's a feature, not a bug (it's what makes M8/M9 the negative
controls).

## Mutations Applied (12 total)

| ID  | Name | Description | Expected Detection |
|-----|------|-------------|--------------------|
| M1  | Inclusive/exclusive end | `slice(start, end)` — treats end as exclusive; drops last byte per part | YES |
| M2  | Naive regex parser | `bytes=k-` parsed with `/(\d+)-(\d*)/`; empty `end` defaults to `start` | YES |
| M3  | Wrong Content-Length | Body is the right slice, but `Content-Length` = full file size | YES (CL check) |
| M4  | Case-sensitive header | `req.headers['Range']` (capitalized) — always undefined; falls back to full 200 body | YES (parse-fail) |
| M5  | Off-by-one open-ended | `bytes=k-` returns `[k, totalSize-2]` instead of `[k, totalSize-1]` | YES |
| M6  | URL-keyed cache | Second request for `/large` returns the cached first slice | YES |
| M7  | Buffer overrun | Appends 2 stray null bytes to every partial response (padded `Content-Length` reported honestly) | YES |
| M8  | Content-Range lies | `Content-Range` header is always `bytes 0-99/998`; body + Content-Length correct | NO  |
| M9  | 200 fallback | Returns `200 OK` with the correct partial slice | YES (parse-fail) |
| M10 | Keep-alive state leak | Prepends bytes from the prior response on the same socket | YES |
| M11 | Silent drop past threshold | `start > 512` returns empty 206 body | YES (parse-fail) |
| M12 | UTF-8 "safe boundary" | Snaps `end` down to the previous 8-byte boundary | YES |

## Mutation Categories

### Detectable via body-concat check (M1, M2, M5, M6, M7, M10, M12)
Anything that changes the **bytes** the client receives breaks
`part1_body + part2_body == full_body` and produces `[VIOLATION]`.

### Detectable via Content-Length consistency check (M3)
The validator also verifies that each partial response's `Content-Length`
header equals its actual body length. M3 sends the right bytes but a lying
header — a real RFC 7230 §3.3.2 violation.

### Detectable via grammar parse failure (M4, M9, M11)
When the target server returns something the grammar's regex can't match
(status 200 where 206 expected, or an empty body where `[\s\S]+` requires
≥1 byte), Fandango's generator raises. `script.py` catches this and emits
`[VIOLATION] Fandango generator raised — response did not match grammar`
so the mutation still counts as detected.

### Undetectable Negative Control (M8)
M8 only lies in the `Content-Range` header. The validator does not read
`Content-Range` (only body bytes and `Content-Length`), so this
semantically-equivalent-to-the-oracle mutation is not flagged — as
intended, to prove the MR discriminates.

## Usage

Run all mutations:
```bash
python run_mutations.py
```

Run a single mutation manually:
```bash
MUTATION=M1 node mutant-server-3001.js
# in another shell, from the MR directory:
python script.py
```

Generate the full analysis report:
```bash
python analyze_mutations.py     # -> mutation_results.txt
python summarize_logs.py        # -> summary.txt (compact per-log table)
```

## Files
- `mutant-server-3001.js` — Server B with all 12 mutations (MUTATION env-var flag)
- `run_mutations.py` — Orchestrator: spawns oracle + mutant, runs `script.py`, saves per-log
- `analyze_mutations.py` — Turns log counts into a scored `mutation_results.txt`
- `summarize_logs.py` — Cross-MR compact summary (`summary.txt`)
- `logs/log_M?.txt` — Per-mutation captured `test_output.log`
- `mutation_results.txt` — Final scoreboard
