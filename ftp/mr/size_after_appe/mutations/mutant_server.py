#!/usr/bin/env python3
"""
Mutated FTP server for the SIZE-after-APPE metamorphic relation.

Server A on port 2121 is always baseline behavior. Server B on port 2122
applies the selected mutation to APPE persistence or SIZE accounting.
"""

import argparse
import os
import shutil
import sys
from pathlib import Path


PYFTPDLIB_PATH = Path("/Users/i7949486/Desktop/uds/thesis/mutation/pyftpdlib")
VENV_PYTHON = PYFTPDLIB_PATH / "venv" / "bin" / "python"
INITIAL_FILE_SIZE = 100
TEST_FILENAME = "test_file.txt"
MUTATIONS = ["BASELINE", "M1", "M2", "M3", "M4", "M5", "M6", "M7"]

MUTATION_DESCRIPTIONS = {
    "BASELINE": "Clean baseline - normal APPE and SIZE behavior",
    "M1": "NO_APPEND_WRITE - APPE succeeds but received bytes are discarded",
    "M2": "STALE_SIZE_AFTER_APPE - SIZE reports stale pre-append size",
    "M3": "DOUBLE_COUNT_SIZE - SIZE adds appended bytes a second time",
    "M4": "OFF_BY_ONE_SIZE - SIZE after APPE reports actual size plus one byte",
    "M5": "PARTIAL_APPEND_WRITE - APPE writes only part of the payload",
    "M6": "APPE_OVERWRITES_FILE - APPE replaces the file instead of appending",
    "M7": "EXTRA_BYTES_ON_APPEND - APPE silently appends extra bytes",
}

if not PYFTPDLIB_PATH.exists():
    print(f"Error: pyftpdlib path not found at {PYFTPDLIB_PATH}")
    sys.exit(1)

try:
    import asynchat  # noqa: F401
except ModuleNotFoundError:
    if VENV_PYTHON.exists() and Path(sys.executable) != VENV_PYTHON:
        os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), *sys.argv])
    raise

sys.path.insert(0, str(PYFTPDLIB_PATH))

from pyftpdlib.authorizers import DummyAuthorizer  # noqa: E402
from pyftpdlib.handlers import FTPHandler  # noqa: E402
from pyftpdlib.servers import FTPServer  # noqa: E402


def setup_data_dir(data_dir: Path) -> None:
    if data_dir.exists():
        shutil.rmtree(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / TEST_FILENAME).write_text("X" * INITIAL_FILE_SIZE)


def make_authorizer(data_dir: Path) -> DummyAuthorizer:
    authorizer = DummyAuthorizer()
    authorizer.add_user("user", "12345", str(data_dir), perm="elradfmwMT")
    return authorizer


