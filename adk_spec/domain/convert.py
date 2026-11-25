"""A model's drafts turned into the domain's types.

What a model may not decide is decided here: a new requirement's ID, a task's number, a change's slug. What a model
writes loosely is made canonical here: a step's keyword, stray spaces, a purpose given for a capability that exists.
What a model drafts is not judged here: the validator judges what comes out, and a gate asks the model again.
What a model points to is held to the text: a finding whose quote is not in the file it names is left out.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping, Sequence
from typing import Protocol

from .brief_md import asked_in, marker_of, render_brief, worded
from .drafts import (
    BriefDraft,
    DeltasDraft,
    DesignDraft,
    FindingsDraft,
    RequirementDraft,
    SurveyDraft,
    TasksDraft,
)
from .ids import SLUG_MAX, next_requirement_id, slug_problem
from .model import (
    Brief,
    Delta,
    Finding,
    GrammarError,
    Removal,
    Requirement,
    Scenario,
    Severity,
    Spec,
    Statement,
    Task,
    TaskGroup,
)
from .spec_md import fenced_lines, paragraphs
from .tasks_md import task_path
from .text import flat, lines_of, normalise, plain, quoted_at

_STEP = re.compile(r"(?:-\s*)?(?:\*\*)?(GIVEN|WHEN|THEN|AND)(?:\*\*)?\s+(\S.*)", re.IGNORECASE | re.DOTALL)
_WORD = re.compile(r"[a-z0-9]+")
FALLBACK = "change"


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
    return f"{found[1].upper()} {flat(found[2])}" if found else flat(text)


def _requirement(req_id: str, draft: RequirementDraft) -> Requirement:
    scenarios = tuple(
        Scenario(name=flat(scenario.name), steps=tuple(_step(step) for step in scenario.steps if step.strip()))
        for scenario in draft.scenarios
    )
    return Requirement(id=req_id, name=flat(draft.name), statement=_text(draft.statement), scenarios=scenarios)


#: What a person is asked for a marker that holds no question.
NO_QUESTION = "The brief leaves a point open and names no question."


def _open(draft: BriefDraft) -> dict[str, str]:
    """The open points a draft names: each question as its marker holds it, with the answer suggested for it. A
    point named twice is one point, with its first suggestion; one with no question is none."""
    points: dict[str, str] = {}
    for one in draft.open_points:
        if asked := worded(one.question):
            points.setdefault(asked, plain(one.suggested))
    return points


def to_brief(draft: BriefDraft) -> Brief:
    """The brief as the domain holds it. Each open point the draft names stands in the assumptions as a marker, a
    paragraph of its own: the file a person reads and the validator counts is what it was before the points were
    data. A point the model also wrote as a marker by hand, in any section, copied from the brief it replaces, is
    not written twice."""
    held = Brief(
        title=flat(draft.title),
        why=_text(draft.why),
        what_changes=_text(draft.what_changes),
        non_goals=_text(draft.non_goals),
        capabilities=_listed(draft.capabilities),
        impact=_text(draft.impact),
        assumptions=_text(draft.assumptions),
    )
    written = set(asked_in(render_brief(held)))
    waiting = _waiting(draft)  # a point that waits on another's answer is listed after those answerable now
    points = [marker_of(asked) for asked in sorted(_open(draft), key=waiting.__contains__) if asked not in written]
    assumptions = "\n\n".join(part for part in (held.assumptions, *points) if part)
    return held.model_copy(update={"assumptions": assumptions})


def questions_of(draft: BriefDraft, *, every: bool = False) -> list[dict[str, str]]:
    """What a person is asked about a draft's brief: one question for each point its file marks as open, in the
    file's order, each with the answer the draft suggests for it, or none. A marker the model wrote in a section by
    itself is asked too. This was a model's stage: the question is the marker's own text, and only the suggestion
    took a model, which the brief stage now gives."""
    suggested, waiting = _open(draft), set() if every else _waiting(draft)
    asked = [one for one in dict.fromkeys(asked_in(render_brief(to_brief(draft)))) if one not in waiting]
    return [{"question": one or NO_QUESTION, "suggested": suggested.get(one, "")} for one in asked]


def _waiting(draft: BriefDraft) -> set[str]:
    """The open points a round does not ask yet, each as its marker holds it: those that wait on another point's
    answer, as the grilling skill asks a design tree only at its frontier. A wait counts only on another point that
    has a question, by its position: found by review, one on a point with none, never asked, held a point back for
    good. A question that stands twice waits only where every copy does; where every point would wait, as in a
    loop, none does, so that a round never asks nothing."""
    worded_points = [worded(one.question) for one in draft.open_points]
    askable = {number for number, asked in enumerate(worded_points, 1) if asked}
    held = {
        number
        for number, one in enumerate(draft.open_points, 1)
        if number in askable and any(other in askable and other != number for other in one.depends_on)
    }
    if held >= askable:
        return set()
    free = {worded_points[number - 1] for number in askable - held}
    return {worded_points[number - 1] for number in held} - free


def to_deltas(
    draft: DeltasDraft,
    living: Mapping[str, Spec],
    taken: Iterable[str],
    kept: Mapping[tuple[str, str], Sequence[str]] | None = None,
) -> dict[str, Delta]:
    """One delta a capability. An added requirement is given the next ID no spec and no open change holds, and each
    one given counts as held; a purpose is kept only for a capability that is not there yet. A requirement given as
    modified that says what the living spec says is left out: a model restating a spec copies its neighbours.

    `kept` holds the IDs a change being revised has already given, by capability and requirement name, in order: a
    requirement the revision keeps by its name keeps its ID, each ID given once. One of those requirements given
    back as modified or removed is no living one: it stays added, with its ID, or is dropped."""
    left = {key: list(ids) for key, ids in (kept or {}).items()}  # each kept ID given once: taken out as it is
    own = {req_id for ids in left.values() for req_id in ids}
    held = set(taken) | own
    slots: dict[str, dict] = {}
    for one in draft.deltas:
        capability = one.capability.strip()
        slot = slots.setdefault(capability, {"purpose": None, "added": [], "modified": [], "removed": []})
        if capability not in living:
            slot["purpose"] = slot["purpose"] or _text(one.purpose) or None
        stands = {req.id: req for req in living[capability].requirements} if capability in living else {}
        for added in one.added:
            ids = left.get((capability, named(added.name)))
            req_id = ids.pop(0) if ids else next_requirement_id(capability, held)
            held.add(req_id)
            slot["added"].append(_requirement(req_id, added))
        mine = own - stands.keys()  # the change's own IDs, which no living spec holds
        for changed in one.modified:
            req = _requirement(changed.id.strip(), changed.requirement)
            if req.id not in mine:
                slot["modified"] += [req] if stands.get(req.id) != req else []
            elif req.id not in {given.id for given in slot["added"]}:
                slot["added"].append(req)
        slot["removed"] += [
            Removal(id=gone, name=stands[gone].name if gone in stands else "", reason=flat(removed.reason))
            for removed in one.removed
            if (gone := removed.id.strip()) not in mine
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
                    description=flat(task.description),
                    files=_listed(task.files),
                    verify=flat(task.verify) or None,
                )
            )
        groups.append(TaskGroup(title=flat(group.title), tasks=_apart(tasks)))
    return tuple(groups)


def _apart(tasks: list[Task]) -> tuple[Task, ...]:
    """Each task's `[P]` where it and the tasks before and after it name their files, and none of its own meets
    theirs: the rule the tasks stage is told, held by code, so no two tasks side by side run on one file. A neighbour
    naming none cannot be said apart either (found by phase 17's last review). Phase 17."""
    files: list[list[str] | None] = [None, *([task_path(one) for one in task.files] for task in tasks), None]
    return tuple(
        task.model_copy(update={"parallel": task.parallel and _apart_from(mine, before, after)})
        for task, before, mine, after in zip(tasks, files, files[1:], files[2:], strict=False)
    )


def _apart_from(mine: list[str] | None, *neighbours: list[str] | None) -> bool:
    """Whether a task naming `mine` touches no file of its `neighbours`: None where there is none, at a group's edge."""
    if not mine or any(side == [] for side in neighbours):
        return False
    return not _meet(mine, [path for side in neighbours if side for path in side])


def _meet(paths: list[str], others: list[str]) -> bool:
    """Whether a path of `paths` is one of `others`, or one is a folder the other is under."""
    return any(
        one == other or other.startswith(f"{one}/") or one.startswith(f"{other}/") for one in paths for other in others
    )


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


_SEVERITY: dict[str, Severity] = {"critical": "ERROR", "warning": "WARNING", "note": "INFO"}


class Pointing(Protocol):
    """What a model says of a text it was shown: the file it means, and the words it copied from it."""

    file: str
    quote: str


def pointed_at(one: Pointing, texts: Mapping[str, str]) -> tuple[str, int] | None:
    """The file a model's finding or statement is about and the line its quote starts at, or nothing where it
    points at nothing: the file it names is none of `texts`, or does not hold the text it quotes."""
    path = one.file.strip()
    line = quoted_at(one.quote, texts[path]) if path in texts else None
    return None if line is None else (path, line)


def to_findings(draft: FindingsDraft, texts: Mapping[str, str]) -> tuple[list[Finding], int]:
    """The findings a model gave that point at something, and how many did not. A model's finding that quotes
    nothing real is no finding, whatever it says."""
    kept = [
        Finding(
            severity=_SEVERITY[one.severity],
            code=f"check.{one.kind}",
            message=plain(one.message),
            path=at[0],
            line=at[1],
        )
        for one in draft.findings
        if (at := pointed_at(one, texts)) is not None
    ]
    return kept, len(draft.findings) - len(kept)


#: How much of a quote a statement keeps: the line a person is shown under it.
QUOTE_SHOWN_CHARS = 200


def to_statements(draft: SurveyDraft, texts: Mapping[str, str]) -> tuple[list[Statement], int]:
    """The statements a model made of the code that point at something, and how many did not. Each is held to the
    text it was shown, as a finding of a check is: a statement that quotes nothing real is no statement, whatever
    a file it read told it to write."""
    kept = [
        Statement(
            kind=one.kind, path=at[0], line=at[1], quote=plain(one.quote)[:QUOTE_SHOWN_CHARS], note=plain(one.note)
        )
        for one in draft.statements
        if (at := pointed_at(one, texts)) is not None
    ]
    return kept, len(draft.statements) - len(kept)


def named(name: str) -> str:
    """A requirement's name as a revision matches it: its words, in one case."""
    return flat(name).casefold()


def kept_ids(deltas: Mapping[str, Delta]) -> dict[tuple[str, str], list[str]]:
    """The IDs a change has given its added requirements, by capability and name, in order: what a revision keeps."""
    kept: dict[tuple[str, str], list[str]] = {}
    for capability, delta in deltas.items():
        for req in delta.added:
            kept.setdefault((capability, named(req.name)), []).append(req.id)
    return kept


def _by_id(deltas: Mapping[str, Delta]) -> dict[str, Requirement | Removal]:
    """Every requirement a change's deltas add, modify or remove, by its ID."""
    return {req.id: req for delta in deltas.values() for req in (*delta.added, *delta.modified, *delta.removed)}


def revision(before: Mapping[str, Delta], after: Mapping[str, Delta]) -> tuple[list[str], list[str], list[str]]:
    """What a revision did to a change's requirements, by ID: added, changed and dropped, each in order."""
    old, new = _by_id(before), _by_id(after)
    changed = sorted(req_id for req_id in old.keys() & new.keys() if old[req_id] != new[req_id])
    return sorted(new.keys() - old.keys()), changed, sorted(old.keys() - new.keys())
