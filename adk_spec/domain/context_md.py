"""What a reading of a repository's code found, each statement with the line it rests on: a change's `context.md`,
the repository's `profile.md`, and the rules `init` drafts into a template constitution from what it found.

Written by code from statements a model made and code kept: a statement is here only because its quote was found in
the file it names. A person may edit the file afterwards, as every file of a change, and a plan is drafted from it
as it stands. It is supporting material, like a report: no part of an approval.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence

from .model import Statement, StatementKind
from .text import code_span, plain

#: How the line begins that a reading which ended early carries at its top.
PARTIAL = "This reading is partial: "
#: The heading of a repository's profile, which `init` writes from a reading of the whole repository.
PROFILE_HEADING = "This repository"
#: The kinds of statement, each with the heading it stands under in a repository's profile: there is no change for
#: a statement to plug into, and a stage that reads the profile beside a change's `context.md` reads no change in it.
PROFILE_SECTIONS = (
    ("exists", "What is here"),
    ("touches", "Where things live"),
    ("convention", "How this repository does things"),
    ("risk", "Risks and what is unclear"),
)
#: The heading of the rules `init` drafts into a template constitution.
DRAFTED_HEADING = "## Drafted from the code"
#: The heading what a review named as still unknown stands under.
UNKNOWN_HEADING = "## What is still unknown"
#: How many statements a reading keeps, and how many unknowns: the reading's budgets, said where it went past them.
STATEMENTS_KEPT = 40
UNKNOWNS_KEPT = 8
#: A statement's line as `render_context` writes it: its file and line in a code span, then its note; and the lines
#: under it, the block it stands in and its quote.
_STATEMENT = re.compile(r"- `(?P<path>[^`]+):[0-9]+`(?:\s|$)")
_WITHIN, _QUOTE = "  in: ", "  > "
#: The kinds of statement, each with the heading it stands under, in the order of the file.
SECTIONS: tuple[tuple[StatementKind, str], ...] = (
    ("exists", "What exists"),
    ("touches", "Where the change plugs in"),
    ("convention", "Conventions to follow"),
    ("risk", "Risks and what is unclear"),
)


def render_context(
    title: str,
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
    sections: Sequence[tuple[str, str]] = SECTIONS,
    over: int = 0,
    unknown_over: int = 0,
    looked: Sequence[str] = (),
) -> str:
    """The file, under `title`: when and of what commit each repository was read, the statements under a heading a
    kind, what is still unknown, what was read, and what was left out. `partial` says why a reading ended early,
    where it did."""
    lines = [f"# {title}", "", _read_from(at, commit, others or {}), ""]
    if partial:
        lines += [f"{PARTIAL}{partial}.", ""]
    # What is unknown and what was left out first: phase 18, a stage is given the file cut at its cap, which took them.
    if unknown:
        lines += [UNKNOWN_HEADING, ""]
        lines += [f"- {question}" + (f" Look in: {where}." if where else "") for question, where in unknown]
        lines.append("")
    if said := _left_out(dropped, disputed, over, unknown_over):
        lines += [said, ""]
    if left_out:
        lines += [f"Not read: {'; '.join(left_out)}.", ""]
    for kind, section in sections:
        held = [one for one in statements if one.kind == kind]
        if held:
            lines += [f"## {section}", ""]
            for one in held:
                lines += [f"- `{one.path}:{one.line}` {one.note}", *([f"{_WITHIN}{one.within}"] if one.within else ())]
                lines.append(f"{_QUOTE}{one.quote}")
            lines.append("")
    lines += ["## What was read", "", *(f"- {one}" for one in (*read, *looked) or ("nothing",)), ""]
    return "\n".join(lines)


def _read_from(at: str, commit: str | None, others: Mapping[str, str | None]) -> str:
    """The line that says when, and at what commit, each repository was read."""
    if not others:
        return f"Read from the repository{f' at commit {commit[:12]}' if commit else ''} on {at[:10]}."
    held = [("this repository", commit), *others.items()]
    return (
        f"Read on {at[:10]}: " + ", ".join(f"{name} at commit {sha[:12]}" if sha else name for name, sha in held) + "."
    )


def _left_out(dropped: int, disputed: int, over: int = 0, unknown_over: int = 0) -> str:
    """What was left out of the statements and the unknowns, and why, or nothing."""
    said = []
    if dropped:
        said.append(f"{dropped} statement{'' if dropped == 1 else 's'} whose quote was not in the file named")
    if disputed:
        noun = "" if said else f" statement{'' if disputed == 1 else 's'}"
        said.append(f"{disputed}{noun} the review disputed")
    if over:
        said.append(f"{over} statement{'' if over == 1 else 's'} past the {STATEMENTS_KEPT} a reading keeps")
    if unknown_over:
        said.append(f"{unknown_over} unknown{'' if unknown_over == 1 else 's'} past the {UNKNOWNS_KEPT} kept")
    return f"Left out: {'; '.join(said)}." if said else ""


#: The heading the person's answers to the questions `propose` asked stand under, in a change's `context.md`.
ANSWERS_HEADING = "## The person's answers"


def with_answers(text: str, answers: str) -> str:
    """A `context.md`, `text`, with the person's `answers` to the questions `propose` asked, each `question ->
    answer` on a line, under their heading before the file's first other one; as it was where there are none. Phase
    18: they lived only in the run, and the stages after the brief read the brief's words alone."""
    said = [plain(one) for one in answers.split("\n") if one.strip()]
    if not said:
        return text
    section = "\n".join([ANSWERS_HEADING, "", *(f"- {one}" for one in said), "", ""])
    at = text.find("\n## ")
    return f"{text.rstrip(chr(10))}\n\n{section}" if at < 0 else text[: at + 1] + section + text[at + 1 :]


def quoted_statements(text: str) -> list[tuple[str, str]]:
    """Each statement of a file `render_context` wrote, as its path and its quote: the `  > ` line under its own.
    Read leniently, as a person may edit the file: any other line, and a statement with no quote, is passed over."""
    found: list[tuple[str, str]] = []
    path: str | None = None
    for line in text.split("\n"):
        if held := _STATEMENT.match(line):
            path = held.group("path")
        elif path is not None and line.startswith(_QUOTE):
            found.append((path, line.removeprefix(_QUOTE)))
            path = None
        elif not line.startswith(_WITHIN):
            path = None
    return found


def unknown_count(text: str) -> int:
    """How many things a `context.md` lists as still unknown: its lines under that heading."""
    count, under = 0, False
    for line in text.split("\n"):
        if line.startswith("## "):
            under = line == UNKNOWN_HEADING
        elif under and line.startswith("- "):
            count += 1
    return count


def drafted_rules(statements: Sequence[Statement]) -> str:
    """The rules a reading of a repository found already true of its code, as a constitution's section: each kept
    `convention` statement, its note the rule and its quote the evidence. Nothing where none is a convention. Drafted
    by code from statements whose quotes were found, and the person's to keep, edit or delete."""
    rules = [
        f"- {_first_sentence(one.note)} (`{one.path}:{one.line}`: {code_span(one.quote)})"
        for one in statements
        if one.kind == "convention"
    ]
    if not rules:
        return ""
    said = "Drafted by `adk-spec init` from the code as it stands: each is yours to keep, edit or delete."
    return "\n".join([DRAFTED_HEADING, "", said, "", *rules, ""])


def _first_sentence(note: str) -> str:
    """A note's first sentence: a rule in a constitution is one. Measured live, a note ran to a paragraph."""
    said = note.strip()
    found = re.match(r"(.+?[.!?])(?=\s+[A-Z(`\"]|$)", said, re.DOTALL)
    return found.group(1) if found else said
