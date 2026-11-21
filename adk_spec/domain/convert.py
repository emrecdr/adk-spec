"""A model's drafts turned into the domain's types.

What a model may not decide is decided here: a new requirement's ID, a task's number, a change's slug. What a model
writes loosely is made canonical here: a step's keyword, stray spaces, a purpose given for a capability that exists.
Nothing is checked: the validator judges what comes out, and a gate asks the model again.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping

from .drafts import BriefDraft, DeltasDraft, DesignDraft, FindingsDraft, RequirementDraft, TasksDraft
from .ids import SLUG_MAX, next_requirement_id, slug_problem
from .model import Brief, Delta, Finding, GrammarError, Removal, Requirement, Scenario, Severity, Spec, Task, TaskGroup
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
    one given counts as held; a purpose is kept only for a capability that is not there yet. A requirement given as
    modified that says what the living spec says is left out: a model restating a spec copies its neighbours."""
    held = set(taken)
    slots: dict[str, dict] = {}
    for one in draft.deltas:
        capability = one.capability.strip()
        slot = slots.setdefault(capability, {"purpose": None, "added": [], "modified": [], "removed": []})
        if capability not in living:
            slot["purpose"] = slot["purpose"] or _text(one.purpose) or None
        stands = {req.id: req for req in living[capability].requirements} if capability in living else {}
        for added in one.added:
            req_id = next_requirement_id(capability, held)
            held.add(req_id)
            slot["added"].append(_requirement(req_id, added))
        restated = [_requirement(changed.id.strip(), changed.requirement) for changed in one.modified]
        slot["modified"] += [req for req in restated if stands.get(req.id) != req]
        slot["removed"] += [
            Removal(id=gone, name=stands[gone].name if gone in stands else "", reason=_line(removed.reason))
            for removed in one.removed
            for gone in [removed.id.strip()]
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


#: A quote shorter than this, once its spaces are settled, points at nothing: `the` is in every file.
QUOTE_MIN_CHARS = 8
_SEVERITY: dict[str, Severity] = {"critical": "ERROR", "warning": "WARNING", "note": "INFO"}


def flat(text: str) -> str:
    """`text` with every run of whitespace read as one space: how a quote is compared with the text it is from, so a
    line break or an indent a model changed does not lose it."""
    return " ".join(text.split())


def quoted_at(quote: str, text: str) -> int | None:
    """The line of `text`, counted from 1, where `quote` starts, or nothing where `text` does not hold it. A quote
    may run over lines; one too short to point at anything is in no text."""
    wanted = flat(quote)
    if len(wanted) < QUOTE_MIN_CHARS:
        return None
    starts: list[tuple[int, int]] = []  # where each line that holds a word starts in the flat text, and its number
    pieces: list[str] = []
    offset = 0
    for number, line in enumerate(lines_of(normalise(text)), 1):
        if piece := flat(line):
            starts.append((offset, number))
            pieces.append(piece)
            offset += len(piece) + 1
    at = " ".join(pieces).find(wanted)
    if at < 0:
        return None
    return max(number for start, number in starts if start <= at)


def to_findings(draft: FindingsDraft, texts: Mapping[str, str]) -> tuple[list[Finding], int]:
    """The findings a model gave that point at something: each kept only where the file it names is one of `texts`
    and holds the text it quotes. With them, how many were left out. A model's finding that quotes nothing real is
    no finding, whatever it says."""
    kept: list[Finding] = []
    for one in draft.findings:
        path = one.file.strip()
        line = quoted_at(one.quote, texts[path]) if path in texts else None
        if line is None:
            continue
        kept.append(
            Finding(
                severity=_SEVERITY[one.severity],
                code=f"check.{one.kind}",
                message=_line(one.message),
                path=path,
                line=line,
            )
        )
    return kept, len(draft.findings) - len(kept)
