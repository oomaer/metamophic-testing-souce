#!/usr/bin/env python3
"""
Simple runner for FTP Rename Consistency MR.
Runs in a subprocess to avoid Fandango singleton issues.
Manages FTP server lifecycle using pyftpdlib with venv.
"""

import subprocess
import sys
import os
import time
import shutil
from pathlib import Path


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


def setup_test_files(data_dir, server_name):
    """Create test files for the specified server."""
    (data_dir / "source.txt").write_text("source file content\n")


def start_ftp_server(server_script, server_name, data_dir, log_path):
    """Write server output to disk so unread pipes cannot block the server."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("w") as server_log:
        return subprocess.Popen(
            [sys.executable, str(server_script), "--server", server_name, "--data-dir", str(data_dir)],
            stdout=server_log,
            stderr=subprocess.STDOUT,
        )


def main():
    script_dir = Path(__file__).resolve().parent
    output_dir = Path(os.environ.get("MR_RUNS_DIR", script_dir / "runs")).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    data_dir_a = script_dir / "data/server_a"
    data_dir_b = script_dir / "data/server_b"

    print("=" * 80)
    print(" FTP Redundant RNFR MR - Test Runner")
    print("=" * 80)
    print()


    # Kill any existing FTP servers
    print("Cleaning up any existing FTP servers...")
    subprocess.run(['pkill', '-f', 'ftp_server'], capture_output=True)
    time.sleep(1)

    # Create/clean data directories
    print("Setting up data directories...")
    for data_dir in [data_dir_a, data_dir_b]:
        if data_dir.exists():
            shutil.rmtree(data_dir)
        data_dir.mkdir(parents=True, exist_ok=True)

    setup_test_files(data_dir_a, "a")
    setup_test_files(data_dir_b, "b")

    print(f"  Server A data: {data_dir_a}")
    print(f"  Server B data: {data_dir_b}")

    ftp_server_script = script_dir.parent / "ftp_server.py"
    server_logs_dir = script_dir / "server_logs"

    # Start FTP servers
    print("Starting FTP server A on port 2121...")
    server_a = start_ftp_server(
        ftp_server_script, "a", data_dir_a, server_logs_dir / "server_a.log",
    )

    print("Starting FTP server B on port 2122...")
    server_b = start_ftp_server(
        ftp_server_script, "b", data_dir_b, server_logs_dir / "server_b.log",
    )
    print(f"Server logs: {server_logs_dir / 'server_a.log'}, {server_logs_dir / 'server_b.log'}")

    time.sleep(2)
    print("FTP servers started")
    print()

    start_time = time.time()

    number_of_runs = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    try:
        # Run the test script in a subprocess
        print("Running Fandango metamorphic tests...")
        print()
        for n in range(number_of_runs):
            print(f"Run {n + 1}/{number_of_runs}...")
            result = subprocess.run(
                [sys.executable, str(script_dir / 'script.py'), str(output_dir / f'test_output_{n+1}.log')],
                cwd=str(script_dir),
                check=True,
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
        print("Stopping FTP servers...")
        server_a.terminate()
        server_b.terminate()
        try:
            server_a.wait(timeout=3)
            server_b.wait(timeout=3)
        except:
            server_a.kill()
            server_b.kill()

        print("Servers stopped")
        print("Done")


if __name__ == '__main__':
    main()
