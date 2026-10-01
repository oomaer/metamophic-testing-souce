#!/usr/bin/env python3
"""Run mutation experiments by protocol and save logs plus the root analyzer's tables."""

import argparse
import ast
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import os
from pathlib import Path
import subprocess
import sys
import threading
import time

from run_all_tests import PROTOCOL_MRS, stop_process_group


ROOT = Path(__file__).resolve().parent


def mutation_ids(runner):
    """Read the runner's active MUTATIONS list without importing or executing it."""
    tree = ast.parse(runner.read_text(encoding="utf-8"), filename=str(runner))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "MUTATIONS"
            for target in node.targets
        ):
            mutations = ast.literal_eval(node.value)
            ids = [item if isinstance(item, str) else item[0] for item in mutations]
            if not ids or not all(isinstance(item, str) for item in ids):
                raise ValueError(f"Invalid MUTATIONS list in {runner}")
            return ids
    raise ValueError(f"No MUTATIONS list found in {runner}")


def run_mr(protocol, number, name, batch_dir, cancel, timeout=None):
    output_dir = batch_dir / f"MR{number}_{protocol}_{name}"
    logs_dir = output_dir / "logs"
    runner = ROOT / protocol / "mr" / name / "mutations" / "run_mutations.py"
    result = dict(number=number, protocol=protocol, name=name, errors=[], wall=0.0,
                  expected=[], found=[], logs_dir=logs_dir,
                  runner_log=output_dir / "runner.log", analysis_text="")
    start = time.monotonic()
    process = None
    try:
        logs_dir.mkdir(parents=True)
        result["expected"] = mutation_ids(runner)
        if cancel.is_set():
            result["errors"].append("Cancelled before starting")
            return result
        print(f"Starting MR{number}: {protocol.upper()} / {name}", flush=True)
        with result["runner_log"].open("w", encoding="utf-8") as log:
            process = subprocess.Popen(
                [sys.executable, "-u", str(runner)], cwd=runner.parent,
                env={**os.environ, "MUTATION_OUTPUT_DIR": str(output_dir)},
                stdout=log, stderr=subprocess.STDOUT,
                start_new_session=(os.name == "posix"),
            )
            while True:
                if cancel.is_set():
                    result["errors"].append("Cancelled")
                    break
                if timeout is not None and time.monotonic() - start >= timeout:
                    result["errors"].append(f"Runner timed out after {timeout:g}s")
                    break
                try:
                    code = process.wait(timeout=0.2)
                    if code:
                        result["errors"].append(f"Runner exited with status {code}")
                    break
                except subprocess.TimeoutExpired:
                    pass
    except (OSError, ValueError, SyntaxError) as error:
        result["errors"].append(str(error))
    finally:
        if process is not None:
            # Do not advance to the next MR if server cleanup fails.
            stop_process_group(process)
        result["wall"] = time.monotonic() - start

    try:
        for mutation in result["expected"]:
            paths = [logs_dir / f"log_{mutation}{suffix}" for suffix in (".txt", ".log")]
            if any(path.is_file() and path.stat().st_size for path in paths):
                result["found"].append(mutation)
            else:
                result["errors"].append(f"Missing or empty log for {mutation}")
        # Use a subprocess: redirect_stdout in concurrent threads would mix reports.
        completed = subprocess.run(
            [sys.executable, str(ROOT / "analyze_mutations.py"), str(logs_dir)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=60,
            text=True, encoding="utf-8", errors="replace",
        )
        result["analysis_text"] = completed.stdout
        if completed.returncode:
            result["errors"].append(f"Analyzer exited with status {completed.returncode}")
    except (OSError, subprocess.TimeoutExpired) as error:
        result["errors"].append(f"Analysis failed: {error}")
    status = "INCOMPLETE" if result["errors"] else "COMPLETE"
    print(f"Finished MR{number}: {status} ({len(result['found'])}/{len(result['expected'])} logs)",
          flush=True)
    return result


def run_protocol(protocol, batch_dir, cancel, timeout):
    results = []
    for number, name in PROTOCOL_MRS[protocol]:
        try:
            results.append(run_mr(protocol, number, name, batch_dir, cancel, timeout))
        except Exception:
            # A cleanup failure must also stop other active runners before we exit.
            cancel.set()
            raise
    return results


def write_report(path, results, workers, elapsed):
    lines = [
        "MR mutation report", f"Parallel protocol workers: {workers}",
        f"Batch wall time: {elapsed:.2f}s",
        "COMPLETE means the runner exited successfully and all configured mutant logs exist.",
        "Detection and test counts are taken unchanged from the root analyze_mutations.py.",
        "A completed batch can include surviving mutants, parse failures, and per-mutant errors.",
    ]
    for result in sorted(results, key=lambda item: item["number"]):
        status = "FAILED / INCOMPLETE" if result["errors"] else "COMPLETE"
        lines += ["", "=" * 100,
                  f"MR{result['number']} | {result['protocol'].upper()} | {result['name']}",
                  f"Status: {status}", f"MR wall time: {result['wall']:.2f}s",
                  f"Mutant logs: {len(result['found'])}/{len(result['expected'])}",
                  f"Logs: {result['logs_dir']}", f"Runner output: {result['runner_log']}"]
        lines += [f"Error: {error}" for error in result["errors"]]
        if result["analysis_text"]:
            lines += ["", result["analysis_text"].rstrip()]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, choices=range(1, 6), default=5)
    parser.add_argument("--protocols", nargs="+", choices=PROTOCOL_MRS, default=list(PROTOCOL_MRS))
    parser.add_argument("--output-dir", type=Path, default=ROOT / "mutation_results",
                        help="Parent for a new timestamped batch directory")
    parser.add_argument("--timeout", type=float,
                        help="Optional maximum seconds for each MR's entire mutation runner")
    args = parser.parse_args()
    if args.timeout is not None and args.timeout <= 0:
        parser.error("timeout must be positive")
    protocols = list(dict.fromkeys(args.protocols))
    workers = min(args.workers, len(protocols))
    batch_dir = args.output_dir.expanduser().resolve() / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    batch_dir.mkdir(parents=True)
    report = batch_dir / "mutation_report.txt"
    print(f"Report: {report}", flush=True)
    started = time.monotonic()
    cancel = threading.Event()
    results = []
    interrupted = False
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(run_protocol, protocol, batch_dir, cancel, args.timeout)
                   for protocol in protocols]
        try:
            for future in as_completed(futures):
                results.extend(future.result())
                write_report(report, results, workers, time.monotonic() - started)
        except KeyboardInterrupt:
            print("\nStopping runners and their servers...", flush=True)
            interrupted = True
            cancel.set()
    if interrupted:
        results = [result for future in futures for result in future.result()]
    write_report(report, results, workers, time.monotonic() - started)
    print(f"\nMutation report saved to: {report}", flush=True)
    return 130 if interrupted else int(any(result["errors"] for result in results))


if __name__ == "__main__":
    sys.exit(main())
