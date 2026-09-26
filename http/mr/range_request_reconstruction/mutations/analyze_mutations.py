#!/usr/bin/env python3
"""
Mutation Testing Results Analyzer for Range Request Reconstruction MR

Reads mutation log files and generates a comprehensive results report.
"""

import re
from pathlib import Path
from datetime import datetime


class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'


# Expected detection results for each mutation.
# YES = the MR should catch it, either as a [VIOLATION] from the body/CL check
#       OR as a grammar parse-failure crash (which script.py now emits as
#       a [VIOLATION] and counts as one violation in its SUMMARY).
# NO  = the mutation preserves body bytes AND Content-Length AND status/grammar
#       shape; validator should not flag it.
EXPECTED_DETECTION = {
    'NONE': 'NO',
    'M1':  'YES',   # last byte per part dropped
    'M2':  'YES',   # bytes=k- returns 1 byte
    'M3':  'YES',   # Content-Length lies (caught by new CL check)
    'M4':  'YES',   # returns full body — grammar parse-fail = violation
    'M5':  'YES',   # last byte of open-ended range missing
    'M6':  'YES',   # second part is identical to first
    'M7':  'YES',   # buffer overrun: 2 stray bytes appended per partial
    'M8':  'NO',    # only Content-Range lies; body + CL correct
    'M9':  'YES',   # 200 status — grammar parse-fail = violation
    'M10': 'YES',   # stale bytes prepended
    'M11': 'YES',   # empty body — grammar parse-fail = violation
    'M12': 'YES',   # truncated end
}


def get_script_dir():
    return Path(__file__).parent


def parse_log_file(log_file):
    if not log_file.exists():
        return {'passes': 0, 'violations': 0, 'status': 'MISSING', 'total_tests': 0}

    with open(log_file, 'r') as f:
        content = f.read()

    passes = content.count('[PASS]')
    violations = content.count('[VIOLATION]')

    if '[TIMEOUT]' in content:
        status = 'TIMEOUT'
    elif '[ERROR]' in content:
        status = 'ERROR'
    else:
        status = 'OK'

    total_tests = 0
    m = re.search(r'Total test cases generated: (\d+)', content)
    if m:
        total_tests = int(m.group(1))

    return {
        'passes': passes,
        'violations': violations,
        'status': status,
        'total_tests': total_tests,
    }


def generate_report(results, output_file):
    lines = []
    lines.append("=" * 100)
    lines.append("MUTATION TESTING RESULTS - Range Request Reconstruction MR")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 100)
    lines.append("")

    lines.append(f"{'ID':<6} {'Description':<55} {'Tests':<6} {'Pass':<6} {'Viol':<6} {'Status':<10} {'Detected':<10} {'Expected':<10}")
    lines.append("-" * 110)

    detected_count = 0
    total_mutations = 0
    for r in results:
        if r['id'] == 'NONE':
            continue
        total_mutations += 1
        if r['detected']:
            detected_count += 1

    for r in results:
        detected_str = 'YES' if r['detected'] else 'NO'
        lines.append(
            f"{r['id']:<6} {r['description'][:54]:<55} {r['total_tests']:<6} "
            f"{r['passes']:<6} {r['violations']:<6} {r['status']:<10} "
            f"{detected_str:<10} {r['expected']:<10}"
        )

    lines.append("-" * 110)
    lines.append("")

    expected_detected = sum(1 for r in results if r['id'] != 'NONE' and r['expected'] == 'YES')
    expected_undetected = sum(1 for r in results if r['id'] != 'NONE' and r['expected'] == 'NO')
    killed = sum(1 for r in results if r['id'] != 'NONE' and r['detected'] and r['expected'] == 'YES')

    lines.append("STATISTICS:")
    lines.append(f"  Total mutations tested: {total_mutations}")
    lines.append(f"  Mutations detected (killed): {detected_count}")
    lines.append(f"  Mutations survived: {total_mutations - detected_count}")
    lines.append(f"  Expected detectable: {expected_detected}")
    lines.append(f"  Expected undetectable: {expected_undetected}")
    lines.append("")

    mutation_score = (killed / expected_detected * 100) if expected_detected else 0
    if expected_detected:
        lines.append(f"  Mutation Score: {killed}/{expected_detected} = {mutation_score:.1f}%")
        lines.append("  (Only counting mutations expected to be detected)")
    else:
        lines.append("  Mutation Score: N/A (no detectable mutations)")
    lines.append("")

    lines.append("DETECTION ANALYSIS:")
    lines.append("")

    lines.append("  Correctly Detected (Expected YES, Got YES):")
    for r in [r for r in results if r['expected'] == 'YES' and r['detected']]:
        lines.append(f"    ✓ {r['id']}: {r['description']}")
    if not any(r['expected'] == 'YES' and r['detected'] for r in results):
        lines.append("    (none)")
    lines.append("")

    lines.append("  Missed (Expected YES, Got NO):")
    for r in [r for r in results if r['expected'] == 'YES' and not r['detected']]:
        lines.append(f"    ✗ {r['id']}: {r['description']}")
    if not any(r['expected'] == 'YES' and not r['detected'] for r in results):
        lines.append("    (none)")
    lines.append("")

    lines.append("  Correctly Not Detected (Expected NO, Got NO):")
    for r in [r for r in results if r['expected'] == 'NO' and not r['detected'] and r['id'] != 'NONE']:
        lines.append(f"    ✓ {r['id']}: {r['description']}")
    if not any(r['expected'] == 'NO' and not r['detected'] and r['id'] != 'NONE' for r in results):
        lines.append("    (none)")
    lines.append("")

    lines.append("  False Positives (Expected NO, Got YES):")
    for r in [r for r in results if r['expected'] == 'NO' and r['detected']]:
        lines.append(f"    ⚠ {r['id']}: {r['description']}")
    if not any(r['expected'] == 'NO' and r['detected'] for r in results):
        lines.append("    (none)")
    lines.append("")

    lines.append("=" * 100)

    with open(output_file, 'w') as f:
        f.write('\n'.join(lines))

    return killed, expected_detected, mutation_score


