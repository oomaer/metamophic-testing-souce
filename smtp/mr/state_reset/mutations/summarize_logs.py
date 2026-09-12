#!/usr/bin/env python3
"""
Summarize the per-mutation log files in ./logs into a single table.

For every log_M*.txt this reports:
  - mutation id + human name
  - total test cases run (TEST CASE #N markers)
  - first test case that produced a failure (violation or parse error)
  - #passes / #violations
  - duration (parsed from the log header)
  - detection kind: VIOLATION (constraint) / PARSE_ERROR / BOTH / NONE
  - killed?  (log ends in a Python traceback with no SUMMARY block emitted)

The output is written next to this script as summary.txt.
"""

import re
from pathlib import Path

# Mirror of the descriptions used by run_mutations.py — kept here so this script
# is standalone and doesn't need to import the runner.
MUTATION_NAMES = {
    'M1': 'INCOMPLETE_SENDER_RESET - RSET does not clear MAIL FROM buffer',
    'M3': 'RSET_CLEARS_AUTH - RSET incorrectly clears authentication',
    'M4': 'RSET_RETURNS_ERROR - RSET returns 500 error',
    'M5': 'RSET_PARTIAL_STATE_CLEAR - Only first RSET works per session',
    'M7': 'RSET_NOOP - RSET returns 250 but does nothing',
}

TEST_CASE_RE = re.compile(r'TEST CASE #(\d+)')
VIOLATION_TAG = '[VIOLATION]'
# Any of these appearing as a raw traceback line means Fandango crashed mid-run.
PARSE_ERROR_MARKERS = (
    'FandangoFailedError',
    'FandangoValueError',
)
DURATION_RE = re.compile(r'^Duration:\s*(.+)$', re.MULTILINE)
DESCRIPTION_RE = re.compile(r'^Description:\s*(.+)$', re.MULTILINE)

# Formats produced by run_mutations.format_duration(): "12.34s", "1m 12.34s",
# "1h 2m 12.34s". Parse each piece back into seconds so we can sum across logs.
_DURATION_PIECE_RE = re.compile(r'(\d+(?:\.\d+)?)\s*([hms])')


def parse_duration_seconds(text: str) -> float | None:
    """Turn '2m 40.48s' style strings back into float seconds. None if unparseable."""
    if not text:
        return None
    total = 0.0
    matched = False
    for value, unit in _DURATION_PIECE_RE.findall(text):
        matched = True
        v = float(value)
        if unit == 'h':
            total += v * 3600
        elif unit == 'm':
            total += v * 60
        else:
            total += v
    return total if matched else None


def format_duration(seconds: float) -> str:
    """Mirror of run_mutations.format_duration for consistency."""
    if seconds < 60:
        return f"{seconds:.2f}s"
    if seconds < 3600:
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}m {secs:.2f}s"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours}h {minutes}m {secs:.2f}s"


def parse_log(path: Path):
    """Extract the summary fields for one log file."""
    text = path.read_text(errors='replace')
    lines = text.splitlines()

    header_duration = ''
    m = DURATION_RE.search(text)
    if m:
        header_duration = m.group(1).strip()

    header_description = ''
    m = DESCRIPTION_RE.search(text)
    if m:
        header_description = m.group(1).strip()

    # NOTE on banner ordering: script.py prints "TEST CASE #N" AFTER Fandango
    # yields solution N, not before. Fandango's logger writes directly to the
    # file mid-generation, and the constraint's [PASS]/[VIOLATION] prints also
    # land mid-generation. So lines that appear BEFORE the "TEST CASE #N"
    # banner belong to solution N (not N-1), and lines AFTER the last banner
    # belong to the next, unfinished solution. `banners_seen` tracks how many
    # banners we've passed; the active solution is banners_seen + 1.
    banners_seen = 0
    active_case = 1             # solution currently being generated
    total_cases = 0             # completed solutions (banners actually printed)
    unfinished_after_last = False   # any real content after the last banner?
    violations = 0
    passes = 0
    parse_errors = 0
    first_failure_case = None
    first_failure_kind = None   # 'VIOLATION' or 'PARSE_ERROR'

    for line in lines:
        m = TEST_CASE_RE.search(line)
        if m:
            banners_seen = int(m.group(1))
            total_cases = max(total_cases, banners_seen)
            active_case = banners_seen + 1
            unfinished_after_last = False
            continue

        # Any non-trivial content after the last banner means another solution
        # was in flight when the run ended — count it toward total_cases too.
        if line.strip() and not unfinished_after_last:
            unfinished_after_last = True

        if VIOLATION_TAG in line:
            violations += 1
            if first_failure_case is None:
                first_failure_case = active_case
                first_failure_kind = 'VIOLATION'
        # Cheap [PASS] counter — script.py counts one pass per solution but the
        # log itself has one line per constraint call. Reporting the raw line
        # count keeps this script honest about what's in the log.
        if '[PASS]' in line:
            passes += 1

        # A single Fandango crash emits its exception name on two lines
        # (once in `raise Xxx(...)` and again in the `xxx.errors.Xxx: ...`
        # summary). Count one crash per traceback by only tallying the line
        # that starts with the fully-qualified error name.
        stripped = line.lstrip()
        if any(stripped.startswith(f'fandango.errors.{m}') for m in PARSE_ERROR_MARKERS):
            parse_errors += 1
            if first_failure_case is None:
                first_failure_case = active_case
                first_failure_kind = 'PARSE_ERROR'

    # If the run died mid-solution (traceback / [VIOLATION] after the last
    # banner), that in-flight solution never got its own banner — count it.
    if unfinished_after_last:
        total_cases = max(total_cases, banners_seen + 1)

    # "Killed" heuristic: Fandango's SUMMARY block is only written when the
    # generator ran to completion. A bare Traceback at EOF with no SUMMARY
    # means the run died mid-flight.
    has_summary = 'SUMMARY' in text and 'Total test cases generated:' in text
    ends_in_traceback = any(
        marker in text for marker in PARSE_ERROR_MARKERS
    ) or 'Traceback (most recent call last)' in text
    killed = ends_in_traceback and not has_summary

    if violations and parse_errors:
        detection_kind = 'BOTH'
    elif violations:
        detection_kind = 'VIOLATION'
    elif parse_errors:
        detection_kind = 'PARSE_ERROR'
    else:
        detection_kind = 'NONE'

    return {
        'log_file': path.name,
        'duration': header_duration or 'n/a',
        'duration_seconds': parse_duration_seconds(header_duration),
        'description_in_log': header_description,
        'total_cases': total_cases,
        'passes': passes,
        'violations': violations,
        'parse_errors': parse_errors,
        'first_failure_case': first_failure_case,
        'first_failure_kind': first_failure_kind,
        'detection_kind': detection_kind,
        'killed': killed,
    }


