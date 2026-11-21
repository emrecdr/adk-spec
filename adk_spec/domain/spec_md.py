"""The living spec as Markdown: rendered in one canonical form, parsed strictly, fingerprinted a requirement at a time.

The grammar: line 1 is `# <capability>`; then `## Purpose`, `## Requirements` and, optionally, `## Retired`, in that
order. A requirement starts at `### <ID>: <name>` and its statement runs to its first scenario. A scenario starts at
`#### Scenario: <name>` and holds steps alone. A line inside a code fence is never a heading; outside one, a heading
the grammar does not name is refused. The parser refuses only what is off the grammar: whether a requirement is a
good one is the validator's to say.
"""

from __future__ import annotations

import re

from .model import GrammarError, Requirement, Retired, Scenario, Spec
from .text import lines_of, normalise, sha256_of

FENCE = "```"
SECTIONS = ("## Purpose", "## Requirements", "## Retired")
_TITLE = re.compile(r"# (\S.*)")
_HEADING = re.compile(r"#{1,6} ")
_REQUIREMENT = re.compile(r"### (REQ-\S+): (\S.*)")
_SCENARIO = re.compile(r"#### Scenario: (\S.*)")
_STEP = re.compile(r"- (?:\*\*)?(GIVEN|WHEN|THEN|AND)(?:\*\*)? (\S.*)", re.IGNORECASE)
_RETIRED = re.compile(r"- (REQ-\S+): (\S.*) \(removed by ([^()]+)\)")


def fenced_lines(lines: list[str]) -> list[bool]:
    """For each line, whether it stands inside a code fence or is one of its two marker lines."""
    inside, held = False, []
    for line in lines:
        marker = line.startswith(FENCE)
        held.append(inside or marker)
        if marker:
            inside = not inside
    return held


def is_heading(lines: list[str], fenced: list[bool], at: int) -> bool:
    return not fenced[at] and _HEADING.match(lines[at]) is not None


def paragraphs(lines: list[str], fenced: list[bool], first: int, last: int) -> str:
    """The text of `lines[first:last]`: blank lines at its ends dropped, and a run of blank lines outside a fence
    held to one."""
    kept: list[str] = []
    for at in range(first, last):
        blank = not lines[at] and not fenced[at]
        if blank and (not kept or not kept[-1]):
            continue
        kept.append(lines[at])
    while kept and not kept[-1]:
        kept.pop()
    return "\n".join(kept)


def title_of(lines: list[str], pattern: re.Pattern[str], expected: str) -> tuple[int, str]:
    """The line index of the title, the first line that is not blank, and what `pattern` reads in it."""
    for at, line in enumerate(lines):
        if not line:
            continue
        if found := pattern.fullmatch(line):
            return at, found[1].strip()
        raise GrammarError(at + 1, f"the first line must be the title, `{expected}`")
    raise GrammarError(1, f"the file is empty: its first line must be the title, `{expected}`")


def sections_of(
    lines: list[str], fenced: list[bool], after: int, known: tuple[str, ...], what: str
) -> dict[str, tuple[int, int]]:
    """Each level-two section after line index `after`, as the range of line indexes under its heading. The sections
    must be among `known` and in that order; text before the first one is refused."""
    found: dict[str, tuple[int, int]] = {}
    order: list[tuple[str, int]] = []
    for at in range(after + 1, len(lines)):
        if fenced[at] or not lines[at].startswith("## "):
            if not order and lines[at] and not fenced[at]:
                raise GrammarError(at + 1, f"text stands before the first section of {what}")
            continue
        name = lines[at]
        if name not in known:
            raise GrammarError(at + 1, f"`{name}` is no section of {what}: its sections are {', '.join(known)}")
        if order and known.index(name) <= known.index(order[-1][0]):
            raise GrammarError(at + 1, f"`{name}` is out of order: the sections of {what} run {', '.join(known)}")
        order.append((name, at))
    for place, (name, at) in enumerate(order):
        end = order[place + 1][1] if place + 1 < len(order) else len(lines)
        found[name] = (at + 1, end)
    return found


def parse_blocks(lines: list[str], first: int, last: int) -> tuple[Requirement, ...]:
    """The requirement blocks in `lines[first:last]`, for a spec's requirements and a delta's added and modified."""
    fenced = fenced_lines(lines)
    starts = [at for at in range(first, last) if is_heading(lines, fenced, at) and lines[at].startswith("### ")]
    for at in range(first, starts[0] if starts else last):
        if lines[at]:
            raise GrammarError(at + 1, "a requirement starts `### REQ-<CAPABILITY>-<NNN>: <name>`")
    blocks = []
    for place, start in enumerate(starts):
        end = starts[place + 1] if place + 1 < len(starts) else last
        blocks.append(_block(lines, fenced, start, end))
    return tuple(blocks)


