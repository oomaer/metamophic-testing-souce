import sys
import os
import re
from pathlib import Path
from datetime import datetime

def parse_log_file(file_path):
    """Extracts test metrics from a single log file."""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    test_cases_match = re.search(r"Total test cases generated:\s*(\d+)", content)
    gen_time_match = re.search(r"Test generation time:\s*([^\n\r]+)", content)
    avg_time_match = re.search(r"Average time per test:\s*([^\n\r]+)", content)

    if not (test_cases_match and gen_time_match and avg_time_match):
        return None

    return {
        "test_cases": test_cases_match.group(1).strip(),
        "gen_time": gen_time_match.group(1).strip(),
        "avg_time": avg_time_match.group(1).strip()
    }

def append_report(folder_path, output_file="summary_report.txt"):
    folder = Path(folder_path)
    
    if not folder.is_dir():
        print(f"Error: Directory '{folder_path}' does not exist.")
        sys.exit(1)

    # Get all log/txt files sorted by name
    log_files = sorted([f for f in folder.iterdir() if f.is_file() and f.suffix in ('.log', '.txt')])

    metrics_map = {}
    valid_files = []

    for f in log_files:
        data = parse_log_file(f)
        if data:
            valid_files.append(f.name)
            metrics_map[f.name] = data

    if not valid_files:
        print(f"No matching log files found in '{folder_path}'.")
        sys.exit(0)

    rows = [
        ("Total test cases", "test_cases"),
        ("Total test generation time", "gen_time"),
        ("Average time per test", "avg_time"),
    ]

    # Calculate column widths for clean alignment
    col_widths = [max(len("Number"), max(len(r[0]) for r in rows))]
    for fname in valid_files:
        max_len = max(
            len(fname),
            len(metrics_map[fname]["test_cases"]),
            len(metrics_map[fname]["gen_time"]),
            len(metrics_map[fname]["avg_time"])
        )
        col_widths.append(max_len)

    # Build table lines
    headers = ["Number"] + valid_files
    header_line = " | ".join(h.ljust(w) for h, w in zip(headers, col_widths))
    divider_line = "-+-".join("-" * w for w in col_widths)

    table_lines = [header_line, divider_line]
    for label, key in rows:
        row_cells = [label.ljust(col_widths[0])]
        for idx, fname in enumerate(valid_files, start=1):
            val = metrics_map[fname][key]
            row_cells.append(val.ljust(col_widths[idx]))
        table_lines.append(" | ".join(row_cells))

    # Prepare section header with date/time and run details
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    section_header = (
        f"\n{'='*80}\n"
        f"RUN REPORT: {folder.resolve()}\n"
        f"TIMESTAMP : {timestamp}\n"
        f"{'='*80}\n"
    )

    out_path = Path(output_file)
    
    # Append mode ('a') ensures previous runs remain intact
    with open(out_path, 'a', encoding='utf-8') as f:
        f.write(section_header + "\n".join(table_lines) + "\n\n")

    print(f"Report appended successfully to: {out_path.resolve()}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python parse_logs.py /path/to/folder [output_file.txt]")
        sys.exit(1)

    folder_arg = sys.argv[1]
    out_arg = sys.argv[2] if len(sys.argv) > 2 else "summary_report.txt"

    append_report(folder_arg, out_arg)