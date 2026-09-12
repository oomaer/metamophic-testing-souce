#!/usr/bin/env python3
"""
Simple runner for Connection Header Variants MR.
Runs in a subprocess to avoid Fandango singleton issues.
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
    project_root = script_dir.parent.parent

    print("=" * 80)
    print(" Connection Header Variants MR - Test Runner")
    print("=" * 80)
    print()

    # Kill any existing servers
    subprocess.run(['pkill', '-f', 'node.*server'], capture_output=True)
    time.sleep(1)

    # Start servers
    print("Starting servers...")
    server_a = subprocess.Popen(
        ['node', str(project_root / 'http-server-8080.js')],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=str(project_root)
    )
    server_b = subprocess.Popen(
        ['node', str(project_root / 'http-server-8081.js')],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        cwd=str(project_root)
    )

    time.sleep(2)
    print("Servers started")
    print()

    start_time = time.time()

    number_of_runs = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    try:
        # Run the test script in a subprocess
        for run in range(number_of_runs):
            print(f"Run {run + 1}/{number_of_runs}")
            result = subprocess.run(
                [sys.executable, str(script_dir / 'script.py'), f'runs/test_output_{run + 1}.log'],
                cwd=str(script_dir),
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
        print("Stopping servers...")
        server_a.terminate()
        server_b.terminate()
        try:
            server_a.wait(timeout=3)
            server_b.wait(timeout=3)
        except:
            server_a.kill()
            server_b.kill()
        print("Done")

if __name__ == '__main__':
    main()
