"""A change's brief as Markdown: why, what changes, what does not, which capabilities, the impact, the assumptions.

The grammar: line 1 is `# <title>`; then the six sections of `SECTIONS`, in that order, each `## <name>`. A missing
section parses as empty, for the validator to judge; one the grammar does not name is refused. `Capabilities` is a
list of `- <slug>` lines. A point the author could not settle is marked `[NEEDS CLARIFICATION: <question>]`.
"""

from __future__ import annotations

import re

from .model import Brief, GrammarError
from .spec_md import fenced_lines, paragraphs, sections_of, title_of
from .text import lines_of, normalise

SECTIONS = ("Why", "What changes", "Non-goals", "Capabilities", "Impact", "Assumptions")
#: A point left open for a person to settle, with or without its question.
MARKER = re.compile(r"\[\s*NEEDS\s+CLARIFICATION\s*(?::[^\]]*)?\]", re.IGNORECASE)
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
    return MARKER.findall(text)


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
