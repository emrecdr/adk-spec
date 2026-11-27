"""Evidence on disk: a change's, folded in beside each living spec at archive, and the living evidence checked
against the code, so that a requirement whose proving lines are gone from it is noted as suspect; and the quotes of
`.spec/profile.md` checked against the code the same way."""

from __future__ import annotations

import functools
import itertools
from collections.abc import Mapping, Sequence
from pathlib import Path, PureWindowsPath

from ..domain.context_md import quoted_statements
from ..domain.evidence_md import Proof, folded, parse_evidence, render_evidence, suspects
from ..domain.model import ChangeState, Delta, Finding, Spec
from ..domain.secrets import holds_a_key, scrub_lines
from ..domain.text import QUOTE_MIN_CHARS, plain, quoted_at
from ..domain.validate import finding
from .config import ConfigError
from .files import NotTextError, read_text
from .git import GitError, files, grep
from .layout import CHANGES, EVIDENCE, PROFILE, SPECS, Workspace
from .paths import linked
from .source import FILE_MAX_BYTES, LIBRARY_SCHEMES, own_config

#: How many of the files a quote's search names are read whole to find it.
ELSEWHERE_MAX = 20


def holds(root: Path, proof: Proof, exclude: Sequence[str]) -> bool | None:
    """Whether `proof`'s quote is still in the code, as `quote_holds` says."""
    return quote_holds(root, proof.repository, proof.path, proof.quote, exclude)


def quote_holds(root: Path, repository: str, path: str, quote: str, exclude: Sequence[str]) -> bool | None:
    """Whether `quote` is still in the code: in `path`, or else in another file of its repository, so that a moved
    function reads as moved. None where its repository is not there to look in, as another one is not in CI, where
    git refuses the search, outside a repository say, or where the quote is too short to find anywhere. `root` is
    the folder that holds `.spec/`; `repository` is `.` for its own; `exclude`, the person's patterns, apply to its
    own."""
    own = repository == "."
    folder = root if own else root / repository
    if len(plain(quote)) < QUOTE_MIN_CHARS or not _within(folder, repository, path, own=own):  # too short to find
        return None
    # Only what a reading could be shown: a file git lists, its repository's exclusions, no link (an outside audit).
    held = tuple(exclude) if own else _their_exclusions(folder)
    if held is None or linked(folder, path):
        return None
    try:
        listed = _listed(folder, held, own)
    except GitError:
        return None
    if path in listed:
        if (first := _found(folder / path, quote)) is None:  # past what a reading reads, or a key's: unknown
            return None
        if first:  # read first: a quote that holds asks git for no search
            return True
    elif (folder / path).exists(follow_symlinks=False):  # there, and not listed: ignored, excluded or git's own
        return None
    return _elsewhere(folder, quote, held, listed, own=own)


def _elsewhere(folder: Path, quote: str, exclude: tuple[str, ...], listed: frozenset[str], *, own: bool) -> bool | None:
    """Whether `quote` is in another file `listed` under `folder`, found by its longest word: None where git refuses
    the search, or where a file that may hold it is past the cap (the code review of phase 24)."""
    try:
        term = max(plain(quote).split(), key=len, default="")  # a fixed string git finds on one line, NUL-free
        hits = grep(folder, term, exclude=exclude, trust=own) if term else []
    except GitError:
        return None
    named = (one for one in dict.fromkeys(hit.split(":", 1)[0] for hit in hits) if one in listed)
    unknown = False
    for one in itertools.islice((one for one in named if not linked(folder, one)), ELSEWHERE_MAX):
        if (found := _found(folder / one, quote)) is None:
            unknown = True
        elif found:
            return True
    return None if unknown else False


@functools.lru_cache(maxsize=8)
def _listed(folder: Path, exclude: tuple[str, ...], own: bool) -> frozenset[str]:
    """Every file git lists under `folder`, less `exclude`: what a quote may be looked for in, asked once a command."""
    return frozenset(files(folder, exclude=exclude, trust=own))


def _their_exclusions(folder: Path) -> tuple[str, ...] | None:
    """Another repository's own exclusions, as the code reading takes them (`own_config`); None where its config does
    not read, so that its quotes are unknown rather than looked for in what it keeps out."""
    try:
        held = own_config(folder)
    except ConfigError, NotTextError, OSError:
        return None
    return held.exclude if held else ()


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


def _found(path: Path, quote: str) -> bool | None:
    """Whether `quote` is in the file at `path` as a reading or a diff is shown it, scrubbed: a quote taken from what
    a model saw holds a secret's stand-in, never the secret, and one matched against the raw text would tell a guess
    at a secret from a wrong one (an outside audit of 171f1c4). None where the file is past what a reading reads,
    which is not read (the audit of 25 November, H3)."""
    try:
        stamp = path.stat()
    except OSError:
        return False
    if stamp.st_size > FILE_MAX_BYTES:
        return None
    if (text := _text(path, stamp.st_mtime_ns, stamp.st_size)) is None:
        return False
    if holds_a_key(text):  # withheld from every reading, so no quote is of it
        return None
    # A quote with no stand-in's bracket that is not in the text is not in its scrubbed text: the scrub, which costs
    # four times the search, is spent only to decide a hit.
    if "[" not in quote and "]" not in quote and quoted_at(quote, text) is None:
        return False
    return quoted_at(quote, _scrubbed(text)) is not None


@functools.lru_cache(maxsize=32)
def _text(path: Path, _mtime: int, _size: int) -> str | None:
    """A file's text, kept by its path and stamp: a file many quotes name is read once a command, not once a quote
    (the audit of 25 November, H3). None where it is no text, or cannot be read."""
    try:
        return read_text(path)
    except NotTextError, OSError:
        return None


@functools.lru_cache(maxsize=32)  # as many as `_text`: one quote's search names up to 21 files (measured: 8 never hit)
def _scrubbed(text: str) -> str:
    """A file's text as a reading or a diff is shown it, scrubbed, kept by the text `_text` keeps."""
    return scrub_lines(text)[0]


def _fresh() -> None:
    """The files a command read forgotten: kept only for one command (the code review of phase 24)."""
    _text.cache_clear()
    _scrubbed.cache_clear()
    _listed.cache_clear()


def evidence_findings(workspace: Workspace, living: Mapping[str, Spec]) -> list[Finding]:
    """A note for each suspect requirement of the `living` specs, and for each evidence line that does not read. A
    requirement the living spec no longer holds is not checked, nor any of a living spec that does not read."""
    _fresh()
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
    _fresh()
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
