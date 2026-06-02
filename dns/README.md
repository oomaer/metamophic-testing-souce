# DNS Metamorphic Testing with Fandango

DNS protocol testing using Fandango grammar and dnslib server for mutation testing support.

## Structure

```
dns/
├── dns_server.py           # dnslib-based DNS server (mutable)
├── dns-utils.fan           # Compression/decompression utilities
├── dns.fan                 # Main DNS protocol grammar
├── script.py               # Basic DNS test runner
└── mr/                     # Metamorphic Relations
    └── cname_resolution_equivalence/
        ├── grammar.fan     # CNAME MR grammar
        ├── script.py       # CNAME MR test runner
        ├── run_test.py     # Server lifecycle manager
        ├── test_output.log # Test results (generated)
        └── README.md       # Detailed MR documentation
```

## Setup

The `dnslib` library is already included in `../dnslib/`.

## Running Tests

### 1. Start DNS Server

```bash
python dns/dns_server.py
```

Server configuration:
- Port: 5053
- Zones: test.local, example.local
- Records: A, AAAA, CNAME, MX, TXT, NS

### 2. Run Basic DNS Tests

```bash
python dns/script.py
```

This runs general DNS protocol testing with Fandango.

### 3. Run CNAME Metamorphic Relation Test

**Recommended** (manages server lifecycle automatically):
```bash
cd dns/mr/cname_resolution_equivalence
python run_test.py
```

This will:
1. Start two DNS servers on ports 5053 and 5054
2. Run the CNAME metamorphic relation test
3. Save results to `test_output.log`
4. Clean up servers on exit

**Manual run**:
```bash
# Terminal 1
python dns_server.py -p 5053

# Terminal 2
python dns_server.py -p 5054

# Terminal 3
cd dns/mr/cname_resolution_equivalence
python script.py test_output.log
```

Or via Fandango CLI:
```bash
fandango -v talk -f dns/mr/cname_resolution_equivalence/grammar.fan -n 1
```

## Metamorphic Relations

### CNAME Resolution Equivalence

**Relation**: Querying a CNAME domain for a record type should return the same final records as directly querying the target domain.

**Test Setup** (Two-server configuration):
- Server A (port 5053): Handles CNAME query
- Server B (port 5054): Handles direct target query
- `example.local` → CNAME → `test.local`
- `test.local` → A → `192.168.1.1`, `192.168.1.2`

**Test Queries**:
1. Query A (Server A): `example.local A` (follows CNAME chain)
2. Query B (Server B): `test.local A` (direct query)

**Expected**: The A records returned by both queries should be identical.

**What it tests**:
- CNAME chain following
- Transitive resolution
- Correct target record retrieval

**Status**: ✅ Implemented and passing

## Mutation Testing (Future)

The `dns_server.py` can be mutated to introduce bugs:

### Potential Mutations for CNAME Testing

1. **Broken CNAME Chain**
   - Return CNAME but no target A records
   - MR should detect: CNAME query returns empty, target query returns records

2. **Incomplete Resolution**
   - Return CNAME and only 1 A record instead of 2
   - MR should detect: Missing records in CNAME response

3. **Wrong Target**
   - CNAME points to wrong domain
   - MR should detect: Different A records

4. **NXDOMAIN for CNAME**
   - Return NXDOMAIN when querying CNAME domain
   - MR should detect: CNAME query fails, target query succeeds

5. **Missing CNAME Record**
   - Return only A records without CNAME record
   - MR should still pass if A records are correct

## DNS Server Zone Data

Current server configuration in `dns_server.py`:

```python
ZONE_DATA = {
    'test.local.': {
        'A': ['192.168.1.1', '192.168.1.2'],
        'AAAA': ['2001:db8::1'],
        'MX': [(10, 'mail.test.local.')],
        'TXT': ['v=spf1 include:test.local ~all'],
        'NS': ['ns1.test.local.', 'ns2.test.local.'],
    },
    'example.local.': {
        'A': ['10.0.0.1'],
        'CNAME': ['test.local.'],  # ← CNAME for testing
    },
    # ... more domains
}
```

## Testing with dig

You can manually test the server:

```bash
# Test CNAME resolution
dig @127.0.0.1 -p 5053 example.local A

# Test direct target query
dig @127.0.0.1 -p 5053 test.local A

# Both should return the same A records (192.168.1.1, 192.168.1.2)
```

## Next Steps

1. ✅ Basic DNS grammar created
2. ✅ CNAME Resolution Equivalence MR implemented
3. ⏭️ Add mutation testing for CNAME MR
4. ⏭️ Implement additional MRs (Query Order, Case Insensitivity, etc.)
