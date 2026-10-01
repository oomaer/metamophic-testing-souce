"""Run timing tests followed by mutation tests, saving results in /results."""
import argparse
from pathlib import Path
import signal
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runs', type=int, default=10, help='Timing repetitions per MR')
    parser.add_argument('--retry', type=int, default=3, help='Retries for each failed timing MR')
    args = parser.parse_args()
    if args.runs < 1 or args.retry < 0:
        parser.error('--runs must be positive; --retry must be nonnegative')

    child = None
    stopped = False

    def stop(signum, frame):
        nonlocal stopped
        stopped = True
        if child is not None and child.poll() is None:
            child.send_signal(signal.SIGINT)

    previous = {sig: signal.signal(sig, stop) for sig in (signal.SIGINT, signal.SIGTERM)}
    failed = False
    try:
        for script, arguments, folder in [
            ('run_all_tests.py', [str(args.runs), '--retry', str(args.retry)], 'timing_results'),
            ('run_all_mutations.py', [], 'mutation_results'),
        ]:
            if stopped:
                break
            print(f'Running {script}; results: /results/{folder}', flush=True)
            child = subprocess.Popen(
                [sys.executable, '-u', str(ROOT / script), *arguments,
                 '--output-dir', f'/results/{folder}'],
                cwd=ROOT, start_new_session=True,
            )
            if stopped:
                stop(signal.SIGINT, None)
            code = child.wait()
            child = None
            failed |= code != 0
            stopped |= code in (130, -signal.SIGINT)
        return 130 if stopped else int(failed)
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


if __name__ == '__main__':
    sys.exit(main())
