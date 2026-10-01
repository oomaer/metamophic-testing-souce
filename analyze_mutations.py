#!/usr/bin/env python3
"""Print all MR mutation tables, or one with: python analyze_mutations.py /path/to/logs."""

import argparse
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
# Ordered by thesis MR number, independent of the current working directory.
MR_LOG_PATHS = [
    PROJECT_ROOT / "smtp/mr/repeated_recipient/mutations/logs",       # MR1
    PROJECT_ROOT / "smtp/mr/state_reset/mutations/logs",              # MR2
    PROJECT_ROOT / "http/mr/connection_header_variants/mutations/logs",  # MR3
    PROJECT_ROOT / "http/mr/range_request_reconstruction/mutations/logs",  # MR4
    PROJECT_ROOT / "ftp/mr/redundant_rnfr/mutations/logs",             # MR5
    PROJECT_ROOT / "ftp/mr/size_after_appe/mutations/logs",            # MR6
    PROJECT_ROOT / "imap/mr/append_search_inclusion/mutations/logs",   # MR7
    PROJECT_ROOT / "dns/mr/cname_recursive_resolver/mutations/logs",   # MR8
]

RUN_MARKER = "fandango:INFO: Starting new protocol run"
PARSE_ERROR = re.compile(
    r"\bparse[ _-]?error\b|\bparsing error\b|\bfailed to parse\b"
    r"|\bFandango(?:Failed|Value|Parse)Error\b",
    re.IGNORECASE,
)


def _header(text, name):
    match = re.search(rf"^{name}:[ \t]*(.*)$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def _sort_key(row):
    match = re.fullmatch(r"M?(\d+)", row[0], re.IGNORECASE)
    return (0, int(match.group(1))) if match else (1, row[0])


def analyze_mutations(logs_folder):
    """Print a table for per-mutation log_*.txt and log_*.log files.

    Metadata comes from Mutation: and Description: NAME - explanation headers.
    Missing IDs fall back to the filename; missing metadata is shown as Unknown.
    Detection (killed) means VIOLATION, a parse error, FandangoError, or
    FandangoFailedError appears anywhere in the log, even alongside PASS.
    Tests are
    counted as protocol-run markers plus one, including when no marker exists.
    Baseline logs, if present, are included using the same rules.
    """
    folder = Path(logs_folder).expanduser()
    if not folder.is_dir():
        raise NotADirectoryError(f"Not a logs directory: {folder}")

    paths = [
        path for path in folder.iterdir()
        if path.is_file()
        and path.name.startswith("log_")
        and path.suffix.lower() in (".txt", ".log")
    ]
    if not paths:
        print(f"No log_*.txt or log_*.log files found in {folder}")
        return

    rows = []
    for path in sorted(paths):
        text = path.read_text(encoding="utf-8", errors="replace")
        mutation = _header(text, "Mutation") or path.stem.removeprefix("log_")
        description = _header(text, "Description")
        name = _header(text, "Name")
        if not name:
            name_part, separator, detail = description.partition(" - ")
            if separator:
                name, description = name_part.strip(), detail.strip()
        detected = (
            "FandangoError" in text
            or "FandangoFailedError" in text
            or "VIOLATION" in text
            or PARSE_ERROR.search(text) is not None
        )
        rows.append([
            mutation,
            name or "Unknown",
            description or "Unknown",
            "YES" if detected else "NO",
            str(text.count(RUN_MARKER) + 1),
        ])

    headers = ["Mutation", "Name", "Description", "Detected", "Tests run"]
    rows.sort(key=_sort_key)
    widths = [max(len(row[i]) for row in [headers] + rows) for i in range(len(headers))]

    def format_row(row):
        return " | ".join(cell.ljust(width) for cell, width in zip(row, widths)).rstrip()

    print(format_row(headers))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(format_row(row))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "logs_folder", nargs="?",
        help="Path to mutation logs (default: all eight MRs in thesis order)",
    )
    args = parser.parse_args()
    if args.logs_folder is not None:
        try:
            analyze_mutations(args.logs_folder)
        except OSError as error:
            parser.exit(1, f"Error: {error}\n")
        return

    for mr_number, logs_folder in enumerate(MR_LOG_PATHS, 1):
        print("\n" + "=" * 100)
        print(f"MR{mr_number}: {logs_folder.relative_to(PROJECT_ROOT)}")
        print("=" * 100)
        try:
            analyze_mutations(logs_folder)
        except OSError as error:
            # Keep printing the remaining MRs when one folder is unavailable.
            print(f"Error: {error}")


if __name__ == "__main__":
    main()
