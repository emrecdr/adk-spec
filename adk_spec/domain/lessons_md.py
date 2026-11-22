"""The lessons file, `.spec/lessons.md`: what every draft in a workspace follows.

A person writes, edits and deletes its lines. adk-spec adds one under its gate heading, in code, for each problem a
drafting gate sent back that the next try put right: by its stage and its code, with the first sentence it was sent
back with as its example, and counts it when it comes back. Only a line in that shape under that heading is
adk-spec's to count; every other line is the person's and is never changed.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from .secrets import scrub
from .text import flat

GATE_HEADING = "## Sent back by a gate"
TEMPLATE = f"""\
# Lessons

What every draft in this workspace follows: each stage that writes a brief, a delta, a design or tasks reads this
file. Write a correction you made to a draft here, in one line, under "From people". adk-spec adds a line under
"Sent back by a gate" each time a gate sent a draft back and the next try put it right, and counts it when it comes
back. Edit or delete any line.

## From people

{GATE_HEADING}
"""
#: How long the example sentence of a lesson may be.
EXAMPLE_MAX_CHARS = 200
_PROBLEM = re.compile(r"(?P<code>[a-z]+\.[a-z][a-z-]*): (?P<sentence>.+)", re.DOTALL)
_LESSON = re.compile(r"- (?P<stage>[a-z]+), `(?P<code>[a-z]+\.[a-z][a-z-]*)` \((?P<count>\d+)\): (?P<example>.*)")


def learned(text: str, sent_back: Iterable[tuple[str, str]]) -> str:
    """`text`, the lessons file as it stands, with each of `sent_back` noted under the gate heading: a stage, and a
    problem its gate sent back that the next try fixed. One seen before for that stage is counted once more; a new
    one is added, its sentence the example. A problem with no code is the engine's, and no lesson. Where nothing is
    learned, `text` comes back as it was."""
    lines = text.splitlines()
    for stage, problem in sent_back:
        if found := _PROBLEM.fullmatch(problem.strip()):
            lines = _noted(lines, stage, found["code"], _example(found["sentence"]))
    return text if lines == text.splitlines() else "\n".join(lines) + "\n"


def _noted(lines: list[str], stage: str, code: str, example: str) -> list[str]:
    """`lines` with one lesson noted: counted where its section holds it, added at the section's end where not."""
    if GATE_HEADING not in lines:  # the person took it out, or renamed it: it is added again, at the end
        lines = [*lines, *([""] if lines and lines[-1].strip() else []), GATE_HEADING]
    start = lines.index(GATE_HEADING) + 1
    end = next((at for at in range(start, len(lines)) if lines[at].startswith("## ")), len(lines))
    for at in range(start, end):
        if (held := _LESSON.fullmatch(lines[at])) and (held["stage"], held["code"]) == (stage, code):
            counted = f"- {stage}, `{code}` ({int(held['count']) + 1}): {held['example']}"
            return [*lines[:at], counted, *lines[at + 1 :]]
    last = end
    while last > start and not lines[last - 1].strip():  # before the blank lines that end the section
        last -= 1
    new = [*([""] if last == start else []), f"- {stage}, `{code}` (1): {example}"]
    return [*lines[:last], *new, *lines[last:]]


def _example(sentence: str) -> str:
    """A problem's sentence as a lesson's example: on one line, scrubbed of secret shapes, and cut."""
    text, _count = scrub(flat(sentence))
    return text if len(text) <= EXAMPLE_MAX_CHARS else text[: EXAMPLE_MAX_CHARS - 1].rstrip() + "…"
