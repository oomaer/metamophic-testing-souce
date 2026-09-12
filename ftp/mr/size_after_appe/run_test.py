#!/usr/bin/env python3
"""
Runner for FTP SIZE After APPE MR.
Manages FTP server lifecycle using pyftpdlib with venv.
Creates test files with known initial size.
"""

import subprocess
import sys
import time
import shutil
from pathlib import Path


INITIAL_FILE_SIZE = 100  # bytes


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
    """Create test file with known initial size."""
    test_file = data_dir / "test_file.txt"
    # Create file with exactly INITIAL_FILE_SIZE bytes
    content = "X" * INITIAL_FILE_SIZE
    test_file.write_text(content)
    print(f"  Created test_file.txt ({INITIAL_FILE_SIZE} bytes) for server {server_name}")


def main():
    script_dir = Path(__file__).parent
    ftp_root = script_dir.parent.parent  # ftp/ directory
    pyftpdlib_path = Path("/Users/i7949486/Desktop/uds/thesis/mutation/pyftpdlib")
    venv_python = pyftpdlib_path / "venv" / "bin" / "python"

    data_dir_a = ftp_root / "data" / "server_a"
    data_dir_b = ftp_root / "data" / "server_b"

    print("=" * 80)
    print(" FTP SIZE After APPE MR - Test Runner")
    print("=" * 80)
    print()

    if not venv_python.exists():
        print(f"Error: venv python not found at {venv_python}")
        sys.exit(1)

    print("Cleaning up any existing FTP servers...")
    subprocess.run(['pkill', '-f', 'ftp_server'], capture_output=True)
    time.sleep(1)

    print("Setting up data directories...")
    for data_dir in [data_dir_a, data_dir_b]:
        if data_dir.exists():
            shutil.rmtree(data_dir)
        data_dir.mkdir(parents=True, exist_ok=True)

    setup_test_files(data_dir_a, "A")
    setup_test_files(data_dir_b, "B")

    print(f"  Server A data: {data_dir_a}")
    print(f"  Server B data: {data_dir_b}")

    ftp_server_script = script_dir.parent / "ftp_server.py"

    print("Starting FTP server A on port 2121...")
    server_a = subprocess.Popen(
        [str(venv_python), str(ftp_server_script), "--server", "a", "--data-dir", str(data_dir_a)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    print("Starting FTP server B on port 2122...")
    server_b = subprocess.Popen(
        [str(venv_python), str(ftp_server_script), "--server", "b", "--data-dir", str(data_dir_b)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    time.sleep(2)
    print("FTP servers started")
    print()

    start_time = time.time()
    number_of_runs = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    try:
        print("Running Fandango metamorphic tests...")
        print()

        for n in range(number_of_runs):
            print(f"Run {n + 1}/{number_of_runs}...")
            result = subprocess.run(
                [sys.executable, str(script_dir / 'script.py'), f'runs/test_output_{n+1}.log'],
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