def _block(lines: list[str], fenced: list[bool], start: int, end: int) -> Requirement:
    header = _REQUIREMENT.fullmatch(lines[start])
    if header is None:
        raise GrammarError(start + 1, "a requirement starts `### REQ-<CAPABILITY>-<NNN>: <name>`")
    marks: list[tuple[int, str]] = []
    for at in range(start + 1, end):
        if not is_heading(lines, fenced, at):
            continue
        named = _SCENARIO.fullmatch(lines[at])
        if named is None:
            raise GrammarError(
                at + 1, f"`{lines[at]}` is no heading of a requirement: a scenario starts `#### Scenario: <name>`"
            )
        marks.append((at, named[1].strip()))
    statement = paragraphs(lines, fenced, start + 1, marks[0][0] if marks else end)
    scenarios = []
    for place, (mark, name) in enumerate(marks):
        stop = marks[place + 1][0] if place + 1 < len(marks) else end
        scenarios.append(Scenario(name=name, steps=_steps(lines, mark, stop)))
    return Requirement(id=header[1], name=header[2].strip(), statement=statement, scenarios=tuple(scenarios))


def _steps(lines: list[str], mark: int, stop: int) -> tuple[str, ...]:
    steps = []
    for at in range(mark + 1, stop):
        if not lines[at]:
            continue
        step = _STEP.fullmatch(lines[at])
        if step is None:
            raise GrammarError(
                at + 1, "under a scenario every line is a step: `- GIVEN ...`, `- WHEN ...`, `- THEN ...`, `- AND ...`"
            )
        steps.append(f"{step[1].upper()} {step[2].strip()}")
    return tuple(steps)


def parse_spec(text: str) -> Spec:
    """The spec `text` holds. `GrammarError`, with its line, where the text is off the grammar."""
    lines = lines_of(normalise(text))
    fenced = fenced_lines(lines)
    top, capability = title_of(lines, _TITLE, "# <capability>")
    found = sections_of(lines, fenced, top, SECTIONS, "a spec")
    for needed in SECTIONS[:2]:
        if needed not in found:
            raise GrammarError(len(lines) or 1, f"a spec needs the section `{needed}`")
    first, last = found["## Purpose"]
    for at in range(first, last):
        if is_heading(lines, fenced, at):
            raise GrammarError(at + 1, f"`{lines[at]}` is a heading inside the purpose, which holds text alone")
    retired = []
    for at in range(*found.get("## Retired", (0, 0))):
        if not lines[at]:
            continue
        entry = _RETIRED.fullmatch(lines[at])
        if entry is None:
            raise GrammarError(at + 1, "a retired entry reads `- <ID>: <name> (removed by <change>)`")
        retired.append(Retired(id=entry[1], name=entry[2].strip(), change=entry[3].strip()))
    return Spec(
        capability=capability,
        purpose=paragraphs(lines, fenced, first, last),
        requirements=parse_blocks(lines, *found["## Requirements"]),
        retired=tuple(retired),
    )


def render_requirement(req: Requirement) -> str:
    """One requirement in its canonical form: what its fingerprint is taken of."""
    chunks = [f"### {req.id}: {req.name}"]
    if req.statement:
        chunks.append(req.statement)
    for scenario in req.scenarios:
        chunks.append(f"#### Scenario: {scenario.name}")
        if scenario.steps:
            chunks.append("\n".join(f"- {step}" for step in scenario.steps))
    return "\n\n".join(chunks) + "\n"


def render_spec(spec: Spec) -> str:
    """The spec in its canonical form: what is written to disk and read in a pull request."""
    chunks = [f"# {spec.capability}", "## Purpose"]
    if spec.purpose:
        chunks.append(spec.purpose)
    chunks.append("## Requirements")
    chunks += [render_requirement(req).rstrip("\n") for req in spec.requirements]
    if spec.retired:
        chunks.append("## Retired")
        chunks.append("\n".join(f"- {gone.id}: {gone.name} (removed by {gone.change})" for gone in spec.retired))
    return "\n\n".join(chunks) + "\n"


def fingerprint(req: Requirement) -> str:
    """The fingerprint of one requirement: of its canonical block alone, so the same on every system and unmoved by
    an edit elsewhere in the spec."""
    return sha256_of(render_requirement(req))
