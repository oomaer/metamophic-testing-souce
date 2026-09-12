#!/usr/bin/env python3
"""
DNS CNAME Resolution Equivalence MR — Test Runner (Architecture 1)

Launches two authoritative dns_server.py processes and runs the MR test:
  - Server A (:5053) — --zone alias  → authoritative for example.local.
  - Server B (:5054) — --zone target → authoritative for test.local.

The MR (see grammar.fan) checks:
  A-records reached via CNAME chase (ClientB → ServerB)
    ==
  A-records reached directly       (ClientC → ServerB)
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
    script_dir = Path(__file__).parent
    dns_server_path = script_dir.parent.parent / "dns_server.py"

    print("=" * 80)
    print(" DNS CNAME Resolution Equivalence MR — Test Runner (Architecture 1)")
    print("=" * 80)
    print()

    # Kill any existing DNS test servers
    print("Cleaning up any existing DNS servers...")
    subprocess.run(['pkill', '-f', 'dns_server.py'], capture_output=True)
    time.sleep(1)

    # Server A — authoritative for the TARGET zone (test.local.)
    print("Starting Server A (--zone target) on port 5053...")
    server_a = subprocess.Popen(
        [sys.executable, str(dns_server_path), '--zone', 'target', '-p', '5053'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(dns_server_path.parent)
    )

    # Server B — authoritative for the ALIAS zone (example.local.)
    print("Starting Server B (--zone alias) on port 5054...")
    server_b = subprocess.Popen(
        [sys.executable, str(dns_server_path), '--zone', 'alias', '-p', '5054'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(dns_server_path.parent)
    )

    time.sleep(2)
    print("Server A (target zone): port 5053 — test.local. → A 192.168.1.1, 192.168.1.2")
    print("Server B (alias zone):  port 5054 — example.local. → CNAME test.local.")
    print()

    start_time = time.time()

    try:
        print("Running Fandango metamorphic tests...")
        print()
        subprocess.run(
            [sys.executable, str(script_dir / 'script.py'), 'test_output.log'],
            cwd=str(script_dir),
            timeout=300
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
        server_b.terminate()
        try:
            server_a.wait(timeout=3)
            server_b.wait(timeout=3)
        except Exception:
            server_a.kill()
            server_b.kill()
        print("Servers stopped")
        print()
        print("View test results: cat test_output.log")
        print("Done")


if __name__ == '__main__':
    main()
