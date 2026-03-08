#!/usr/bin/env python3
"""
Generate a simple summary of all test cases from log file.
For SMTP State Reset MR (RFC 5321).
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

    # Split by "Starting new protocol run"
    sections = content.split('Starting new protocol run')

    test_cases = []

    for section in sections:
        if 'ClientB' not in section:
            continue

        case = {'events': [], 'result': None}
        lines = section.split('\n')

        for line in lines:
            if 'ClientB: <request_mail_from>' in line and 'invalid' not in line:
                case['events'].append('MAIL FROM:<sender@example.com>')
            elif 'ClientB: <request_invalid_mail_from>' in line:
                case['events'].append('MAIL FROM:<invalid@> (ERROR)')
            elif 'ClientB: <request_rcpt_to>' in line and 'invalid' not in line:
                case['events'].append('RCPT TO:<recipient@example.com>')
            elif 'ClientB: <request_invalid_rcpt_to>' in line:
                case['events'].append('RCPT TO:<invalid@> (ERROR)')
            elif 'ClientB: <request_rset>' in line:
                case['events'].append('RSET')
            elif '[PASS]' in line and not case['result']:
                case['result'] = 'PASS'
            elif '[VIOLATION]' in line and not case['result']:
                case['result'] = 'FAIL'

        if case['events']:
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
    output.append(c(" SMTP STATE RESET - ALL TEST CASES", Colors.BOLD + Colors.CYAN))
    output.append(c("=" * 80, Colors.CYAN))
    output.append("")
    output.append(f"Total test cases: {c(str(len(test_cases)), Colors.GREEN + Colors.BOLD)}")
    output.append("")

    # Test cases
    passed = 0
    failed = 0

    for i, case in enumerate(test_cases, 1):
        output.append(c(f"Test Case #{i}", Colors.CYAN + Colors.BOLD))
        output.append(c("-" * 80, Colors.DIM))

        output.append("  Connection B Flow:")

        for event in case['events']:
            if 'ERROR' in event:
                output.append(c(f"    • {event}", Colors.YELLOW))
            elif event == 'RSET':
                output.append(c(f"    • {event}", Colors.BLUE + Colors.BOLD))
            else:
                output.append(f"    • {event}")

        # Result
        if case['result'] == 'PASS':
            output.append(c(f"  Result: PASS", Colors.GREEN + Colors.BOLD))
            passed += 1
        elif case['result'] == 'FAIL':
            output.append(c(f"  Result: FAIL", Colors.RED + Colors.BOLD))
            failed += 1
        else:
            output.append(c(f"  Result: Unknown", Colors.DIM))

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
    output.append(f"RFC 5321 Compliance: {c('VERIFIED' if failed == 0 else 'ISSUES FOUND', Colors.GREEN + Colors.BOLD if failed == 0 else Colors.RED + Colors.BOLD)}")
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
