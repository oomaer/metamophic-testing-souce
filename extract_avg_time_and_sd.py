import sys
import re
import statistics
from pathlib import Path

def parse_avg_time(file_path):
    """Extracts the numeric average time per test in seconds from a log file."""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Matches numeric value (integers or floats) after "Average time per test:"
    match = re.search(r"Average time per test:\s*([\d.]+)", content)
    if match:
        return float(match.group(1))
    return None

def generate_latex_row(folder_path, output_file="summary_report.txt", mr_label="MR-1"):
    folder = Path(folder_path)
    
    if not folder.is_dir():
        print(f"Error: Directory '{folder_path}' does not exist.")
        sys.exit(1)

    # Find and sort all log/txt files
    log_files = sorted([f for f in folder.iterdir() if f.is_file() and f.suffix in ('.log', '.txt')])

    avg_times = []
    for f in log_files:
        time_val = parse_avg_time(f)
        if time_val is not None:
            avg_times.append(time_val)

    if not avg_times:
        print(f"No valid log files with average times found in '{folder_path}'.")
        sys.exit(0)

    # Compute Mean and Standard Deviation (SD)
    mean_val = statistics.mean(avg_times)
    sd_val = statistics.stdev(avg_times) if len(avg_times) > 1 else 0.0

    # Format row: MR-1 & file1_val & file2_val & ... & mean & SD \\
    formatted_times = [f"{v:.2f}" for v in avg_times]
    formatted_mean = f"{mean_val:.2f}"
    formatted_sd = f"{sd_val:.2f}"

    columns = [mr_label] + formatted_times + [formatted_mean, formatted_sd]
    latex_row = " & ".join(columns) + r" \\"

    # Append row to output file
    out_path = Path(output_file)
    with open(out_path, 'a', encoding='utf-8') as f:
        f.write(latex_row + "\n")

    print("Generated Row:")
    print(latex_row)
    print(f"\nAppended successfully to: {out_path.resolve()}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python parse_logs.py /path/to/folder [output_file.txt] [MR_LABEL]")
        sys.exit(1)

    folder_arg = sys.argv[1]
    out_arg = sys.argv[2] if len(sys.argv) > 2 else "summary_report.txt"
    mr_arg = sys.argv[3] if len(sys.argv) > 3 else "MR-1"

    generate_latex_row(folder_arg, out_arg, mr_arg)