def main():
    script_dir = get_script_dir()
    logs_dir = script_dir / 'logs'

    print(f"{Colors.CYAN}{Colors.BOLD}")
    print("=" * 80)
    print(" MUTATION TESTING RESULTS ANALYZER")
    print("=" * 80)
    print(f"{Colors.RESET}")

    if not logs_dir.exists():
        print(f"{Colors.RED}Error: logs/ directory not found. Run 'python run_mutations.py' first.{Colors.RESET}")
        return

    # Keep in sync with run_mutations.MUTATIONS.
    MUTATIONS = [
        ('NONE', 'Baseline (no mutation)'),
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

    results = []

    print("Reading log files...")
    for mutation_id, description in MUTATIONS:
        log_file = logs_dir / f'log_{mutation_id}.txt'

        if not log_file.exists():
            print(f"{Colors.YELLOW}  Warning: logs/{log_file.name} not found{Colors.RESET}")
            continue

        parsed = parse_log_file(log_file)
        detected = parsed['violations'] > 0 or parsed['status'] == 'TIMEOUT'
        expected = EXPECTED_DETECTION.get(mutation_id, 'UNKNOWN')

        results.append({
            'id': mutation_id,
            'description': description,
            'passes': parsed['passes'],
            'violations': parsed['violations'],
            'status': parsed['status'],
            'total_tests': parsed['total_tests'],
            'detected': detected,
            'expected': expected,
        })

        status_color = Colors.GREEN if parsed['status'] == 'OK' else Colors.YELLOW
        detected_color = Colors.GREEN if detected else Colors.RED
        print(f"  {mutation_id}: {status_color}{parsed['status']}{Colors.RESET}, "
              f"Detected: {detected_color}{detected}{Colors.RESET}")

    print()

    if not results:
        print(f"{Colors.RED}No log files found in logs/. Run 'python run_mutations.py' first.{Colors.RESET}")
        return

    output_file = script_dir / 'mutation_results.txt'
    killed, expected, score = generate_report(results, output_file)

    print(f"{Colors.CYAN}{Colors.BOLD}")
    print("=" * 80)
    print(" SUMMARY")
    print("=" * 80)
    print(f"{Colors.RESET}")

    if expected > 0:
        score_color = Colors.GREEN if score >= 80 else Colors.YELLOW if score >= 60 else Colors.RED
        print(f"  Mutation Score: {score_color}{score:.1f}%{Colors.RESET} ({killed}/{expected} detected)")
    else:
        print(f"  Mutation Score: N/A")

    print(f"  Total mutations: {len(results) - (1 if any(r['id'] == 'NONE' for r in results) else 0)}")
    print()
    print(f"{Colors.GREEN}Results saved to: {output_file}{Colors.RESET}")
    print()


if __name__ == '__main__':
    main()
