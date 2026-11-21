"""A model's drafts turned into the domain's types.

What a model may not decide is decided here: a new requirement's ID, a task's number, a change's slug. What a model
writes loosely is made canonical here: a step's keyword, stray spaces, a purpose given for a capability that exists.
Nothing is checked: the validator judges what comes out, and a gate asks the model again.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping

from .drafts import BriefDraft, DeltasDraft, DesignDraft, RequirementDraft, TasksDraft
from .ids import SLUG_MAX, next_requirement_id, slug_problem
from .model import Brief, Delta, Removal, Requirement, Scenario, Spec, Task, TaskGroup

_STEP = re.compile(r"(?:-\s*)?(?:\*\*)?(GIVEN|WHEN|THEN|AND)(?:\*\*)?\s+(\S.*)", re.IGNORECASE | re.DOTALL)
_WORD = re.compile(r"[a-z0-9]+")
FALLBACK = "change"


def _line(text: str) -> str:
    """`text` on one line."""
    return " ".join(text.split())


def _step(text: str) -> str:
    """A step with its keyword in upper case and no bullet; one with no keyword is left for the validator."""
    found = _STEP.fullmatch(text.strip())
    return f"{found[1].upper()} {_line(found[2])}" if found else _line(text)


def _requirement(req_id: str, draft: RequirementDraft) -> Requirement:
    scenarios = tuple(
        Scenario(name=_line(scenario.name), steps=tuple(_step(step) for step in scenario.steps if step.strip()))
        for scenario in draft.scenarios
    )
    return Requirement(id=req_id, name=_line(draft.name), statement=draft.statement.strip(), scenarios=scenarios)


def to_brief(draft: BriefDraft) -> Brief:
    return Brief(
        title=_line(draft.title),
        why=draft.why.strip(),
        what_changes=draft.what_changes.strip(),
        non_goals=draft.non_goals.strip(),
        capabilities=tuple(capability.strip() for capability in draft.capabilities if capability.strip()),
        impact=draft.impact.strip(),
        assumptions=draft.assumptions.strip(),
    )


def to_deltas(draft: DeltasDraft, living: Mapping[str, Spec], taken: Iterable[str]) -> dict[str, Delta]:
    """One delta a capability. An added requirement is given the next ID no spec and no open change holds, and each
    one given counts as held; a purpose is kept only for a capability that is not there yet."""
    held = set(taken)
    slots: dict[str, dict] = {}
    for one in draft.deltas:
        capability = one.capability.strip()
        slot = slots.setdefault(capability, {"purpose": None, "added": [], "modified": [], "removed": []})
        if one.purpose.strip() and capability not in living:
            slot["purpose"] = slot["purpose"] or one.purpose.strip()
        names = {req.id: req.name for req in living[capability].requirements} if capability in living else {}
        for added in one.added:
            req_id = next_requirement_id(capability, held)
            held.add(req_id)
            slot["added"].append(_requirement(req_id, added))
        slot["modified"] += [_requirement(changed.id.strip(), changed.requirement) for changed in one.modified]
        slot["removed"] += [
            Removal(id=gone.id.strip(), name=names.get(gone.id.strip(), ""), reason=_line(gone.reason))
            for gone in one.removed
        ]
    return {
        capability: Delta(
            capability=capability,
            purpose=slot["purpose"],
            added=tuple(slot["added"]),
            modified=tuple(slot["modified"]),
            removed=tuple(slot["removed"]),
        )
        for capability, slot in slots.items()
    }


def to_tasks(draft: TasksDraft) -> tuple[TaskGroup, ...]:
    """The groups with each task numbered in order across them, none done."""
    number = 0
    groups = []
    for group in draft.groups:
        tasks = []
        for task in group.tasks:
            number += 1
            tasks.append(
                Task(
                    id=f"T{number:03d}",
                    done=False,
                    parallel=task.parallel,
                    requirements=tuple(named.strip() for named in task.requirements if named.strip()),
                    description=_line(task.description),
                    files=tuple(path.strip() for path in task.files if path.strip()),
                    verify=_line(task.verify) or None,
                )
            )
        groups.append(TaskGroup(title=_line(group.title), tasks=tuple(tasks)))
    return tuple(groups)


def render_design(draft: DesignDraft) -> str:
    sections = (
        ("Context", draft.context),
        ("Goals", draft.goals),
        ("Decisions", draft.decisions),
        ("Risks", draft.risks),
    )
    return "# Design\n\n" + "\n\n".join(f"## {name}\n\n{text.strip()}" for name, text in sections) + "\n"


def slug_of(title: str, held: Iterable[str]) -> str:
    """A change's slug from its title: its lowercase ASCII words joined by hyphens, cut at a word's end to what a
    slug may hold, and numbered where `held` has it already."""
    words = _WORD.findall(title.lower())
    if not words or not words[0][0].isalpha():
        words.insert(0, FALLBACK)
    base = words[0][:SLUG_MAX]
    for word in words[1:]:
        if len(base) + 1 + len(word) > SLUG_MAX:
            break
        base = f"{base}-{word}"
    if slug_problem(base):  # a name Windows reserves
        base = f"{base}-{FALLBACK}"
    taken, slug, number = set(held), base, 1
    while slug in taken:
        number += 1
        tail = f"-{number}"
        slug = base[: SLUG_MAX - len(tail)].rstrip("-") + tail
    return slug
