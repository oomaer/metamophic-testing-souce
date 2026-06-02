# AGENTS.md

This file provides guidance to Codex (Codex.ai/code) when working with code in this repository.

## Project Overview

This repository implements **metamorphic testing** for network protocols using the **Fandango** fuzzing framework. Metamorphic testing validates protocol implementations by comparing outcomes of semantically equivalent operations (e.g., "does sending recipients in different orders produce the same result?").

## Running Tests

### SMTP Tests (Primary Focus)

Start the SMTP test servers:
```bash
cd mt-smtp/docker/opensmtpd
docker-compose up -d
```

Run a metamorphic relation test:
```bash
python mt-smtp/MRs/state_reset/script.py
python mt-smtp/MRs/repeated_recipient/script.py
```

Run via Fandango CLI:
```bash
fandango -v talk -f mt-smtp/MRs/state_reset/grammar.fan -n 1
```

### HTTP Tests
```bash
python mt-http/test-http.py
```

### DNS Tests

Run CNAME Resolution Equivalence MR test:
```bash
cd dns/mr/cname_resolution_equivalence
python run_test.py
```

This will:
1. Start two DNS servers on ports 5053 and 5054
2. Run the metamorphic relation test
3. Save results to `test_output.log`

## Architecture

### Grammar Files (`.fan`)

Fandango grammar files define:
1. **Protocol message sequences** using BNF-like syntax
2. **Multi-party communication** with `<Party:message>` syntax
3. **Metamorphic constraints** using `where` clauses

Example structure:
```
<start> ::= <Interaction1> <ChangeConnection> <Interaction2>
where validateResponses(<response_A>, <response_B>)
```

### Utils Files (`*-utils.fan`)

Define `NetworkParty` subclasses for each protocol:
- `ClientA/ServerA` - First connection (port 8026 for SMTP, 5053 for DNS)
- `ClientB/ServerB` - Second connection (port 8027 for SMTP, 5054 for DNS)
- Connection management functions (`changeConnection()`, `resetConnection()`)
- Response validation functions
- For DNS: Custom send/receive methods with compression/decompression

### MR (Metamorphic Relation) Structure

Each MR test lives in `mt-smtp/MRs/<relation_name>/`:
- `grammar.fan` - Protocol grammar with the metamorphic relation
- `script.py` - Python runner using Fandango API

### Fandango API Usage

```python
from fandango.evolution.algorithm import Fandango, LoggerLevel
from fandango.language.grammar import FuzzingMode
from fandango.language.parse.parse import parse

with open(grammar_path) as f:
    grammar, constraints = parse(f, use_stdlib=False)
fandango = Fandango(grammar=grammar, constraints=constraints, logger_level=LoggerLevel.INFO)
for solution in fandango.generate(mode=FuzzingMode.IO):
    # solution is a generated test case
```

### Protocol Ports

- **SMTP**: 8026 (ServerA), 8027 (ServerB) - mapped from container port 8025
- **DNS**: 5053 (ServerA), 5054 (ServerB) - UDP protocol, dnslib server
- **FTP**: 2121 (control), 50100 (data)
- **MQTT**: 1883
- **IMAP**: Standard ports in docker

## Key Patterns

### Multi-Party Grammar Syntax
```
<ClientA:request_ehlo>        # Client A sends
<ServerA:response_ehlo>       # Server A responds
<ChangeConnection> ::= r".*" := changeConnection()  # Switch to connection B
```

### Metamorphic Constraint Pattern
```
where validateResponses(<response_A>, <response_B>)

def validateResponses(responseA, responseB):
    codeA = responseA[:3]
    codeB = responseB[:3]
    return codeA == codeB  # Must match for relation to hold
```
These always return True, because execution stops if a contraint is violated, 
but we want to continue the next solution, So we print out voilation ([VIOLATION] detailed message) and detect it in the script and just continue.

### Dynamic Grammar Generation

Some tests (like `smtp.py`) dynamically generate grammar by:
1. Using Fandango to generate input variations
2. String-replacing placeholders in template grammars
3. Running the generated grammar through Fandango

To generate more test-cases / solutions, Fandango uses k-paths. It works in a tree that if unique non-terminals are visited or not. Make use of it to generate more test cases.

## Mutation Testing 
For each protocol, we will perform mutation testing, we will plant seeded faults/bugs in our test target and check if our framework catches those bugs. The mutation testing is not of entire protocol but of a single MR, and they must be related to the MR and be meaningful according to the MR. 


## Protocols Supported

- `mt-smtp/` - SMTP with AUTH LOGIN (primary, most developed)
- `dns/` - DNS protocol with dnslib server, CNAME Resolution Equivalence MR
- `mt-http/` - HTTP header ordering tests
- `ftp/` - FTP multi-party interactions
- `imap/` - IMAP session testing
- `mqtt/` - MQTT broker communication
