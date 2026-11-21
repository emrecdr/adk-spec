"""What a stage is given to read from the workspace.

A capability is named with its purpose, so a model chooses one by what it is for. A living spec is given whole or
not at all: there is no retrieval index in this version, and a spec cut to fit would hide requirements from the
model in silence. Past the limit the run is refused, and the sentence names what to split.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from ..domain.spec_md import render_spec
from .files import read_text
from .layout import CONSTITUTION, Workspace, WorkspaceError

#: What a stage may be given of living specs, in characters. Provisional: sized for the smallest model a role may
#: run on, 128,000 input tokens in the pinned LiteLLM map, until a live run measures it.
CONTEXT_MAX_CHARS = 120_000
#: Past this a constitution draws a warning: it is read by every stage of every run.
CONSTITUTION_MAX_CHARS = 16_000


class ContextTooLargeError(WorkspaceError):
    """The living specs a stage would be given pass what it may read."""


def capability_index(workspace: Workspace) -> str:
    """One line a capability: its slug, and the first line of its purpose."""
    specs, _problems = workspace.specs()
    return "\n".join(f"{slug}: {(spec.purpose.splitlines() or [''])[0]}" for slug, spec in sorted(specs.items()))


def living_text(workspace: Workspace, capabilities: Iterable[str]) -> str:
    """The canonical text of each named capability's living spec, whole, under a line naming it. A capability with
    no spec yet is one the change creates, and adds nothing."""
    specs, _problems = workspace.specs()
    return joined({slug: render_spec(specs[slug]) for slug in capabilities if slug in specs})


def joined(parts: Mapping[str, str]) -> str:
    """Each capability's spec text under a line naming it, whole. `ContextTooLargeError` past the limit."""
    text = "\n".join(f"=== {slug}\n{held}" for slug, held in parts.items())
    if len(text) > CONTEXT_MAX_CHARS:
        sizes = ", ".join(f"{slug} ({len(held):,})" for slug, held in parts.items())
        raise ContextTooLargeError(
            f"the living specs of {sizes} hold {len(text):,} characters, past the {CONTEXT_MAX_CHARS:,} a stage is "
            "given. Split a capability, or name fewer in the change"
        )
    return text


def constitution_text(workspace: Workspace) -> str:
    """The constitution as it stands, or nothing where there is none."""
    path = workspace.home / CONSTITUTION
    return read_text(path) if path.is_file() else ""
