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


OUTPUT_DIR = Path(os.environ.get("MUTATION_OUTPUT_DIR", Path(__file__).resolve().parent)).resolve()

# Mutations to test — realistic, real-world range-handling bugs.
MUTATIONS = [
    ('M1',  'Inclusive/exclusive end confusion (drops last byte per part)'),
    ('M2',  'Naive regex parser: bytes=k- treated as bytes=k-k'),
    ('M3', 'Silently drops range requests past a fixed offset threshold'),
    ('M4',  'Case-sensitive Range header lookup (misses every request)'),
    ('M5',  'Off-by-one on open-ended range (last byte missing)'),
    ('M6',  'URL-keyed cache ignores Range header'),
    ('M7',  'Buffer overrun: appends 2 stray bytes to every partial response'),
    ('M8',  'Content-Range header lies; body correct'),
    ('M9',  'Returns 200 OK with correct partial slice'),
    # ('M10', 'Keep-alive state leak; stale bytes bleed into next response'),
    # ('M11',  'Content-Length reflects full file, not chunk'),
    # ('M12', 'UTF-8 "safe boundary" rounding truncates end'),
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


def main():
    script_dir = Path(__file__).resolve().parent
    mr_dir = script_dir.parent
    project_root = mr_dir.parent.parent  # http/ directory
    logs_dir = OUTPUT_DIR / "logs"

    logs_dir.mkdir(parents=True, exist_ok=True)

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
            ['node', str(project_root / 'http-server-8080.js')],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            cwd=str(project_root)
        )

        env = os.environ.copy()
        env['MUTATION'] = mutation_id
        env['PORT'] = '8081'
        server_b = subprocess.Popen(
            ['node', str(script_dir / 'mutant-server-3001.js')],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            cwd=str(project_root)
        )

        time.sleep(2)

        run_start = time.time()
        mutation_log = logs_dir / f'log_{mutation_id}.txt'
        output = ''
        try:
            for name, server in [('A', server_a), ('B', server_b)]:
                if server.poll() is not None:
                    error = server.stderr.read().decode(errors='replace')
                    raise RuntimeError(f'Server {name} failed to start: {error}')
            print("  Running tests...")
            result = subprocess.run(
                [sys.executable, str(mr_dir / 'script.py'), os.devnull],
                cwd=str(mr_dir),
                timeout=120,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
            output = result.stdout
            print(output, end='')
            if result.returncode:
                output += f'\nTest exited with code {result.returncode}\n'

        except subprocess.TimeoutExpired as exc:
            output = exc.stdout or b''
            if isinstance(output, bytes):
                output = output.decode(errors='replace')
            output += '\nTimeout after 120 seconds\n'
            print(f"  Timeout after 120 seconds")

        except Exception as e:
            output += f'\nError: {e}\n'
            print(f"  Error: {str(e)}")

        finally:
            header = (
                f"Mutation: {mutation_id}\n"
                f"Description: {description}\n"
                f"Duration: {format_duration(time.time() - run_start)}\n"
                + ("=" * 80) + "\n\n"
            )
            mutation_log.write_text(header + output)
            print(f"  Log saved to: {mutation_log}")
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
    print("=" * 80)


if __name__ == '__main__':
    main()
