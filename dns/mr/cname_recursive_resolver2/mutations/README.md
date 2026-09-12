# DNS CNAME Recursive Resolver 2 - Mutation Testing

This directory contains mutation testing infrastructure for the
`cname_recursive_resolver2` metamorphic relation.

## Metamorphic Relation

The MR checks two properties of the recursive resolver:

1. The question forwarded upstream preserves the client's `(qname, qtype, qclass)`.
2. The final recursive response contains the same A-record set as the upstream
   response observed during the CNAME chase.

## Directory Structure

```text
mutations/
├── mutant_resolver.py      # Recursive resolver with BASELINE and M1-M7
├── run_mutations.py        # Runs baseline and selected mutants
├── analyze_mutations.py    # Summarizes generated logs
├── MUTATIONS.txt           # Mutation descriptions
├── README.md
├── .gitignore
└── logs/                   # Per-mutation logs, generated at runtime
```

## Running

```bash
cd dns/mr/cname_recursive_resolver2/mutations
python run_mutations.py
```

The runner starts:

- `dns_server.py --zone all` on `127.0.0.1:5053`
- `mutant_resolver.py` on `127.0.0.1:5055`
- resolver upstream as `127.0.0.1:5054`, where the grammar MITM listens

Then it runs the parent MR script and counts `[PASS]` and `[VIOLATION]`
markers in the output.

## Implemented Mutations

| ID | Name | Expected violation |
|----|------|--------------------|
| `BASELINE` | Clean baseline | None |
| `M1` | Rewrite qname to `test.local.` | Upstream qname mismatch |
| `M2` | Rewrite qtype to `AAAA` | Upstream qtype mismatch |
| `M3` | Rewrite qclass to `CH` | Upstream qclass mismatch |
| `M4` | Drop all A records | Missing chased A records |
| `M5` | Replace A records with wrong IP | A-record set mismatch |
| `M6` | Drop all but first A record | Incomplete A-record set |
| `M7` | Add fake extra A record | Extra A-record mismatch |
