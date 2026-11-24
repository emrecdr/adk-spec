"""The domain's types: what a spec, a delta, a brief, a task list, a finding and a change's state hold.

Each is frozen and refuses a field it does not know. They are the code's own types, never sent to a model as a
schema: those are in `drafts.py`, plain and written for the strictest arm.
"""

from __future__ import annotations

from typing import Literal, get_args

from pydantic import BaseModel, ConfigDict, Field

Severity = Literal["ERROR", "WARNING", "INFO"]
Tier = Literal["lean", "standard", "strict"]
#: Every tier, as a person names one.
TIERS: tuple[Tier, ...] = get_args(Tier)
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


#: What a statement about a repository's code says of it, for a change: that something is there already, that the
#: change plugs in there, that the repository does a thing a certain way, or that something is unclear or at risk.
StatementKind = Literal["exists", "touches", "convention", "risk"]


class Statement(_Held):
    """One thing a reading of the code found, with the line it rests on: the quote was found in that file."""

    kind: StatementKind
    path: str
    line: int
    quote: str
    note: str
    #: The line that opens the block the quoted line stands in, found by code in the file as it stands; empty at
    #: the top level. It is what shows a note about one function resting on a line of another.
    within: str = ""


class Finding(_Held):
    severity: Severity
    code: str
    message: str
    path: str | None = None
    line: int | None = None


class Seconded(_Held):
    """The second approval a strict change owes: by another name than the first, and when."""

    by: str
    at: str


class Approval(_Held):
    """Who approved a change, when, and exactly what: each file's fingerprint and the bases it was approved against.
    The name is a recorded claim, not an authentication."""

    by: str
    at: str
    files: dict[str, str]
    bases: dict[str, str]
    #: Why the approver set a blocking finding of the check aside, in their words. None where nothing was.
    override: str | None = None
    #: A strict change's second approval, by another name; until it is given, the change stays a draft.
    second: Seconded | None = None


class Checked(_Held):
    """What a check of a change read and found: each file's fingerprint as it stood, how many findings block an
    approval, the model that judged, none where code alone did, and how many of the blocking findings the model made
    itself. That last is none where code alone judged, or where an older adk-spec recorded the check, which counted
    the code's findings into the model's: found by the code review, read as the model's own, they held a strict
    change for good."""

    at: str
    files: dict[str, str]
    blocking: int
    model: str | None = None
    #: Left out of the record where there is none, so that a check by code alone stays one an older adk-spec reads,
    #: which refuses a field it does not know.
    model_blocking: int | None = Field(default=None, exclude_if=lambda held: held is None)


#: What a run of a project's tests that passed came to: every other outcome says why it did not.
PASSED = "passed"


class Verification(_Held):
    """What a verification of a change judged and found: the commit the work was compared with, the fingerprint of
    the diff, a verdict for each requirement, and the reason where a person verified it over a verdict."""

    at: str
    base: str
    diff: str
    verdicts: dict[str, str]
    override: str | None = None
    model: str | None = None
    #: The commit each other repository's work was compared with.
    bases: dict[str, str] = {}
    #: What each run of the project's tests came to, by repository, `.` for the workspace's own: `passed`, or why not.
    tests: dict[str, str] = {}

    @property
    def tests_passed(self) -> bool:
        """Whether every run of the project's tests passed: true where none was run."""
        return all(outcome == PASSED for outcome in self.tests.values())


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
    #: The last check of the change's files against each other. Void once one of them changes.
    check: Checked | None = None
    #: The last verification of the work against the change's requirements.
    verification: Verification | None = None
    #: The commit checked out when the change was first approved, where the repository is git's: where the work
    #: began, and what `verify` compares it with. It is the change's, not one approval's: approving again after an
    #: edit, or after a rebase, does not move it past work already done.
    base_commit: str | None = None
    #: The other repositories the change spans, each a name and a path from the folder that holds `.spec/`, with
    #: forward slashes: read, approved and verified with this change alone. Named with `--with`.
    repositories: dict[str, str] = {}
    #: Where the work began in each of `repositories`, recorded at the first approval that found it there, and never
    #: moved past work already done, as `base_commit` is not.
    base_commits: dict[str, str] = {}
    #: The fingerprint each file had as adk-spec drafted it, by its path, as an approval takes it: what `approve`
    #: compares to name a draft a person corrected. Once named, the approved fingerprint stands in its place.
    drafted: dict[str, str] = {}


class Change(_Held):
    """A change's folder, read: its state and each file that parsed."""

    state: ChangeState
    brief: Brief | None = None
    brief_raw: str | None = None
    deltas: dict[str, Delta] = {}
    tasks: tuple[TaskGroup, ...] | None = None
    design: str | None = None
