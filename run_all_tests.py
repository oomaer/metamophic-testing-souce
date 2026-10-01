#!/usr/bin/env python3
"""Run protocol MRs in parallel and write a timing report in thesis MR order."""

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

from extract_avg_time_and_sd import mean_and_sd, parse_avg_time, parse_time


ROOT = Path(__file__).resolve().parent
PROTOCOL_MRS = {
    "smtp": [(1, "repeated_recipient"), (2, "state_reset")],
    "http": [(3, "connection_header_variants"), (4, "range_request_reconstruction")],
    "ftp": [(5, "redundant_rnfr"), (6, "size_after_appe")],
    "imap": [(7, "append_search_inclusion")],
    "dns": [(8, "cname_recursive_resolver")],
}


def stop_process_group(process):
    """Clean up the runner and its servers before the next MR uses the ports."""
    if os.name == "posix":
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            process.wait()
            return
        # The runner may already have exited while a server still needs cleanup.
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            process.poll()
            try:
                os.killpg(process.pid, 0)
            except ProcessLookupError:
                break
            except PermissionError:
                # A group that is exiting can temporarily reject a probe on macOS.
                # Retry through the grace period; an actual kill failure still propagates.
                pass
            time.sleep(0.05)
        else:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    elif process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()
    process.wait()


