#!/usr/bin/env python3
"""
Mutated FTP server for the Redundant RNFR metamorphic relation.

Server A on port 2121 is always baseline behavior. Server B on port 2122
applies the selected mutation to RNFR/RNTO state management or execution.
"""

import argparse
import os
import shutil
import sys
from pathlib import Path


PYFTPDLIB_PATH = Path("/Users/i7949486/Desktop/uds/thesis/mutation/pyftpdlib")
VENV_PYTHON = PYFTPDLIB_PATH / "venv" / "bin" / "python"
MUTATIONS = ["BASELINE", "M1", "M2", "M3", "M4", "M5", "M6"]

MUTATION_DESCRIPTIONS = {
    "BASELINE": "Clean baseline - normal RNFR/RNTO behavior",
    "M1": "FIRST_RNFR_WINS - Only first RNFR is stored; subsequent ignored",
    "M2": "REJECT_REDUNDANT_RNFR - Second RNFR returns 503 error",
    "M3": "SILENT_STATE_CLEAR - RNTO renames first RNFR's target (state cleared to first, not last)",
    "M4": "RNFR_OK_WRONG_CODE - RNFR returns 250 instead of 350",
    "M5": "RENAME_WRONG_TARGET - RNTO renames completely random/wrong directory",
    "M6": "WRONG_RNTO_SUCCESS_CODE - RNTO returns 200 instead of 250",
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
    """Create empty data directory for FTP server."""
    if data_dir.exists():
        shutil.rmtree(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)


def make_authorizer(data_dir: Path) -> DummyAuthorizer:
    authorizer = DummyAuthorizer()
    authorizer.add_user("user", "12345", str(data_dir), perm="elradfmwMT")
    return authorizer


class MutatedFTPHandler(FTPHandler):
    """FTP handler with mutation support for RNFR/RNTO operations."""

    mutation_id = "BASELINE"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._rnfr_count = 0
        self._first_rnfr_target = None
        self._rnfr_called = False
        self._m3_first_rnfr = None

    def ftp_RNFR(self, path):
        """
        Rename from - marks source file for rename.
        Mutations M1, M2, M3, M4 modify this behavior.
        """
        if self.mutation_id == "M1":
            # M1: FIRST_RNFR_WINS - Only first RNFR is stored
            if self._first_rnfr_target is None:
                self._first_rnfr_target = path
                print(f"[M1] Stored first RNFR target: {path}")
                return super().ftp_RNFR(path)
            else:
                # Ignore subsequent RNFRs but respond as if we accepted it
                print(f"[M1] Ignoring redundant RNFR: {path} (keeping first: {self._first_rnfr_target})")
                self.respond("350 File or directory exists, ready for destination name.")
                return

        elif self.mutation_id == "M2":
            # M2: REJECT_REDUNDANT_RNFR - Second RNFR returns error
            if self._rnfr_called:
                self.respond("503 Bad sequence of commands.")
                print(f"[M2] Rejected redundant RNFR: {path}")
                return
            self._rnfr_called = True
            print(f"[M2] Accepted first RNFR: {path}")
            return super().ftp_RNFR(path)

        elif self.mutation_id == "M3":
            # M3: SILENT_STATE_CLEAR - remember the FIRST RNFR; on every subsequent
            # RNFR, respond 350 but overwrite the pending rename source back to the
            # first target. RNTO then renames the first, not the last -> violates
            # "last RNFR wins" and MR should catch it via dirB1/dirB2 checks.
            result = super().ftp_RNFR(path)
            if self._m3_first_rnfr is None:
                self._m3_first_rnfr = self.fs.rnfr
                print(f"[M3] Captured first RNFR target: {self._m3_first_rnfr}")
            else:
                # Silently revert pending source to the first RNFR's target
                print(f"[M3] Silently reverting pending RNFR source "
                      f"{self.fs.rnfr!r} -> {self._m3_first_rnfr!r}")
                self.fs.rnfr = self._m3_first_rnfr
            return result

        elif self.mutation_id == "M4":
            # M4: RNFR_OK_WRONG_CODE - respond with 250 instead of 350. The grammar's
            # <rnfr_ok> is pinned to <resp_350>, so this shows up as a parse mismatch.
            # We still set fs.rnfr so RNTO can proceed (otherwise RNTO would 503 and
            # mask the mutation with a different symptom).
            try:
                if not self.fs.lexists(self.fs.ftp2fs(path)):
                    self.respond(f"550 No such file or directory.")
                    return
                self.fs.rnfr = path
                self.respond("250 Ready for destination name.")
                print(f"[M4] Returned 250 instead of 350 for RNFR: {path}")
                return path
            except (OSError, IOError) as err:
                self.respond(f"550 {err}")
                return

        else:
            # BASELINE or other mutations
            print(f"[{self.mutation_id}] Processing RNFR: {path}")
            return super().ftp_RNFR(path)

    def ftp_RNTO(self, path):
        """
        Rename to - completes the rename operation.
        Mutations M5, M6 modify this behavior.
        """
        if self.mutation_id == "M5":
            # M5: RENAME_WRONG_TARGET - Use completely wrong/random source
            if hasattr(self.fs, 'rnfr') and self.fs.rnfr:
                original_target = self.fs.rnfr
                # Use a completely random non-existent source
                import random
                wrong_target = f"nonexistent_dir_{random.randint(10000, 99999)}"
                print(f"[M5] Attempting to rename wrong target: {wrong_target} instead of {original_target}")
                self.fs.rnfr = wrong_target
                # This will definitely fail with "No such file or directory"
            return super().ftp_RNTO(path)

        elif self.mutation_id == "M6":
            # M6: WRONG_RNTO_SUCCESS_CODE - Return wrong success code
            print(f"[M6] Processing RNTO, will return wrong code")
            # Call super to do the actual rename
            result = super().ftp_RNTO(path)
            # Override the response (super already sent 250, so send 200 after)
            # This will cause a response code mismatch
            # Actually, let's intercept before super() sends response
            # We need to prevent super from responding and send our own response

            # Check if we have a pending RNFR
            line = self.fs.fs2ftp(path)
            if not self.fs.validpath(path):
                self.respond(f"553 {line} is not a valid file-system path")
                return

            src = self.fs.rnfr
            if src is None:
                self.respond("503 Bad sequence of commands: use RNFR first.")
                return

            try:
                # Perform the actual rename
                src = self.fs.ftp2fs(src)
                dst = self.fs.ftp2fs(path)
                self.run_as_current_user(self.fs.rename, src, dst)
                self.fs.rnfr = None

                # Return WRONG success code (200 instead of 250)
                self.respond("200 Command okay.")
                print(f"[M6] Returned 200 instead of 250 for successful RNTO")
                return path
            except (OSError, IOError) as err:
                self.respond(f"550 {err}")
                return

        else:
            # BASELINE or other mutations
            print(f"[{self.mutation_id}] Processing RNTO: {path}")
            return super().ftp_RNTO(path)


def make_handler(authorizer: DummyAuthorizer, mutation_id: str):
    class ConfiguredHandler(MutatedFTPHandler):
        pass

    ConfiguredHandler.authorizer = authorizer
    ConfiguredHandler.mutation_id = mutation_id
    return ConfiguredHandler


def start_servers(mutation_id: str, ftp_root: Path):
    """Start dual FTP servers: A (baseline) and B (mutant)."""
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
    parser = argparse.ArgumentParser(description="FTP Redundant RNFR mutation server")
    parser.add_argument("--mutation", default="BASELINE", choices=MUTATIONS)
    parser.add_argument("--port-a", type=int, default=2121)
    parser.add_argument("--port-b", type=int, default=2122)
    args = parser.parse_args()

    ftp_root = Path(__file__).parent.parent
    print(f"FTP Redundant RNFR Mutation Server")
    print(f"Mutation: {args.mutation}")
    print(f"Description: {MUTATION_DESCRIPTIONS.get(args.mutation, 'Unknown')}")
    print(f"Server A (Baseline): 127.0.0.1:{args.port_a}")
    print(f"Server B (Mutant): 127.0.0.1:{args.port_b}")
    print(f"Data root: {ftp_root / 'data'}")
    print("=" * 80)

    server_a, server_b, data_dir_a, data_dir_b = start_servers(args.mutation, ftp_root)

    try:
        print("Starting FTP servers...")
        server_a.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        server_a.close_all()


if __name__ == "__main__":
    main()
