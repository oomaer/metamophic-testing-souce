#!/usr/bin/env python3
"""
DNS CNAME Resolution Equivalence MR - Test Runner

Manages DNS server lifecycle and runs the metamorphic relation test.
"""

import subprocess
import os
import sys
import time
from pathlib import Path


def format_duration(seconds):
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.2f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}h {minutes}m {secs:.2f}s"


def main():
    script_dir = Path(__file__).parent
    dns_server_path = script_dir.parent.parent / "dns_server.py"

    print("=" * 80)
    print(" DNS CNAME Resolution Equivalence MR - Test Runner")
    print("=" * 80)
    print()

    # Kill any existing DNS test servers
    print("Cleaning up any existing DNS servers...")
    subprocess.run(['pkill', '-f', 'dns_server.py'], capture_output=True)
    time.sleep(1)

    # Start DNS servers on ports 5053 and 5054
    print("Starting DNS servers...")
    dns_server_a = subprocess.Popen(
        [sys.executable, str(dns_server_path), '-p', '5053'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(dns_server_path.parent)
    )
    dns_server_b = subprocess.Popen(
        [sys.executable, str(dns_server_path), '-p', '5054'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(dns_server_path.parent)
    )

    time.sleep(2)
    print("✓ DNS servers started on ports 5053 and 5054")
    print()

    start_time = time.time()

    try:
        # Run the test script in a subprocess
        print("Running Fandango metamorphic tests...")
        print()
        result = subprocess.run(
            [sys.executable, str(script_dir / 'script.py'), 'test_output.log'],
            cwd=str(script_dir),
            timeout=300
        )

        end_time = time.time()
        duration = end_time - start_time

        print()
        print("=" * 80)
        print(f" Test completed in {format_duration(duration)}")
        print("=" * 80)

    except subprocess.TimeoutExpired:
        print()
        print("ERROR: Test timed out after 300 seconds")

    finally:
        # Cleanup
        print()
        print("Stopping DNS servers...")
        dns_server_a.terminate()
        dns_server_b.terminate()
        try:
            dns_server_a.wait(timeout=3)
            dns_server_b.wait(timeout=3)
        except:
            dns_server_a.kill()
            dns_server_b.kill()
        print("✓ Servers stopped")
        print()
        print("View test results: cat test_output.log")
        print("Done")


if __name__ == '__main__':
    main()
