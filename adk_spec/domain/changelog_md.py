"""`.spec/changelog.md`: an entry for each archived change, newest first, naming each requirement it added,
modified and removed. adk-spec adds an entry under the heading and leaves everything below it as it stands, so a
person may write in it."""

from __future__ import annotations

from collections.abc import Mapping

from .model import Delta

HEADING = "# Changelog"


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
    """The changelog `text` with `entry` first under its heading; a changelog where there is none."""
    text = text or ""
    body = text.removeprefix(HEADING).lstrip("\n") if text.startswith(HEADING) else text
    return f"{HEADING}\n\n{entry}" + (f"\n{body}" if body.strip() else "")
