"""`reports/remaining.md`: what a verification left to do, for the person or the coding assistant who does it next.
Each requirement not shown met, what code finds about it first (a task ticked though its requirement is unmet, the
files its tasks named that the diff never touched), then the model's reason, which code has not checked."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from .model import TaskGroup
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


def remaining(verdicts: Sequence[Verdict], groups: Sequence[TaskGroup], touched: frozenset[str]) -> list[Left]:
    """Each of `verdicts` that is not `met`, in the order of its ID, with the tasks of `groups` that name it and the
    files they named that are not among `touched`, the paths of the diff."""
    tasks = [task for group in groups for task in group.tasks]
    left = []
    for verdict in sorted(verdicts, key=lambda one: one.id):
        if verdict.verdict == "met":
            continue
        serving = [task for task in tasks if verdict.id in task.requirements]
        named = dict.fromkeys(_path(path) for task in serving for path in task.files)
        left.append(
            Left(
                id=verdict.id,
                verdict=verdict.verdict,
                reason=verdict.reason,
                ticked=tuple(task.id for task in serving if task.done),
                open=tuple(task.id for task in serving if not task.done),
                untouched=tuple(path for path in named if not _touched(path, touched)),
            )
        )
    return left


def _path(named: str) -> str:
    """A task's file as a path: written by a person or a model, it may be quoted in backticks or open on `./`."""
    return named.strip().strip("`").removeprefix("./").rstrip("/")


def _touched(path: str, touched: frozenset[str]) -> bool:
    """Whether the diff touched `path`, or a file under it where it is a folder."""
    return path in touched or any(one.startswith(f"{path}/") for one in touched)


def render_remaining(change_id: str, left: Sequence[Left]) -> str:
    """The report of what `change_id` has left to do."""
    lines = [
        f"# Remaining: {change_id}",
        "",
        f"The last verification did not show these met. Work on them, then run `adk-spec verify {change_id}`.",
        "",
    ]
    for one in left:
        lines += [f"## {one.id}: {one.verdict}", ""]
        if one.ticked:
            lines.append(f"- Ticked, yet unmet: {', '.join(one.ticked)}")
        if one.open:
            lines.append(f"- Not ticked: {', '.join(one.open)}")
        if not one.ticked and not one.open:
            lines.append("- No task names it.")
        if one.untouched:
            lines.append(f"- Named by its tasks, untouched by the work: {', '.join(one.untouched)}")
        lines += [f"- The model's reason, which code has not checked: {one.reason}", ""]
    return "\n".join(lines).rstrip("\n") + "\n"
