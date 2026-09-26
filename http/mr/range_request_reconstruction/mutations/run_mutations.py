#!/usr/bin/env python3
"""
Mutation Testing Runner for Range Request Reconstruction MR

Runs script.py for each mutation and saves logs.
"""

import subprocess
import os
import sys
import time
from pathlib import Path

# Mutations to test — realistic, real-world range-handling bugs.
MUTATIONS = [
    ('M1',  'Inclusive/exclusive end confusion (drops last byte per part)'),
    ('M2',  'Naive regex parser: bytes=k- treated as bytes=k-k'),
    ('M3',  'Content-Length reflects full file, not chunk'),
    ('M4',  'Case-sensitive Range header lookup (misses every request)'),
    ('M5',  'Off-by-one on open-ended range (last byte missing)'),
    ('M6',  'URL-keyed cache ignores Range header'),
    ('M7',  'Buffer overrun: appends 2 stray bytes to every partial response'),
    ('M8',  'Content-Range header lies; body correct'),
    ('M9',  'Returns 200 OK with correct partial slice'),
    ('M10', 'Keep-alive state leak; stale bytes bleed into next response'),
    ('M11', 'Silently drops range requests past a fixed offset threshold'),
    ('M12', 'UTF-8 "safe boundary" rounding truncates end'),
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
    project_root = mr_dir.parent.parent  # http/ directory
    logs_dir = script_dir / 'logs'

    logs_dir.mkdir(exist_ok=True)

    print("=" * 80)
    print(" MUTATION TESTING: Range Request Reconstruction MR")
    print("=" * 80)
    print()

    for mutation_id, description in MUTATIONS:
        print(f"Testing {mutation_id}: {description}")

        subprocess.run(['pkill', '-f', 'node.*server'], capture_output=True)
        subprocess.run(['pkill', '-f', 'node.*mutant'], capture_output=True)
        time.sleep(1)

        print("  Starting servers...")
        server_a = subprocess.Popen(
            ['node', str(project_root / 'http-server-3000.js')],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(project_root)
        )

        env = os.environ.copy()
        env['MUTATION'] = mutation_id
        server_b = subprocess.Popen(
            ['node', str(script_dir / 'mutant-server-3001.js')],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=str(project_root)
        )

        time.sleep(2)

        run_start = time.time()
        try:
            print("  Running tests...")
            subprocess.run(
                [sys.executable, str(mr_dir / 'script.py')],
                cwd=str(mr_dir),
                timeout=120
            )

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
            print(f"  Timeout after 120 seconds")

        except Exception as e:
            print(f"  Error: {str(e)}")

        finally:
            server_a.terminate()
            server_b.terminate()
            try:
                server_a.wait(timeout=3)
                server_b.wait(timeout=3)
            except Exception:
                server_a.kill()
                server_b.kill()

        print()

    print("=" * 80)
    print("All mutations completed!")
    print("Run 'python analyze_mutations.py' to generate results.")
    print("Run 'python summarize_logs.py' for a compact per-log summary.")
    print("=" * 80)


if __name__ == '__main__':
    main()
