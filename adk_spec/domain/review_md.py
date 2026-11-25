"""`reports/review.md`: what a change does to each requirement it touches, as its approver reads it. A requirement it
adds is shown whole, one it removes with its reason and as the living spec holds it, one it modifies as a diff of the
living requirement against the delta's; and each the change modifies or removes that another open change modifies or
removes too is named, so the approver learns it now, not at the second archive."""

from __future__ import annotations

import difflib
from collections.abc import Mapping, Sequence

from .model import Delta, Requirement, Spec
from .spec_md import render_requirement
from .text import longest_backticks

#: How many overlaps the line a command prints names; the view names every one.
SAID = 3


def render_review(
    change_id: str,
    deltas: Mapping[str, Delta],
    living: Mapping[str, Spec],
    overlaps: Mapping[str, Sequence[str]],
) -> str:
    """The view of `change_id`, from its `deltas`, the `living` specs they change, and `overlaps`: each requirement
    ID to the other open changes that modify or remove it too."""
    lines = [f"# Review: {change_id}", ""]
    for capability, delta in sorted(deltas.items()):
        held = {req.id: req for req in living[capability].requirements} if capability in living else {}
        lines += [f"## {capability}", ""]
        if capability not in living and delta.purpose:  # the new living spec opens on it
            lines += ["### Purpose", "", *_fenced("markdown", delta.purpose.split("\n"))]
        if delta.added:
            lines += ["### Added", ""]
            for req in delta.added:
                lines += _whole(req)
        if delta.modified:
            lines += ["### Modified", ""]
            for req in delta.modified:
                lines += _changed(held.get(req.id), req, change_id)
        if delta.removed:
            lines += ["### Removed", ""]
            for gone in delta.removed:  # as the living spec holds it: found by a review, an edit to it went unseen
                lines += [f"- {gone.id}: {gone.name}. {gone.reason}", ""]
                lines += _whole(held[gone.id]) if gone.id in held else []
    if overlaps:
        lines += ["## Also changed by open changes", ""]
        lines += [f"- {req_id}: {', '.join(others)}" for req_id, others in sorted(overlaps.items())] + [""]
    return "\n".join(lines).rstrip("\n") + "\n"


def review_said(deltas: Mapping[str, Delta], overlaps: Mapping[str, Sequence[str]]) -> str:
    """What a command says of the view on its one line: how many requirements each kind of change holds, and the
    first overlaps."""
    counts = {
        kind: sum(len(getattr(delta, kind)) for delta in deltas.values()) for kind in ("added", "modified", "removed")
    }
    said = ", ".join(f"{count} {kind}" for kind, count in counts.items() if count) or "no requirement"
    named = [f"{req_id} also changed by {', '.join(others)}" for req_id, others in sorted(overlaps.items())]
    if named:
        more = f", and {len(named) - SAID} more" if len(named) > SAID else ""
        said += "; " + "; ".join(named[:SAID]) + more
    return said


def _fenced(kind: str, lines: list[str]) -> list[str]:
    """`lines` in a code fence longer than any run of backticks they hold, so a fence inside a statement, or a diff
    line of one, cannot close it."""
    fence = "`" * max(3, longest_backticks("\n".join(lines)) + 1)
    return [fence + kind, *lines, fence, ""]


def _whole(req: Requirement) -> list[str]:
    return _fenced("markdown", render_requirement(req).rstrip("\n").split("\n"))


def _changed(before: Requirement | None, after: Requirement, change_id: str) -> list[str]:
    """A modified requirement as a diff of the living one against the delta's; whole where no living spec holds it."""
    if before is None:
        return [f"{after.id} is in no living spec now: shown as the change has it.", "", *_whole(after)]
    old, new = render_requirement(before).splitlines(), render_requirement(after).splitlines()
    if old == new:
        return [f"{after.id} is unchanged from the living spec.", ""]
    diff = difflib.unified_diff(old, new, fromfile="living", tofile=change_id, lineterm="")
    return _fenced("diff", list(diff))
