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
from .model import Brief, Delta, GrammarError, Removal, Requirement, Scenario, Spec, Task, TaskGroup
from .spec_md import fenced_lines, paragraphs
from .text import lines_of, normalise

_STEP = re.compile(r"(?:-\s*)?(?:\*\*)?(GIVEN|WHEN|THEN|AND)(?:\*\*)?\s+(\S.*)", re.IGNORECASE | re.DOTALL)
_WORD = re.compile(r"[a-z0-9]+")
FALLBACK = "change"


def _line(text: str) -> str:
    """`text` on one line."""
    return " ".join(text.split())


def _text(text: str) -> str:
    """Prose as its file holds it, so a draft reads back as written: the lines the parsers read, one blank line
    between paragraphs, none at the ends. Text with a fence left open is passed on as it is, for a gate to name."""
    lines = [line if line.strip() else "" for line in lines_of(normalise(text))]  # a no-break space is no text
    try:
        return paragraphs(lines, fenced_lines(lines), 0, len(lines))
    except GrammarError:
        return "\n".join(lines).strip()


def _listed(items: list[str]) -> tuple[str, ...]:
    """Each item of a list, where a model may have given several in one string with commas between."""
    return tuple(part.strip() for item in items for part in item.split(",") if part.strip())


def _step(text: str) -> str:
    """A step with its keyword in upper case and no bullet; one with no keyword is left for the validator."""
    found = _STEP.fullmatch(text.strip())
    return f"{found[1].upper()} {_line(found[2])}" if found else _line(text)


def _requirement(req_id: str, draft: RequirementDraft) -> Requirement:
    scenarios = tuple(
        Scenario(name=_line(scenario.name), steps=tuple(_step(step) for step in scenario.steps if step.strip()))
        for scenario in draft.scenarios
    )
    return Requirement(id=req_id, name=_line(draft.name), statement=_text(draft.statement), scenarios=scenarios)


def to_brief(draft: BriefDraft) -> Brief:
    return Brief(
        title=_line(draft.title),
        why=_text(draft.why),
        what_changes=_text(draft.what_changes),
        non_goals=_text(draft.non_goals),
        capabilities=_listed(draft.capabilities),
        impact=_text(draft.impact),
        assumptions=_text(draft.assumptions),
    )


def to_deltas(draft: DeltasDraft, living: Mapping[str, Spec], taken: Iterable[str]) -> dict[str, Delta]:
    """One delta a capability. An added requirement is given the next ID no spec and no open change holds, and each
    one given counts as held; a purpose is kept only for a capability that is not there yet."""
    held = set(taken)
    slots: dict[str, dict] = {}
    for one in draft.deltas:
        capability = one.capability.strip()
        slot = slots.setdefault(capability, {"purpose": None, "added": [], "modified": [], "removed": []})
        if capability not in living:
            slot["purpose"] = slot["purpose"] or _text(one.purpose) or None
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
                    requirements=_listed(task.requirements),
                    description=_line(task.description),
                    files=_listed(task.files),
                    verify=_line(task.verify) or None,
                )
            )
        groups.append(TaskGroup(title=_line(group.title), tasks=tuple(tasks)))
    return tuple(groups)


#: The sections of a design, in the order of its file: each a field of `DesignDraft`.
DESIGN_SECTIONS = ("context", "goals", "decisions", "risks")


def render_design(draft: DesignDraft) -> str:
    sections = (f"## {name.capitalize()}\n\n{getattr(draft, name).strip()}" for name in DESIGN_SECTIONS)
    return "# Design\n\n" + "\n\n".join(sections) + "\n"


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
    taken, slug, number = {name.casefold() for name in held}, base, 1  # macOS and Windows read a twin by case as one
    while slug in taken:
        number += 1
        tail = f"-{number}"
        slug = base[: SLUG_MAX - len(tail)].rstrip("-") + tail
    return slug
