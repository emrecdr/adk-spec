"""Evidence on disk: a change's, folded in beside each living spec at archive, and the living evidence checked
against the code, so that a requirement whose proving lines are gone from it is noted as suspect; and the quotes of
`.spec/profile.md` checked against the code the same way."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path, PureWindowsPath

from ..domain.context_md import quoted_statements
from ..domain.evidence_md import Proof, folded, parse_evidence, render_evidence, suspects
from ..domain.model import ChangeState, Delta, Finding, Spec
from ..domain.secrets import scrub_lines
from ..domain.text import plain, quoted_at
from ..domain.validate import finding
from .config import ConfigError
from .files import NotTextError, read_text
from .git import GitError, grep
from .layout import CHANGES, EVIDENCE, PROFILE, SPECS, Workspace
from .source import LIBRARY_SCHEMES

#: How many of the files a quote's search names are read whole to find it.
ELSEWHERE_MAX = 20


def holds(root: Path, proof: Proof, exclude: Sequence[str]) -> bool | None:
    """Whether `proof`'s quote is still in the code, as `quote_holds` says."""
    return quote_holds(root, proof.repository, proof.path, proof.quote, exclude)


def quote_holds(root: Path, repository: str, path: str, quote: str, exclude: Sequence[str]) -> bool | None:
    """Whether `quote` is still in the code: in `path`, or else in another file of its repository, so that a moved
    function reads as moved. None where its repository is not there to look in, as another one is not in CI, or git
    refuses the search, outside a repository say. `root` is the folder that holds `.spec/`; `repository` is `.` for
    its own; `exclude`, the person's patterns, apply to its own."""
    own = repository == "."
    folder = root if own else root / repository
    if not _within(folder, repository, path, own=own):
        return None
    if _found(folder / path, quote):  # read first: a quote that holds asks git nothing
        return True
    try:
        # A fixed string git finds on one line, NUL-free and no stand-in's, which no file holds as it stands.
        term = max((word for word in plain(quote).split() if "[" not in word and "]" not in word), key=len, default="")
        hits = grep(folder, term, exclude=exclude if own else (), trust=own) if term else []
    except GitError:
        return None
    named = list(dict.fromkeys(hit.split(":", 1)[0] for hit in hits))[:ELSEWHERE_MAX]
    return any(_found(folder / one, quote) for one in named)


def _within(folder: Path, repository: str, path: str, *, own: bool) -> bool:
    """Whether a quote names a file of a repository that is there: its path relative and inside it, and another
    repository one's top folder. Found by the code review: a line edited to `..` or an absolute path was read wherever
    it pointed, so in CI a pull request could learn from a note whether a string is in a file on the runner."""
    # A root or a drive on either system, `C:x` too, or a NUL that no file system takes.
    if any(PureWindowsPath(part).anchor or "\x00" in part for part in (repository, path)):
        return False
    if not folder.is_dir() or (not own and not (folder / ".git").exists()):
        return False
    return (folder / path).resolve().is_relative_to(folder.resolve())


def _found(path: Path, quote: str) -> bool:
    """Whether `quote` is in the file at `path`, as it stands or as a reading or a diff is shown it, scrubbed: a quote
    taken from what a model saw may hold a secret's stand-in, whole or cut through. Found by phase 17's reviews, where
    guessing such a quote by its shape missed some and took ordinary code for others."""
    try:
        text = read_text(path)
    except NotTextError, OSError:
        return False
    if quoted_at(quote, text) is not None:
        return True
    # A stand-in opens on `[` and ends on `]`: a quote of neither is not of the scrubbed text alone, nor costs a scrub.
    return ("[" in quote or "]" in quote) and quoted_at(quote, scrub_lines(text)[0]) is not None


