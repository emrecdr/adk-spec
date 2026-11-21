"""Diffs the recorded outputs of two harness runs after masking run-specific noise
(UUIDs, timestamps, pids, durations, virtual-environment and data directory names, line numbers
inside site-packages tracebacks).   python compare_versions.py out_2150 out_2141"""
import difflib
import re
import sys
from pathlib import Path

a_dir, b_dir = Path(sys.argv[1]), Path(sys.argv[2])
SUBS = [
    (r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", "<UUID>"),
    (r"paused with interrupt [0-9a-f]{8}", "paused with interrupt <ID8>"),
    (r"\b1[78]\d{8}\.\d+\b", "<TS>"),
    (r"deltas between consecutive events \(ms\): \[.*?\]", "deltas: <MS>"),
    (r"\b(process|pid) \d+", r"\1 <PID>"),
    (r'"pid": \d+', '"pid": <PID>'),
    (r"in \d+\.\d+s", "in <SECS>"),
    (r"\.venv(-2141)?", "<VENV>"),
    (r"data_21(50|41)", "<DATA>"),
    (r"(site-packages/[\w/\.]+\.py)\", line \d+", r'\1", line <N>'),
    (r"\(\d+ bytes\)", "(<N> bytes)"),
]


def norm(text: str) -> list[str]:
    for pat, rep in SUBS:
        text = re.sub(pat, rep, text)
    return text.splitlines()


same, differ = [], []
for a in sorted(a_dir.glob("*.txt")):
    b = b_dir / a.name
    if not b.exists():
        print(f"MISSING in {b_dir}: {a.name}")
        continue
    la, lb = norm(a.read_text()), norm(b.read_text())
    if la == lb:
        same.append(a.name)
        continue
    differ.append(a.name)
    print(f"\n########## {a.name}: DIFFERS ({a_dir} -> {b_dir})")
    for line in difflib.unified_diff(la, lb, a_dir.name, b_dir.name, lineterm="", n=1):
        print(line[:400])
print(f"\nIDENTICAL after masking ({len(same)}): {same}")
print(f"DIFFERENT ({len(differ)}): {differ}")
