"""The reports a command writes under a change's `reports/` folder.

A report is generated: written whole each time, for a person to read, and never parsed back. What a later command
needs of a check or a verification is in the change's state file, not here.
"""

from __future__ import annotations

from collections.abc import Sequence

from .model import Finding
from .verify import Verdict

_HEADINGS = (("ERROR", "Blocking"), ("WARNING", "Worth a look"), ("INFO", "Notes"))


def place(found: Finding) -> str:
    """Where a finding is: its file, and its line where it has one."""
    return f"{found.path}:{found.line}" if found.line else (found.path or "")


def left_out(dropped: int) -> str:
    """The sentence for a model's findings that quoted nothing real."""
    were = "finding of the model was" if dropped == 1 else "findings of the model were"
    return f"{dropped} {were} left out: the text quoted is not in the file named"


def _listed(found: Finding) -> str:
    return f"- `{found.code}` {place(found)}: {found.message}".replace(" :", ":")


def render_check(change_id: str, at: str, findings: Sequence[Finding], *, model: str | None, dropped: int = 0) -> str:
    """`reports/check.md`: when the change was checked and by what, what blocks its approval, and the rest."""
    blocking = sum(found.severity == "ERROR" for found in findings)
    judge = f"by code and by {model}" if model else "by code alone: the model's pass was not run"
    lines = [f"# Check of `{change_id}`", "", f"Checked {at}, {judge}.", ""]
    lines += [f"{blocking} blocking." if blocking else "Nothing blocks an approval.", ""]
    for severity, heading in _HEADINGS:
        held = [found for found in findings if found.severity == severity]
        if held:
            lines += [f"## {heading}", "", *(_listed(found) for found in held), ""]
    if dropped:
        lines += [f"{left_out(dropped)}.", ""]
    return "\n".join(lines)


def render_verify(
    change_id: str, at: str, base: str, verdicts: Sequence[Verdict], *, model: str | None, override: str | None = None
) -> str:
    """`reports/verify.md`: what the work was compared with, and for each requirement its verdict, the reason, and
    the lines of the diff that show it."""
    judge = f"by {model}" if model else "with no requirement to judge"
    lines = [f"# Verification of `{change_id}`", "", f"Judged {at} against the commit {base[:12]}, {judge}.", ""]
    open_ = [one for one in verdicts if one.verdict != "met"]
    if not open_:
        lines += ["Every requirement is shown met.", ""]
    else:
        lines += [f"{len(open_)} of {len(verdicts)} requirements are not shown met.", ""]
    if override:
        lines += [f"Verified all the same, by a person's decision: {override}", ""]
    for one in verdicts:
        lines += [f"## {one.id}: {one.verdict}", "", one.reason, ""]
        if one.evidence:
            lines += [*(f"- {path}: {quote}" for path, quote in one.evidence), ""]
    return "\n".join(lines)