def evidence_findings(workspace: Workspace, living: Mapping[str, Spec]) -> list[Finding]:
    """A note for each suspect requirement of the `living` specs, and for each evidence line that does not read. A
    requirement the living spec no longer holds is not checked, nor any of a living spec that does not read."""
    found: list[Finding] = []
    exclude = _excluded(workspace)
    for capability in workspace.capabilities():
        path = workspace.home / SPECS / capability / EVIDENCE
        shown = workspace.shown(path)
        read, unread = _read(path)
        if read is None:
            found.append(
                finding(
                    "spec.evidence-unreadable",
                    "It will not open, or is not UTF-8 text: nothing in it is checked.",
                    path=shown,
                )
            )
            continue
        found += [
            finding(
                "spec.evidence-unreadable", "This line is no evidence entry: it is not checked.", path=shown, line=at
            )
            for at in unread
        ]
        held = {req.id for req in living[capability].requirements} if capability in living else set()
        if kept := [(at, one) for at, one in read if one.req in held]:
            found += suspects(kept, lambda one: holds(workspace.root, one, exclude), path=shown)
    return found


def profile_gone(workspace: Workspace) -> tuple[int, int]:
    """Of the quotes of `.spec/profile.md`, each once, how many are no longer in the code, and how many were looked
    for: none where there is no profile that reads. Phase 17: every drafting stage reads the profile, and nothing else
    checks it. A library's quote is not looked for, nor counted one that could not be: unknown is not gone. Read
    whole: found by its code review, the cap a stage reads it at could halve a quote."""
    path = workspace.home / PROFILE
    try:
        text = read_text(path) if path.is_file() else ""
    except NotTextError, OSError:
        return 0, 0
    exclude = _excluded(workspace)
    looked = [
        quote_holds(workspace.root, ".", named, quote, exclude)
        for named, quote in dict.fromkeys(quoted_statements(text))
        if not named.startswith(LIBRARY_SCHEMES)
    ]
    held = [one for one in looked if one is not None]
    return held.count(False), len(held)


def _excluded(workspace: Workspace) -> tuple[str, ...]:
    """The person's exclude patterns; none where the config does not read. Found by the code review: read first, a
    fault in it, or no config at all, stopped `validate` and `status` where no evidence was kept."""
    try:
        return workspace.config().exclude
    except ConfigError, NotTextError, OSError:
        return ()


def evidence_folded(
    workspace: Workspace, state: ChangeState, deltas: Mapping[str, Delta]
) -> tuple[dict[str, str], list[str]]:
    """What an archive writes beside each living spec its change merges into, by path from `.spec/`, and the living
    evidence files it leaves as they are because they do not read. The change's evidence counts only where it is of
    the verification the change records: one written by a verification since superseded is left out."""
    proofs: list[Proof] = []
    if held := state.verification:  # an approval of other files drops it: none of an earlier version is folded
        mine, _unread = _read(workspace.home / CHANGES / state.id / EVIDENCE)
        proofs = [one for _line, one in mine or [] if one.at == held.at]
    files: dict[str, str] = {}
    left: list[str] = []
    proved = {one.req for one in proofs}
    for capability, delta in sorted(deltas.items()):
        replaced = frozenset(req.id for req in (*delta.added, *delta.modified))
        removed = frozenset(gone.id for gone in delta.removed)
        path = workspace.home / SPECS / capability / EVIDENCE
        living, unread = _read(path) if workspace.writable(SPECS, capability, EVIDENCE) else (None, [])
        if living is None or unread:
            if replaced & proved or delta.modified or removed:  # said only where something would go in or out
                left.append(workspace.shown(path))
            continue
        before = [one for _line, one in living]
        after = folded(before, proofs, replaced=replaced, removed=removed)
        if after != before:
            files[f"{SPECS}/{capability}/{EVIDENCE}"] = render_evidence(capability, after)
    return files, left


def _read(path: Path) -> tuple[list[tuple[int, Proof]] | None, list[int]]:
    """An evidence file's entries and the lines that are none; None for entries where it is no UTF-8 text or will
    not open, and nothing where it is not there."""
    try:
        return parse_evidence(read_text(path))
    except FileNotFoundError:
        return [], []
    except NotTextError, OSError:
        return None, []
