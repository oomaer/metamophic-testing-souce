#!/usr/bin/env python3
"""
DNS CNAME Resolution Equivalence MR — Test Runner (Recursive Resolver)

Launches an authoritative server plus a recursive resolver forwarding to it:
  - Server A     (:5053) — dns_server.py --zone all
                           (authoritative for both example.local. + test.local.)
  - Recursive R. (:5055) — dns_recursive_resolver.py -u 127.0.0.1:5053
                           (system under test; forwards every query to Server A)

The MR (see grammar.fan) checks:
  A-records reached via the recursive resolver
    ==
  A-records reached directly from the authoritative server
"""

import subprocess
import os
import sys
import time
from pathlib import Path


def format_duration(seconds):
    if seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        m = int(seconds // 60); s = seconds % 60
        return f"{m}m {s:.2f}s"
    else:
        h = int(seconds // 3600); m = int((seconds % 3600) // 60); s = seconds % 60
        return f"{h}h {m}m {s:.2f}s"


def main():
    script_dir = Path(__file__).resolve().parent
    output_dir = Path(os.environ.get("MR_RUNS_DIR", script_dir / "runs")).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    dns_dir = script_dir.parent.parent
    dns_server_path = dns_dir / "dns_server.py"
    recursive_resolver_path = dns_dir / "dns_recursive_resolver.py"

    print("=" * 80)
    print(" DNS CNAME Resolution Equivalence MR — Test Runner (Recursive Resolver)")
    print("=" * 80)
    print()

    # Kill any existing DNS test servers / resolvers
    print("Cleaning up any existing DNS servers...")
    subprocess.run(['pkill', '-f', 'dns_server.py'], capture_output=True)
    subprocess.run(['pkill', '-f', 'dns_recursive_resolver.py'], capture_output=True)
    time.sleep(1)

    # Server A — authoritative for BOTH zones (alias + target). It holds the
    # CNAME chain (example.local. -> test.local.) and the A records. Using
    # --zone all lets one authoritative server chase the CNAME server-side.
    print("Starting Server A (--zone all) on port 5053...")
    server_a = subprocess.Popen(
        [sys.executable, str(dns_server_path), '--zone', 'all', '-p', '5053'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(dns_server_path.parent)
    )

    # Recursive resolver — system under test. Forwards every query it receives
    # to Server A. This is where mutants will be planted for mutation testing.
    print("Starting Recursive Resolver on port 5055 (upstream 127.0.0.1:5053)...")
    recursive_resolver = subprocess.Popen(
        [sys.executable, str(recursive_resolver_path),
         '-p', '5055', '-u', '127.0.0.1:5054'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(recursive_resolver_path.parent)
    )

    time.sleep(2)
    print("Server A          (:5053) — authoritative, zone=all "
          "(example.local. CNAMEs + test.local. A records)")
    print("Recursive resolver (:5055) — forwards upstream to 127.0.0.1:5053")
    print()

    start_time = time.time()

    try:
        number_of_runs = int(sys.argv[1]) if len(sys.argv) > 1 else 1
        print("Running Fandango metamorphic tests...")
        print()
        for n in range(number_of_runs):
            subprocess.run(
                [sys.executable, str(script_dir / 'script.py'), str(output_dir / f'test_output_{n+1}.log')],
                cwd=str(script_dir),
                check=True,
                timeout=300,
            )

        duration = time.time() - start_time
        print()
        print("=" * 80)
        print(f" Test completed in {format_duration(duration)}")
        print("=" * 80)

    except subprocess.TimeoutExpired:
        print()
        print("ERROR: Test timed out after 300 seconds")

    finally:
        print()
        print("Stopping DNS servers...")
        server_a.terminate()
        recursive_resolver.terminate()
        try:
            server_a.wait(timeout=3)
            recursive_resolver.wait(timeout=3)
        except Exception:
            server_a.kill()
            recursive_resolver.kill()
        print("Servers stopped")
        print()
        print("View test results: cat test_output.log")
        print("Done")


if __name__ == '__main__':
    main()
