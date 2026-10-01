#!/usr/bin/env python3
"""Run FTP Redundant RNFR mutations and collect per-mutant logs."""

import subprocess
import re
import sys
import os
import time
from pathlib import Path


OUTPUT_DIR = Path(os.environ.get("MUTATION_OUTPUT_DIR", Path(__file__).resolve().parent)).resolve()


MUTATIONS = ["M1", "M2", "M3", "M4", "M5", "M6"]

MUTATION_DESCRIPTIONS = {
    "BASELINE": "Clean baseline - normal RNFR/RNTO behavior",
    "M1": "FIRST_RNFR_WINS - Only first RNFR is stored; subsequent ignored",
    "M2": "REJECT_REDUNDANT_RNFR - Second RNFR returns 503 error",
    "M3": "SILENT_STATE_CLEAR - RNTO renames first RNFR's target (state cleared to first, not last)",
    "M4": "RNFR_OK_WRONG_CODE - RNFR returns 250 instead of 350",
    "M5": "RENAME_WRONG_TARGET - RNTO renames completely random/wrong directory",
    "M6": "WRONG_RNTO_SUCCESS_CODE - RNTO returns 200 instead of 250",
}

PYFTPDLIB_PATH = Path("/Users/i7949486/Desktop/uds/thesis/mutation/pyftpdlib")
VENV_PYTHON = PYFTPDLIB_PATH / "venv" / "bin" / "python"


def format_duration(seconds):
    if seconds < 60:
        return f"{seconds:.2f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.2f}s"


