"""Exercise timing extraction and scheduling without launching protocol servers."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
import io
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

import extract_avg_time_and_sd as timing
import run_all_tests as runner


FAKE_RUNNER = '''\
import os
from pathlib import Path
import sys
import time
output = Path(os.environ['MR_RUNS_DIR'])
start = time.monotonic()
time.sleep(0.15)
for run in range(1, int(sys.argv[1]) + 1):
    (output / f'test_output_{run}.log').write_text(
        f'Test generation time: 1m 2.50s\\nAverage time per test: {run} seconds\\n')
(output / 'interval').write_text(f'{start} {time.monotonic()}')
'''


class TimingTests(unittest.TestCase):
    def test_durations_and_invalid_values(self):
        for value, expected in [('2.25 seconds', 2.25), ('1m 2.50s', 62.5),
                                ('1h 2m 3.25s', 3723.25), ('0', 0)]:
            self.assertEqual(timing.parse_duration(value), expected)
        for value in ['n/a', 'nan', '-1 seconds', '2 seconds extra']:
            with self.assertRaises(ValueError):
                timing.parse_duration(value)

    def test_numeric_order_statistics_and_legacy_interface(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            logs = root / 'runs'
            logs.mkdir()
            for number in [10, 2, 1]:
                (logs / f'test_output_{number}.log').write_text(
                    f'Average time per test: {number} seconds\n')
            self.assertEqual([v for _, v in timing.collect_avg_times(logs)], [1, 2, 10])
            self.assertEqual(timing.mean_and_sd([1, 2, 3]), (2, 1))
            self.assertEqual(timing.mean_and_sd([2]), (2, 0))
            with redirect_stdout(io.StringIO()):
                timing.generate_latex_row(logs, root / 'report.txt', 'MR-3', 'HTTP')
            self.assertIn('MR-3 (HTTP) & 1.00 & 2.00 & 10.00',
                          (root / 'report.txt').read_text())

    def make_project(self, root, script=FAKE_RUNNER):
        for protocol, mrs in runner.PROTOCOL_MRS.items():
            for _, name in mrs:
                folder = root / protocol / 'mr' / name
                folder.mkdir(parents=True)
                (folder / 'run_test.py').write_text(script)
                (folder / 'runs').mkdir()
                (folder / 'runs' / 'test_output_99.log').write_text('old results')

    def test_protocol_overlap_sequential_mrs_and_ordered_report(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_project(root)
            batch = root / 'batch'
            with patch.object(runner, 'ROOT', root), ThreadPoolExecutor(max_workers=5) as pool:
                futures = [pool.submit(runner.run_protocol, protocol, 3, batch,
                                       threading.Event(), None)
                           for protocol in runner.PROTOCOL_MRS]
                results = [result for future in futures for result in future.result()]
            self.assertEqual(len(results), 8)
            self.assertTrue(all(not result['errors'] for result in results))
            intervals = {}
            for result in results:
                intervals[result['number']] = tuple(map(float, (
                    result['runner_log'].parent / 'runs' / 'interval').read_text().split()))
                self.assertEqual(len(result['rows']), 3)
            for first, second in [(1, 2), (3, 4), (5, 6)]:
                self.assertLessEqual(intervals[first][1], intervals[second][0])
            self.assertLess(max(intervals[n][0] for n in [1, 3, 5, 7, 8]),
                            min(intervals[n][1] for n in [1, 3, 5, 7, 8]))
            report = root / 'report.txt'
            runner.write_report(report, results[::-1], 3, 5, 1)
            text = report.read_text()
            self.assertEqual(sorted(range(1, 9), key=lambda n: text.index(f'MR{n} |')),
                             list(range(1, 9)))
            self.assertEqual(text.count('Mean average time per test: 2.00s'), 8)
            self.assertEqual(text.count('Sample SD: 1.00s'), 8)
            self.assertEqual((root / 'smtp/mr/repeated_recipient/runs/test_output_99.log').read_text(),
                             'old results')

    def test_failed_mr_recovers_and_keeps_only_successful_attempt(self):
        script = """import os
from pathlib import Path
output = Path(os.environ['MR_RUNS_DIR'])
count = output.parent / 'attempt_count'
attempt = int(count.read_text()) + 1 if count.exists() else 1
count.write_text(str(attempt))
print(f'attempt {attempt}')
for run in range(1, 3):
    (output / f'test_output_{run}.log').write_text(
        f'Test generation time: {attempt} seconds\\nAverage time per test: {attempt} seconds\\n')
