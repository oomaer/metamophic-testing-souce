#!/usr/bin/env python3
"""Analyze FTP Redundant RNFR mutation logs."""

import re
from pathlib import Path


MUTATION_DESCRIPTIONS = {
    "BASELINE": "Clean baseline - normal RNFR/RNTO behavior",
    "M1": "FIRST_RNFR_WINS - Only first RNFR is stored; subsequent ignored",
    "M2": "REJECT_REDUNDANT_RNFR - Second RNFR returns 503 error",
    "M5": "RENAME_WRONG_TARGET - RNTO renames completely random/wrong directory",
    "M6": "WRONG_RNTO_SUCCESS_CODE - RNTO returns 200 instead of 250",
}

MUTATIONS = ["BASELINE", "M1", "M2", "M5", "M6"]


def parse_duration_to_seconds(duration_str):
    total = 0.0
    hours = re.search(r"(\d+)h", duration_str)
    minutes = re.search(r"(\d+)m", duration_str)
    seconds = re.search(r"([\d.]+)\s*s(?:econds?)?", duration_str)
    if hours:
        total += int(hours.group(1)) * 3600
    if minutes:
        total += int(minutes.group(1)) * 60
    if seconds:
        total += float(seconds.group(1))
    return total


def format_duration(seconds):
    if seconds < 60:
        return f"{seconds:.2f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.2f}s"


def parse_log(log_file):
    if not log_file.exists():
        return {
            "status": "MISSING",
            "duration": 0.0,
            "test_cases": 0,
            "passes": 0,
            "violations": 0,
            "solution_violations": {},
        }

    content = log_file.read_text()
    duration = 0.0
    match = re.search(r"^Duration:\s*(.+)", content, re.MULTILINE)
    if match:
        duration = parse_duration_to_seconds(match.group(1))

    test_cases = 0
    match = re.search(r"^Total test cases generated:\s*(\d+)", content, re.MULTILINE)
    if match:
        test_cases = int(match.group(1))

    passes = 0
    match = re.search(r"^Passed:\s*(\d+)", content, re.MULTILINE)
    if match:
        passes = int(match.group(1))
    else:
        passes = content.count("[PASS]")

    violations = 0
    match = re.search(r"^Violations:\s*(\d+)", content, re.MULTILINE)
    if match:
        violations = int(match.group(1))
    else:
        violations = content.count("[VIOLATION]")

    solution_violations = {}
    current_solution = None
    for line in content.splitlines():
        solution_match = re.match(r"^\s+(solution\d+):", line)
        if solution_match:
            current_solution = solution_match.group(1)
            solution_violations[current_solution] = []
            continue
        if current_solution and re.match(r"^\s+-\s+", line):
            solution_violations[current_solution].append(line.strip().lstrip("- "))

    status = "ERROR" if "Traceback (most recent call last)" in content else "OK"
    return {
        "status": status,
        "duration": duration,
        "test_cases": test_cases,
        "passes": passes,
        "violations": violations,
        "solution_violations": solution_violations,
    }


def main():
    mutations_dir = Path(__file__).parent
    logs_dir = mutations_dir / "logs"
    if not logs_dir.exists():
        print(f"Logs directory not found: {logs_dir}")
        return 1

    results = []
    for mutation_id in MUTATIONS:
        parsed = parse_log(logs_dir / f"log_{mutation_id}.txt")
        parsed["mutation"] = mutation_id
        parsed["description"] = MUTATION_DESCRIPTIONS[mutation_id]
        parsed["killed"] = parsed["violations"] > 0 or parsed["status"] == "ERROR"
        results.append(parsed)

    total_mutations = len([r for r in results if r["mutation"] != "BASELINE"])
    killed_count = len([r for r in results if r["mutation"] != "BASELINE" and r["killed"]])
    total_time = sum(r["duration"] for r in results)
    score = killed_count / total_mutations * 100 if total_mutations else 0

    print("=" * 90)
    print(" MUTATION TESTING SUMMARY - FTP Redundant RNFR MR")
    print("=" * 90)
    print()
    print(f"{'Mutant':<10} {'Tests':<7} {'Passes':<8} {'Violations':<12} {'Killed':<9} {'Duration':<10} Description")
    print("-" * 90)
    for result in results:
        killed = "N/A" if result["mutation"] == "BASELINE" else ("YES" if result["killed"] else "NO")
        print(
            f"{result['mutation']:<10} {result['test_cases']:<7} {result['passes']:<8} "
            f"{result['violations']:<12} {killed:<9} {format_duration(result['duration']):<10} "
            f"{result['description']}"
        )
    print("-" * 90)
    print(f"Mutation score: {killed_count}/{total_mutations} ({score:.1f}%)")
    print(f"Total time: {format_duration(total_time)}")

    results_file = mutations_dir / "mutation_results.txt"
    with open(results_file, "w") as handle:
        handle.write("=" * 90 + "\n")
        handle.write(" MUTATION TESTING RESULTS - FTP Redundant RNFR MR\n")
        handle.write("=" * 90 + "\n\n")
        handle.write(f"Total mutants:   {total_mutations}\n")
        handle.write(f"Killed:          {killed_count}\n")
        handle.write(f"Survived:        {total_mutations - killed_count}\n")
        handle.write(f"Mutation score:  {killed_count}/{total_mutations} ({score:.1f}%)\n")
        handle.write(f"Total time:      {format_duration(total_time)}\n\n")
        handle.write(f"{'Mutant':<10} {'Tests':<7} {'Passes':<8} {'Violations':<12} {'Killed':<9} {'Duration':<10} Description\n")
        handle.write("-" * 90 + "\n")
        for result in results:
            killed = "N/A" if result["mutation"] == "BASELINE" else ("YES" if result["killed"] else "NO")
            handle.write(
                f"{result['mutation']:<10} {result['test_cases']:<7} {result['passes']:<8} "
                f"{result['violations']:<12} {killed:<9} {format_duration(result['duration']):<10} "
                f"{result['description']}\n"
            )

        handle.write("\nDETAILED VIOLATIONS\n")
        handle.write("=" * 90 + "\n\n")
        for result in results:
            handle.write(f"Mutation: {result['mutation']}\n")
            handle.write(f"Description: {result['description']}\n")
            if result["solution_violations"]:
                for solution, violations in result["solution_violations"].items():
                    handle.write(f"  {solution}: {len(violations)} violation(s)\n")
                    for violation in violations:
                        handle.write(f"    - {violation}\n")
            else:
                handle.write("  No violations recorded.\n")
            handle.write("\n" + "-" * 90 + "\n\n")

    print(f"\nDetailed results saved to: {results_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
