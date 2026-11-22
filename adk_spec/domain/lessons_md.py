"""The lessons file, `.spec/lessons.md`: what every draft in a workspace follows.

A person writes, edits and deletes its lines. adk-spec adds one under its gate heading, in code, for each problem a
drafting gate sent back that the next try put right: by its stage and its code, with the first sentence it was sent
back with as its example, and counts it when it comes back. Only a line in that shape under that heading is
adk-spec's to count; every other line is the person's, and its words are never changed. The file is written as
every file adk-spec writes is: with LF line ends, and no trailing space on a line.

A problem a gate sends back is `coded`: its code, then its sentence. The validator's findings have the same shape, and
a problem without one, an answer off its schema or a marker repeated, is the engine's, and no lesson.
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from .secrets import scrub
from .text import lines_of, plain

GATE_HEADING = "## Sent back by a gate"
_PREAMBLE = """\
What every draft in this workspace follows: each stage that writes a brief, a delta, a design or tasks reads this
file. Write a correction you made to a draft here, in one line, under "From people". adk-spec adds a line under
"Sent back by a gate" each time a gate sent a draft back and the next try put it right, and counts it when it comes
back. Edit or delete any line.
"""
TEMPLATE = f"# Lessons\n\n{_PREAMBLE}\n## From people\n\n{GATE_HEADING}\n"
#: How long the example sentence of a lesson may be.
EXAMPLE_MAX_CHARS = 200
_CODE = r"[a-z]+\.[a-z][a-z-]*"
_PROBLEM = re.compile(rf"(?P<code>{_CODE}): (?P<sentence>.+)", re.DOTALL)
_LESSON = re.compile(rf"- (?P<stage>[a-z]+), `(?P<code>{_CODE})` \((?P<count>\d+)\): (?P<example>.*)")
_HEADING = re.compile(r"#{1,6} ")


def coded(code: str, sentence: str) -> str:
    """A problem as a gate sends it back: its code, then its sentence."""
    return f"{code}: {sentence}"


def learned(text: str, sent_back: Iterable[Iterable[str]]) -> str:
    """`text`, the lessons file as it stands, with each of `sent_back` noted under the gate heading: a stage, and a
    problem its gate sent back that the next try fixed: one run's. A lesson seen before for that stage is counted
    once more, once a run however often the run was sent back for it; a new one is added, its first sentence the
    example. Where nothing is learned, `text` comes back as it was."""
    found: dict[tuple[str, str], str] = {}
    for stage, problem in sent_back:
        if held := _PROBLEM.fullmatch(problem.strip()):
            found.setdefault((stage, held["code"]), held["sentence"])
    if not found:
        return text
    lines = lines_of(text)
    for (stage, code), sentence in found.items():
        _note(lines, stage, code, _example(sentence))
    return "\n".join(lines) + "\n"


def as_read(text: str) -> str:
    """The lessons file as a drafting stage is given it: its lessons under their headings, without what is written
    for a person, the template's opening, a section with nothing in it and a lesson's count. Nothing where it holds
    no lesson."""
    blocks: list[list[str]] = [[]]
    for line in lines_of(text.replace(_PREAMBLE, "")):
        if _HEADING.match(line):
            blocks.append([line])
        else:
            held = _LESSON.fullmatch(line)
            blocks[-1].append(f"- {held['stage']}, `{held['code']}`: {held['example']}" if held else line)
    kept = [block for block in blocks if any(line.strip() for line in block if not _HEADING.match(line))]
    return "\n".join("\n".join(block).strip() for block in kept).strip()


def _note(lines: list[str], stage: str, code: str, example: str) -> None:
    """One lesson noted in `lines`: counted where its section holds it, added at the section's end where not."""
    if GATE_HEADING not in lines:  # the person took it out, or renamed it: it is added again, at the end
        lines += [*([""] if lines and lines[-1].strip() else []), GATE_HEADING]
    start = lines.index(GATE_HEADING) + 1
    end = next((at for at in range(start, len(lines)) if lines[at].startswith("## ")), len(lines))
    for at in range(start, end):
        if (held := _LESSON.fullmatch(lines[at])) and (held["stage"], held["code"]) == (stage, code):
            lines[at] = _line(stage, code, int(held["count"]) + 1, held["example"])
            return
    last = end
    while last > start and not lines[last - 1].strip():  # before the blank lines that end the section
        last -= 1
    lines[last:last] = [*([""] if last == start else []), _line(stage, code, 1, example)]


def _line(stage: str, code: str, count: int, example: str) -> str:
    return f"- {stage}, `{code}` ({count}): {example}"


def _example(sentence: str) -> str:
    """A problem's sentence as a lesson's example: on one line, plain, scrubbed of secret shapes, and cut."""
    text, _count = scrub(plain(sentence))
    return text if len(text) <= EXAMPLE_MAX_CHARS else text[: EXAMPLE_MAX_CHARS - 1].rstrip() + "…"
