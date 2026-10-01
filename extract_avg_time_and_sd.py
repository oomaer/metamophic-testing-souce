"""Extract per-run average test times, their mean, and sample SD in seconds."""

import argparse
import re
import statistics
from pathlib import Path


def parse_duration(value):
    """Handle the seconds, minutes, and hours formats emitted by script.py."""
    match = re.fullmatch(
        r"\s*(?:(\d+)h\s*)?(?:(\d+)m\s*)?(\d+(?:\.\d+)?)\s*(?:seconds?|s)?\s*",
        value,
    )
    if not match:
        raise ValueError(f"Invalid duration: {value!r}")
    hours, minutes, seconds = match.groups()
    return int(hours or 0) * 3600 + int(minutes or 0) * 60 + float(seconds)


def parse_time(file_path, label="Average time per test"):
    content = Path(file_path).read_text(encoding="utf-8", errors="replace")
    match = re.search(rf"{re.escape(label)}:[ \t]*([^\r\n]+)", content)
    return parse_duration(match.group(1)) if match else None


def parse_avg_time(file_path):
    return parse_time(file_path)


def log_sort_key(path):
    # Natural ordering: test_output_2.log precedes test_output_10.log.
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", path.name)]


def collect_avg_times(folder_path):
    folder = Path(folder_path)
    if not folder.is_dir():
        raise NotADirectoryError(f"Directory does not exist: {folder}")
    files = sorted(
        (p for p in folder.iterdir() if p.is_file() and p.suffix in (".log", ".txt")),
        key=log_sort_key,
    )
    return [(path, value) for path in files if (value := parse_avg_time(path)) is not None]


def mean_and_sd(values):
    return statistics.mean(values), statistics.stdev(values) if len(values) > 1 else 0.0


def generate_latex_row(folder_path, output_file="summary_report.txt", mr_label="MR-1", mr_name=None):
    rows = collect_avg_times(folder_path)
    if not rows:
        raise ValueError(f"No valid log files with average times found in '{folder_path}'.")
    values = [value for _, value in rows]
    mean, sd = mean_and_sd(values)
    label = f"{mr_label} ({mr_name})" if mr_name else mr_label
    latex_row = " & ".join([label] + [f"{v:.2f}" for v in values + [mean, sd]]) + r" \\"
    with Path(output_file).open("a", encoding="utf-8") as output:
        output.write(latex_row + "\n")
    print(latex_row)
    print(f"Appended successfully to: {Path(output_file).resolve()}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder", type=Path)
    parser.add_argument("output", nargs="?", default="summary_report.txt")
    parser.add_argument("mr_label", nargs="?", default="MR-1", help="Legacy MR label")
    parser.add_argument("--mr-number", type=int)
    parser.add_argument("--mr-name")
    args = parser.parse_args()
    if args.mr_number is not None and args.mr_number < 1:
        parser.error("MR number must be positive")
    label = f"MR-{args.mr_number}" if args.mr_number is not None else args.mr_label
    try:
        generate_latex_row(args.folder, args.output, label, args.mr_name)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Error: {error}\n")


if __name__ == "__main__":
    main()
