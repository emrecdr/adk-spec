"""The reports a command writes under a change's `reports/` folder.

A report is generated: written whole each time, for a person to read, and never parsed back. What a later command
needs of a check or a verification is in the change's state file, not here.
"""

from __future__ import annotations

from collections.abc import Sequence

from .model import Finding

_HEADINGS = (("ERROR", "Blocking"), ("WARNING", "Worth a look"), ("INFO", "Notes"))


def _listed(found: Finding) -> str:
    place = f"{found.path}:{found.line}" if found.line else (found.path or "")
    return f"- `{found.code}` {place}: {found.message}".replace(" :", ":")


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
        were = "finding of the model was" if dropped == 1 else "findings of the model were"
        lines += [f"{dropped} {were} left out: the text quoted is not in the file named.", ""]
    return "\n".join(lines)
