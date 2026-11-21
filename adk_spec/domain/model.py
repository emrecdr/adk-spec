"""The domain's types: what a spec, a delta, a brief, a task list, a finding and a change's state hold.

Each is frozen and refuses a field it does not know. They are the code's own types, never sent to a model as a
schema: those are in `drafts.py`, plain and written for the strictest arm.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

Severity = Literal["ERROR", "WARNING", "INFO"]
Tier = Literal["lean", "standard", "strict"]
Status = Literal["draft", "approved", "verified", "archived"]


class GrammarError(Exception):
    """A file that does not follow its grammar: the line, counted from 1, and what is wrong there."""

    def __init__(self, line: int, message: str) -> None:
        super().__init__(f"line {line}: {message}")
        self.line = line
        self.message = message


class _Held(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Scenario(_Held):
    name: str
    #: Each step as `WHEN ...`, `THEN ...`, `AND ...` or `GIVEN ...`, the keyword in upper case.
    steps: tuple[str, ...]


class Requirement(_Held):
    id: str
    name: str
    statement: str
    scenarios: tuple[Scenario, ...]


class Retired(_Held):
    """A requirement a change removed: its ID is never used again."""

    id: str
    name: str
    change: str


class Spec(_Held):
    """One capability's living spec."""

    capability: str
    purpose: str
    requirements: tuple[Requirement, ...]
    retired: tuple[Retired, ...] = ()


class Removal(_Held):
    id: str
    name: str
    reason: str


class Delta(_Held):
    """What one change does to one capability's spec, keyed by requirement ID."""

    capability: str
    #: Held only where the change creates the capability.
    purpose: str | None = None
    added: tuple[Requirement, ...] = ()
    modified: tuple[Requirement, ...] = ()
    removed: tuple[Removal, ...] = ()


class Task(_Held):
    id: str
    done: bool
    #: May run beside its neighbours: it touches other files than they do.
    parallel: bool
    requirements: tuple[str, ...]
    description: str
    files: tuple[str, ...] = ()
    verify: str | None = None


class TaskGroup(_Held):
    title: str
    tasks: tuple[Task, ...]


class Brief(_Held):
    title: str
    why: str
    what_changes: str
    non_goals: str
    capabilities: tuple[str, ...]
    impact: str
    assumptions: str


class Finding(_Held):
    severity: Severity
    code: str
    message: str
    path: str | None = None
    line: int | None = None


class Approval(_Held):
    """Who approved a change, when, and exactly what: each file's fingerprint and the bases it was approved against.
    The name is a recorded claim, not an authentication."""

    by: str
    at: str
    files: dict[str, str]
    bases: dict[str, str]


class ChangeState(_Held):
    """A change's state file: what neither a folder's place nor a chat records."""

    id: str
    tier: Tier
    status: Status = "draft"
    skip_specs: bool = False
    #: The fingerprint each modified or removed requirement had in the living spec when the delta was based on it.
    bases: dict[str, str] = {}
    approval: Approval | None = None
    #: Whether the change owes a design before its tasks: the brief's own call, or the strict tier's.
    needs_design: bool = False


class Change(_Held):
    """A change's folder, read: its state and each file that parsed."""

    state: ChangeState
    brief: Brief | None = None
    brief_raw: str | None = None
    deltas: dict[str, Delta] = {}
    tasks: tuple[TaskGroup, ...] | None = None
    design: str | None = None
