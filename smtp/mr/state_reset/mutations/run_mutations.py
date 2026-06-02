#!/usr/bin/env python3
"""
Run all mutations for State Reset MR and collect results.
"""

import subprocess
import time
import sys
from pathlib import Path


MUTATIONS = ['M1', 'M3', 'M4', 'M5', 'M7']
# MUTATIONS = ['M7']

MUTATION_DESCRIPTIONS = {
    'BASELINE': 'Clean baseline - RFC compliant RSET behavior',
    'M1': 'INCOMPLETE_SENDER_RESET - RSET does not clear MAIL FROM buffer',
    'M3': 'RSET_CLEARS_AUTH - RSET incorrectly clears authentication',
    'M4': 'RSET_RETURNS_ERROR - RSET returns 500 error',
    'M5': 'RSET_PARTIAL_STATE_CLEAR - Only first RSET works per session',
    'M7': 'RSET_NOOP - RSET returns 250 but does nothing',
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
    logs_dir = mutations_dir / 'logs'
    logs_dir.mkdir(exist_ok=True)

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
    print("Servers started\n")

    start_time = time.time()

    try:
        # Run the test script
        print("Running metamorphic test...\n")

        # Run with real-time output to console AND capture for log
        process = subprocess.Popen(
            [sys.executable, str(parent_dir / 'script.py'), 'mutations/mutation_test_output.log'],
            cwd=str(parent_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )

        # Capture output while displaying in real-time
        output_lines = []
        while True:
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                break
            if line:
                print(line, end='')  # Print to console in real-time
                output_lines.append(line)

        process.wait(timeout=120)
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

        # Check for violations and parse errors (both indicate mutation detection)
        violations = full_output.count('[VIOLATION]')
        passes = full_output.count('[PASS]')

        # Also count FandangoFailedError as detections - these occur when
        # the mutation causes unexpected responses that don't match grammar
        parse_errors = full_output.count('FandangoFailedError')

        # Total detections = explicit violations + protocol parse failures
        total_detections = violations + parse_errors

        print(f"\n{'='*80}")
        print(f"Test completed in {format_duration(duration)}")
        print(f"  Passes: {passes}")
        print(f"  Violations: {violations}")
        print(f"  Parse errors: {parse_errors}")
        print(f"  Total detections: {total_detections}")
        print(f"  Log saved: {log_file.name}")

        return {
            'mutation': mutation_id,
            'description': MUTATION_DESCRIPTIONS.get(mutation_id, 'Unknown'),
            'duration': duration,
            'passes': passes,
            'violations': violations,
            'parse_errors': parse_errors,
            'total_detections': total_detections,
            'detected': total_detections > 0,
            'log_file': log_file.name
        }

    except subprocess.TimeoutExpired:
        print("Test timed out after 120 seconds")
        return {
            'mutation': mutation_id,
            'description': MUTATION_DESCRIPTIONS.get(mutation_id, 'Unknown'),
            'duration': 120,
            'passes': 0,
            'violations': 0,
            'detected': False,
            'error': 'TIMEOUT',
            'log_file': log_file.name
        }
    except Exception as e:
        print(f"Error running test: {e}")
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
        print("Servers stopped")
        time.sleep(2)  # Wait before next test


def main():
    mutations_dir = Path(__file__).parent
    parent_dir = mutations_dir.parent

    print("="*80)
    print(" SMTP STATE RESET - MUTATION TESTING")
    print("="*80)
    print(f"\nTotal mutations to test: {len(MUTATIONS)}")
    print(f"Mutations: {', '.join(MUTATIONS)}")
    print("\nThis will take approximately 10-20 minutes...")
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
    print(f"{'Mutation':<12} {'Detected':<10} {'Passes':<8} {'Violations':<12} {'ParseErr':<10} {'Duration':<10} {'Status'}")
    print("-"*90)

    detected_count = 0
    total_mutations = 0
    for r in results:
        # Skip baseline from detection metrics
        if r['mutation'] == 'BASELINE':
            detected_str = "N/A"
        else:
            detected_str = "YES" if r['detected'] else "NO"
            total_mutations += 1
            if r['detected']:
                detected_count += 1

        status = r.get('error', 'OK')
        duration_str = format_duration(r['duration'])
        parse_errors = r.get('parse_errors', 0)

        print(f"{r['mutation']:<12} {detected_str:<10} {r['passes']:<8} {r['violations']:<12} {parse_errors:<10} {duration_str:<10} {status}")

    print("-"*90)
    if total_mutations > 0:
        print(f"\nMutation Score: {detected_count}/{total_mutations} ({detected_count/total_mutations*100:.1f}%)")
    else:
        print("\nNo mutations tested (only baseline)")

    # Save results
    results_file = mutations_dir / 'mutation_results.txt'
    with open(results_file, 'w') as f:
        f.write("SMTP STATE RESET - MUTATION TESTING RESULTS\n")
        f.write("="*80 + "\n\n")
        f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Total Duration: {format_duration(total_duration)}\n")
        if total_mutations > 0:
            f.write(f"Mutation Score: {detected_count}/{total_mutations} ({detected_count/total_mutations*100:.1f}%)\n\n")

        f.write(f"{'Mutation':<12} {'Description':<45} {'Detected':<10} {'P':<4} {'V':<4} {'PE':<4}\n")
        f.write("-"*85 + "\n")

        for r in results:
            if r['mutation'] == 'BASELINE':
                detected_str = "N/A"
            else:
                detected_str = "YES" if r['detected'] else "NO"
            desc_short = r['description'][:42] + "..." if len(r['description']) > 45 else r['description']
            parse_errors = r.get('parse_errors', 0)
            f.write(f"{r['mutation']:<12} {desc_short:<45} {detected_str:<10} {r['passes']:<4} {r['violations']:<4} {parse_errors:<4}\n")

        f.write("\n" + "="*80 + "\n")
        f.write("DETAILED RESULTS\n")
        f.write("="*80 + "\n\n")

        for r in results:
            f.write(f"Mutation: {r['mutation']}\n")
            f.write(f"Description: {r['description']}\n")
            if r['mutation'] == 'BASELINE':
                f.write(f"Detected: N/A (baseline)\n")
            else:
                f.write(f"Detected: {'YES' if r['detected'] else 'NO'}\n")
            f.write(f"Passes: {r['passes']}\n")
            f.write(f"Violations: {r['violations']}\n")
            f.write(f"Parse Errors: {r.get('parse_errors', 0)}\n")
            f.write(f"Total Detections: {r.get('total_detections', 0)}\n")
            f.write(f"Duration: {format_duration(r['duration'])}\n")
            f.write(f"Log: {r['log_file']}\n")
            if 'error' in r:
                f.write(f"Error: {r['error']}\n")
            f.write("\n" + "-"*80 + "\n\n")

    print(f"\nResults saved to: {results_file}")
    print(f"Individual logs saved to: {mutations_dir / 'logs'}/")
    print("\nDone!")


if __name__ == '__main__':
    main()
