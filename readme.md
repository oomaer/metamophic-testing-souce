Metamorphic testing

Run all MR timing experiments from the repository root, using the Python
environment in which the individual `run_test.py` scripts work:

```sh
python3 run_all_tests.py 10
```

If a run fails with `IndexError: list index out of range`, run the same command
again. For example:

```sh
python3 run_all_tests.py 10
```


This runs each MR ten times, with five parallel protocol workers. Within a
protocol, the next MR starts only after the previous runner and its servers stop:

| Protocol | MR order |
| --- | --- |
| SMTP | MR1 repeated_recipient, MR2 state_reset |
| HTTP | MR3 connection_header_variants, MR4 range_request_reconstruction |
| FTP | MR5 redundant_rnfr, MR6 size_after_appe |
| IMAP | MR7 append_search_inclusion |
| DNS | MR8 cname_recursive_resolver |

The console prints the report path and progress. Each invocation creates
`timing_results/<timestamp>/timing_report.txt`, with sections in MR1–MR8 order.
Each section includes the MR number/name, each run's test generation time and
average time per test, the mean and sample SD of those per-run averages, and
the MR's total wall time including server startup/cleanup. Durations are seconds.
The mean/SD use the same metric as `extract_avg_time_and_sd.py` and the precision
recorded in the logs; they are not statistics over individual test cases.

Raw logs are saved beside the report in `MR<number>_<protocol>_<name>/runs/`;
`runner.log` contains that MR's console output. Existing grammar-level `runs/`
folders remain intact. A failed runner or missing timing summary is reported as
incomplete, without a mean/SD, and the command exits with a nonzero status.
Other MRs continue. Timing completion does not certify that the MR assertions passed.

Useful options:

```sh
# Serial execution for timings without contention from other protocol workers
python3 run_all_tests.py 10 --workers 1

# Only SMTP and HTTP
python3 run_all_tests.py 10 --protocols smtp http

# Save batches elsewhere; limit each entire MR runner to one hour
python3 run_all_tests.py 10 --output-dir /path/to/results --timeout 3600
```

Individual runners still support `python3 run_test.py 10` and default to their
local `runs/` folder. The root script sets `MR_RUNS_DIR` to redirect their output.
The existing server/dependency setup is still required (including Node for HTTP
and the configured pyftpdlib environment for FTP SIZE). Avoid running another
experiment on the same protocol ports at the same time.

To extract a LaTeX row from existing logs, the old positional interface still
works, and MR number/name flags are also available:

```sh
python3 extract_avg_time_and_sd.py /path/to/runs summary_report.txt --mr-number 1 --mr-name "Repeated Recipient"
```

Run the automation's checks without launching protocol servers:

```sh
python3 -m unittest discover -s tests -v
```

Follow these steps to run the mutation experiments:

1. Open a terminal in the repository root (the directory containing
   `run_all_mutations.py`). Use the Python environment in which the individual
   mutation runners work, with their existing server dependencies installed.
   Stop any timing or mutation experiments using the same protocol ports.

2. Start the mutation batch:

   ```sh
   python3 run_all_mutations.py
   ```

   No run-count argument is needed. This runs every configured mutant once and
   skips baselines for all eight MRs. The runners start and stop their servers
   automatically.

3. Watch the terminal for each MR's start/completion status. Five protocols run
   in parallel; MRs belonging to the same protocol run sequentially. The terminal
   prints the batch's report path, so you can locate its output while it runs.

4. When the batch finishes, open
   `mutation_results/<timestamp>/mutation_report.txt`, using the timestamp printed
   in the terminal. This contains the analyzed result tables in MR1–MR8 order;
   no separate analyzer command is required. If an MR is marked incomplete,
   inspect its `runner.log` and the errors listed in the report.

This uses the same MR order and five protocol workers as the timing runner.
SMTP runs MR1 then MR2, HTTP runs MR3 then MR4, and FTP runs MR5 then MR6;
IMAP and DNS run MR7 and MR8. Each runner uses its existing active `MUTATIONS`
list; baselines are skipped for all MRs. The next MR of a protocol starts after
the preceding runner and its server processes have stopped.

Each invocation creates `mutation_results/<timestamp>/mutation_report.txt`.
The report contains all eight tables in MR order, produced by the root
`analyze_mutations.py` with its existing detection and test-count rules.
Within each `MR<number>_<protocol>_<name>/` directory, the batch also saves:

- `logs/log_<mutation>.txt`: per-mutant logs supplied to the analyzer.
- `runner.log`: the mutation runner's console output and errors.

The combined `mutation_report.txt` is the only generated analysis report.
MR-local analysis/summary scripts have been removed, and mutation runners no
longer write separate `mutation_results.txt`, `summary.txt`, or `analysis.txt`
reports. Use the root `analyze_mutations.py` to inspect any saved logs manually.

The root runner sets `MUTATION_OUTPUT_DIR` for each MR; running an individual
`python3 run_mutations.py` still writes its per-mutant logs in the local `logs/`
folder and prints progress and results to the terminal.
Mutation runners capture test output in `logs/log_<mutation>.txt` and disable
the test script's duplicate file output. They do not generate extra
`test_output_<mutation>.log`, `mutation_test_output.log`, or default
`test_output.log` files. Timing runs still write their normal per-run logs.

An unsuccessful runner or a missing/empty expected mutant log marks the MR
incomplete and gives the root command a nonzero exit status. Other MRs continue,
and partial logs and tables remain available. `COMPLETE` describes collection
of the configured logs; it does not mean all mutants were detected or that every
per-mutant test succeeded. Inspect the tables and runner logs for those details.

```sh
# Run only SMTP and HTTP mutations
python3 run_all_mutations.py --protocols smtp http

# Run protocols sequentially
python3 run_all_mutations.py --workers 1

# Choose an output location and limit each MR's entire runner to one hour
python3 run_all_mutations.py --output-dir /path/to/results --timeout 3600
```

To analyze saved logs again, run the root analyzer with that MR's `logs/` path.
For example, replace `<timestamp>` with your batch directory's name:

```sh
python3 analyze_mutations.py "mutation_results/<timestamp>/MR1_smtp_repeated_recipient/logs"
```

The optional timeout applies to an entire MR's mutation runner. Ctrl+C stops
active runners and their servers and saves a partial report. Use the same Python
environment and server dependencies as for the individual mutation runners.
Do not run timing experiments alongside mutation experiments on the same ports.
