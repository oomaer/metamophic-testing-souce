#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path

pyftpdlib_path = Path("/Users/i7949486/Desktop/uds/thesis/mutation/pyftpdlib")
sys.path.insert(0, str(pyftpdlib_path))

from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

PORTS = {"a": 2121, "b": 2122}
PASSIVE_PORTS = {"a": (50100, 50100), "b": (50101, 50101)}

parser = argparse.ArgumentParser()
parser.add_argument("--server", choices=["a", "b"], required=True)
parser.add_argument("--data-dir", required=True)
args = parser.parse_args()

port = PORTS[args.server]
data_dir = Path(args.data_dir)

authorizer = DummyAuthorizer()
authorizer.add_user("user", "12345", str(data_dir), perm="elradfmwMT")
handler = FTPHandler
handler.authorizer = authorizer
server = FTPServer(("127.0.0.1", port), handler)
print(f"Server {args.server.upper()} started on port {port}")
server.serve_forever()
