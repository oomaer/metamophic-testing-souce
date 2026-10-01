Metamorphic testing

Run in Docker

With Docker running, build the image from this folder:

```sh
docker build -t metamorphic-testing .
```

Run both scripts, setting the number of timing repetitions with `--runs`:

```sh
docker run --rm -v "/absolute/path/to/results:/results" metamorphic-testing --runs 10
```

Replace `/absolute/path/to/results` with the folder where you want the output.
The container runs `run_all_tests.py` first, then `run_all_mutations.py`.
Reports and logs are saved under `timing_results/` and `mutation_results/`
inside your chosen folder. `--runs` controls the timing repetitions; mutations
use their configured mutation lists. Add `--retry 2` to change the number of
retries for each failed timing MR (default: 3; `--retry 0` disables retries).

Setup for another computer

Use Python 3.12 (the experiments were checked with Python 3.12.0) on macOS
or Linux. Install Node.js for the HTTP servers; this computer uses Node
25.2.1. The JavaScript servers use only Node's built-in `http` module, so no
npm packages are required. The cleanup scripts also require `pkill` and `lsof`.

Install all Python runtime dependencies with the same interpreter you will
use for the experiments:

```sh
python3 -m pip install -r requirements.txt
```

`requirements.txt` pins the direct and transitive runtime libraries from the
current environment. Fandango is installed from Git revision
`0357637f3afb2e051de645416f8804fc8b6a6bb2`, matching the local development
checkout used for these experiments. Although that checkout reports version
1.1.1, it is newer than the published release; installing `fandango-fuzzer==1.1.1`
would not reproduce the same code. This source installation requires Git,
a C++17 compiler and CMake 3.18 or newer. Pip installs Fandango's declared
Python build dependencies automatically. Local Fandango build files have
editable-install adjustments; these are not part of the Git pin, and the
fresh source installation still needs validation on the recipient's computer.

The runners currently use Unix process-cleanup commands; native Windows is
not supported by this setup. Run everything with the same Python interpreter.
Run all MR timing experiments from the repository root, using the Python
environment in which the individual `run_test.py` scripts work:

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
Other MRs continue. 
A timing MR that fails is retried up to three more times by default. Use
`--retry 2` for two retries or `--retry 0` to disable retries. Only the final
attempt's logs and timings are kept. If all attempts fail, the runner reports
"Failed after N retries" and continues to the next MR. Cancellation is not
retried. An optional `--timeout` applies separately to each attempt. 

Useful options:

```sh
# Only SMTP and HTTP
python3 run_all_tests.py 10 --protocols smtp http

```

To run only individual mr and go its mr folder and run `python3 run_test.py 10` , it saves logs to 
local `runs/` folder. 
The existing server/dependency setup is still required (including Node for HTTP
and the installed `pyftpdlib` package for FTP). Avoid running another
experiment on the same protocol ports at the same time.

FTP baseline and mutation servers use the same Python interpreter as their
runners (`sys.executable`) and import the installed package. Install it into
the Python environment used to run the experiments:

```sh
python3 -m pip install pyftpdlib==2.2.0
```

No separate pyftpdlib checkout or FTP-specific virtual environment is required.

To extract times per test from existing logs of any mr, run this script with path to the logs of the mr

```sh
python3 extract_avg_time_and_sd.py /path/to/runs summary_report.txt --mr-number 1 --mr-name "Repeated Recipient"
```


Follow these steps to run the mutation experiments:

1. Open a terminal in the repository root (the directory containing
   `run_all_mutations.py`). Use the Python environment in which the individual
   mutation runners (mutation runner in the specific folder) work, with their existing server dependencies installed.
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
   in the terminal. This contains the analyzed result tables in MR1–MR8 order. 
   If an MR is marked incomplete,
   inspect its `runner.log` and the errors listed in the report, and try running it again.

This uses the same MR order and five protocol workers as the timing runner.
SMTP runs MR1 then MR2, HTTP runs MR3 then MR4, and FTP runs MR5 then MR6;
IMAP and DNS run MR7 and MR8. Each runner uses its existing active `MUTATIONS`
list. The next MR of a protocol starts after
the preceding runner and its server processes have stopped.

Each invocation creates `mutation_results/<timestamp>/mutation_report.txt`.
The report contains all eight tables in MR order, produced by the root
`analyze_mutations.py` with its existing detection and test-count rules.
Within each `MR<number>_<protocol>_<name>/` directory, the batch also saves:

- `logs/log_<mutation>.txt`: per-mutant logs supplied to the analyzer.
- `runner.log`: the mutation runner's console output and errors.

The combined `mutation_report.txt` is the only generated analysis report.

Running an individual
`python3 run_mutations.py` still writes its per-mutant logs in the local `logs/`. and 
can use paths to those logs to run analyze_mutations in root directory to see the results.

```sh
python3 analyze_mutations.py "mutation_results/<timestamp>/MR1_smtp_repeated_recipient/logs"
```

