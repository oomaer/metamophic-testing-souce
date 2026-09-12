#!/usr/bin/env python3
"""Summarize cname_recursive_resolver2 mutation logs."""

from pathlib import Path


def analyze_log(path):
    text = path.read_text(errors="replace")
    return {
        "mutation": path.stem.replace("log_", ""),
        "passes": text.count("[PASS]"),
        "violations": text.count("[VIOLATION]"),
        "tracebacks": text.count("Traceback (most recent call last)"),
    }


def main():
    mutations_dir = Path(__file__).parent
    logs_dir = mutations_dir / "logs"

    if not logs_dir.exists():
        print(f"No logs found at {logs_dir}")
        print("Run python run_mutations.py first.")
        return

    results = [analyze_log(path) for path in sorted(logs_dir.glob("log_*.txt"))]
    if not results:
        print(f"No log_*.txt files found at {logs_dir}")
        return

    print("=" * 80)
    print(" DNS CNAME RECURSIVE RESOLVER 2 - MUTATION LOG ANALYSIS")
    print("=" * 80)
    print(f"{'Mutation':<12} {'Detected':<10} {'Passes':<8} {'Violations':<12} {'Tracebacks'}")
    print("-" * 80)

    detected = 0
    total = 0
    for result in results:
        is_baseline = result["mutation"] == "BASELINE"
        is_detected = result["violations"] > 0 or result["tracebacks"] > 0
        if is_baseline:
            detected_text = "N/A"
        else:
            detected_text = "YES" if is_detected else "NO"
            total += 1
            if is_detected:
                detected += 1
        print(
            f"{result['mutation']:<12} {detected_text:<10} {result['passes']:<8} "
            f"{result['violations']:<12} {result['tracebacks']}"
        )

    print("-" * 80)
    score = detected / total * 100 if total else 0
    print(f"Mutation Score: {detected}/{total} ({score:.1f}%)")


if __name__ == "__main__":
    main()
