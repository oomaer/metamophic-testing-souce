#!/usr/bin/env python3
"""
Generate a simple summary of all test cases from log file.
For FTP Redundant RNFR MR (RFC 959).
"""

import re
import sys
from pathlib import Path

# ANSI color codes
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    BOLD = '\033[1m'
    DIM = '\033[2m'
    RESET = '\033[0m'


def parse_test_cases(log_file):
    """Parse log and extract test case flows."""
    with open(log_file, 'r') as f:
        content = f.read()

    # Split by TEST CASE markers
    sections = re.split(r'={80}\nTEST CASE #\d+', content)

    test_cases = []

    for section in sections:
        if '<rnfr_B>' not in section:
            continue

        case = {
            'dir_A': None, 'target_A': None,
            'dir_B': None, 'target_B': None,
            'rnfr_count_B': 0,
            'result': None
        }
        lines = section.split('\n')

        for line in lines:
            # Extract directory names from MKD/RNFR/RNTO commands
            if '<mkd_A>' in line:
                match = re.search(r"'MKD (.+?)\\r\\n'", line)
                if match:
                    case['dir_A'] = match.group(1)
            elif '<rnto_A>' in line:
                match = re.search(r"'RNTO (.+?)\\r\\n'", line)
                if match:
                    case['target_A'] = match.group(1)
            elif '<mkd_B>' in line:
                match = re.search(r"'MKD (.+?)\\r\\n'", line)
                if match:
                    case['dir_B'] = match.group(1)
            elif '<rnfr_B>' in line:
                case['rnfr_count_B'] += 1
            elif '<rnto_B>' in line:
                match = re.search(r"'RNTO (.+?)\\r\\n'", line)
                if match:
                    case['target_B'] = match.group(1)
            elif '[PASS]' in line and not case['result']:
                case['result'] = 'PASS'
            elif '[VIOLATION]' in line and not case['result']:
                case['result'] = 'FAIL'

        if case['dir_A'] or case['dir_B']:
            test_cases.append(case)

    return test_cases


def c(text, color):
    """Colorize text."""
    return f"{color}{text}{Colors.RESET}"


def main():
    script_dir = Path(__file__).parent
    log_file = script_dir / "test_output.log"

    if not log_file.exists():
        print(f"{Colors.RED}Error: {log_file} not found. Run the test first.{Colors.RESET}")
        sys.exit(1)

    test_cases = parse_test_cases(log_file)

    output = []

    # Header
    output.append(c("=" * 80, Colors.CYAN))
    output.append(c(" FTP REDUNDANT RNFR - ALL TEST CASES", Colors.BOLD + Colors.CYAN))
    output.append(c("=" * 80, Colors.CYAN))
    output.append("")
    output.append(c("Metamorphic Relation (MR):", Colors.BOLD))
    output.append("  Multiple RNFR commands before RNTO should work correctly.")
    output.append("  The last RNFR determines which file/directory to rename.")
    output.append("  Both normal (1 RNFR) and redundant (multiple RNFR) should succeed identically.")
    output.append("")
    output.append(f"Total test cases: {c(str(len(test_cases)), Colors.GREEN + Colors.BOLD)}")
    output.append("")

    # Test cases
    passed = 0
    failed = 0

    for i, case in enumerate(test_cases, 1):
        output.append(c(f"Test Case #{i}", Colors.CYAN + Colors.BOLD))
        output.append(c("-" * 80, Colors.DIM))

        # Session A (Normal)
        output.append("  " + c("Session A (Normal rename):", Colors.BOLD))
        output.append(f"    1. {c('USER/PASS', Colors.DIM)}    → Login")
        output.append(f"    2. {c('MKD', Colors.YELLOW)}       {case.get('dir_A', 'N/A')} → Create directory")
        output.append(f"    3. {c('RNFR', Colors.BLUE)}      {case.get('dir_A', 'N/A')} → Mark for rename (1x)")
        output.append(f"    4. {c('RNTO', Colors.GREEN)}      {case.get('target_A', 'N/A')} → Rename to target")
        output.append(f"    5. {c('EPSV', Colors.CYAN)}        → Enter passive mode")
        output.append(f"    6. {c('LIST', Colors.CYAN)}        → Verify renamed directory exists")
        output.append(f"    7. {c('RMD', Colors.YELLOW)}       {case.get('target_A', 'N/A')} → Cleanup")
        output.append(f"    8. {c('QUIT', Colors.DIM)}        → Disconnect")
        output.append("")

        # Session B (Redundant RNFR)
        rnfr_count = case.get('rnfr_count_B', 0)
        output.append("  " + c("Session B (Redundant RNFR):", Colors.BOLD))
        output.append(f"    1. {c('USER/PASS', Colors.DIM)}    → Login")
        output.append(f"    2. {c('MKD', Colors.YELLOW)}       {case.get('dir_B', 'N/A')} → Create directory")
        output.append(f"    3. {c('RNFR', Colors.BLUE)}      {case.get('dir_B', 'N/A')} → Mark for rename ({rnfr_count}x redundant)")
        output.append(f"    4. {c('RNTO', Colors.GREEN)}      {case.get('target_B', 'N/A')} → Rename to target")
        output.append(f"    5. {c('EPSV', Colors.CYAN)}        → Enter passive mode")
        output.append(f"    6. {c('LIST', Colors.CYAN)}        → Verify renamed directory exists")
        output.append(f"    7. {c('RMD', Colors.YELLOW)}       {case.get('target_B', 'N/A')} → Cleanup")
        output.append(f"    8. {c('QUIT', Colors.DIM)}        → Disconnect")
        output.append("")

        # Metamorphic Relation Check
        output.append("  " + c("Metamorphic Relation:", Colors.BOLD))
        output.append(f"    • Both RNTO operations should return same status code")
        output.append(f"    • Both LIST outputs should show renamed directories")
        output.append(f"    • Last RNFR in Session B determines file to rename")
        output.append("")

        # Result
        if case['result'] == 'PASS':
            output.append(c(f"  ✓ Result: PASS - Redundant RNFR handled correctly", Colors.GREEN + Colors.BOLD))
            passed += 1
        elif case['result'] == 'FAIL':
            output.append(c(f"  ✗ Result: FAIL - Metamorphic relation violated", Colors.RED + Colors.BOLD))
            failed += 1
        else:
            output.append(c(f"  ? Result: Unknown", Colors.DIM))

        output.append("")

    # Summary
    output.append(c("=" * 80, Colors.CYAN))
    output.append(c(" SUMMARY", Colors.BOLD + Colors.CYAN))
    output.append(c("=" * 80, Colors.CYAN))
    output.append("")
    output.append(f"Total test cases:  {c(str(len(test_cases)), Colors.BOLD)}")
    output.append(f"Passed:            {c(str(passed), Colors.GREEN + Colors.BOLD)}")
    output.append(f"Failed:            {c(str(failed), Colors.RED + Colors.BOLD if failed > 0 else Colors.GREEN)}")
    output.append("")
    output.append(f"RFC 959 Compliance: {c('VERIFIED' if failed == 0 else 'ISSUES FOUND', Colors.GREEN + Colors.BOLD if failed == 0 else Colors.RED + Colors.BOLD)}")
    output.append("")

    # Print and save
    result_text = '\n'.join(output)
    print(result_text)

    output_file = script_dir / "all_test_cases.txt"
    with open(output_file, 'w') as f:
        f.write(result_text)

    print(c(f"Saved to: {output_file}", Colors.DIM))


if __name__ == "__main__":
    main()
