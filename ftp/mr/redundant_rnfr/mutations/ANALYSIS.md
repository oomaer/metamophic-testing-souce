# Mutation Testing Analysis: FTP Redundant RNFR

## Current Status: 0/5 mutations detected (0% mutation score)

## Root Cause Analysis

### The Metamorphic Relation

**Property being tested:** Multiple RNFR commands before RNTO should work correctly.

**Current grammar behavior:**
- Session A: `MKD testdir_a` → `RNFR testdir_a` → `RNTO renamed_a`
- Session B: `MKD testdir_b` → `RNFR testdir_b` → `RNFR testdir_b` → `RNTO renamed_b`

**Key issue:** ALL redundant RNFR commands send the **SAME path** (`testdir_b`).

### Why Mutations Aren't Detected

#### M1: FIRST_RNFR_WINS
- **Expected:** Only first RNFR stored, later ones ignored
- **Actual:** First and second RNFR both send `testdir_b`, so it doesn't matter which one wins
- **Result:** PASS (no violation detected)

#### M2: REJECT_REDUNDANT_RNFR
- **Expected:** Second RNFR returns 503
- **Actual:** Second RNFR DOES return 503 (mutation working!)
- **Problem:** First RNFR already set `fs.rnfr = testdir_b`, so RNTO still succeeds
- **Result:** PASS (no violation detected)

#### M3: CLEAR_STATE_ON_RNFR  
- **Expected:** Each RNFR clears pending state → RNTO should fail
- **Actual:** Mutation is applied but grammar accepts 350 response
- **Problem:** Even with cleared state, pyftpdlib recovers or tests pass
- **Result:** PASS (66 passes, 0 violations)

#### M5: RENAME_WRONG_TARGET
- **Expected:** RNTO renames wrong directory → fails or LIST verification fails
- **Actual:** Sets `fs.rnfr = testdir_b_wrong`, RNTO should fail
- **Problem:** Mutation might not be effective enough
- **Result:** PASS (no violation detected)

#### M6: WRONG_RNTO_SUCCESS_CODE
- **Expected:** Returns 200 instead of 250 → code mismatch detected
- **Actual:** Implementation causes server timeout/hang
- **Problem:** Response handling is breaking the FTP protocol flow
- **Result:** CRASH (server hangs)

## The Fundamental Problem

**The MR doesn't test "last RNFR wins" - it tests "redundant RNFR on same file works".**

To properly test "last RNFR wins", the grammar needs:
- Session A: `RNFR file1` → `RNTO renamed1`
- Session B: `RNFR file1` → `RNFR file2` → `RNTO renamed2`

Then:
- Normal behavior: `file2` gets renamed (last RNFR wins)
- M1 bug: `file1` gets renamed (first RNFR wins) → **VIOLATION**

But the current MR doesn't have multiple source files created.

## Solutions

### Option 1: Fix the Grammar (Proper "Last RNFR Wins" Test)

Modify the grammar to create multiple directories and use different RNFR targets:

```
# Session B
<create_multiple_dirs_B> ::= <mkd_B1> <mkd_B2>
<mkd_B1> ::= "MKD testdir_b1\r\n"
<mkd_B2> ::= "MKD testdir_b2\r\n"

# Different RNFR targets
<double_rnfr> ::= 
  "RNFR testdir_b1\r\n" <response>
  "RNFR testdir_b2\r\n" <response>

# Then RNTO - should rename testdir_b2 (last one)
<rnto_B> ::= "RNTO renamed_b\r\n"
```

**Pros:**
- Actually tests "last RNFR wins" property
- M1 would be detectable
- More meaningful MR

**Cons:**
- Requires significant grammar rewrite
- Changes the MR being tested

### Option 2: Accept Weaker Mutations

Keep current MR but use mutations that ARE detectable:

**M2 (Modified): REJECT_ALL_RNFR_AFTER_FIRST**
```python
def ftp_RNFR(self, path):
    if self._rnfr_called:
        self.respond("503 Bad sequence of commands")
        # ALSO clear the first RNFR state
        self.fs.rnfr = None
        return
    self._rnfr_called = True
    return super().ftp_RNFR(path)
```
Now RNTO will fail → **VIOLATION**

**M4 (New): NO_RNTO_AFTER_REDUNDANT**
```python
def ftp_RNTO(self, path):
    # If we had redundant RNFRs, fail
    if hasattr(self, '_rnfr_count') and self._rnfr_count > 1:
        self.respond("503 Redundant RNFR not allowed")
        return
    return super().ftp_RNTO(path)
```
RNTO fails in Session B → **VIOLATION**

**M6 (Simplified): WRONG_RNTO_CODE_SIMPLE**
```python
def ftp_RNTO(self, path):
    # Do the rename
    result = super().ftp_RNTO(path)
    # Don't try to override response - just change what we check
    return result
```
Actually, M6 can't work by overriding because super() already sent the response.

### Option 3: Different MR Entirely

Test a different property that's easier to mutate:

**"RNFR without RNTO should be idempotent"**
- Session A: `RNFR file` → `RNTO renamed`
- Session B: `RNFR file` → `RNFR file` → `RNFR file` → `RNTO renamed`

Easier mutations:
- M1: Counter that limits RNFR calls
- M2: State corruption after multiple RNFRs
- M3: RNTO fails if >1 RNFR

## Recommendation

**I recommend Option 1** (fix the grammar) because:
1. It properly tests the "last RNFR wins" semantic
2. Makes M1 detectable (the most important mutation)
3. More meaningful and realistic MR
4. Aligns with what the MR description claims to test

Would you like me to:
A. Implement Option 1 (rewrite grammar for "last RNFR wins")
B. Implement Option 2 (strengthen existing mutations)
C. Keep current implementation and document known limitations
