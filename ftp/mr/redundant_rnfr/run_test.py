#!/usr/bin/env python3
"""
Simple runner for FTP Rename Consistency MR.
Runs in a subprocess to avoid Fandango singleton issues.
Manages FTP server lifecycle using pyftpdlib with venv.
"""

import subprocess
import os
import sys
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


def main():
    script_dir = Path(__file__).parent
    ftp_root = script_dir.parent.parent  # ftp/ directory
    pyftpdlib_path = Path("/Users/i7949486/Desktop/uds/thesis/mutation/pyftpdlib")
    venv_python = pyftpdlib_path / "venv" / "bin" / "python"

    # Create separate data directories for each server
    data_dir_a = ftp_root / "data" / "server_a"
    data_dir_b = ftp_root / "data" / "server_b"

    print("=" * 80)
    print(" FTP Redundant RNFR MR - Test Runner")
    print("=" * 80)
    print()

    # Check if venv exists
    if not venv_python.exists():
        print(f"Error: venv python not found at {venv_python}")
        sys.exit(1)

    # Kill any existing FTP servers
    print("Cleaning up any existing FTP servers...")
    subprocess.run(['pkill', '-f', 'temp_server'], capture_output=True)
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

    # Create server scripts
    server_a_script = script_dir / "temp_server_a.py"
    server_a_script.write_text(f'''#!/usr/bin/env python3
import sys
sys.path.insert(0, "{pyftpdlib_path}")
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

authorizer = DummyAuthorizer()
authorizer.add_user("user", "12345", "{data_dir_a}", perm="elradfmwMT")
handler = FTPHandler
handler.authorizer = authorizer
server = FTPServer(("127.0.0.1", 2121), handler)
print("Server A started on port 2121")
server.serve_forever()
''')

    server_b_script = script_dir / "temp_server_b.py"
    server_b_script.write_text(f'''#!/usr/bin/env python3
import sys
sys.path.insert(0, "{pyftpdlib_path}")
from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

authorizer = DummyAuthorizer()
authorizer.add_user("user", "12345", "{data_dir_b}", perm="elradfmwMT")
handler = FTPHandler
handler.authorizer = authorizer
server = FTPServer(("127.0.0.1", 2122), handler)
print("Server B started on port 2122")
server.serve_forever()
''')

    # Start FTP servers
    print("Starting FTP server A on port 2121...")
    server_a = subprocess.Popen(
        [str(venv_python), str(server_a_script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(data_dir_a)
    )

    print("Starting FTP server B on port 2122...")
    server_b = subprocess.Popen(
        [str(venv_python), str(server_b_script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(data_dir_b)
    )

    time.sleep(2)
    print("FTP servers started")
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
        print("Stopping FTP servers...")
        server_a.terminate()
        server_b.terminate()
        try:
            server_a.wait(timeout=3)
            server_b.wait(timeout=3)
        except:
            server_a.kill()
            server_b.kill()

        # Clean up temporary server scripts
        for f in [server_a_script, server_b_script]:
            if f.exists():
                f.unlink()

        print("Servers stopped")
        print("Done")


if __name__ == '__main__':
    main()
