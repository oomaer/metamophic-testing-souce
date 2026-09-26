#!/usr/bin/env python3
"""Summarize mutation testing results from log files."""

import os
import re
import sys
from pathlib import Path


MUTATION_DESCRIPTIONS = {
    'M1': 'STRICT_DUPLICATE_REJECT - Reject all duplicates with 550',
    'M2': 'ACCEPT_FIRST_N_DUPLICATES - Accept first 2, reject 3rd+',
    'M10': 'REJECT_FIRST_DUPLICATE_ONLY - Reject 2nd occurrence, accept 3rd+',
    'M30': 'DUPLICATE_DELIVERS_TO_WRONG_RECIPIENT - Duplicate RCPT adds unintended recipient',
    'M44': 'MULTIPLE_RESPONSE_LINES - Send multiple 250 responses (protocol violation)',
    'M48': 'REJECT_ALL_AFTER_DUPLICATE - After duplicate, reject all subsequent RCPT',
}


def parse_duration_to_seconds(duration_str):
    """Parse duration strings like '3m 0.67s', '29.82s', '1h 2m 3.45s' to seconds."""
    total = 0.0
    h = re.search(r'(\d+)h', duration_str)
    m = re.search(r'(\d+)m', duration_str)
    s = re.search(r'([\d.]+)\s*s(?:econds?)?', duration_str)
    if h:
        total += int(h.group(1)) * 3600
    if m:
        total += int(m.group(1)) * 60
    if s:
        total += float(s.group(1))
    return total


def format_duration(seconds):
    if seconds < 60:
        return f"{seconds:.2f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.2f}s"


def parse_log(filepath):
    """Parse a single mutation log file and return results."""
    content = filepath.read_text()

    mutation_id = None
    match = re.search(r'^Mutation:\s*(\S+)', content, re.MULTILINE)
    if match:
        mutation_id = match.group(1)

    # Duration from header (written by run_mutations.py)
    duration = 0.0
    match = re.search(r'^Duration:\s*(.+)', content, re.MULTILINE)
    if match:
        duration = parse_duration_to_seconds(match.group(1))

    # Test cases
    test_cases = 0
    match = re.search(r'^Total test cases generated:\s*(\d+)', content, re.MULTILINE)
    if match:
        test_cases = int(match.group(1))

    # Violations count (from summary, not raw count)
    violations = 0
    match = re.search(r'^Violations:\s*(\d+)', content, re.MULTILINE)
    if match:
        violations = int(match.group(1))

    # Extract per-solution violations
    solution_violations = {}
    current_solution = None
    for line in content.splitlines():
        sol_match = re.match(r'^\s+(solution\d+):', line)
        if sol_match:
            current_solution = sol_match.group(1)
            solution_violations[current_solution] = []
        elif current_solution and re.match(r'^\s+-\s+', line):
            violation_text = line.strip().lstrip('- ')
            # Extract just the [VIOLATION] part
            v_match = re.search(r'\[VIOLATION\]\s*(.+)', violation_text)
            if v_match:
                solution_violations[current_solution].append(v_match.group(1))

    # Check for crashes/errors (Traceback present means it errored)
    has_error = 'Traceback (most recent call last)' in content
    error_msg = None
    if has_error:
        # Extract the last line of the traceback (the actual error)
        err_match = re.search(r'(fandango\.errors\.\w+:.+)', content)
        if err_match:
            error_msg = err_match.group(1)
        if test_cases == 0:
            violations = -1  # sentinel for "error/crash"

    killed = violations != 0

    return {
        'mutation': mutation_id,
        'description': MUTATION_DESCRIPTIONS.get(mutation_id, 'Unknown'),
        'test_cases': test_cases,
        'violations': violations,
        'killed': killed,
        'has_error': has_error,
        'error_msg': error_msg,
        'duration': duration,
        'solution_violations': solution_violations,
    }


