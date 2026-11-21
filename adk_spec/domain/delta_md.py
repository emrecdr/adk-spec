"""A delta as Markdown: what one change does to one capability's spec, keyed by requirement ID.

The grammar: line 1 is `# Delta: <capability>`; then, each optional and in this order, `## Purpose` (for a
capability the change creates), `## ADDED Requirements`, `## MODIFIED Requirements`, `## REMOVED Requirements`.
ADDED and MODIFIED hold whole requirement blocks. A REMOVED block is its header and one line, `Reason: <why>`.
There is no RENAMED section: the ID is the key, so a rename is a MODIFIED block with the new name.
"""

from __future__ import annotations

import re

from .model import Delta, GrammarError, Removal
from .spec_md import fenced_lines, is_heading, paragraphs, parse_blocks, render_requirement, sections_of, title_of
from .text import lines_of, normalise

PURPOSE, ADDED, MODIFIED, REMOVED = (
    "## Purpose",
    "## ADDED Requirements",
    "## MODIFIED Requirements",
    "## REMOVED Requirements",
)
SECTIONS = (PURPOSE, ADDED, MODIFIED, REMOVED)
_TITLE = re.compile(r"# Delta: (\S.*)")
_REMOVED = re.compile(r"### (REQ-\S+): (\S.*)")
_REASON = "Reason:"


def parse_delta(text: str) -> Delta:
    """The delta `text` holds. `GrammarError`, with its line, where the text is off the grammar."""
    lines = lines_of(normalise(text))
    fenced = fenced_lines(lines)
    top, capability = title_of(lines, _TITLE, "# Delta: <capability>")
    for at, line in enumerate(lines):
        if line == "## RENAMED Requirements" and not fenced[at]:
            raise GrammarError(
                at + 1, "a delta has no RENAMED section: a rename is a MODIFIED block with the new name, under its ID"
            )
    found = sections_of(lines, fenced, top, SECTIONS, "a delta")
    purpose = None
    if PURPOSE in found:
        first, last = found[PURPOSE]
        for at in range(first, last):
            if is_heading(lines, fenced, at):
                raise GrammarError(at + 1, f"`{lines[at]}` is a heading inside the purpose, which holds text alone")
        purpose = paragraphs(lines, fenced, first, last)
    return Delta(
        capability=capability,
        purpose=purpose,
        added=parse_blocks(lines, *found[ADDED]) if ADDED in found else (),
        modified=parse_blocks(lines, *found[MODIFIED]) if MODIFIED in found else (),
        removed=_removals(lines, fenced, *found[REMOVED]) if REMOVED in found else (),
    )


def _removals(lines: list[str], fenced: list[bool], first: int, last: int) -> tuple[Removal, ...]:
    removals: list[Removal] = []
    header: re.Match[str] | None = None
    reason: list[str] = []

    def close() -> None:
        if header is not None:
            removals.append(Removal(id=header[1], name=header[2].strip(), reason=" ".join(reason)))

    for at in range(first, last):
        line = lines[at]
        if is_heading(lines, fenced, at):
            close()
            header, reason = _REMOVED.fullmatch(line), []
            if header is None:
                raise GrammarError(at + 1, "a removed requirement starts `### REQ-<CAPABILITY>-<NNN>: <name>`")
        elif not line:
            continue
        elif header is None:
            raise GrammarError(at + 1, "a removed requirement starts `### REQ-<CAPABILITY>-<NNN>: <name>`")
        elif not reason and not line.startswith(_REASON):
            raise GrammarError(at + 1, f"under a removed requirement write one line, `{_REASON} <why>`")
        else:
            reason.append(line.removeprefix(_REASON).strip() if not reason else line.strip())
    close()
    return tuple(removals)


def render_delta(delta: Delta) -> str:
    """The delta in its canonical form: only the sections that hold something."""
    chunks = [f"# Delta: {delta.capability}"]
    if delta.purpose is not None:
        chunks += [PURPOSE, *([delta.purpose] if delta.purpose else [])]
    for heading, blocks in ((ADDED, delta.added), (MODIFIED, delta.modified)):
        if blocks:
            chunks += [heading, *(render_requirement(req).rstrip("\n") for req in blocks)]
    if delta.removed:
        chunks.append(REMOVED)
        for gone in delta.removed:
            chunks.append(f"### {gone.id}: {gone.name}")
            if gone.reason:
                chunks.append(f"{_REASON} {gone.reason}")
    return "\n\n".join(chunks) + "\n"
