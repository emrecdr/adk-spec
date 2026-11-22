"""`context.md`: what a reading of the repository's code found for one change, each statement with the line it
rests on.

Written by code from statements a model made and code kept: a statement is here only because its quote was found in
the file it names. A person may edit the file afterwards, as every file of a change, and a plan is drafted from it
as it stands. It is supporting material, like a report: no part of an approval.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from .model import Statement, StatementKind

#: How the line begins that a reading which ended early carries at its top.
PARTIAL = "This reading is partial: "
#: The heading what a review named as still unknown stands under.
UNKNOWN_HEADING = "## What is still unknown"
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
    others: Mapping[str, str | None] | None = None,
    unknown: Sequence[tuple[str, str]] = (),
    disputed: int = 0,
) -> str:
    """The file: when and of what commit each repository was read, the statements under a heading a kind, what is
    still unknown, what was read, and what was left out. `partial` says why a reading ended early, where it did."""
    lines = [f"# Context: {change_id}", "", _read_from(at, commit, others or {}), ""]
    if partial:
        lines += [f"{PARTIAL}{partial}.", ""]
    for kind, heading in SECTIONS:
        held = [one for one in statements if one.kind == kind]
        if held:
            lines += [f"## {heading}", ""]
            for one in held:
                lines += [f"- `{one.path}:{one.line}` {one.note}", *([f"  in: {one.within}"] if one.within else ())]
                lines.append(f"  > {one.quote}")
            lines.append("")
    if unknown:
        lines += [UNKNOWN_HEADING, ""]
        lines += [f"- {question}" + (f" Look in: {where}." if where else "") for question, where in unknown]
        lines.append("")
    lines += ["## What was read", "", *(f"- {one}" for one in read or ("nothing",)), ""]
    if said := _left_out(dropped, disputed):
        lines += [said, ""]
    if left_out:
        lines += [f"Not read: {'; '.join(left_out)}.", ""]
    return "\n".join(lines)


def _read_from(at: str, commit: str | None, others: Mapping[str, str | None]) -> str:
    """The line that says when, and at what commit, each repository was read."""
    if not others:
        return f"Read from the repository{f' at commit {commit[:12]}' if commit else ''} on {at[:10]}."
    held = [("this repository", commit), *others.items()]
    return (
        f"Read on {at[:10]}: " + ", ".join(f"{name} at commit {sha[:12]}" if sha else name for name, sha in held) + "."
    )


def _left_out(dropped: int, disputed: int) -> str:
    """What was left out of the statements, and why, or nothing."""
    said = (
        [f"{dropped} statement{'' if dropped == 1 else 's'} whose quote was not in the file named"] if dropped else []
    )
    if disputed:
        said.append(f"{disputed}{'' if said else ' statement' + ('' if disputed == 1 else 's')} the review disputed")
    return f"Left out: {'; '.join(said)}." if said else ""


def unknown_count(text: str) -> int:
    """How many things a `context.md` lists as still unknown: its lines under that heading."""
    count, under = 0, False
    for line in text.split("\n"):
        if line.startswith("## "):
            under = line == UNKNOWN_HEADING
        elif under and line.startswith("- "):
            count += 1
    return count
