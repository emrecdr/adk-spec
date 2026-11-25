"""`reports/summary.md`: a change as a reviewer of its pull request reads it, in Markdown to paste there: why, the
requirements it adds, modifies and removes, each verdict, the tests, and who approved."""

from __future__ import annotations

from .changelog_md import changed_lines
from .model import Change, ChangeState


def render_summary(change: Change, state: ChangeState) -> str:
    """The summary of `change` as `state` records it: the verdicts and tests of its last verification, the reason a
    person gave for verifying it over them, where one did, and its approval."""
    done, approval = state.verification, state.approval
    verdicts, tests = (done.verdicts, done.tests) if done else ({}, {})
    brief = change.brief
    lines = [f"# {brief.title if brief else change.state.id}", ""]
    if brief and brief.why.strip():
        lines += [brief.why.strip(), ""]
    lines += ["## Requirements", "", *(changed_lines(change.deltas) or ["- None."]), ""]
    lines += ["## Verification", ""]
    lines += [f"- {req_id}: {said}" for req_id, said in sorted(verdicts.items())]
    lines += [f"- Tests{'' if name == '.' else f' of {name}'}: {outcome}" for name, outcome in sorted(tests.items())]
    if done and done.override:
        lines += [f"- Verified by override: {done.override}"]
    if approval is not None:
        second = f" and {approval.second.by}" if approval.second else ""
        lines += ["", f"Approved by {approval.by}{second}."]
    lines += ["", f"Change `{change.state.id}`, {change.state.tier} tier, specified with adk-spec."]
    return "\n".join(lines) + "\n"
