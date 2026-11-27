"""Evidence: the lines `verify` found in the diff for each requirement it showed met, kept so that a requirement can
be checked against the code long after its change was archived.

One entry a line, `- <requirement> | <repository> | <path> | <change> | <time> | <quote>`, the quote last and
taking the rest of the line. One entry a line, so that deleting a line by hand, as a suspect is cleared once
reviewed, always leaves a file that reads. The repository is `.` for the one holding `.spec/`, else its path from the
folder that holds `.spec/`, as the change that proved it recorded it."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import astuple, dataclass

from .ids import REQ_ID
from .model import Finding
from .text import lines_of, normalise
from .validate import finding
from .verify import Verdict

#: The longest quote kept, in characters, and how many are kept for one requirement.
QUOTE_MAX = 240
QUOTES_A_REQUIREMENT = 3
#: What parts an entry.
_APART = " | "
_ENTRY = "- "
_TITLE = "# Evidence: "
_NOTE = "> "
#: The diff a model is shown is scrubbed: a quote holding this was over a secret, and is weak evidence of the code, cut
#: diffs scrubbing it otherwise than the file whole (found by phase 18's code review).
_HIDDEN = "[REDACTED"


@dataclass(frozen=True)
class Proof:
    """One quote that showed one requirement met: where, by which change, when it was verified."""

    req: str
    repository: str
    path: str
    change: str
    at: str
    quote: str


def render_evidence(title: str, proofs: Sequence[Proof]) -> str:
    """An evidence file: its title, a note on what it is, and each of `proofs` on a line of its own, in order."""
    lines = [
        f"{_TITLE}{title}",
        "",
        f"{_NOTE}The lines `adk-spec verify` proved each requirement with. Delete a requirement's lines, in a reviewed "
        "commit, to clear it.",
        "",
    ]
    lines += [_ENTRY + _APART.join(astuple(one)) for one in _sorted(proofs)]  # in the order `Proof(*parts)` reads
    return "\n".join(lines) + "\n"


def parse_evidence(text: str) -> tuple[list[tuple[int, Proof]], list[int]]:
    """Each entry of an evidence file with its line, counted from 1, and the lines that are no entry: the title, a
    note or a blank line aside, a line edited off the grammar is named rather than refused."""
    read: list[tuple[int, Proof]] = []
    unread: list[int] = []
    for number, line in enumerate(lines_of(normalise(text)), 1):
        if not line.strip() or line.startswith((_TITLE, _NOTE)):
            continue
        parts = line.removeprefix(_ENTRY).split(_APART, 5) if line.startswith(_ENTRY) else []
        if len(parts) == 6 and REQ_ID.fullmatch(parts[0]) and all(parts):
            read.append((number, Proof(*parts)))
        else:
            unread.append(number)
    return read, unread


def kept(
    verdicts: Sequence[Verdict], *, added: frozenset[str], change: str, at: str, repositories: Mapping[str, str]
) -> list[Proof]:
    """The evidence of `verdicts` worth keeping: each quote of a `met` verdict of a requirement in `added`, the ones
    the change adds or modifies. A removed requirement's quotes are of lines taken out, and one over a secret is
    weak evidence of the code. A path under another repository's name is kept as that repository's folder, from
    `repositories`, and the path within it."""
    proofs: list[Proof] = []
    for verdict in verdicts:
        if verdict.verdict != "met" or verdict.id not in added:
            continue
        held: list[Proof] = []
        for named, quote in verdict.evidence:
            repository, path = _placed(named, repositories)
            # Cut where it may be: what a quote begins with is found wherever the whole quote is.
            one = Proof(verdict.id, repository, path, change, at, quote[:QUOTE_MAX].rstrip())
            if _HIDDEN not in quote and _APART not in repository + path and one not in held:
                held.append(one)
        proofs += held[:QUOTES_A_REQUIREMENT]
    return _sorted(proofs)


def folded(
    living: Sequence[Proof], change: Sequence[Proof], *, replaced: frozenset[str], removed: frozenset[str]
) -> list[Proof]:
    """A capability's evidence once a change is archived: the `living` evidence of every requirement the change
    leaves alone, and the `change`'s own for those it adds or modifies (`replaced`). A requirement it removes
    keeps none."""
    gone = replaced | removed
    return _sorted([one for one in living if one.req not in gone] + [one for one in change if one.req in replaced])


def suspects(proofs: Sequence[tuple[int, Proof]], holds: Callable[[Proof], bool | None], *, path: str) -> list[Finding]:
    """A note for each requirement none of whose evidence is in the code: `holds` says of a proof whether its quote
    is found (True), is not (False), or could not be looked for (None, which keeps its requirement from being
    suspect). Each note points at the requirement's first line of `path`, the evidence file."""
    held: dict[str, list[tuple[int, Proof]]] = {}
    for line, one in proofs:
        held.setdefault(one.req, []).append((line, one))
    found = []
    for req, lines in sorted(held.items()):
        if all(holds(one) is False for _line, one in lines):
            first, one = lines[0]
            files = ", ".join(dict.fromkeys(proof.path for _line, proof in lines))
            found.append(
                finding(
                    "spec.evidence-gone",
                    f"{req} has none of its evidence left in the files git tracks ({files}, proved by {one.change}). "
                    f'Run `adk-spec propose "keep {req}: its evidence is gone"` and verify that change, or delete '
                    "its lines once that is reviewed.",
                    path=path,
                    line=first,
                )
            )
    return found


def _placed(named: str, repositories: Mapping[str, str]) -> tuple[str, str]:
    """The repository and the path within it of a path as `verify` named it."""
    name, _, rest = named.partition("/")
    return (repositories[name], rest) if rest and name in repositories else (".", named)


def _sorted(proofs: Sequence[Proof]) -> list[Proof]:
    return sorted(proofs, key=lambda one: (one.req, one.repository, one.path, one.quote))
