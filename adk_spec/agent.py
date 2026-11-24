"""The shape ADK's own interface loads: `adk web <the folder that holds this package>`, started from inside a
repository that holds `.spec/`.

One message typed is one request. It is drafted as `adk-spec propose --no-input` drafts it, and the chat ends on the
drafts as their files, or on the reason there are none. Nothing is written, and no question is asked: a chat is for
watching a run stage by stage, and the command is what writes a change. Run on the pinned engine
(`q20_plan3_adk_web_shape_probe.py`): the loader finds `app` here, the first node receives the message typed, and
text a function node emits reaches the chat. And (`q18`): a run that pauses for an answer cannot carry the plugin
that survives an answer off its schema, which is why this shape asks nothing.

This is the one module of the package that builds at import, as the loader requires of it. Nothing of the package
imports it, so no command pays for it. The workspace is read once, where the process stands when it is loaded; the
ledger has no ceiling here, since it would count every chat of a process that stays up.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from .orchestration.graph import Known, build_chat_app
from .orchestration.plugins import UsageLedger
from .orchestration.stages import CAPABILITIES, CONSTITUTION, LESSONS_TEXT, PROFILE_TEXT
from .workspace.context import capability_index, constitution_text, lessons_text, profile_text
from .workspace.files import NotTextError
from .workspace.layout import Workspace, WorkspaceError


def _known() -> tuple[Known, dict[str, str]]:
    """What a chat is told of the workspace the process stands in, or of none: with no `.spec/` at or above it,
    the chat still loads, and knows no capability."""
    try:
        workspace = Workspace.find(Path.cwd())
    except WorkspaceError:
        return Known(living={}, taken=frozenset()), dict.fromkeys(
            (CAPABILITIES, CONSTITUTION, LESSONS_TEXT, PROFILE_TEXT), ""
        )
    specs, _problems = workspace.specs()
    told = {
        CAPABILITIES: capability_index(specs),
        CONSTITUTION: _readable(constitution_text, workspace),
        LESSONS_TEXT: _readable(lessons_text, workspace),
        PROFILE_TEXT: _readable(profile_text, workspace),  # found by the fourth audit: `propose` gave it, the chat not
    }
    return Known(living=specs, taken=frozenset(workspace.taken(specs))), told


def _readable(read: Callable[[Workspace], str], workspace: Workspace) -> str:
    """A file of the workspace as a chat's drafts read it, or none where it is no text: a file a person edits by
    hand, as PowerShell 5.1 writes UTF-16, does not stop the chat loading."""
    try:
        return read(workspace)
    except NotTextError, OSError:  # found by the code review: a profile that would not open stopped the chat
        return ""


app = build_chat_app(*_known(), ledger=UsageLedger())
root_agent = app.root_agent
