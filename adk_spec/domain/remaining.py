"""`reports/remaining.md`: what a verification left to do, for the person or the coding assistant who does it next.
Each requirement not shown met, what code finds about it first (a task ticked though its requirement is unmet, the
files its tasks named that the diff never touched), then the model's reason, which code has not checked."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .model import TaskGroup
from .tasks_md import task_path
from .verify import Verdict


@dataclass(frozen=True)
class Left:
    """One requirement a verification did not show met, and what bears on it."""

    id: str
    verdict: str
    reason: str
    #: The tasks that name it and are ticked, then those that are not, by ID.
    ticked: tuple[str, ...]
    open: tuple[str, ...]
    #: The files those tasks named that the diff never touched.
    untouched: tuple[str, ...]
    #: Whether code wrote the reason, as `Verdict.coded`.
    coded: bool


def remaining(verdicts: Sequence[Verdict], groups: Sequence[TaskGroup], touched: frozenset[str]) -> list[Left]:
    """Each of `verdicts` that is not `met`, in the order of its ID, with the tasks of `groups` that name it and the
    files they named that are not among `touched`, the paths of the diff."""
    tasks = [task for group in groups for task in group.tasks]
    left = []
    for verdict in sorted(verdicts, key=lambda one: one.id):
        if verdict.verdict == "met":
            continue
        serving = [task for task in tasks if verdict.id in task.requirements]
        named = dict.fromkeys(task_path(path) for task in serving for path in task.files)
        left.append(
            Left(
                id=verdict.id,
                verdict=verdict.verdict,
                reason=verdict.reason,
                ticked=tuple(task.id for task in serving if task.done),
                open=tuple(task.id for task in serving if not task.done),
                untouched=tuple(path for path in named if not _touched(path, touched)),
                coded=verdict.coded,
            )
        )
    return left


def _touched(path: str, touched: frozenset[str]) -> bool:
    """Whether the diff touched `path`, or a file under it where it is a folder."""
    return path in touched or any(one.startswith(f"{path}/") for one in touched)


def render_remaining(
    change_id: str, left: Sequence[Left], *, last: str = "verify", names: Mapping[str, str] | None = None
) -> str:
    """The report of what `change_id` has left to do, and `last`, the command that follows: `verify`, or `archive`
    for a tier that owes no verification. Each requirement is named beside its ID, from `names`."""
    lines = [
        f"# Remaining: {change_id}",
        "",
        f"The last verification did not show these met. Work on them, then run `adk-spec {last} {change_id}`.",
        "",
    ]
    for one in left:
        named = (names or {}).get(one.id)
        lines += [f"## {one.id}{f' {named}' if named else ''}: {one.verdict}", ""]
        if one.ticked:
            lines.append(f"- Ticked, yet unmet: {', '.join(one.ticked)}")
        if one.open:
            lines.append(f"- Not ticked: {', '.join(one.open)}")
        if not one.ticked and not one.open:
            lines.append("- No task names it.")
        if one.untouched:
            lines.append(f"- Named by its tasks, untouched by the work: {', '.join(one.untouched)}")
        said = "What code found" if one.coded else "The model's reason, which code has not checked"
        lines += [f"- {said}: {one.reason}", ""]
    return "\n".join(lines).rstrip("\n") + "\n"