def main():
    logs_dir = Path(__file__).parent / 'logs'
    if not logs_dir.exists():
        print(f"Logs directory not found: {logs_dir}")
        sys.exit(1)

    log_files = sorted(logs_dir.glob('log_M*.txt'))
    # Skip baseline
    log_files = [f for f in log_files if 'BASELINE' not in f.name]

    if not log_files:
        print("No mutation log files found.")
        sys.exit(1)

    results = []
    for f in log_files:
        results.append(parse_log(f))

    total_mutations = len(results)
    killed_count = sum(1 for r in results if r['killed'])
    total_time = sum(r['duration'] for r in results)
    mutation_score = (killed_count / total_mutations * 100) if total_mutations > 0 else 0

    # Print report
    print("=" * 90)
    print(" MUTATION TESTING SUMMARY — Repeated Recipient MR")
    print("=" * 90)
    print()

    header = f"{'Mutant':<8} {'Tests':<7} {'Violations':<12} {'Killed':<9} {'Duration':<12} {'Description'}"
    print(header)
    print("-" * 90)

    for r in results:
        v_str = "ERROR" if r['violations'] == -1 else str(r['violations'])
        k_str = "YES ✓" if r['killed'] else "NO  ✗"
        print(f"{r['mutation']:<8} {r['test_cases']:<7} {v_str:<12} {k_str:<9} {format_duration(r['duration']):<12} {r['description']}")

    print("-" * 90)
    print()
    print(f"  Total mutants:   {total_mutations}")
    print(f"  Killed:          {killed_count}")
    print(f"  Survived:        {total_mutations - killed_count}")
    print(f"  Mutation score:  {killed_count}/{total_mutations} ({mutation_score:.1f}%)")
    print(f"  Total time:      {format_duration(total_time)}")
    print()
    print("=" * 90)

    # Write detailed results file
    results_file = Path(__file__).parent / 'mutation_results.txt'
    with open(results_file, 'w') as f:
        f.write("=" * 90 + "\n")
        f.write(" MUTATION TESTING RESULTS — Repeated Recipient MR (RFC 5321)\n")
        f.write("=" * 90 + "\n\n")

        f.write("OVERVIEW\n")
        f.write("-" * 90 + "\n")
        f.write(f"  Total mutants:   {total_mutations}\n")
        f.write(f"  Killed:          {killed_count}\n")
        f.write(f"  Survived:        {total_mutations - killed_count}\n")
        f.write(f"  Mutation score:  {killed_count}/{total_mutations} ({mutation_score:.1f}%)\n")
        f.write(f"  Total time:      {format_duration(total_time)}\n")
        f.write("\n")

        f.write("SUMMARY TABLE\n")
        f.write("-" * 90 + "\n")
        f.write(f"{'Mutant':<8} {'Tests':<7} {'Violations':<12} {'Killed':<9} {'Duration':<12} {'Description'}\n")
        f.write("-" * 90 + "\n")

        for r in results:
            v_str = "ERROR" if r['violations'] == -1 else str(r['violations'])
            k_str = "YES" if r['killed'] else "NO"
            f.write(f"{r['mutation']:<8} {r['test_cases']:<7} {v_str:<12} {k_str:<9} {format_duration(r['duration']):<12} {r['description']}\n")

        f.write("-" * 90 + "\n\n")

        f.write("DETAILED RESULTS PER MUTANT\n")
        f.write("=" * 90 + "\n\n")

        for r in results:
            f.write(f"Mutant:      {r['mutation']}\n")
            f.write(f"Description: {r['description']}\n")
            f.write(f"Killed:      {'YES' if r['killed'] else 'NO'}\n")
            f.write(f"Test cases:  {r['test_cases']}\n")
            v_str = "ERROR (crash)" if r['violations'] == -1 else str(r['violations'])
            f.write(f"Violations:  {v_str}\n")
            f.write(f"Duration:    {format_duration(r['duration'])}\n")

            if r['has_error'] and r['error_msg']:
                f.write(f"Error:       {r['error_msg']}\n")

            if r['solution_violations']:
                f.write("\n  Violations per test case:\n")
                for sol_key, sol_vs in r['solution_violations'].items():
                    f.write(f"    {sol_key}: ({len(sol_vs)} violations)\n")
                    # Deduplicate repeated messages, show counts
                    from collections import Counter
                    counts = Counter(sol_vs)
                    for msg, count in counts.items():
                        if count > 1:
                            f.write(f"      - {msg} (x{count})\n")
                        else:
                            f.write(f"      - {msg}\n")

            f.write("\n" + "-" * 90 + "\n\n")

    print(f"\nDetailed results saved to: {results_file}")


if __name__ == '__main__':
    main()
