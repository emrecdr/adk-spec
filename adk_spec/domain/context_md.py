"""`context.md`: what a reading of the repository's code found for one change, each statement with the line it
rests on.

Written by code from statements a model made and code kept: a statement is here only because its quote was found in
the file it names. A person may edit the file afterwards, as every file of a change, and a plan is drafted from it
as it stands. It is supporting material, like a report: no part of an approval.
"""

from __future__ import annotations

from collections.abc import Sequence

from .model import Statement, StatementKind

#: How the line begins that a reading which ended early carries at its top.
PARTIAL = "This reading is partial: "
#: The kinds of statement, each with the heading it stands under, in the order of the file.
SECTIONS: tuple[tuple[StatementKind, str], ...] = (
    ("exists", "What exists"),
    ("touches", "Where the change plugs in"),
    ("convention", "Conventions to follow"),
    ("risk", "Risks and what is unclear"),
)


def render_context(
    change_id: str,
    *,
    at: str,
    commit: str | None,
    statements: Sequence[Statement],
    read: Sequence[str],
    left_out: Sequence[str] = (),
    dropped: int = 0,
    partial: str | None = None,
) -> str:
    """The file: when and of what commit the repository was read, the statements under a heading a kind, what was
    read, and what was left out. `partial` says why a reading ended early, where it did."""
    where = f" at commit {commit[:12]}" if commit else ""
    lines = [f"# Context: {change_id}", "", f"Read from the repository{where} on {at[:10]}.", ""]
    if partial:
        lines += [f"{PARTIAL}{partial}.", ""]
    for kind, heading in SECTIONS:
        held = [one for one in statements if one.kind == kind]
        if held:
            lines += [f"## {heading}", ""]
            for one in held:
                lines += [f"- `{one.path}:{one.line}` {one.note}", f"  > {one.quote}"]
            lines.append("")
    lines += ["## What was read", "", *(f"- {one}" for one in read or ("nothing",)), ""]
    if dropped:
        statements_ = "statement" if dropped == 1 else "statements"
        lines += [f"Left out: {dropped} {statements_} whose quote was not in the file named.", ""]
    if left_out:
        lines += [f"Not read: {'; '.join(left_out)}.", ""]
    return "\n".join(lines)
