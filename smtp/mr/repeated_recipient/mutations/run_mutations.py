#!/usr/bin/env python3
"""
Run all mutations for Repeated Recipient MR and collect results.
"""

import subprocess
import time
import sys
import os
from pathlib import Path


OUTPUT_DIR = Path(os.environ.get("MUTATION_OUTPUT_DIR", Path(__file__).resolve().parent)).resolve()


MUTATIONS = ['M1', 'M2', 'M3', 'M4', 'M5', 'M6']
# MUTATIONS = ['M5']  # For quick testing, focus on M5 which is a protocol violation

# MUTATIONS = ['M6']

MUTATION_DESCRIPTIONS = {
    # 'BASELINE': 'Clean baseline - accepts all duplicates (RFC compliant)',
    'M1': 'STRICT_DUPLICATE_REJECT - Reject all duplicates with 550',
    'M2': 'ACCEPT_FIRST_N_DUPLICATES - Accept first 2, reject 3rd+',
    'M3': 'REJECT_FIRST_DUPLICATE_ONLY - Reject 2nd occurrence, accept 3rd+',
    'M4': 'DUPLICATE_DELIVERS_TO_WRONG_RECIPIENT - Duplicate RCPT adds unintended recipient',
    'M5': 'MULTIPLE_RESPONSE_LINES - Send multiple 250 responses (protocol violation)',
    'M6': 'REJECT_ALL_AFTER_DUPLICATE - After duplicate, reject all subsequent RCPT',
}


def format_duration(seconds):
    if seconds < 60:
        return f"{seconds:.2f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.2f}s"


def run_mutation(mutation_id, mutations_dir, parent_dir):
    """Run a single mutation test."""
    print(f"\n{'='*80}")
    print(f"Running Mutation: {mutation_id}")
    print(f"Description: {MUTATION_DESCRIPTIONS.get(mutation_id, 'Unknown')}")
    print(f"{'='*80}\n")

    # Create logs directory if it doesn't exist
    logs_dir = OUTPUT_DIR / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    log_file = logs_dir / f'log_{mutation_id}.txt'

    # Start mutant server
    print("Starting mutant servers...")
    server_process = subprocess.Popen(
        [sys.executable, str(mutations_dir / 'mutant_server.py'),
         '--mutation', mutation_id],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(mutations_dir)
    )

    time.sleep(3)  # Wait for servers to start
    print("✓ Servers started\n")

    start_time = time.time()

    try:
        # Run the test script
        print("Running metamorphic test...\n")

        # Run with real-time output to console AND capture for log
        process = subprocess.Popen(
            [sys.executable, str(parent_dir / 'script.py'), os.devnull],
            cwd=str(parent_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        # Keep collecting output until the test exits naturally, including
        # output after violations or protocol errors.
        output_lines = []
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                print(line, end='')
                output_lines.append(line)

        process.wait()
        full_output = ''.join(output_lines)

        end_time = time.time()
        duration = end_time - start_time

        # Save log
        with open(log_file, 'w') as f:
            f.write(f"Mutation: {mutation_id}\n")
            f.write(f"Description: {MUTATION_DESCRIPTIONS.get(mutation_id, 'Unknown')}\n")
            f.write(f"Duration: {format_duration(duration)}\n")
            f.write("="*80 + "\n\n")
            f.write(full_output)

        # Check for violations
        violations = full_output.count('[VIOLATION]')
        passes = full_output.count('[PASS]')

        print(f"\n{'='*80}")
        print(f"✓ Test completed in {format_duration(duration)}")
        print(f"  Passes: {passes}")
        print(f"  Violations: {violations}")
        print(f"  Log saved: {log_file.name}")

        return {
            'mutation': mutation_id,
            'description': MUTATION_DESCRIPTIONS.get(mutation_id, 'Unknown'),
            'duration': duration,
            'passes': passes,
            'violations': violations,
            'detected': violations > 0 or any(
                marker in full_output
                for marker in ('FandangoFailedError', 'FandangoValueError')
            ),
            'log_file': log_file.name
        }

    except Exception as e:
        print(f"✗ Error running test: {e}")
        return {
            'mutation': mutation_id,
            'description': MUTATION_DESCRIPTIONS.get(mutation_id, 'Unknown'),
            'duration': 0,
            'passes': 0,
            'violations': 0,
            'detected': False,
            'error': str(e),
            'log_file': log_file.name
        }
    finally:
        # Stop servers
        print("\nStopping servers...")
        server_process.terminate()
        try:
            server_process.wait(timeout=3)
        except:
            server_process.kill()
        print("✓ Servers stopped")
        time.sleep(2)  # Wait before next test


def main():
    mutations_dir = Path(__file__).resolve().parent
    parent_dir = mutations_dir.parent

    print("="*80)
    print(" SMTP REPEATED RECIPIENT - MUTATION TESTING")
    print("="*80)
    print(f"\nTotal mutations to test: {len(MUTATIONS)}")
    print(f"Mutations: {', '.join(MUTATIONS)}")
    print("\nThis will take approximately 10-15 minutes...")
    print("="*80 + "\n")

    start_time = time.time()
    results = []

    for i, mutation in enumerate(MUTATIONS, 1):
        print(f"\n[{i}/{len(MUTATIONS)}] Testing {mutation}...")
        result = run_mutation(mutation, mutations_dir, parent_dir)
        results.append(result)
        time.sleep(1)  # Brief pause between mutations

    end_time = time.time()
    total_duration = end_time - start_time

    # Generate summary
    print("\n" + "="*80)
    print(" MUTATION TESTING SUMMARY")
    print("="*80 + "\n")

    print(f"Total mutations tested: {len(results)}")
    print(f"Total time: {format_duration(total_duration)}\n")

    # Results table
    print(f"{'Mutation':<12} {'Detected':<10} {'Passes':<8} {'Violations':<12} {'Duration':<10} {'Status'}")
    print("-"*80)

    detected_count = 0
    total_mutations = 0
    for r in results:
        # Skip baseline from detection metrics
        if r['mutation'] == 'BASELINE':
            detected_str = "N/A"
        else:
            detected_str = "YES ✓" if r['detected'] else "NO ✗"
            total_mutations += 1
            if r['detected']:
                detected_count += 1

        status = r.get('error', 'OK')
        duration_str = format_duration(r['duration'])

        print(f"{r['mutation']:<12} {detected_str:<10} {r['passes']:<8} {r['violations']:<12} {duration_str:<10} {status}")

    print("-"*80)
    print(f"\nDetection rate: {detected_count}/{total_mutations} ({detected_count/total_mutations*100:.1f}%)")

    print(f"✓ Individual logs saved to: {OUTPUT_DIR / 'logs'}/")
    print("\nDone!")


if __name__ == '__main__':
    main()