def run_mutation(mutation_id, mutations_dir, parent_dir):
    print(f"\n{'=' * 80}")
    print(f"Running Mutation: {mutation_id}")
    print(f"Description: {MUTATION_DESCRIPTIONS.get(mutation_id, 'Unknown')}")
    print(f"{'=' * 80}\n")

    logs_dir = OUTPUT_DIR / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / f"log_{mutation_id}.txt"

    # Kill any existing FTP servers
    subprocess.run(["pkill", "-9", "-f", re.escape(str(mutations_dir / "mutant_server.py"))], capture_output=True)
    time.sleep(1)

    server_python = str(VENV_PYTHON) if VENV_PYTHON.exists() else sys.executable

    print("Starting mutant FTP servers...")
    server_process = subprocess.Popen(
        [server_python, str(mutations_dir / "mutant_server.py"), "--mutation", mutation_id],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(mutations_dir),
    )

    time.sleep(2)
    if server_process.poll() is not None:
        stdout, stderr = server_process.communicate()
        print("ERROR: Server failed to start!")
        print(f"stdout: {stdout.decode(errors='replace')}")
        print(f"stderr: {stderr.decode(errors='replace')}")
        return {
            "mutation": mutation_id,
            "description": MUTATION_DESCRIPTIONS.get(mutation_id, "Unknown"),
            "duration": 0,
            "passes": 0,
            "violations": 0,
            "detected": False,
            "error": "SERVER_FAILED",
            "log_file": log_file.name,
        }

    print("FTP servers started\n")
    start_time = time.time()

    try:
        print("Running metamorphic test...\n")
        process = subprocess.Popen(
            [sys.executable, str(parent_dir / "script.py"), os.devnull],
            cwd=str(parent_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        output_lines = []
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                print(line, end="")
                output_lines.append(line)

        process.wait(timeout=300)
        full_output = "".join(output_lines)
        duration = time.time() - start_time

        with open(log_file, "w") as handle:
            handle.write(f"Mutation: {mutation_id}\n")
            handle.write(f"Description: {MUTATION_DESCRIPTIONS.get(mutation_id, 'Unknown')}\n")
            handle.write(f"Duration: {format_duration(duration)}\n")
            handle.write("=" * 80 + "\n\n")
            handle.write(full_output)

        violations = full_output.count("[VIOLATION]")
        passes = full_output.count("[PASS]")

        # Check for parse errors (Fandango grammar parse failures) - these count as violations
        if "FandangoFailedError" in full_output or "Could not parse received message" in full_output:
            violations += 1
            print("\n[DETECTION] Grammar parse error detected - mutation caused protocol violation")

        # Check for crashes/tracebacks
        if "Traceback (most recent call last)" in full_output and mutation_id != "BASELINE":
            violations += 1
            print("\n[DETECTION] Test crashed - mutation caused failure")

        print(f"\n{'=' * 80}")
        print(f"Test completed in {format_duration(duration)}")
        print(f"  Passes: {passes}")
        print(f"  Violations: {violations}")
        print(f"  Log saved: {log_file.name}")

        return {
            "mutation": mutation_id,
            "description": MUTATION_DESCRIPTIONS.get(mutation_id, "Unknown"),
            "duration": duration,
            "passes": passes,
            "violations": violations,
            "detected": violations > 0,
            "log_file": log_file.name,
        }

    except subprocess.TimeoutExpired:
        print("Test timed out after 300 seconds")
        # TIMEOUT is treated as a VIOLATION (mutation detected)
        return {
            "mutation": mutation_id,
            "description": MUTATION_DESCRIPTIONS.get(mutation_id, "Unknown"),
            "duration": 300,
            "passes": 0,
            "violations": 1,  # Timeout counts as violation
            "detected": True,  # Mutation detected via timeout
            "error": "TIMEOUT",
            "log_file": log_file.name,
        }
    except Exception as exc:
        print(f"Error running test: {exc}")
        # CRASH/ERROR is treated as a VIOLATION (mutation detected)
        return {
            "mutation": mutation_id,
            "description": MUTATION_DESCRIPTIONS.get(mutation_id, "Unknown"),
            "duration": 0,
            "passes": 0,
            "violations": 1,  # Crash counts as violation
            "detected": True,  # Mutation detected via crash
            "error": str(exc),
            "log_file": log_file.name,
        }
    finally:
        print("\nStopping FTP servers...")
        server_process.terminate()
        try:
            server_process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            server_process.kill()
        subprocess.run(["pkill", "-9", "-f", re.escape(str(mutations_dir / "mutant_server.py"))], capture_output=True)
        print("FTP servers stopped")
        time.sleep(1)


def print_results(results, total_duration):
    detected_count = 0
    total_mutations = 0

    print("\n" + "=" * 80)
    print(" MUTATION TESTING SUMMARY")
    print("=" * 80 + "\n")
    print(f"Total mutations tested: {len(results)}")
    print(f"Total time: {format_duration(total_duration)}\n")
    print(f"{'Mutation':<12} {'Detected':<10} {'Passes':<8} {'Violations':<12} {'Duration':<10} {'Status'}")
    print("-" * 80)

    for result in results:
        if result["mutation"] == "BASELINE":
            detected_str = "N/A"
        else:
            detected_str = "YES" if result["detected"] else "NO"
            total_mutations += 1
            if result["detected"]:
                detected_count += 1
        status = result.get("error", "OK")
        print(
            f"{result['mutation']:<12} {detected_str:<10} {result['passes']:<8} "
            f"{result['violations']:<12} {format_duration(result['duration']):<10} {status}"
        )

    print("-" * 80)
    score = detected_count / total_mutations * 100 if total_mutations else 0
    print(f"\nMutation Score: {detected_count}/{total_mutations} ({score:.1f}%)")

    print(f"Individual logs saved to: {OUTPUT_DIR / 'logs'}")


def main():
    mutations_dir = Path(__file__).resolve().parent
    parent_dir = mutations_dir.parent

    print("=" * 80)
    print(" FTP REDUNDANT RNFR - MUTATION TESTING")
    print("=" * 80)
    print(f"\nTotal mutations to test: {len(MUTATIONS)}")
    print(f"Mutations: {', '.join(MUTATIONS)}")
    print("=" * 80 + "\n")

    start_time = time.time()
    results = []
    for index, mutation in enumerate(MUTATIONS, 1):
        print(f"\n[{index}/{len(MUTATIONS)}] Testing {mutation}...")
        results.append(run_mutation(mutation, mutations_dir, parent_dir))
        time.sleep(1)

    print_results(results, time.time() - start_time)
    print("\nDone")


if __name__ == "__main__":
    main()
