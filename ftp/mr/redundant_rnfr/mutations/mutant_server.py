#!/usr/bin/env python3
"""
Mutated FTP server for the Redundant RNFR metamorphic relation.

Server A on port 2121 is always baseline behavior. Server B on port 2122
applies the selected mutation to RNFR/RNTO state management or execution.
"""

import argparse
import os
import shutil
from pathlib import Path

from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer


MUTATIONS = ["BASELINE", "M1", "M2", "M3", "M4", "M5", "M6"]
# MUTATIONS = ["M3"]

MUTATION_DESCRIPTIONS = {
    "BASELINE": "Clean baseline - normal RNFR/RNTO behavior",
    "M1": "FIRST_RNFR_WINS - Only first RNFR is stored; subsequent ignored",
    "M2": "REJECT_REDUNDANT_RNFR - Second RNFR returns 503 error",
    "M3": "SILENT_STATE_CLEAR - RNTO renames first RNFR's target (state cleared to first, not last)",
    "M4": "RNFR_OK_WRONG_CODE - RNFR returns 250 instead of 350",
    "M5": "RENAME_WRONG_TARGET - RNTO renames completely random/wrong directory",
    "M6": "WRONG_RNTO_SUCCESS_CODE - RNTO returns 200 instead of 250",
}

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
                # pyftpdlib keeps the pending rename source on the handler.
                self._m3_first_rnfr = self._rnfr
                print(f"[M3] Captured first RNFR target: {self._m3_first_rnfr}")
            else:
                # Silently revert pending source to the first RNFR's target
                print(f"[M3] Silently reverting pending RNFR source "
                      f"{self._rnfr!r} -> {self._m3_first_rnfr!r}")
                self._rnfr = self._m3_first_rnfr
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
            if self._rnfr:
                original_target = self._rnfr
                # pyftpdlib stores the pending source on the handler, as an
                # absolute filesystem path. Pick a source that cannot exist.
                wrong_target = os.path.join(self.fs.root, "nonexistent_dir_m5")
                while self.fs.lexists(wrong_target):
                    wrong_target += "_"
                print(f"[M5] Attempting to rename wrong target: {wrong_target} instead of {original_target}")
                self._rnfr = wrong_target
                # This will definitely fail with "No such file or directory"
            return super().ftp_RNTO(path)

        elif self.mutation_id == "M6":
            # Keep pyftpdlib's rename and error handling, replacing only the
            # successful RNTO reply. Sending 250 first would mask the mutation.
            original_respond = self.respond

            def respond_rnto(response, *args, **kwargs):
                if response.startswith("250 "):
                    response = "200 Command okay."
                return original_respond(response, *args, **kwargs)

            self.respond = respond_rnto
            try:
                return super().ftp_RNTO(path)
            finally:
                self.respond = original_respond

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
