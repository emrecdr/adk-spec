"""Evidence on disk: a change's, folded in beside each living spec at archive, and the living evidence checked
against the code, so that a requirement whose proving lines are gone from it is noted as suspect."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path, PureWindowsPath

from ..domain.context_md import quoted_statements
from ..domain.evidence_md import Proof, folded, parse_evidence, render_evidence, suspects
from ..domain.model import ChangeState, Delta, Finding, Spec
from ..domain.text import quoted_at
from ..domain.validate import finding
from .config import ConfigError
from .files import NotTextError, read_text
from .git import GitError, grep
from .layout import CHANGES, EVIDENCE, PROFILE, SPECS, Workspace

#: How many of the files a quote's search names are read whole to find it.
ELSEWHERE_MAX = 20


def holds(root: Path, proof: Proof, exclude: Sequence[str]) -> bool | None:
    """Whether `proof`'s quote is still in the code: in its file, or else in another file of its repository, so that
    a moved function reads as moved. None where its repository is not there to look in, as another one is not in CI.
    `root` is the folder that holds `.spec/`; `exclude`, the person's patterns, apply to its own repository."""
    own = proof.repository == "."
    folder = root if own else root / proof.repository
    if not _within(folder, proof.repository, proof.path, own=own):
        return None
    return _quoted(folder, proof.path, proof.quote, exclude if own else (), trust=own)


def _quoted(folder: Path, path: str, quote: str, exclude: Sequence[str], *, trust: bool) -> bool | None:
    """Whether `quote` is in `path` of the repository at `folder`, or else in another of its files; None where git
    refuses the search, outside a repository say: not looked for."""
    if _found(folder / path, quote):  # read first: a quote that holds asks git nothing
        return True
    try:
        term = max(quote.split(), key=len, default="")  # a fixed string git finds on one line
        hits = grep(folder, term, exclude=exclude, trust=trust) if term else []
    except GitError:
        return None
    named = list(dict.fromkeys(hit.split(":", 1)[0] for hit in hits))[:ELSEWHERE_MAX]
    return any(_found(folder / path, quote) for path in named)


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
    try:
        return quoted_at(quote, read_text(path)) is not None
    except NotTextError, OSError:
        return False


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


#: The schemes of an installed library's paths, which a reading may open and the repository does not hold.
LIBRARIES = ("python:", "node:")


def profile_gone(workspace: Workspace) -> tuple[int, int] | None:
    """Of the quotes `.spec/profile.md` holds, how many are no longer in the code, and how many were looked for; None
    where there is no profile that reads, or none of its quotes could be looked for. Phase 17: every drafting stage
    reads the profile, and nothing else checks it. A library's quote is not looked for, nor one git cannot search for
    outside its file: unknown is not gone."""
    path = workspace.home / PROFILE
    try:
        text = read_text(path) if path.is_file() else ""
    except NotTextError, OSError:
        return None
    exclude, root = _excluded(workspace), workspace.root
    looked = [
        _quoted(root, named, quote, exclude, trust=True) if _within(root, ".", named, own=True) else None
        for named, quote in quoted_statements(text)
        if not named.startswith(LIBRARIES)
    ]
    held = [one for one in looked if one is not None]
    return (held.count(False), len(held)) if held else None


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
