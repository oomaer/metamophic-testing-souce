"""Regression checks for MR2 connection ordering and server cleanup (no sockets)."""

from contextlib import contextmanager
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from fandango.io import FandangoIO, NetworkParty
from fandango.language.parse.parse import parse

import run_test


class ConnectionOrderingTests(unittest.TestCase):
    def test_switch_opens_b_only_when_transmitted(self):
        with patch.object(NetworkParty, 'start', autospec=True) as start, \
                patch.object(NetworkParty, 'stop', autospec=True) as stop:
            with Path(__file__).with_name('grammar.fan').open() as source:
                grammar, _ = parse(source, use_stdlib=False)
            io = FandangoIO.instance()
            start.reset_mock()
            # Fandango may generate/evaluate multiple candidates before sending.
            for _ in range(10):
                candidate = grammar.fuzz('<ChangeConnection>')
                grammar.populate_sources(candidate)
            start.assert_not_called()
            stop.assert_not_called()

            io.transmit('ConnectionControl', None, candidate)
            self.assertEqual([call.args[0].party_name for call in stop.call_args_list],
                             ['ClientA', 'ServerA'])
            self.assertEqual([call.args[0].party_name for call in start.call_args_list],
                             ['ClientB', 'ServerB'])

            # Fandango resets parties between generated test cases. Only A
            # should reconnect, and queued bytes from the old case must be gone.
            io.add_receive('ServerB', 'ClientB', b'old response\r\n')
            start.reset_mock()
            io.reset_parties()
            self.assertEqual({call.args[0].party_name for call in start.call_args_list},
                             {'ClientA', 'ServerA'})
            self.assertFalse(io.received_msg())
            self.assertIn('ConnectionControl', io.parties)


class RunnerLifecycleTests(unittest.TestCase):
    def test_each_run_stops_servers_before_next_start(self):
        events = []

        @contextmanager
        def servers(*args):
            events.append('start')
            try:
                yield
            finally:
                events.append('stop')

        with tempfile.TemporaryDirectory() as directory, \
                patch.object(sys, 'argv', ['run_test.py', '3', '--output-dir', directory]), \
                patch.object(run_test, 'smtp_servers', side_effect=servers), \
                patch.object(run_test.subprocess, 'run', side_effect=lambda *a, **k: events.append('test')):
            self.assertEqual(run_test.main(), 0)
        self.assertEqual(events, ['start', 'test', 'stop'] * 3)

    def test_startup_failure_stops_and_reaps_both_servers(self):
        processes = [Mock(), Mock()]
        for process in processes:
            process.poll.return_value = None
        with patch.object(run_test, 'check_ports_available'), \
                patch.object(run_test.subprocess, 'Popen', side_effect=processes), \
                patch.object(run_test, 'wait_for_servers', side_effect=RuntimeError('startup failed')):
            with self.assertRaisesRegex(RuntimeError, 'startup failed'):
                with run_test.smtp_servers(Path('/tmp/server.py')):
                    self.fail('Tests must not start if SMTP startup failed')
        for process in processes:
            process.terminate.assert_called_once()
            process.wait.assert_called_once_with(timeout=3)

    def test_forced_kill_is_reaped(self):
        process = Mock()
        process.poll.return_value = None
        process.wait.side_effect = [subprocess.TimeoutExpired('server', 3), 0]
        run_test.stop_processes([process])
        process.kill.assert_called_once()
        self.assertEqual(process.wait.call_count, 2)
        process.wait.assert_called_with()

    def test_test_timeout_stops_servers_and_fails_run(self):
        events = []

        @contextmanager
        def servers(*args):
            try:
                yield
            finally:
                events.append('stop')

        with tempfile.TemporaryDirectory() as directory, \
                patch.object(sys, 'argv', ['run_test.py', '10', '--output-dir', directory]), \
                patch.object(run_test, 'smtp_servers', side_effect=servers), \
                patch.object(run_test.subprocess, 'run', side_effect=subprocess.TimeoutExpired('script.py', 300)) as run:
            self.assertEqual(run_test.main(), 1)
        run.assert_called_once()
        self.assertEqual(events, ['stop'])


if __name__ == '__main__':
    unittest.main()
