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

# Mutations to test
MUTATIONS = [
    # ('NONE', 'Baseline (no mutation)'),
    ('M1', 'Different status for close (201 vs 200)'),
    ('M2', 'Error on close (500)'),
    ('M3', 'Return 204 No Content'),
    ('M8', 'Empty body'),
    ('M20', 'Different transfer encoding'),
]


def format_duration(seconds):
    """Mirror of the SMTP runners' format so summarize_logs.py can parse it back."""
    if seconds < 60:
        return f"{seconds:.2f}s"
    if seconds < 3600:
        minutes = int(seconds // 60)
        return f"{minutes}m {seconds % 60:.2f}s"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}h {minutes}m {seconds % 60:.2f}s"


def main():
    script_dir = Path(__file__).parent
    mr_dir = script_dir.parent
    project_root = mr_dir.parent.parent  # mt-http directory
    logs_dir = script_dir / 'logs'

    # Create logs directory if it doesn't exist
    logs_dir.mkdir(exist_ok=True)

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

        run_start = time.time()
        try:
            # Run the test script
            print("  Running tests...")
            result = subprocess.run(
                [sys.executable, str(mr_dir / 'script.py')],
                cwd=str(mr_dir),
                timeout=90
            )

            # Copy the log file with a header the summarizer can read (Mutation
            # id / Description / Duration). Matches the shape SMTP runners use
            # so summarize_logs.py works across MRs unchanged.
            test_log = mr_dir / 'test_output.log'
            mutation_log = logs_dir / f'log_{mutation_id}.txt'

            if test_log.exists():
                duration = time.time() - run_start
                header = (
                    f"Mutation: {mutation_id}\n"
                    f"Description: {description}\n"
                    f"Duration: {format_duration(duration)}\n"
                    + ("=" * 80) + "\n\n"
                )
                mutation_log.write_text(header + test_log.read_text(errors='replace'))
                print(f"  Log saved to: logs/{mutation_log.name}")
            else:
                print(f"  Warning: test_output.log not found")

        except subprocess.TimeoutExpired:
            print(f"  Timeout after 90 seconds")

        except Exception as e:
            print(f"  Error: {str(e)}")

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
    print("Run 'python analyze_mutations.py' to generate results.")
    print("=" * 80)

if __name__ == '__main__':
    main()
