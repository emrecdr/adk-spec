"""What a change's files show against each other, with no judgement in it: which requirement no task serves, and
which task names a requirement nothing holds.

The validator reads each file by itself; this reads them together. It is code from the start: the answer is a
function of the files, an oracle for it exists (the IDs), and a model asked the same would cost a call to be right
most of the time.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from .ids import REQ_ID
from .lifecycle import TASKS_FILE
from .model import Change, Delta, Finding, Spec, TaskGroup
from .validate import finding


def owed(deltas: Mapping[str, Delta]) -> frozenset[str]:
    """Every requirement a change adds or modifies: each is owed a verdict the diff's added lines ground, as each a
    change removes is owed one its removed lines ground."""
    return frozenset(req.id for delta in deltas.values() for req in (*delta.added, *delta.modified))


def tasked(deltas: Mapping[str, Delta]) -> frozenset[str]:
    """Every requirement a change's task list owes a task: what it adds or modifies, and what it removes, whose code
    a task takes out. Found by an outside audit, the owner's choice: `verify` asks a removed requirement for the
    lines that took it out, and no task was owed to take them out."""
    return owed(deltas) | removed(deltas)


def removed(deltas: Mapping[str, Delta]) -> frozenset[str]:
    """Every requirement a change removes."""
    return frozenset(gone.id for delta in deltas.values() for gone in delta.removed)


def nameable(deltas: Mapping[str, Delta], living: Mapping[str, Spec]) -> frozenset[str]:
    """Every requirement a task of the change may name: what it adds, modifies or removes, and what any living
    spec holds. A task may serve a requirement the change leaves alone and must keep true."""
    held = {req.id for spec in living.values() for req in spec.requirements}
    return tasked(deltas) | held


def coverage(groups: Sequence[TaskGroup], *, owed: frozenset[str], nameable: frozenset[str]) -> list[Finding]:
    """What a task list shows against the requirements of its change. A task that names no requirement, a setup
    task, draws no finding; a name that is no requirement ID at all is the validator's to report."""
    tasks = [task for group in groups for task in group.tasks]
    served = {named for task in tasks for named in task.requirements}
    found = [
        finding("check.requirement-no-task", f"No task serves {req_id}. Give it a task, or take it out of the delta.")
        for req_id in sorted(owed - served)
    ]
    found += [
        finding(
            "check.task-unknown-requirement",
            f"{task.id} names {named}, which this change does not touch and no living spec holds. Name a "
            "requirement that exists, or one this change adds.",
        )
        for task in tasks
        for named in task.requirements
        if REQ_ID.fullmatch(named) and named not in nameable
    ]
    return found


def coverage_of(change: Change, living: Mapping[str, Spec]) -> list[Finding]:
    """`coverage` for a change as it was read, each finding about its task list. Nothing where it has no task yet:
    that is one finding of the validator's, not one a requirement."""
    groups = change.tasks or ()
    if not any(group.tasks for group in groups):
        return []
    found = coverage(groups, owed=tasked(change.deltas), nameable=nameable(change.deltas, living))
    return [held.model_copy(update={"path": TASKS_FILE}) for held in found]
