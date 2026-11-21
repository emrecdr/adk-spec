"""What a command sent to a model and what came back, kept one file a command under `.spec/runs/`.

A recording is what a stage is measured on afterwards, what a fake model replays in a test, and where a person
reads why a gate sent an answer back. It holds the texts that were sent and received and nothing of how the
provider was reached: no key and no token is ever part of an instruction. What was sent is what the command read:
specs and a change's files, and for `verify` a diff of the working tree, which holds whatever changed in files git
does not ignore. The folder ignores itself for git.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from .files import read_text, write_all
from .layout import Workspace

RUNS = "runs"
IGNORE = ".gitignore"


class Call(BaseModel):
    """One call of one stage: the instruction as it was sent, what its gate had told the stage, and the answer."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    stage: str
    instruction: str
    #: What the gate found wrong with the stage's answer before this one, where it asked again.
    findings: str | None = None
    #: The answer as it came, before any check. None where none came: a call refused or one that raised.
    answer: str | None = None
    error: str | None = None
    tokens: int = 0
    seconds: float = 0.0


class Recording(BaseModel):
    """One command's model calls, in order, and how the command ended."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    command: str
    change: str | None
    at: str
    model: str
    #: For `propose`: `written` or `nothing owed`. For a command of one model pass: `answered`, where the pass
    #: gave an answer to use. For any: `interrupted`, or `failed: ` and the sentence the person was given.
    outcome: str
    calls: tuple[Call, ...]


def listed(workspace: Workspace) -> list[Path]:
    """Every recording of the workspace, the newest first. A file's name starts with the moment it was written."""
    folder = workspace.home / RUNS
    return sorted(folder.glob("*.json"), reverse=True) if folder.is_dir() else []


def read(path: Path) -> Recording:
    return Recording.model_validate_json(read_text(path))


def write(workspace: Workspace, recording: Recording, *, keep: int) -> Path | None:
    """`recording` written as the newest, and every recording past the newest `keep` removed. With `keep` at 0
    nothing is written, and no folder made."""
    if keep <= 0:
        return None
    folder = workspace.home / RUNS
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")  # to the microsecond: two commands a second sort apart
    path = folder / f"{stamp}-{recording.command}.json"
    files = {path: recording.model_dump_json(indent=2) + "\n"}
    if not (folder / IGNORE).is_file():
        files[folder / IGNORE] = "*\n"
    write_all(files)
    for old in listed(workspace)[keep:]:
        old.unlink(missing_ok=True)
    return path
