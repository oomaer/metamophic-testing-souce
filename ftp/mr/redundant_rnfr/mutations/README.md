# FTP Redundant RNFR - Mutation Testing

This directory contains mutation testing infrastructure for the **Redundant RNFR** metamorphic relation.

## Metamorphic Relation

**Property tested:** Multiple RNFR (rename from) commands before RNTO (rename to) should work correctly, with the last RNFR determining which file gets renamed.

**Validation:**
1. RNTO response codes match between single-RNFR and multiple-RNFR sessions
2. Renamed directories appear in LIST output for both sessions

## Mutations Implemented

| ID | Name | Description | Expected Violation |
|----|------|-------------|-------------------|
| BASELINE | Clean baseline | Normal RNFR/RNTO behavior | None (0 violations) |
| M1 | FIRST_RNFR_WINS | Only first RNFR stored; later ignored | LIST fails to find target_b |
| M2 | REJECT_REDUNDANT_RNFR | Second RNFR returns 503 error | RNTO response codes differ |
| M3 | CLEAR_STATE_ON_RNFR | Each RNFR clears pending state | RNTO fails with 503 |
| M5 | RENAME_WRONG_TARGET | RNTO renames wrong directory | LIST verification fails |
| M6 | WRONG_RNTO_SUCCESS_CODE | RNTO returns 200 instead of 250 | Response codes differ |

## Directory Structure

```
mutations/
├── mutant_server.py        # Dual FTP server (baseline + mutant)
├── run_mutations.py        # Orchestrator (runs all mutations)
├── analyze_mutations.py    # Results analyzer
├── .gitignore             # Excludes logs and results
└── logs/                  # Per-mutation output (generated)
    ├── log_BASELINE.txt
    ├── log_M1.txt
    ├── log_M2.txt
    ├── log_M3.txt
    ├── log_M5.txt
    └── log_M6.txt
```

## Running Mutation Tests

### Full Test Suite

Run all mutations (6 tests: BASELINE + 5 mutants):

```bash
cd mutations/
python run_mutations.py
```

**Expected output:**
- BASELINE: 0 violations (all tests pass)
- M1, M2, M3, M5, M6: >0 violations (mutations detected)
- Mutation score: 5/5 (100%)

### Single Mutation

Test a specific mutation manually:

```bash
# Start mutant server
python mutant_server.py --mutation M1

# In another terminal, run the test
cd ..
python script.py
```

### Analyze Results

After running tests, generate summary:

```bash
python analyze_mutations.py
```

## Server Architecture

**Dual-server design:**
- **Server A (port 2121):** Always runs BASELINE (normal pyftpdlib)
- **Server B (port 2122):** Runs selected mutation

**Data directories:**
- `ftp/data/server_a/` - Session A data (baseline)
- `ftp/data/server_b/` - Session B data (mutant)

Each test run:
1. Clears data directories
2. Starts both servers
3. Runs metamorphic test via Fandango
4. Captures [VIOLATION] markers
5. Logs results to `logs/log_<mutation>.txt`

## Mutation Implementation

### M1: FIRST_RNFR_WINS
```python
def ftp_RNFR(self, path):
    if self._first_rnfr_target is None:
        self._first_rnfr_target = path
        return super().ftp_RNFR(path)
    else:
        # Ignore, but respond as accepted
        self.respond("350 Ready for destination name")
        return
```

### M2: REJECT_REDUNDANT_RNFR
```python
def ftp_RNFR(self, path):
    if self._rnfr_called:
        self.respond("503 Bad sequence of commands")
        return
    self._rnfr_called = True
    return super().ftp_RNFR(path)
```

### M3: CLEAR_STATE_ON_RNFR
```python
def ftp_RNFR(self, path):
    self.fs.rnfr = None  # Clear before
    result = super().ftp_RNFR(path)
    self.fs.rnfr = None  # Clear after
    return result
```

### M5: RENAME_WRONG_TARGET
```python
def ftp_RNTO(self, path):
    if self.fs.rnfr:
        self.fs.rnfr += "_wrong"  # Wrong source
    return super().ftp_RNTO(path)
```

### M6: WRONG_RNTO_SUCCESS_CODE
```python
def ftp_RNTO(self, path):
    # Perform rename...
    self.respond("200 Renaming ok")  # Wrong code
    return path
```

## Expected Results

| Mutation | Passes | Violations | Detected | Reason |
|----------|--------|------------|----------|--------|
| BASELINE | >0 | 0 | N/A | Normal operation |
| M1 | 0 | >0 | YES | LIST fails to find renamed_b |
| M2 | 0 | >0 | YES | RNTO codes differ (250 vs 5xx) |
| M3 | 0 | >0 | YES | RNTO fails (503 Bad sequence) |
| M5 | 0 | >0 | YES | RNTO fails (wrong target) |
| M6 | 0 | >0 | YES | Codes differ (250 vs 200) |

**Mutation Score:** 5/5 (100%) - All mutations should be detected

## Troubleshooting

**Server fails to start:**
- Check pyftpdlib path in mutant_server.py (line 16)
- Verify venv exists: `/Users/i7949486/Desktop/uds/thesis/mutation/pyftpdlib/venv`
- Check ports 2121/2122 are free: `lsof -i :2121`

**No violations detected:**
- Check server logs in mutations folder
- Verify grammar.fan constraint function is working
- Run single mutation manually to see detailed output

**Tests timeout:**
- Increase timeout in run_mutations.py (line 100)
- Check for hung server processes: `pkill -9 -f mutant_server`

## Files

- **mutant_server.py** - Mutation server implementation (265 lines)
- **run_mutations.py** - Test orchestrator (295 lines)
- **analyze_mutations.py** - Results analyzer (175 lines)
- **logs/** - Test output per mutation (auto-generated)
