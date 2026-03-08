#!/usr/bin/env python3
"""
Simple runner for SMTP Repeated Recipient MR.
Runs in a subprocess to avoid Fandango singleton issues.
Manages SMTP server lifecycle (start/stop).
"""

import subprocess
import os
import sys
import time
from pathlib import Path
from datetime import datetime


def format_duration(seconds):
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
    mutation_server_path = Path("/Users/i7949486/Desktop/uds/thesis/mutation/aiosmtpd/run-test-server.py")

    print("=" * 80)
    print(" SMTP Repeated Recipient MR - Test Runner")
    print("=" * 80)
    print()

    # Kill any existing SMTP test servers
    print("Cleaning up any existing SMTP servers...")
    subprocess.run(['pkill', '-f', 'run-test-server.py'], capture_output=True)
    time.sleep(1)

    # Start SMTP servers on ports 8026 and 8027
    print("Starting SMTP servers...")
    server_a = subprocess.Popen(
        [sys.executable, str(mutation_server_path), '-p', '8026'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(mutation_server_path.parent)
    )
    server_b = subprocess.Popen(
        [sys.executable, str(mutation_server_path), '-p', '8027'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(mutation_server_path.parent)
    )

    time.sleep(2)
    print("✓ SMTP servers started on ports 8026 and 8027")
    print()

    start_time = time.time()

    try:
        # Run the test script in a subprocess
        print("Running Fandango metamorphic tests...")
        print()
        result = subprocess.run(
            [sys.executable, str(script_dir / 'script.py')],
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
        print("Stopping SMTP servers...")
        server_a.terminate()
        server_b.terminate()
        try:
            server_a.wait(timeout=3)
            server_b.wait(timeout=3)
        except:
            server_a.kill()
            server_b.kill()
        print("✓ Servers stopped")
        print("Done")


if __name__ == '__main__':
    main()
