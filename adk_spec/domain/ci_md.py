"""What `validate` says to GitHub Actions: each finding as a workflow command, which GitHub shows on the file's
line, and a short summary for the run's page. GitHub shows ten annotations of each kind a step; the summary carries
the rest. Each message is scrubbed, as a pull request shows its annotations to everyone who reads it; the job's log
holds what `validate` printed above them."""

from __future__ import annotations

from collections.abc import Sequence

from .model import Finding
from .report_md import place
from .secrets import scrub
from .text import flat

#: The workflow command each severity is said with.
LEVELS = {"ERROR": "error", "WARNING": "warning", "INFO": "notice"}
#: How many findings the summary lists.
ROWS = 50


def annotation_lines(findings: Sequence[Finding]) -> list[str]:
    """A workflow command for each finding with a path; one with none has no line to be shown on."""
    lines = []
    for held in findings:
        if not held.path:
            continue
        where = [f"file={_property(held.path)}", *([f"line={held.line}"] if held.line else [])]
        where.append(f"title={_property(held.code)}")
        lines.append(f"::{LEVELS[held.severity]} {','.join(where)}::{_data(scrub(held.message)[0])}")
    return lines


def step_summary(findings: Sequence[Finding], *, failed: bool) -> str:
    """The run page's summary: whether the gate failed, the counts, and a table of the first `ROWS` findings."""
    count = {level: sum(held.severity == level for held in findings) for level in LEVELS}
    said = f"{count['ERROR']} errors, {count['WARNING']} warnings, {count['INFO']} notes"
    lines = ["## adk-spec validate", "", f"**{'failed' if failed else 'passed'}**: {said}", ""]
    if findings:
        lines += ["| Severity | Code | Where | Message |", "| --- | --- | --- | --- |"]
        lines += [
            f"| {held.severity} | {held.code} | {_cell(place(held))} | {_cell(scrub(held.message)[0])} |"
            for held in findings[:ROWS]
        ]
        if len(findings) > ROWS:
            lines += ["", f"and {len(findings) - ROWS} more: run `adk-spec validate` to list them"]
    return "\n".join(lines) + "\n"


def _data(text: str) -> str:
    """A command's message as GitHub reads it: a line break or a percent sign escaped."""
    return text.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")


def _property(text: str) -> str:
    """A command's property, where a colon or a comma would end it, escaped as well."""
    return _data(text).replace(":", "%3A").replace(",", "%2C")


def _cell(text: str) -> str:
    """A table cell: on one line, a pipe kept from ending it."""
    return flat(text).replace("|", "\\|")
