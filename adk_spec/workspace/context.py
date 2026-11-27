"""What a stage is given to read from the workspace.

A capability is named with its purpose, so a model chooses one by what it is for. A living spec is given whole or
not at all: there is no retrieval index in this version, and a spec cut to fit would hide requirements from the
model in silence. Past the limit the run is refused, and the sentence names what to split.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

from ..domain.lessons_md import as_read
from ..domain.model import Spec
from ..domain.spec_md import render_spec
from ..domain.text import counted, first_of, lines_of
from .files import read_text
from .layout import CHANGES, CONSTITUTION, CONTEXT_FILE, LESSONS, PROFILE, Workspace, WorkspaceError

#: What a stage may be given of living specs, in characters. Provisional: sized for the smallest model a role may
#: run on, 128,000 input tokens in the pinned LiteLLM map, until a live run measures it.
CONTEXT_MAX_CHARS = 120_000
#: Past this a constitution draws a warning: it is read by every stage of every run.
CONSTITUTION_MAX_CHARS = 16_000
#: How many of a repository's files a stage is shown by name. Past it, it is shown folders and counts.
TREE_MAX_PATHS = 300
#: How many of the files at a repository's top a folded tree names: phase 18, folded, it hid README.md and the like.
TOP_FILES_NAMED = 30


class ContextTooLargeError(WorkspaceError):
    """The living specs a stage would be given pass what it may read."""


def capability_index(specs: Mapping[str, Spec]) -> str:
    """One line a capability: its slug, and the first line of its purpose."""
    return "\n".join(f"{slug}: {(lines_of(spec.purpose) or [''])[0]}" for slug, spec in sorted(specs.items()))


#: What stands for a capability with no living spec yet: one the change creates. Found by the third audit: left out
#: without a word, the deltas stage, told to give a purpose only to a new capability, was never told which were new.
NEW_CAPABILITY = "(no living spec yet: the change creates this capability)"


def living_text(specs: Mapping[str, Spec], capabilities: Iterable[str]) -> str:
    """The canonical text of each named capability's living spec, whole, under a line naming it; one with no spec
    yet, which the change creates, is named as new. `ContextTooLargeError` past the limit."""
    return joined({slug: render_spec(specs[slug]) if slug in specs else NEW_CAPABILITY for slug in capabilities})


def joined(
    parts: Mapping[str, str],
    *,
    what: str = "the living specs of",
    remedy: str = "Split a capability, or name fewer in the change",
) -> str:
    """Each text under a line naming it, whole. `ContextTooLargeError` past the limit, naming `what` they are."""
    text = "\n".join(f"=== {name}\n{held}" for name, held in parts.items())
    if len(text) > CONTEXT_MAX_CHARS:
        sizes = ", ".join(f"{name} ({len(held):,})" for name, held in parts.items())
        raise ContextTooLargeError(
            f"{what} {sizes} hold {len(text):,} characters, past the {CONTEXT_MAX_CHARS:,} a stage is given. {remedy}"
        )
    return text


def files_text(texts: Mapping[str, str]) -> str:
    """A change's own files, each under a line naming its path in the change's folder, whole."""
    return joined(texts, what="the change's files", remedy="Split the change")


#: How much of a change's `context.md` a stage is given.
CONTEXT_FILE_MAX_CHARS = 20_000


def context_text(workspace: Workspace, change_id: str) -> str:
    """A change's `context.md` as a stage reads it: as the file stands, a person's edits and all, or nothing where
    there is none. One past the cap is cut, and says so. `NotTextError` where the file is no text: it is there, and
    reading it as nothing would also keep the code from being read again."""
    return _capped(workspace.home / CHANGES / change_id / CONTEXT_FILE, CONTEXT_FILE_MAX_CHARS)


#: How much of the repository's `profile.md` a stage is given: as much as of a `context.md`. A reading keeps at most
#: 40 statements, and cut shorter, the profile lost the risks and the unknowns, which come last.
PROFILE_MAX_CHARS = 20_000


def profile_text(workspace: Workspace) -> str:
    """The repository's `profile.md` as a stage reads it: as the file stands, or nothing where there is none. One
    past the cap is cut, and says so."""
    return _capped(workspace.home / PROFILE, PROFILE_MAX_CHARS)


#: How much of `.spec/lessons.md` a drafting stage is given.
LESSONS_MAX_CHARS = 6_000


def lessons_text(workspace: Workspace) -> str:
    """The lessons file as a drafting stage reads it: its lessons, without what is written for a person, cut past
    the cap; nothing where there is none, or it holds no lesson yet."""
    path = workspace.home / LESSONS
    return _cut(as_read(read_text(path)) if path.is_file() else "", LESSONS, LESSONS_MAX_CHARS)


def context_of(text: str) -> str:
    """A reading's text as a stage is given it before it is written as a change's `context.md`: cut as that file
    would be."""
    return _cut(text.strip(), CONTEXT_FILE, CONTEXT_FILE_MAX_CHARS)


def _capped(path: Path, cap: int) -> str:
    """A file a stage reads as it stands, stripped, or nothing where there is none: cut past `cap`, saying so."""
    return _cut(read_text(path).strip() if path.is_file() else "", path.name, cap)


def _cut(text: str, name: str, cap: int) -> str:
    return text if len(text) <= cap else text[:cap] + f"\n(cut here: {name} is longer than a stage is given)"


def constitution_text(workspace: Workspace) -> str:
    """The constitution as it stands, or nothing where there is none."""
    path = workspace.home / CONSTITUTION
    return read_text(path) if path.is_file() else ""


def tree_text(paths: Sequence[str]) -> str:
    """A repository's files for a stage to name real paths by: every path, one a line, or past `TREE_MAX_PATHS`
    each folder two levels deep with the number of files under it, under a first line that says so; one level deep
    where those are too many still, and the largest `TREE_MAX_PATHS` of them, with how many more there are. A list
    cut short in silence would hide the files a task needs."""
    if len(paths) <= TREE_MAX_PATHS:
        return "\n".join(paths)
    deep, folders = "two levels", _folders(paths, 2)
    if len(folders) > TREE_MAX_PATHS:  # found by the fourth audit: a monorepo's folders were as many as its files
        deep, folders = "one level", _folders(paths, 1)
    kept = sorted(folders.most_common(TREE_MAX_PATHS))  # the largest, by name
    lines = [f"{len(paths):,} files: too many to list. Each folder, {deep} deep, with the files under it:"]
    if top := sorted(path for path in paths if "/" not in path):
        lines.append("files at the top: " + first_of(top, TOP_FILES_NAMED))
    lines += [f"{folder}/ ({counted(count, 'file')})" for folder, count in kept]
    if more := len(folders) - len(kept):
        lines.append(f"and {counted(more, 'more folder')}")
    return "\n".join(lines)


def _folders(paths: Sequence[str], depth: int) -> Counter[str]:
    """How many of `paths` stand under each folder `depth` levels deep: `.` for the files at the top."""
    return Counter("/".join(path.split("/")[:-1][:depth]) or "." for path in paths)
