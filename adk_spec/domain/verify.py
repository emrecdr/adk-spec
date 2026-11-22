"""A diff read as the lines it adds and removes, and a model's verdicts held to them.

A model says whether the work meets a requirement; code decides whether what it points to is there. `met` stands
only where a line it quotes is a line of the diff, on the side that can show it: an added line for a requirement
the change adds or modifies, a removed line for one it removes. Anything else is `unclear`, so a missing or an
invented piece of evidence never reads as a pass.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .drafts import VerdictsDraft
from .secrets import scrub
from .text import lines_of, plain, quoted_at

UNGROUNDED = "no quoted line is in the diff"
NO_VERDICT = "no verdict was given"


@dataclass(frozen=True)
class Verdict:
    """Whether one requirement is met by the work, with the lines that show it and the reason given."""

    id: str
    verdict: str
    evidence: tuple[tuple[str, str], ...]  # (path, quote), each found in the diff
    reason: str


def lines_of_diff(diff: str) -> dict[str, tuple[list[str], list[str]]]:
    """By file: the lines a unified diff adds and the lines it removes, each without its sign. A file is known by
    its new name, and one that was deleted by the name it had."""
    files: dict[str, tuple[list[str], list[str]]] = {}
    old = new = None
    sides: tuple[list[str], list[str]] | None = None
    in_hunk = False
    for line in lines_of(diff):
        if line.startswith("diff --git "):
            old = new = sides = None
            in_hunk = False
        elif not in_hunk and line.startswith("--- "):
            old = _path(line[4:])
        elif not in_hunk and line.startswith("+++ "):
            new = _path(line[4:])
        elif line.startswith("@@"):
            in_hunk = True
            if sides is None and (name := new or old):
                sides = files.setdefault(name, ([], []))
        elif in_hunk and sides is not None and line[:1] in "+-" and line:
            sides[0 if line[0] == "+" else 1].append(line[1:])
    return files


def parts_of_diff(diff: str) -> list[tuple[str | None, str]]:
    """A unified diff by file, in its order: each file's name, as `lines_of_diff` knows it, with its part of the
    text. The parts put together are the diff. A part with no name shows no line: a file renamed and not changed,
    or one that is no text."""
    parts: list[tuple[str | None, str]] = []
    for part in re.split(r"(?m)^(?=diff --git )", diff):
        if part:
            heading = part.split("\n@@", 1)[0]  # a line a hunk adds may itself begin with `+++ `
            named = {line[:3]: _path(line[4:]) for line in heading.split("\n") if line.startswith(("--- ", "+++ "))}
            parts.append((named.get("+++") or named.get("---"), part))
    return parts


def _path(named: str) -> str | None:
    """A file's path from a `---` or `+++` line: without git's `a/` or `b/`, and nothing for `/dev/null`."""
    named = named.split("\t", 1)[0].strip()
    if named == "/dev/null":
        return None
    return named[2:] if named[:2] in ("a/", "b/") else named


def _shown(quote: str, lines: list[str]) -> bool:
    """Whether `quote` is in `lines`, by the one test of a quote the package has."""
    return quoted_at(quote, "\n".join(lines)) is not None


def grounded(draft: VerdictsDraft, diff: str, *, added: frozenset[str], removed: frozenset[str]) -> list[Verdict]:
    """One verdict for each requirement of `added` and `removed`, in the order of their IDs. `added` are the
    requirements the change adds or modifies, shown by lines the diff adds; `removed` the ones it removes, shown by
    lines the diff removes. A requirement the model gave no verdict is `unclear`, and so is a `met` none of whose
    quotes is such a line. A verdict for any other requirement is left out."""
    sides = lines_of_diff(diff)
    given = {}
    for one in draft.verdicts:
        given.setdefault(one.id.strip(), one)
    verdicts = []
    for req_id in sorted(added | removed):
        one = given.get(req_id)
        if one is None:
            verdicts.append(Verdict(req_id, "unclear", (), NO_VERDICT))
            continue
        side = 1 if req_id in removed else 0
        evidence = tuple(
            (path, quote)
            for piece in one.evidence
            for path, quote in [(_named(piece.path, sides), plain(piece.quote))]  # as plain text, then looked for
            if path is not None and _shown(quote, sides[path][side])
        )
        reason = plain(one.reason)
        if one.verdict == "met" and not evidence:
            verdicts.append(Verdict(req_id, "unclear", (), f"{UNGROUNDED}. The model's reason: {reason}"))
        else:
            verdicts.append(Verdict(req_id, one.verdict, evidence, reason))
    return verdicts


def _named(path: str, sides: dict[str, tuple[list[str], list[str]]]) -> str | None:
    """The file of the diff a model named: as it is spelled there, or with a leading `a/`, `b/` or `./` it copied."""
    named = path.strip()
    for candidate in (named, named.removeprefix("./"), named[2:] if named[:2] in ("a/", "b/") else named):
        if candidate in sides:
            return candidate
    return None


@dataclass(frozen=True)
class TestRun:
    """What one run of a project's tests came to."""

    #: The repository it ran in: empty for the workspace's own.
    name: str
    argv: tuple[str, ...]
    #: `passed`, `failed (exit N)`, `timed out after N s`, or `not run: <why>`.
    outcome: str
    #: The end of its output, scrubbed.
    tail: str
    #: How long it ran, or nothing where it never started.
    seconds: float | None

    @property
    def label(self) -> str:
        return self.name or "this repository"

    @property
    def command(self) -> str:
        """The command as it is shown, scrubbed: a test command may carry a token of its own."""
        return scrub(" ".join(self.argv))[0]
