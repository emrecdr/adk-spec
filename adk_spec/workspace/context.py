"""What a stage is given to read from the workspace.

A capability is named with its purpose, so a model chooses one by what it is for. A living spec is given whole or
not at all: there is no retrieval index in this version, and a spec cut to fit would hide requirements from the
model in silence. Past the limit the run is refused, and the sentence names what to split.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path

from ..domain.lessons_md import TEMPLATE as LESSONS_TEMPLATE
from ..domain.model import Spec
from ..domain.spec_md import render_spec
from ..domain.text import lines_of
from .files import read_text
from .layout import CHANGES, CONSTITUTION, CONTEXT, LESSONS, PROFILE, Workspace, WorkspaceError

#: What a stage may be given of living specs, in characters. Provisional: sized for the smallest model a role may
#: run on, 128,000 input tokens in the pinned LiteLLM map, until a live run measures it.
CONTEXT_MAX_CHARS = 120_000
#: Past this a constitution draws a warning: it is read by every stage of every run.
CONSTITUTION_MAX_CHARS = 16_000
#: How many of a repository's files a stage is shown by name. Past it, it is shown folders and counts.
TREE_MAX_PATHS = 300


class ContextTooLargeError(WorkspaceError):
    """The living specs a stage would be given pass what it may read."""


def capability_index(specs: Mapping[str, Spec]) -> str:
    """One line a capability: its slug, and the first line of its purpose."""
    return "\n".join(f"{slug}: {(lines_of(spec.purpose) or [''])[0]}" for slug, spec in sorted(specs.items()))


def living_text(specs: Mapping[str, Spec], capabilities: Iterable[str]) -> str:
    """The canonical text of each named capability's living spec, whole, under a line naming it. A capability with
    no spec yet is one the change creates, and adds nothing. `ContextTooLargeError` past the limit."""
    return joined({slug: render_spec(specs[slug]) for slug in capabilities if slug in specs})


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
    return _capped(workspace.home / CHANGES / change_id / CONTEXT, CONTEXT_FILE_MAX_CHARS)


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
    """The lessons file as a drafting stage reads it: as the file stands, cut past the cap, or nothing where there is
    none or it holds no lesson yet."""
    text = _capped(workspace.home / LESSONS, LESSONS_MAX_CHARS)
    return "" if text == LESSONS_TEMPLATE.strip() else text


def _capped(path: Path, cap: int) -> str:
    """A file a stage reads as it stands, stripped, or nothing where there is none: cut past `cap`, saying so."""
    text = read_text(path).strip() if path.is_file() else ""
    return text if len(text) <= cap else text[:cap] + f"\n(cut here: {path.name} is longer than a stage is given)"


def constitution_text(workspace: Workspace) -> str:
    """The constitution as it stands, or nothing where there is none."""
    path = workspace.home / CONSTITUTION
    return read_text(path) if path.is_file() else ""


def tree_text(paths: Sequence[str]) -> str:
    """A repository's files for a stage to name real paths by: every path, one a line, or past `TREE_MAX_PATHS`
    each folder two levels deep with the number of files under it, under a first line that says so. A list cut
    short in silence would hide the files a task needs."""
    if len(paths) <= TREE_MAX_PATHS:
        return "\n".join(paths)
    folders = Counter("/".join(path.split("/")[:-1][:2]) or "." for path in paths)
    lines = [f"{len(paths):,} files: too many to list. Each folder, two levels deep, with the files under it:"]
    lines += [f"{folder}/ ({count:,} file{'' if count == 1 else 's'})" for folder, count in sorted(folders.items())]
    return "\n".join(lines)
