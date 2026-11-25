"""`.spec/changelog.md`: an entry for each archived change, newest first, naming each requirement it added,
modified and removed. adk-spec adds each entry above the first one already there, and leaves every other line as it
stands, an introduction under the heading too, so a person may write in it."""

from __future__ import annotations

import re
from collections.abc import Mapping

from .model import Delta
from .spec_md import fenced_lines

HEADING = "# Changelog"
#: An entry's heading, as `changelog_entry` writes it, and a note a person adds after it: a `## ` heading of their
#: introduction is none, nor a line in one of its code blocks.
_ENTRY = re.compile(r"## \S+, \d{4}-\d{2}-\d{2}")


def changed_lines(deltas: Mapping[str, Delta]) -> list[str]:
    """One line for each requirement `deltas` add, modify and remove, in that order, by capability."""
    lines: list[str] = []
    for kind, of in (("Added", "added"), ("Modified", "modified"), ("Removed", "removed")):
        for capability, delta in sorted(deltas.items()):
            lines += [f"- {kind} {req.id}: {req.name} ({capability})" for req in getattr(delta, of)]
    return lines


def changelog_entry(change_id: str, day: str, deltas: Mapping[str, Delta]) -> str:
    """The entry of `change_id`, archived on `day`."""
    return "\n".join([f"## {change_id}, {day}", "", *(changed_lines(deltas) or ["- No requirement changed."])]) + "\n"


def with_entry(text: str | None, entry: str) -> str:
    """The changelog `text` with `entry` above its first entry, below any introduction; a changelog where there is
    none."""
    lines = (text or "").lstrip("\n").split("\n")
    body = lines[1:] if lines[0].rstrip() == HEADING else lines  # a heading of theirs is kept, as their text
    fenced = fenced_lines(body, strict=False)
    first = next((at for at, line in enumerate(body) if not fenced[at] and _ENTRY.match(line)), len(body))
    parts = (HEADING, "\n".join(body[:first]), entry, "\n".join(body[first:]))
    return "\n\n".join(filter(None, (part.strip("\n") for part in parts))) + "\n"
