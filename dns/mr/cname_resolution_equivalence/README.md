# DNS CNAME Resolution Equivalence - Metamorphic Relation

## Metamorphic Relation

**Property**: Querying a CNAME domain for a record type should return the same final records as directly querying the target domain for that type.

## Test Setup

Server configuration (in `dns_server.py`):
```
example.local → CNAME → test.local
test.local → A → 192.168.1.1, 192.168.1.2
```

## Test Queries

1. **Query A**: `example.local A`
   - Follows CNAME chain
   - Should return: CNAME record + A records of test.local

2. **Query B**: `test.local A`
   - Direct query to target
   - Should return: A records of test.local

## Metamorphic Relation

**Relation**: The A records returned by both queries must be identical.

```
A_records(CNAME_query) = A_records(direct_target_query)
```

## Files

- `grammar.fan` - Fandango grammar defining the MR
- `script.py` - Test runner (called by run_test.py)
- `run_test.py` - Main entry point (manages server lifecycle)
- `test_output.log` - Generated test log

## Running the Test

### Quick Run (Recommended)

```bash
python run_test.py
```

This will:
1. Start two DNS servers on ports 5053 and 5054
2. Run the metamorphic relation test
3. Generate `test_output.log`
4. Stop both servers

### Manual Run

If you prefer to manage the servers yourself:

**Terminal 1 - Start Server A:**
```bash
python ../../dns_server.py -p 5053
```

**Terminal 2 - Start Server B:**
```bash
python ../../dns_server.py -p 5054
```

**Terminal 3 - Run Test:**
```bash
python script.py test_output.log
```

## Expected Output

```
[CONNECTION] Switched to Server B (port 5054)
[DEBUG] CNAME query RCODE: NOERROR
[DEBUG] Target query RCODE: NOERROR
[DEBUG] CNAME response A record: 192.168.1.1
[DEBUG] CNAME response A record: 192.168.1.2
[DEBUG] Target response A record: 192.168.1.1
[DEBUG] Target response A record: 192.168.1.2
[PASS] CNAME resolution equivalence holds: {'192.168.1.1', '192.168.1.2'}
```

## Viewing Results

```bash
cat test_output.log
```

## What This Tests

1. **CNAME Chain Following**: Server correctly follows CNAME to target domain
2. **Transitive Resolution**: Final A records are returned after CNAME resolution
3. **Consistency**: Same A records whether queried via CNAME or directly

## Mutation Testing (Next Steps)

Future mutations to test detection capability:

### Mutation 1: Broken CNAME Chain
**Change**: Return CNAME but no target A records
```python
# In dns_server.py resolve() method
if qtype != 'CNAME' and 'CNAME' in zone:
    reply.add_answer(RR(..., CNAME(...)))
    # MUTANT: Comment out the following lines
    # target = zone['CNAME'][0]
    # if target in self.ZONE_DATA...
```
**Expected**: `[VIOLATION] A records differ! CNAME query returned: set(), Target query returned: {...}`

### Mutation 2: Incomplete Resolution
**Change**: Return only 1 A record instead of 2
```python
# In dns_server.py ZONE_DATA
'test.local.': {
    'A': ['192.168.1.1'],  # MUTANT: Removed second IP
```
**Expected**: `[VIOLATION] Missing in CNAME: {'192.168.1.2'}`

### Mutation 3: Wrong RCODE for CNAME
**Change**: Return NXDOMAIN when querying CNAME domain
```python
# In dns_server.py resolve() method
if qname == 'example.local.':  # MUTANT
    reply.header.rcode = RCODE.NXDOMAIN
    return reply
```
**Expected**: `[VIOLATION] Non-NOERROR response: CNAME=NXDOMAIN, Target=NOERROR`

### Mutation 4: Missing CNAME Record
**Change**: Skip adding CNAME to response
```python
# In dns_server.py resolve() method
if qtype != 'CNAME' and 'CNAME' in zone:
    # MUTANT: Comment out CNAME addition
    # reply.add_answer(RR(..., CNAME(...)))
    target = zone['CNAME'][0]
    # Continue with target resolution
```
**Expected**: Should still pass if A records are correct (tests final result, not intermediate records)

## Statistics

- **Grammar Constraints**: 1 main validation constraint
- **Network Parties**: 4 (ClientA, ServerA, ClientB, ServerB)
- **Query Types**: 2 (CNAME domain query, direct target query)
- **Test Duration**: ~10-30 seconds per run