raise SystemExit(1 if attempt < 3 else 0)
"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_project(root, script)
            with patch.object(runner, 'ROOT', root), redirect_stdout(io.StringIO()) as console:
                result = runner.run_mr('smtp', 1, 'repeated_recipient', 2,
                                       root / 'batch', threading.Event(), retry=2)
            self.assertEqual(result['errors'], [])
            self.assertEqual(result['rows'], [(1, 3, 3), (2, 3, 3)])
            self.assertEqual(result['runner_log'].read_text(), 'attempt 3\n')
            self.assertNotIn('FAILED', console.getvalue())
            self.assertEqual((result['runner_log'].parent / 'attempt_count').read_text(), '3')

    def test_retry_limits_and_default(self):
        script = """import os
from pathlib import Path
count = Path(os.environ['MR_RUNS_DIR']).parent / 'attempt_count'
count.write_text(str(int(count.read_text()) + 1 if count.exists() else 1))
raise SystemExit(2)
"""
        for retry in [0, 2, None]:
            with self.subTest(retry=retry), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.make_project(root, script)
                options = {} if retry is None else {'retry': retry}
                expected = 3 if retry is None else retry
                with patch.object(runner, 'ROOT', root), redirect_stdout(io.StringIO()) as console:
                    result = runner.run_mr('smtp', 1, 'repeated_recipient', 1,
                                           root / 'batch', threading.Event(), **options)
                self.assertEqual((result['runner_log'].parent / 'attempt_count').read_text(),
                                 str(expected + 1))
                self.assertIn(f'Failed after {expected} retries', result['errors'])
                self.assertIn(f'FAILED after {expected} retries', console.getvalue())

    def test_retry_discards_stale_timing_summaries(self):
        script = """import os
from pathlib import Path
output = Path(os.environ['MR_RUNS_DIR'])
count = output.parent / 'attempt_count'
attempt = int(count.read_text()) + 1 if count.exists() else 1
count.write_text(str(attempt))
text = 'Test generation time: 1 seconds\\nAverage time per test: 1 seconds\\n'
(output / 'test_output_1.log').write_text(text)
if attempt == 1:
    (output / 'test_output_2.log').write_text(text)
raise SystemExit(1 if attempt == 1 else 0)
"""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_project(root, script)
            with patch.object(runner, 'ROOT', root), redirect_stdout(io.StringIO()):
                result = runner.run_mr('smtp', 1, 'repeated_recipient', 2,
                                       root / 'batch', threading.Event(), retry=2)
            self.assertEqual(len(result['rows']), 1)
            self.assertTrue(any(error.startswith('Run 2:') for error in result['errors']))
            self.assertEqual((result['runner_log'].parent / 'attempt_count').read_text(), '3')

    def test_cancellation_is_not_retried(self):
        cancel = threading.Event()

        def cancelled(*args):
            cancel.set()
            return {'errors': ['Cancelled'], 'wall': 0}

        with patch.object(runner, '_run_mr_attempt', side_effect=cancelled) as attempt, redirect_stdout(io.StringIO()):
            result = runner.run_mr('smtp', 1, 'repeated_recipient', 1,
                                   Path('unused'), cancel, retry=3)
        attempt.assert_called_once()
        self.assertEqual(result['errors'], ['Cancelled'])

    def test_failure_timeout_and_missing_logs_are_not_success(self):
        scripts = ['raise SystemExit(2)', 'import time; time.sleep(10)', 'pass']
        with tempfile.TemporaryDirectory() as directory:
            for index, script in enumerate(scripts):
                root = Path(directory) / str(index)
                self.make_project(root, script)
                with patch.object(runner, 'ROOT', root):
                    result = runner.run_mr('smtp', 1, 'repeated_recipient', 2,
                                           root / 'batch', threading.Event(), 0.3)
                self.assertTrue(result['errors'])
                report = root / 'report.txt'
                runner.write_report(report, [result], 2, 1, 0.3)
                self.assertIn('Mean / SD: unavailable', report.read_text())
                if index == 0:
                    self.assertIn('Runner exited with status 2', result['errors'])
                if index == 1:
                    self.assertTrue(any('timed out' in error for error in result['errors']))


if __name__ == '__main__':
    unittest.main()