class MutatedFTPHandler(FTPHandler):
    mutation_id = "BASELINE"
    appended_totals = {}
    stale_sizes = {}
    pending_size_offsets = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._appe_pre_sizes = {}

    def ftp_APPE(self, file):
        file_path = os.path.abspath(file)
        self._appe_pre_sizes[file_path] = self._safe_size(file_path)

        if self.mutation_id == "M6":
            self._truncate(file_path, 0)
            print(f"[M6] Truncated file before APPE, making append behave like overwrite for {file_path}")

        return super().ftp_APPE(file)

    def ftp_SIZE(self, path):
        file_path = os.path.abspath(path)

        if self._current_type == "a":
            self.respond("550 SIZE not allowed in ASCII mode.")
            return
        if not self.fs.isfile(self.fs.realpath(path)):
            line = self.fs.fs2ftp(path)
            self.respond(f"550 {line} is not retrievable")
            return

        actual_size = self._safe_size(file_path)
        reported_size = actual_size
        appended_total = self.appended_totals.get(file_path, 0)

        if self.mutation_id == "M2" and file_path in self.stale_sizes:
            reported_size = self.stale_sizes[file_path]
            print(f"[M2] Reporting stale SIZE {reported_size} instead of {actual_size}")
        elif self.mutation_id == "M3" and appended_total > 0:
            reported_size = actual_size + appended_total
            print(f"[M3] Reporting double-counted SIZE {reported_size} instead of {actual_size}")
        elif self.mutation_id == "M4" and file_path in self.pending_size_offsets:
            offset = self.pending_size_offsets.pop(file_path)
            reported_size = actual_size + offset
            print(f"[M4] Reporting off-by-one SIZE {reported_size} instead of {actual_size}")

        self.respond(f"213 {reported_size}")
        return path

    def on_file_received(self, file):
        file_path = os.path.abspath(file)
        pre_size = self._appe_pre_sizes.pop(file_path, self._safe_size(file_path))
        actual_size = self._safe_size(file_path)
        delta = max(0, actual_size - pre_size)

        if self.mutation_id == "M1":
            self._truncate(file_path, pre_size)
            self.stale_sizes[file_path] = pre_size
            print(f"[M1] Discarded {delta} appended bytes for {file_path}")
        elif self.mutation_id == "M2":
            self.appended_totals[file_path] = self.appended_totals.get(file_path, 0) + delta
            self.stale_sizes[file_path] = pre_size
            print(f"[M2] Stored append but cached stale size {pre_size} for {file_path}")
        elif self.mutation_id == "M3":
            self.appended_totals[file_path] = self.appended_totals.get(file_path, 0) + delta
            print(f"[M3] Stored append; total appended bytes tracked as {self.appended_totals[file_path]}")
        elif self.mutation_id == "M4":
            self.appended_totals[file_path] = self.appended_totals.get(file_path, 0) + delta
            self.pending_size_offsets[file_path] = 1
            print(f"[M4] Stored append; next SIZE will be off by one for {file_path}")
        elif self.mutation_id == "M5":
            partial_delta = delta // 2
            self._truncate(file_path, pre_size + partial_delta)
            self.appended_totals[file_path] = self.appended_totals.get(file_path, 0) + partial_delta
            print(f"[M5] Kept only {partial_delta}/{delta} appended bytes for {file_path}")
        elif self.mutation_id == "M6":
            new_size = self._safe_size(file_path)
            self.appended_totals[file_path] = new_size
            print(f"[M6] File was overwritten; new size is {new_size} for {file_path}")
        elif self.mutation_id == "M7":
            extra = b"\r\n"
            with open(file_path, "ab") as handle:
                handle.write(extra)
            self.appended_totals[file_path] = self.appended_totals.get(file_path, 0) + delta + len(extra)
            print(f"[M7] Added {len(extra)} extra bytes after APPE for {file_path}")
        else:
            self.appended_totals[file_path] = self.appended_totals.get(file_path, 0) + delta
            print(f"[BASELINE] APPE stored {delta} bytes for {file_path}")

        super().on_file_received(file)

    @staticmethod
    def _safe_size(file_path: str) -> int:
        try:
            return os.path.getsize(file_path)
        except OSError:
            return 0

    @staticmethod
    def _truncate(file_path: str, size: int) -> None:
        with open(file_path, "r+b") as handle:
            handle.truncate(size)


def make_handler(authorizer: DummyAuthorizer, mutation_id: str):
    class ConfiguredHandler(MutatedFTPHandler):
        pass

    ConfiguredHandler.authorizer = authorizer
    ConfiguredHandler.mutation_id = mutation_id
    ConfiguredHandler.appended_totals = {}
    ConfiguredHandler.stale_sizes = {}
    ConfiguredHandler.pending_size_offsets = {}
    return ConfiguredHandler


def start_servers(mutation_id: str, ftp_root: Path):
    data_dir_a = ftp_root / "data" / "server_a"
    data_dir_b = ftp_root / "data" / "server_b"
    setup_data_dir(data_dir_a)
    setup_data_dir(data_dir_b)

    handler_a = make_handler(make_authorizer(data_dir_a), "BASELINE")
    handler_b = make_handler(make_authorizer(data_dir_b), mutation_id)

    server_a = FTPServer(("127.0.0.1", 2121), handler_a)
    server_b = FTPServer(("127.0.0.1", 2122), handler_b, ioloop=server_a.ioloop)
    return server_a, server_b, data_dir_a, data_dir_b


def main():
    parser = argparse.ArgumentParser(description="FTP SIZE-after-APPE mutation server")
    parser.add_argument("--mutation", default="BASELINE", choices=MUTATIONS)
    parser.add_argument("--port-a", type=int, default=2121)
    parser.add_argument("--port-b", type=int, default=2122)
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    ftp_root = script_dir.parent.parent.parent

    if args.port_a != 2121 or args.port_b != 2122:
        print("Note: grammar uses fixed FTP ports 2121 and 2122; custom ports are ignored.")

    print("=" * 80)
    print("FTP MUTATION TESTING - SIZE After APPE MR")
    print("=" * 80)
    print(f"Server A: localhost:2121 (BASELINE)")
    print(f"Server B: localhost:2122 ({args.mutation})")
    print(f"Mutation: {args.mutation} - {MUTATION_DESCRIPTIONS[args.mutation]}")
    print("=" * 80)

    server_a, server_b, data_dir_a, data_dir_b = start_servers(args.mutation, ftp_root)
    print(f"Server A data: {data_dir_a}")
    print(f"Server B data: {data_dir_b}")
    print("Credentials: user / 12345")
    print("Press Ctrl+C to stop")
    print()

    try:
        server_a.serve_forever()
    finally:
        server_b.close_all()


if __name__ == "__main__":
    main()
