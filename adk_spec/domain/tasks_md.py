"""A change's task list as Markdown.

The grammar: line 1 is `# Tasks`; each group is `## <title>`; a task is
`- [ ] T001 [P] [REQ-A-001, REQ-A-002] description`, where `[P]` (it may run beside its neighbours) and the list of
requirements are each optional; under a task, optional `  - files: a, b` and `  - verify: <command or check>`.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from .model import GrammarError, Task, TaskGroup
from .spec_md import title_of
from .text import lines_of, normalise

_TITLE = re.compile(r"# (Tasks)")
_GROUP = re.compile(r"## (\S.*)")
_TASK = re.compile(r"- \[( |x|X)\] (T\d{3,})( \[P\])?(?: \[([^\]]*)\])? (\S.*)")
_DETAIL = re.compile(r"\s+- (\w+):\s*(.*)")
_SHAPE = "- [ ] T001 [P] [REQ-<CAPABILITY>-<NNN>] description"


def parse_tasks(text: str) -> tuple[TaskGroup, ...]:
    """The groups of tasks `text` holds. `GrammarError`, with its line, where the text is off the grammar."""
    lines = lines_of(normalise(text))
    top, _title = title_of(lines, _TITLE, "# Tasks")
    groups: list[tuple[str, list[dict]]] = []
    for at in range(top + 1, len(lines)):
        line = lines[at]
        if not line:
            continue
        if group := _GROUP.fullmatch(line):
            groups.append((group[1].strip(), []))
        elif task := _TASK.fullmatch(line):
            if not groups:
                raise GrammarError(at + 1, "a task stands under a group, `## <title>`")
            named = tuple(part.strip() for part in (task[4] or "").split(",") if part.strip())
            groups[-1][1].append(
                {
                    "id": task[2],
                    "done": task[1] != " ",
                    "parallel": task[3] is not None,
                    "requirements": named,
                    "description": task[5].strip(),
                }
            )
        elif detail := _DETAIL.fullmatch(line):
            _detail(groups, detail, at)
        else:
            raise GrammarError(at + 1, f"a task reads `{_SHAPE}`")
    return tuple(TaskGroup(title=title, tasks=tuple(Task(**held) for held in tasks)) for title, tasks in groups)


def _detail(groups: list[tuple[str, list[dict]]], detail: re.Match[str], at: int) -> None:
    """One line under a task, `files` or `verify`, kept on the task above it."""
    if not groups or not groups[-1][1]:
        raise GrammarError(at + 1, "a `files` or `verify` line stands under a task")
    task = groups[-1][1][-1]
    if detail[1] in task:  # a later line would replace an earlier one in silence, past what an approval saw
        raise GrammarError(at + 1, f"a task holds one `{detail[1]}` line, and this is its second")
    if detail[1] in ("files", "verify") and not detail[2].strip():
        raise GrammarError(at + 1, f"this `{detail[1]}` line is empty: say what it names, or remove it")
    if detail[1] == "files":
        task["files"] = tuple(part.strip() for part in detail[2].split(",") if part.strip())
    elif detail[1] == "verify":
        task["verify"] = detail[2].strip() or None
    else:
        raise GrammarError(at + 1, f"`{detail[1]}` is no line of a task: under one, write `files` or `verify`")


def render_tasks(groups: Sequence[TaskGroup], *, unchecked: bool = False) -> str:
    """The task list in its canonical form. With `unchecked`, every box is empty: what an approval is taken of, so
    ticking a task during the work changes nothing an approver read."""
    chunks = ["# Tasks"]
    for group in groups:
        chunks.append(f"## {group.title}")
        lines = []
        for task in group.tasks:
            box = "x" if task.done and not unchecked else " "
            beside = " [P]" if task.parallel else ""
            # An empty list is written where the description opens with a bracket, which would read as the list.
            named = f" [{', '.join(task.requirements)}]" if task.requirements or task.description[:1] == "[" else ""
            lines.append(f"- [{box}] {task.id}{beside}{named} {task.description}")
            if task.files:
                lines.append(f"  - files: {', '.join(task.files)}")
            if task.verify:
                lines.append(f"  - verify: {task.verify}")
        if lines:
            chunks.append("\n".join(lines))
    return "\n\n".join(chunks) + "\n"


def task_path(named: str) -> str:
    """A task's file as a path: written by a person or a model, it may be quoted in backticks or open on `./`."""
    return named.strip().strip("`").replace("\\", "/").removeprefix("./").rstrip("/")


def paths_meet(one: str, other: str) -> bool:
    """Whether two of a task's paths are one file, or one is a folder the other is under."""
    return one == other or one.startswith(f"{other}/") or other.startswith(f"{one}/")
