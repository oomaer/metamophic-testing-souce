#!/usr/bin/env python3
"""Run SMTP State Reset MR with fresh, owned server processes for every run."""

import argparse
from contextlib import contextmanager
from pathlib import Path
import socket
import subprocess
import sys
import os
import time


SMTP_PORTS = (8026, 8027)


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


def stop_processes(processes):
    """Stop all owned processes and reap them, including after a forced kill."""
    for process in processes:
        if process.poll() is None:
            process.terminate()
    for process in processes:
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def check_ports_available(ports):
    # Do not silently connect to an older server or kill an unrelated process.
    for port in ports:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(('127.0.0.1', port))
            except OSError as error:
                raise RuntimeError(
                    f"SMTP port {port} is unavailable. Stop the existing listener "
                    "before starting this runner."
                ) from error


def wait_for_servers(processes, ports, timeout=10):
    """Require an SMTP greeting and live child processes, not a fixed sleep."""
    pending = set(ports)
    deadline = time.monotonic() + timeout
    while pending:
        for process in processes:
            if process.poll() is not None:
                raise RuntimeError(
                    f"SMTP server {process.pid} exited during startup "
                    f"(status {process.returncode})."
                )
        if time.monotonic() >= deadline:
            raise RuntimeError(f"Timed out waiting for SMTP ports {sorted(pending)}.")
        for port in tuple(pending):
            try:
                with socket.create_connection(('127.0.0.1', port), timeout=0.2) as sock:
                    greeting = b''
                    while not greeting.endswith(b'\r\n') and len(greeting) < 4096:
                        chunk = sock.recv(4096)
                        if not chunk:
                            break
                        greeting += chunk
                    if greeting.startswith(b'220 ') and greeting.endswith(b'\r\n'):
                        pending.remove(port)
            except OSError:
                pass
        if pending:
            time.sleep(0.05)
    for process in processes:
        if process.poll() is not None:
            raise RuntimeError(f"SMTP server {process.pid} exited during startup.")


@contextmanager
def smtp_servers(server_path, ports=SMTP_PORTS):
    check_ports_available(ports)
    processes = []
    try:
        for port in ports:
            processes.append(subprocess.Popen(
                [sys.executable, '-u', str(server_path), '-p', str(port)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=str(server_path.parent),
            ))
        wait_for_servers(processes, ports)
        print(f"SMTP servers ready on ports {ports}", flush=True)
        yield processes
    finally:
        stop_processes(processes)
        print("SMTP servers stopped", flush=True)


def main():
    script_dir = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('runs', type=int, nargs='?', default=1)
    parser.add_argument('--timeout', type=float, default=300,
                        help='Maximum seconds for each Fandango run (default: 300)')
    parser.add_argument('--output-dir', type=Path, default=Path(os.environ.get('MR_RUNS_DIR', script_dir / 'runs')))
    args = parser.parse_args()
    if args.runs < 1 or args.timeout <= 0:
        parser.error('runs and timeout must be positive')
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    server_path = script_dir.parents[1] / 'smtpserver.py'
    start_time = time.monotonic()

    print("SMTP State Reset MR - Test Runner", flush=True)
    try:
        for run in range(1, args.runs + 1):
            print(f"\nRun {run}/{args.runs}", flush=True)
            with smtp_servers(server_path):
                subprocess.run(
                    [sys.executable, str(script_dir / 'script.py'),
                     str(output_dir / f'test_output_{run}.log')],
                    cwd=str(script_dir),
                    timeout=args.timeout,
                    check=True,
                )
    except subprocess.TimeoutExpired:
        print(f"ERROR: Test timed out after {args.timeout:g} seconds", file=sys.stderr)
        return 1
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nTest interrupted", file=sys.stderr)
        return 130

    print(f"\nTest completed in {format_duration(time.monotonic() - start_time)}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