def _run_mr_attempt(protocol, number, name, runs, batch_dir, cancel, timeout=None):
    output_dir = batch_dir / f"MR{number}_{protocol}_{name}"
    logs_dir = output_dir / "runs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    runner_log = output_dir / "runner.log"
    result = dict(number=number, protocol=protocol, name=name, rows=[], errors=[],
                  wall=0.0, runner_log=runner_log)
    if cancel.is_set():
        result["errors"].append("Cancelled before starting")
        return result
    start = time.monotonic()
    process = None
    try:
        with runner_log.open("w", encoding="utf-8") as log:
            process = subprocess.Popen(
                [sys.executable, "-u", "run_test.py", str(runs)],
                cwd=ROOT / protocol / "mr" / name,
                env={**os.environ, "MR_RUNS_DIR": str(logs_dir)},
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
    except OSError as error:
        result["errors"].append(str(error))
    finally:
        if process is not None:
            stop_process_group(process)
        result["wall"] = time.monotonic() - start

    # Only this batch's expected logs count, even if old runs exist beside a grammar.
    for run in range(1, runs + 1):
        path = logs_dir / f"test_output_{run}.log"
        try:
            average = parse_avg_time(path)
            generation = parse_time(path, "Test generation time")
            if average is None or generation is None:
                raise ValueError("missing timing summary")
            result["rows"].append((run, generation, average))
        except (OSError, ValueError) as error:
            result["errors"].append(f"Run {run}: {error}")
    return result


def run_mr(protocol, number, name, runs, batch_dir, cancel, timeout=None, retry=3):
    """Retry a failed MR, keeping only the final attempt's output."""
    if retry < 0:
        raise ValueError("retry must be nonnegative")
    print(f"Starting MR{number}: {protocol.upper()} / {name}", flush=True)
    started = time.monotonic()
    for attempt in range(retry + 1):
        if attempt and not cancel.is_set():
            # Do not let a previous attempt's timing summaries fill gaps in
            # the next attempt. Server cleanup has already completed.
            logs_dir = batch_dir / f"MR{number}_{protocol}_{name}" / "runs"
            for run in range(1, runs + 1):
                (logs_dir / f"test_output_{run}.log").unlink(missing_ok=True)
        result = _run_mr_attempt(protocol, number, name, runs, batch_dir, cancel, timeout)
        if not result["errors"] or cancel.is_set():
            break
    result["wall"] = time.monotonic() - started
    status = "FAILED" if result["errors"] else "OK"
    if result["errors"] and attempt == retry and not cancel.is_set():
        label = "retry" if retry == 1 else "retries"
        result["errors"].append(f"Failed after {retry} {label}")
        status = f"FAILED after {retry} {label}"
    print(f"Finished MR{number}: {status} ({result['wall']:.2f}s)", flush=True)
    return result


def run_protocol(protocol, runs, batch_dir, cancel, timeout, retry=3):
    # One worker owns a protocol; its MRs can never overlap.
    return [run_mr(protocol, number, name, runs, batch_dir, cancel, timeout, retry)
            for number, name in PROTOCOL_MRS[protocol]]


def write_report(path, results, runs, workers, elapsed):
    lines = [
        "MR timing report", f"Requested runs per MR: {runs}",
        f"Parallel protocol workers: {workers}", f"Batch wall time: {elapsed:.2f}s",
        "All timings below are in seconds.",
        "Mean and sample SD are calculated across the per-run average times per test",
        "(the same metric as extract_avg_time_and_sd.py; SD is 0 for one run).",
        "MR wall time includes server startup, cleanup and any retries. Parallel work can affect timings.",
        "OK means the runner exited successfully and all requested timing summaries exist.",
    ]
    for result in sorted(results, key=lambda item: item["number"]):
        status = "FAILED / INCOMPLETE" if result["errors"] else "OK"
        lines += ["", "=" * 80,
                  f"MR{result['number']} | {result['protocol'].upper()} | {result['name']}",
                  f"Status: {status}", f"MR wall time: {result['wall']:.2f}s",
                  f"Timing summaries: {len(result['rows'])}/{runs}",
                  "Run | Test generation time (s) | Average time per test (s)"]
        for run, generation, average in result["rows"]:
            lines.append(f"{run:3d} | {generation:24.2f} | {average:25.2f}")
        if result["rows"] and not result["errors"]:
            mean, sd = mean_and_sd([row[2] for row in result["rows"]])
            lines += [f"Mean average time per test: {mean:.2f}s", f"Sample SD: {sd:.2f}s"]
        else:
            lines.append("Mean / SD: unavailable (batch for this MR did not complete successfully)")
        lines += [f"Error: {error}" for error in result["errors"]]
        lines.append(f"Runner output: {result['runner_log']}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("runs", type=int, nargs="?", default=10)
    parser.add_argument("--retry", type=int, default=3,
                        help="Additional attempts for a failed MR (default: 3; 0 disables retries)")
    parser.add_argument("--workers", type=int, choices=range(1, 6), default=5,
                        help="Parallel protocols (default: 5; use 1 for serial timing)")
    parser.add_argument("--protocols", nargs="+", choices=PROTOCOL_MRS, default=list(PROTOCOL_MRS))
    parser.add_argument("--output-dir", type=Path, default=ROOT / "timing_results",
                        help="Parent for a new timestamped batch directory")
    parser.add_argument("--timeout", type=float,
                        help="Optional maximum seconds for each attempt of an MR runner")
    args = parser.parse_args()
    if args.runs < 1 or args.retry < 0 or (args.timeout is not None and args.timeout <= 0):
        parser.error("runs and timeout must be positive; retry must be nonnegative")
    protocols = list(dict.fromkeys(args.protocols))
    workers = min(args.workers, len(protocols))
    batch_dir = args.output_dir.expanduser().resolve() / datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    batch_dir.mkdir(parents=True)
    report = batch_dir / "timing_report.txt"
    print(f"Report: {report}", flush=True)
    cancel = threading.Event()
    started = time.monotonic()
    results = []
    interrupted = False
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(run_protocol, protocol, args.runs, batch_dir, cancel, args.timeout, args.retry)
                   for protocol in protocols]
        try:
            for future in as_completed(futures):
                results.extend(future.result())
                write_report(report, results, args.runs, workers, time.monotonic() - started)
        except KeyboardInterrupt:
            print("\nStopping runners and their servers...", flush=True)
            interrupted = True
            cancel.set()
    if interrupted:
        results = [result for future in futures for result in future.result()]
    write_report(report, results, args.runs, workers, time.monotonic() - started)
    print(f"\nTiming report saved to: {report}", flush=True)
    return 130 if interrupted else int(any(result["errors"] for result in results))


if __name__ == "__main__":
    sys.exit(main())
