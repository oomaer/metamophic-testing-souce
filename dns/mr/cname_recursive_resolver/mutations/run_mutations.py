#!/usr/bin/env python3
"""Run cname_recursive_resolver2 mutations and collect per-mutant logs."""

import subprocess
import sys
import os
import time
from pathlib import Path


OUTPUT_DIR = Path(os.environ.get("MUTATION_OUTPUT_DIR", Path(__file__).resolve().parent)).resolve()


MUTATIONS = ["M1", "M2", "M3", "M4", "M5", "M6", "M7"]

MUTATION_DESCRIPTIONS = {
    # "BASELINE": "Clean baseline - forward request and response unchanged",
    "M1": "REWRITE_QNAME_TO_TARGET - Forward test.local. instead of client qname",
    "M2": "REWRITE_QTYPE_AAAA - Forward AAAA instead of A",
    "M3": "REWRITE_QCLASS_CH - Forward CH instead of IN",
    "M4": "DROP_A_RECORDS - Remove all A records from recursive response",
    "M5": "WRONG_A_RECORDS - Replace A records with 10.10.10.10",
    "M6": "MISSING_ONE_A_RECORD - Keep only the first A record",
    "M7": "EXTRA_A_RECORD - Add fake A record 192.168.1.99",
}


def format_duration(seconds):
    if seconds < 60:
        return f"{seconds:.2f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.2f}s"


def stop_existing_processes():
    patterns = [
        "mutant_resolver.py",
        "dns_recursive_resolver.py",
        "dns_server.py",
    ]
    for pattern in patterns:
        subprocess.run(["pkill", "-f", pattern], capture_output=True)


def run_mutation(mutation_id, mutations_dir, parent_dir, dns_dir):
    print(f"\n{'=' * 80}")
    print(f"Running Mutation: {mutation_id}")
    print(f"Description: {MUTATION_DESCRIPTIONS.get(mutation_id, 'Unknown')}")
    print(f"{'=' * 80}\n")

    logs_dir = OUTPUT_DIR / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / f"log_{mutation_id}.txt"

    stop_existing_processes()
    time.sleep(1)

    print("Starting authoritative DNS server on 127.0.0.1:5053...")
    authoritative = subprocess.Popen(
        [sys.executable, str(dns_dir / "dns_server.py"), "--zone", "all", "-p", "5053"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(dns_dir),
    )

    print("Starting mutant recursive resolver on 127.0.0.1:5055...")
    resolver = subprocess.Popen(
        [
            sys.executable,
            str(mutations_dir / "mutant_resolver.py"),
            "--mutation",
            mutation_id,
            "-p",
            "5055",
            "-u",
            "127.0.0.1:5054",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(mutations_dir),
    )

    time.sleep(2)
    failed = []
    for name, process in (("authoritative server", authoritative), ("mutant resolver", resolver)):
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            failed.append(
                f"{name} failed\nstdout:\n{stdout.decode(errors='replace')}\nstderr:\n{stderr.decode(errors='replace')}"
            )

    if failed:
        for message in failed:
            print(message)
        return {
            "mutation": mutation_id,
            "description": MUTATION_DESCRIPTIONS.get(mutation_id, "Unknown"),
            "duration": 0,
            "passes": 0,
            "violations": 1,
            "detected": mutation_id != "BASELINE",
            "error": "SERVER_FAILED",
            "log_file": log_file.name,
        }

    print("Servers started\n")
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
        return {
            "mutation": mutation_id,
            "description": MUTATION_DESCRIPTIONS.get(mutation_id, "Unknown"),
            "duration": 300,
            "passes": 0,
            "violations": 1,
            "detected": mutation_id != "BASELINE",
            "error": "TIMEOUT",
            "log_file": log_file.name,
        }
    except Exception as exc:
        print(f"Error running test: {exc}")
        return {
            "mutation": mutation_id,
            "description": MUTATION_DESCRIPTIONS.get(mutation_id, "Unknown"),
            "duration": 0,
            "passes": 0,
            "violations": 1,
            "detected": mutation_id != "BASELINE",
            "error": str(exc),
            "log_file": log_file.name,
        }
    finally:
        print("\nStopping DNS processes...")
        for process in (resolver, authoritative):
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
        stop_existing_processes()
        print("DNS processes stopped")
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
    dns_dir = parent_dir.parent.parent

    print("=" * 80)
    print(" DNS CNAME RECURSIVE RESOLVER 2 - MUTATION TESTING")
    print("=" * 80)
    print(f"\nTotal mutations to test: {len(MUTATIONS)}")
    print(f"Mutations: {', '.join(MUTATIONS)}")
    print("=" * 80 + "\n")

    start_time = time.time()
    results = []

    for index, mutation in enumerate(MUTATIONS, 1):
        print(f"\n[{index}/{len(MUTATIONS)}] Testing {mutation}...")
        results.append(run_mutation(mutation, mutations_dir, parent_dir, dns_dir))
        time.sleep(1)

    print_results(results, time.time() - start_time)


if __name__ == "__main__":
    main()
