"""A change's brief as Markdown: why, what changes, what does not, which capabilities, the impact, the assumptions.

The grammar: line 1 is `# <title>`; then the six sections of `SECTIONS`, in that order, each `## <name>`. A missing
section parses as empty, for the validator to judge; one the grammar does not name is refused. `Capabilities` is a
list of `- <slug>` lines. A point the author could not settle is marked `[NEEDS CLARIFICATION: <question>]`.
"""

from __future__ import annotations

import re

from .model import Brief, GrammarError
from .spec_md import fenced_lines, paragraphs, sections_of, title_of
from .text import flat, lines_of, normalise, plain

SECTIONS = ("Why", "What changes", "Non-goals", "Capabilities", "Impact", "Assumptions")
#: A point left open for a person to settle, with or without its question, which is the pattern's one group.
MARKER = re.compile(r"\[\s*NEEDS\s+CLARIFICATION\s*(?::([^\]]*))?\]", re.IGNORECASE)
#: How every marker begins. One that begins so and is no marker was left unclosed, holds no colon before its
#: question, or stands inside the question of another.
_OPENER = re.compile(r"\[\s*NEEDS\s+CLARIFICATION", re.IGNORECASE)
#: How many markers a brief may hold: past it, the request is not ready to be specified.
MARKER_BUDGET = 3
_TITLE = re.compile(r"# (\S.*)")
_ITEM = re.compile(r"- (\S.*)")
_HEADINGS = tuple(f"## {name}" for name in SECTIONS)
_CAPABILITIES = "## Capabilities"
_FIELDS = {
    "## Why": "why",
    "## What changes": "what_changes",
    "## Non-goals": "non_goals",
    "## Impact": "impact",
    "## Assumptions": "assumptions",
}


def markers(text: str) -> list[str]:
    """Every clarification marker in `text`, in order."""
    return [found[0] for found in MARKER.finditer(text)]


def malformed(text: str) -> int:
    """How often `text` begins a marker that is none. Such a line is counted as no open point, or runs on to the
    next `]` and takes what stands between into its question."""
    return len(_OPENER.findall(text)) - len(MARKER.findall(text))


def asked_in(text: str) -> list[str]:
    """The question of each marker in `text`, in order, on one line: nothing for a marker that holds none."""
    return [flat(found[1] or "") for found in MARKER.finditer(text)]


def worded(question: str) -> str:
    """An open point's question as a marker can hold it, and as `asked_in` reads it back: plain text on one line,
    with no bracket in it that would end the marker early."""
    return plain(question).replace("[", "(").replace("]", ")")


def marker_of(question: str) -> str:
    """The marker a brief's file holds for an open point."""
    return f"[NEEDS CLARIFICATION: {worded(question)}]"


def assumption_count(text: str) -> int:
    """How many assumptions a brief's Assumptions section states: its sentences, its open points' markers aside. Found
    live, phase 15: on gpt-4.1 a standard brief assumed where it might have asked, and the owner chose to have
    `propose` say how many there are to check before approving."""
    for marker in markers(text):
        text = text.replace(marker, "")
    lines = [line.strip() for line in text.strip().split("\n") if line.strip()]
    # Found by an outside audit: a list's items without full stops were one, a numbered list counted its numbers as
    # sentences, and "None." was one.
    if len(lines) == 1 and _NO_ASSUMPTION.fullmatch(lines[0]):
        return 0
    if items := [line for line in lines if _LIST_ITEM.match(line)]:
        return len(items)
    return len([one for one in re.split(r"(?<=[.!?])\s+", text.strip()) if one.strip()])


#: A line that says there is no assumption; and one that opens an item of a list, bulleted or numbered.
_NO_ASSUMPTION = re.compile(r"(?i)(?:none|n/?a|no assumptions?)\.?")
_LIST_ITEM = re.compile(r"(?:[-*]|\d+[.)])\s")


def parse_brief(text: str) -> Brief:
    """The brief `text` holds. `GrammarError`, with its line, where the text is off the grammar."""
    lines = lines_of(normalise(text))
    fenced = fenced_lines(lines)
    top, title = title_of(lines, _TITLE, "# <title>")
    found = sections_of(lines, fenced, top, _HEADINGS, "a brief")
    capabilities = []
    for at in range(*found.get(_CAPABILITIES, (0, 0))):
        if not lines[at]:
            continue
        item = _ITEM.fullmatch(lines[at])
        if item is None:
            raise GrammarError(at + 1, "under Capabilities each line names one capability, `- <slug>`")
        capabilities.append(item[1].strip())
    held = {field: paragraphs(lines, fenced, *found.get(heading, (0, 0))) for heading, field in _FIELDS.items()}
    return Brief(title=title, capabilities=tuple(capabilities), **held)


def render_brief(brief: Brief) -> str:
    """The brief in its canonical form: every section, in order."""
    chunks = [f"# {brief.title}"]
    for heading in _HEADINGS:
        chunks.append(heading)
        if heading == _CAPABILITIES:
            body = "\n".join(f"- {capability}" for capability in brief.capabilities)
        else:
            body = getattr(brief, _FIELDS[heading])
        if body:
            chunks.append(body)
    return "\n\n".join(chunks) + "\n"
