#!/usr/bin/env python3
"""
IMAP Append+Search MR - Fandango Test Runner

Runs the metamorphic relation test using Fandango.
"""

import os
import sys
import time
import io
import logging
import re

from fandango.evolution.algorithm import Fandango, LoggerLevel
from fandango.language.grammar import FuzzingMode
from fandango.language.parse.parse import parse


class TeeStream:
    """Stream that writes to both stdout and file."""

    def __init__(self, original_stdout, log_file):
        self.original = original_stdout
        self.log_file = log_file
        self.captured = io.StringIO()

    def write(self, data):
        self.original.write(data)
        self.log_file.write(data)
        self.captured.write(data)

    def flush(self):
        self.original.flush()
        self.log_file.flush()

    def getvalue(self):
        return self.captured.getvalue()

    def reset(self):
        content = self.captured.getvalue()
        self.captured = io.StringIO()
        return content


class LoggerTeeHandler(logging.Handler):
    """Custom logging handler."""

    def __init__(self, log_file):
        super().__init__()
        self.log_file = log_file

    def emit(self, record):
        msg = self.format(record)
        self.log_file.write(msg + '\n')
        self.log_file.flush()


def format_duration(seconds):
    """Format duration in human-readable format."""
    if seconds < 60:
        return f"{seconds:.2f} seconds"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.2f}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}h {minutes}m {secs:.2f}s"


def run_fandango(grammar_path, log_file_path):
    """Run Fandango tests and collect results."""
    start_time = time.time()
    log_file = open(log_file_path, 'w')

    def log_print(*args, **kwargs):
        print(*args, **kwargs)
        print(*args, **kwargs, file=log_file)

    log_print("=" * 80)
    log_print("IMAP Metamorphic Relation: Append Then Search")
    log_print("=" * 80)
    log_print("")
    log_print("Source Test Case:")
    log_print("  SEARCH FROM 'unique-mr-test@example.com' → 0 results")
    log_print("")
    log_print("Follow-up Test Case:")
    log_print("  APPEND message with From: unique-mr-test@example.com")
    log_print("  SEARCH FROM 'unique-mr-test@example.com' → 1 result")
    log_print("")
    log_print("Relation: follow-up count == source count + 1")
    log_print("=" * 80)
    log_print("")

    log_print(f"Grammar: {grammar_path}")
    log_print("")

    # Parse grammar
    with open(grammar_path) as f:
        grammar, constraints = parse(f, use_stdlib=False)
    assert grammar is not None

    # Setup Fandango logger
    fandango_logger = logging.getLogger('fandango')
    tee_handler = LoggerTeeHandler(log_file)
    tee_handler.setFormatter(logging.Formatter('%(name)s:%(levelname)s: %(message)s'))
    fandango_logger.addHandler(tee_handler)

    # Create Fandango instance
    fandango = Fandango(
        grammar=grammar,
        constraints=constraints,
        logger_level=LoggerLevel.INFO,
        diversity_k=5,  # Back to 5 for the simple version
    )

    solutions = []
    violations = {}
    passes = 0

    old_stdout = sys.stdout
    tee_stream = TeeStream(old_stdout, log_file)
    sys.stdout = tee_stream

    generation_start = time.time()

    try:
        for solution in fandango.generate(mode=FuzzingMode.IO):
            solution_index = len(solutions)
            print(f"\n{'=' * 80}")
            print(f"TEST CASE #{solution_index + 1}")
            print(f"{'=' * 80}\n")

            solutions.append(solution)

            captured_output = tee_stream.reset()
            solution_violations = []
            has_pass = False

            for line in captured_output.split('\n'):
                if '[VIOLATION]' in line:
                    solution_violations.append(line.strip())
                if '[PASS]' in line:
                    has_pass = True

            if has_pass:
                passes += 1

            if solution_violations:
                violations[f"solution{solution_index + 1}"] = solution_violations

            print("-" * 80)

    except Exception as e:
        log_print(f"\nError during generation: {e}")
        import traceback
        traceback.print_exc()
    finally:
        sys.stdout = old_stdout
        fandango_logger.removeHandler(tee_handler)

    generation_end = time.time()
    end_time = time.time()

    total_duration = end_time - start_time
    generation_duration = generation_end - generation_start

    # Summary
    log_print("\n" + "=" * 80)
    log_print("SUMMARY")
    log_print("=" * 80)
    log_print(f"Total test cases generated: {len(solutions)}")
    log_print(f"Passed: {passes}")
    log_print(f"Violations: {len(violations)}")

    if violations:
        log_print("\nViolations per solution:")
        for sol_key, sol_violations in violations.items():
            log_print(f"  {sol_key}:")
            for v in sol_violations:
                log_print(f"    - {v}")
    else:
        log_print("\nAll solutions passed! Append+Search MR is working correctly.")

    log_print("")
    log_print("TIMING:")
    log_print(f"  Test generation time: {format_duration(generation_duration)}")
    log_print(f"  Total execution time: {format_duration(total_duration)}")
    if len(solutions) > 0:
        log_print(f"  Average time per test: {format_duration(generation_duration / len(solutions))}")

    log_print("=" * 80)

    log_file.close()
    print(f"\nLog saved to: {log_file_path}")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    grammar_path = os.path.join(script_dir, "grammar.fan")
    log_file_name = sys.argv[1] if len(sys.argv) > 1 else "test_output.log"
    log_file_path = os.path.join(script_dir, log_file_name)

    print("=" * 80)
    print("IMAP Append+Search Metamorphic Relation Test")
    print("=" * 80)
    print()
    print("Make sure imap_server.py is running on port 1144:")
    print("  python imap_server.py")
    print()
    print("Starting test...")
    print()

    run_fandango(grammar_path, log_file_path)


if __name__ == "__main__":
    main()
