#!/usr/bin/env python3
"""
IMAP Append+Search MR - Test Runner

Manages IMAP server lifecycle and runs the metamorphic relation test.
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
    number_of_runs = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    script_dir = Path(__file__).parent
    server_path = script_dir / "imap_server.py"

    print("=" * 80)
    print(" IMAP Append+Search MR - Test Runner")
    print("=" * 80)
    print()

    # Kill any existing IMAP test servers
    print("Cleaning up any existing IMAP servers on port 1144...")
    subprocess.run(['pkill', '-f', 'imap_server.py'], capture_output=True)
    # Also try to kill by port
    subprocess.run(['lsof', '-ti', ':1144'], capture_output=True)
    time.sleep(1)

    # Start IMAP server
    print("Starting IMAP server on port 1144...")
    imap_server = subprocess.Popen(
        [sys.executable, str(server_path), '-p', '1144'],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(script_dir)
    )

    # Wait for server to start
    time.sleep(2)

    # Check if server is running
    if imap_server.poll() is not None:
        print("ERROR: IMAP server failed to start!")
        stdout, stderr = imap_server.communicate()
        print(f"stdout: {stdout.decode()}")
        print(f"stderr: {stderr.decode()}")
        return 1

    print("✓ IMAP server started on port 1144")
    print()

    start_time = time.time()

    try:
        # Run the test script
        print("Running Fandango metamorphic tests...")
        print()
        for n in range(number_of_runs):
            result = subprocess.run(
                [sys.executable, str(script_dir / 'script.py'), f'runs/test_output_{n+1}.log'],
                cwd=str(script_dir)
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
        print("Stopping IMAP server...")
        imap_server.terminate()
        try:
            imap_server.wait(timeout=3)
        except:
            imap_server.kill()
        print("✓ Server stopped")
        print()
        print("View test results: cat runs/test_output.log")
        print("Done")


if __name__ == '__main__':
    main()
