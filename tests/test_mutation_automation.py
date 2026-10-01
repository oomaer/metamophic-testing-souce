"""Check scheduling, output isolation, and cleanup without real protocol servers."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import redirect_stdout
import importlib.util
import io
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

import run_all_mutations as runner


FAKE_RUNNER = '''\
import os
from pathlib import Path
import time
MUTATIONS = [('M1', 'First mutant'), ('M2', 'Second mutant')]
output = Path(os.environ['MUTATION_OUTPUT_DIR'])
start = time.monotonic()
time.sleep(0.2)
for mutation, description in MUTATIONS:
    (output / 'logs' / f'log_{mutation}.txt').write_text(
        f'Mutation: {mutation}\\nDescription: {description}\\n'
        'fandango:INFO: Starting new protocol run\\n[VIOLATION] detected\\n')
(output / 'interval').write_text(f'{start} {time.monotonic()}')
'''


class MutationAutomationTests(unittest.TestCase):
    def make_project(self, root):
        shutil.copy(runner.ROOT / 'analyze_mutations.py', root / 'analyze_mutations.py')
        for protocol, mrs in runner.PROTOCOL_MRS.items():
            for _, name in mrs:
                folder = root / protocol / 'mr' / name / 'mutations'
                folder.mkdir(parents=True)
                (folder / 'run_mutations.py').write_text(FAKE_RUNNER)
                (folder / 'logs').mkdir()
                (folder / 'logs' / 'log_OLD.txt').write_text('old experiment')

    def test_five_protocols_overlap_mrs_are_sequential_and_tables_match(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_project(root)
            with patch.object(runner, 'ROOT', root), ThreadPoolExecutor(max_workers=5) as pool:
                futures = [pool.submit(runner.run_protocol, protocol, root / 'batch',
                                       threading.Event(), None)
                           for protocol in runner.PROTOCOL_MRS]
                results = [result for future in futures for result in future.result()]
            self.assertEqual(len(results), 8)
            intervals = {}
            for result in results:
                self.assertFalse(result['errors'])
                self.assertEqual(result['found'], ['M1', 'M2'])
                intervals[result['number']] = tuple(map(float, (
                    result['logs_dir'].parent / 'interval').read_text().split()))
                expected = subprocess.check_output(
                    [sys.executable, str(root / 'analyze_mutations.py'), str(result['logs_dir'])],
                    text=True)
                self.assertEqual(result['analysis_text'], expected)
                self.assertFalse((result['logs_dir'].parent / 'analysis.txt').exists())
            for first, second in [(1, 2), (3, 4), (5, 6)]:
                self.assertLessEqual(intervals[first][1], intervals[second][0])
            self.assertLess(max(intervals[n][0] for n in [1, 3, 5, 7, 8]),
                            min(intervals[n][1] for n in [1, 3, 5, 7, 8]))
            report = root / 'report.txt'
            runner.write_report(report, results[::-1], 5, 1)
            text = report.read_text()
            self.assertEqual(sorted(range(1, 9), key=lambda n: text.index(f'MR{n} |')),
                             list(range(1, 9)))
            self.assertEqual(text.count('Status: COMPLETE'), 8)
            self.assertNotIn('OLD', text)
            for path in root.glob('*/mr/*/mutations/logs/log_OLD.txt'):
                self.assertEqual(path.read_text(), 'old experiment')

    def test_cli_failure_continues_next_mr_and_reports_missing_logs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_project(root)
            script = root / 'smtp/mr/repeated_recipient/mutations/run_mutations.py'
            script.write_text("MUTATIONS = ['M1', 'M2']\nraise SystemExit(2)\n")
            with patch.object(runner, 'ROOT', root), patch.object(sys, 'argv', [
                'run_all_mutations.py', '--protocols', 'smtp', 'smtp', '--workers', '1',
                '--output-dir', str(root / 'results'),
            ]), redirect_stdout(io.StringIO()):
                self.assertEqual(runner.main(), 1)
            reports = list((root / 'results').glob('*/mutation_report.txt'))
            self.assertEqual(len(reports), 1)
            text = reports[0].read_text()
            self.assertIn('Runner exited with status 2', text)
            self.assertIn('Missing or empty log for M1', text)
            self.assertIn('MR2 | SMTP | state_reset', text)
            self.assertEqual(text.count('Status: COMPLETE'), 1)

    def test_timeout_and_cancellation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.make_project(root)
            script = root / 'smtp/mr/repeated_recipient/mutations/run_mutations.py'
            script.write_text("MUTATIONS = ['M1']\nimport time\ntime.sleep(20)\n")
            with patch.object(runner, 'ROOT', root):
                result = runner.run_mr('smtp', 1, 'repeated_recipient', root / 'timeout',
                                       threading.Event(), 0.1)
                self.assertTrue(any('timed out' in error for error in result['errors']))
                cancel = threading.Event()
                cancel.set()
                with patch.object(runner.subprocess, 'Popen') as popen:
                    result = runner.run_mr('smtp', 1, 'repeated_recipient', root / 'cancel',
                                           cancel)
                    popen.assert_not_called()
                self.assertIn('Cancelled before starting', result['errors'])

    def test_real_mutation_lists(self):
        counts = []
        for protocol, mrs in runner.PROTOCOL_MRS.items():
            for _, name in mrs:
                path = runner.ROOT / protocol / 'mr' / name / 'mutations/run_mutations.py'
                mutations = runner.mutation_ids(path)
                self.assertNotIn('BASELINE', mutations)
                self.assertNotIn('NONE', mutations)
                counts.append(len(mutations))
        self.assertEqual(counts, [6, 5, 5, 9, 6, 7, 6, 7])

    def test_ftp_and_imap_cleanup_does_not_match_smtp(self):
        for protocol in ['ftp', 'imap']:
            for _, name in runner.PROTOCOL_MRS[protocol]:
                folder = runner.ROOT / protocol / 'mr' / name / 'mutations'
                with tempfile.TemporaryDirectory() as directory, patch.dict(
                    os.environ, {'MUTATION_OUTPUT_DIR': directory}
                ):
                    spec = importlib.util.spec_from_file_location('mutation_fixture', folder / 'run_mutations.py')
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    with patch.object(module.subprocess, 'run') as run, patch.object(
                        module.subprocess, 'Popen'
                    ) as popen, patch.object(module.time, 'sleep'), redirect_stdout(io.StringIO()):
                        popen.return_value.poll.return_value = 1
                        popen.return_value.communicate.return_value = (b'', b'fake startup failure')
                        module.run_mutation('M1', folder, folder.parent)
                    patterns = [call.args[0][-1] for call in run.call_args_list
                                if call.args[0][0] == 'pkill']
                    self.assertTrue(patterns)
                    smtp = str(runner.ROOT / 'smtp/mr/state_reset/mutations/mutant_server.py')
                    self.assertTrue(all(re.search(pattern, smtp) is None for pattern in patterns))
                    self.assertTrue(any(re.search(pattern, str(folder / 'mutant_server.py'))
                                        for pattern in patterns))


if __name__ == '__main__':
    unittest.main()
