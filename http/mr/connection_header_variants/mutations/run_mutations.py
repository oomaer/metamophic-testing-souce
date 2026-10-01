#!/usr/bin/env python3
"""
Mutation Testing Runner for Connection Header Variants MR

Runs script.py for each mutation and saves logs.
"""

import subprocess
import os
import sys
import time
from pathlib import Path


OUTPUT_DIR = Path(os.environ.get("MUTATION_OUTPUT_DIR", Path(__file__).resolve().parent)).resolve()

# Mutations to test
MUTATIONS = [
    # ('NONE', 'Baseline (no mutation)'),
    ('M1', 'Different status for close (201 vs 200)'),
    ('M2', 'Error on close (500)'),
    ('M3', 'Return 204 No Content'),
    ('M4', 'Empty body'),
    ('M5', 'Different transfer encoding'),
]


def format_duration(seconds):
    """Format elapsed time for the mutation log."""
    if seconds < 60:
        return f"{seconds:.2f}s"
    if seconds < 3600:
        minutes = int(seconds // 60)
        return f"{minutes}m {seconds % 60:.2f}s"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}h {minutes}m {seconds % 60:.2f}s"


def run_test(mr_dir, mutation_log, mutation_id, description, timeout=90):
    """Save this run's output even if the test crashes or times out."""
    run_start = time.time()
    with mutation_log.open('w') as log:
        log.write(f"Mutation: {mutation_id}\nDescription: {description}\n")
        log.write("=" * 80 + "\n\n")
        log.flush()
        try:
            result = subprocess.run(
                [sys.executable, '-u', str(mr_dir / 'script.py'), os.devnull],
                cwd=str(mr_dir),
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=timeout,
            )
            if result.returncode:
                log.write(f"\n[ERROR] Test exited with code {result.returncode}\n")
        except subprocess.TimeoutExpired:
            log.write(f"\n[TIMEOUT] Test exceeded {timeout} seconds\n")
        except Exception as error:
            log.write(f"\n[ERROR] {error}\n")
        finally:
            log.write(f"\nDuration: {format_duration(time.time() - run_start)}\n")


def main():
    script_dir = Path(__file__).resolve().parent
    mr_dir = script_dir.parent
    project_root = mr_dir.parent.parent  # mt-http directory
    logs_dir = OUTPUT_DIR / "logs"

    # Create logs directory if it doesn't exist
    logs_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print(" MUTATION TESTING: Connection Header Variants MR")
    print("=" * 80)
    print()

    for mutation_id, description in MUTATIONS:
        print(f"Testing {mutation_id}: {description}")

        # Kill any existing servers
        subprocess.run(['pkill', '-f', 'node.*server'], capture_output=True)
        subprocess.run(['pkill', '-f', 'node.*mutant'], capture_output=True)
        time.sleep(1)

        # Start servers
        print("  Starting servers...")
        server_a = subprocess.Popen(
            ['node', str(project_root / 'http-server-8080.js')],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(project_root)
        )

        env = os.environ.copy()
        env['MUTATION'] = mutation_id
        server_b = subprocess.Popen(
            ['node', str(script_dir / 'mutant-server-8081.js')],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(project_root)
        )

        time.sleep(2)

        try:
            print("  Running tests...")
            mutation_log = logs_dir / f'log_{mutation_id}.txt'
            run_test(mr_dir, mutation_log, mutation_id, description)
            print(f"  Log saved to: {mutation_log}")
        finally:
            # Cleanup servers
            server_a.terminate()
            server_b.terminate()
            try:
                server_a.wait(timeout=3)
                server_b.wait(timeout=3)
            except:
                server_a.kill()
                server_b.kill()

        print()

    print("=" * 80)
    print("All mutations completed!")
    print("=" * 80)

if __name__ == '__main__':
    main()