def format_first_failure(row):
    if row['first_failure_case'] is None:
        return '-'
    return f"#{row['first_failure_case']} ({row['first_failure_kind']})"


def render_table(rows):
    headers = [
        'Mutation', 'Name', 'Cases', 'FirstFail',
        'Pass', 'Viol', 'ParseErr', 'Killed', 'Detection', 'Duration',
    ]
    display_rows = []
    for r in rows:
        display_rows.append([
            r['mutation'],
            r['name'],
            str(r['total_cases']),
            format_first_failure(r),
            str(r['passes']),
            str(r['violations']),
            str(r['parse_errors']),
            'YES' if r['killed'] else 'no',
            r['detection_kind'],
            r['duration'],
        ])

    # Aggregate row across all mutations.
    total_cases = sum(r['total_cases'] for r in rows)
    total_pass = sum(r['passes'] for r in rows)
    total_viol = sum(r['violations'] for r in rows)
    total_parse = sum(r['parse_errors'] for r in rows)
    killed_count = sum(1 for r in rows if r['killed'])
    known_durations = [r['duration_seconds'] for r in rows if r['duration_seconds'] is not None]
    if known_durations:
        total_duration_str = format_duration(sum(known_durations))
        if len(known_durations) < len(rows):
            total_duration_str += '*'  # asterisk = at least one duration was missing
    else:
        total_duration_str = 'n/a'
    totals_row = [
        'TOTAL',
        f'{len(rows)} mutations',
        str(total_cases),
        '-',
        str(total_pass),
        str(total_viol),
        str(total_parse),
        f'{killed_count}/{len(rows)}',
        '-',
        total_duration_str,
    ]

    widths = [len(h) for h in headers]
    for row in display_rows + [totals_row]:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def fmt_row(cells):
        return '  '.join(cell.ljust(widths[i]) for i, cell in enumerate(cells))

    sep = '-' * (sum(widths) + 2 * (len(widths) - 1))
    lines = [fmt_row(headers), sep]
    for row in display_rows:
        lines.append(fmt_row(row))
    lines.append(sep)
    lines.append(fmt_row(totals_row))
    return '\n'.join(lines), total_duration_str


def main():
    mutations_dir = Path(__file__).parent
    logs_dir = mutations_dir / 'logs'

    log_paths = sorted(
        logs_dir.glob('log_M*.txt'),
        key=lambda p: (len(p.stem), p.stem),  # M1 M3 M4 M5 M7 order
    )
    if not log_paths:
        print(f"No log_M*.txt files under {logs_dir}")
        return

    rows = []
    for path in log_paths:
        # log_M1.txt -> M1
        mutation_id = path.stem.split('_', 1)[1]
        parsed = parse_log(path)
        parsed['mutation'] = mutation_id
        parsed['name'] = MUTATION_NAMES.get(
            mutation_id, parsed['description_in_log'] or 'unknown'
        )
        rows.append(parsed)

    table, total_duration_str = render_table(rows)

    out_path = mutations_dir / 'summary.txt'
    with out_path.open('w') as f:
        f.write("SMTP STATE RESET - MUTATION LOG SUMMARY\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Logs scanned: {len(rows)}  (source: {logs_dir})\n")
        f.write(f"Total time (sum of per-log Duration headers): {total_duration_str}\n\n")
        f.write("Legend:\n")
        f.write("  Cases     = total 'TEST CASE #N' markers seen in the log\n")
        f.write("  FirstFail = first test case that produced a failure (VIOLATION or PARSE_ERROR)\n")
        f.write("  Pass/Viol = raw [PASS] / [VIOLATION] line counts\n")
        f.write("  ParseErr  = FandangoFailedError / FandangoValueError occurrences\n")
        f.write("  Killed    = run ended in a Python traceback with no SUMMARY block written\n")
        f.write("  Detection = VIOLATION (constraint), PARSE_ERROR (grammar mismatch), BOTH, or NONE\n")
        f.write("  Duration* = one or more logs had no parseable duration header\n\n")
        f.write(table + "\n")

    print(table)
    print(f"\nTotal time: {total_duration_str}")
    print(f"Summary written to: {out_path}")


if __name__ == '__main__':
    main()
