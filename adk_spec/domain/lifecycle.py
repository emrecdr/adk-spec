"""The lifecycle's rules, as functions of a change's state: what a base is, what an approval records and what voids
it, what blocks approval and archive, and what a person does next.

An approval is a recorded fact, not a conversation: who, when, the fingerprint of each approved file and the bases
the deltas were approved against. Any later edit to one of those files voids it, except ticking a task's box: the
task list is fingerprinted with every box empty.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from .model import Approval, ChangeState, Delta, Finding, GrammarError, Spec
from .spec_md import fingerprint
from .tasks_md import parse_tasks, render_tasks
from .text import sha256_of

#: Findings that block an approval whatever their severity: an open point, no plan, or a delta with no recorded base.
BLOCKS_APPROVAL = frozenset({"brief.marker-unresolved", "change.missing-tasks", "delta.base-missing"})
TASKS_FILE = "tasks.md"


def capture_bases(deltas: Mapping[str, Delta], living: Mapping[str, Spec]) -> dict[str, str]:
    """For every requirement a delta modifies or removes that the living spec holds: its fingerprint there now."""
    held: dict[str, str] = {}
    for capability, delta in deltas.items():
        spec = living.get(capability)
        now = {req.id: req for req in spec.requirements} if spec else {}
        for target in (*delta.modified, *delta.removed):
            if target.id in now:
                held[target.id] = fingerprint(now[target.id])
    return held


def _as_approved(path: str, text: str) -> str:
    """The text an approval is taken of: a task list with every box empty, every other file as it stands."""
    if path != TASKS_FILE:
        return text
    try:
        return render_tasks(parse_tasks(text), unchecked=True)
    except GrammarError:  # off its grammar: fingerprinted as it stands, and the validator names the fault
        return text


def approval_files(texts: Mapping[str, str]) -> dict[str, str]:
    """The fingerprint of each file an approval covers, by its path in the change's folder."""
    return {path: sha256_of(_as_approved(path, text)) for path, text in texts.items()}


def approve(
    state: ChangeState, *, files: Mapping[str, str], by: str, at: str, override: str | None = None
) -> ChangeState:
    """The state with the approval recorded: who, when, each file's fingerprint and the bases as they stand, and
    the reason where the approver set a blocking finding of the check aside."""
    approval = Approval(by=by, at=at, files=dict(files), bases=dict(state.bases), override=override)
    return state.model_copy(update={"status": "approved", "approval": approval})


def check_blockers(state: ChangeState, files: Mapping[str, str]) -> list[Finding]:
    """What a change's check still owes its approval, as one finding or none. A lean change owes no check. Any
    other owes one of its files as they stand now (`files`, their fingerprints), with nothing blocking in it."""
    cid = state.id
    if state.tier == "lean":
        return []
    if state.check is None:
        why = ("check.missing", f"`{cid}` has not been checked. Run `adk-spec check {cid}`.")
    elif state.check.files != dict(files):
        why = ("check.stale", f"A file of `{cid}` changed since its check. Run `adk-spec check {cid}` again.")
    elif state.check.blocking:
        why = (
            "check.blocking",
            f"The check of `{cid}` found {state.check.blocking} blocking: reports/check.md lists them. Fix them and "
            "check again, or approve with --override and your reason.",
        )
    else:
        return []
    return [Finding(severity="ERROR", code=why[0], message=why[1], path="reports/check.md")]


def approval_stale(state: ChangeState, files: Mapping[str, str]) -> list[str]:
    """What an approval no longer covers: `approval` where none is recorded; else each file added, removed or
    changed since, and `bases` where they were recorded anew. Empty where the approval stands."""
    if state.approval is None:
        return ["approval"]
    was = state.approval.files
    moved = sorted(path for path in {*was, *files} if was.get(path) != files.get(path))
    return moved + (["bases"] if state.bases != state.approval.bases else [])


def approve_blockers(state: ChangeState, findings: Sequence[Finding], *, strict: bool = False) -> list[Finding]:
    """The findings that block an approval: every ERROR, every finding of `BLOCKS_APPROVAL`, and under `strict`
    every WARNING. An archived change is approved no more."""
    if state.status == "archived":
        return [Finding(severity="ERROR", code="change.archived", message=f"`{state.id}` is archived already.")]
    return [
        found
        for found in findings
        if found.severity == "ERROR" or found.code in BLOCKS_APPROVAL or (strict and found.severity == "WARNING")
    ]


def archive_blockers(state: ChangeState, stale: Sequence[str]) -> list[str]:
    """Why a change cannot be archived yet, a sentence each; empty where it can. A lean change is archived once
    approved; a standard or strict one once verified."""
    cid = state.id
    if state.status == "archived":
        return [f"`{cid}` is archived already"]
    if state.approval is None or state.status == "draft":
        return [f"`{cid}` is not approved: run `adk-spec approve {cid}`"]
    if stale:
        return [
            f"the approval of `{cid}` is void: {', '.join(stale)} changed since. Run `adk-spec approve {cid}` again"
        ]
    if state.tier != "lean" and state.status != "verified":
        return [f"`{cid}` is a {state.tier} change and is not verified: run `adk-spec verify {cid}` first"]
    return []


def next_action(
    state: ChangeState, findings: Sequence[Finding], stale: Sequence[str], *, check: Sequence[Finding] = ()
) -> str:
    """What a person does next with a change, in one phrase. `check` is what `check_blockers` gives for it."""
    cid = state.id
    if state.status == "archived":
        return "nothing: archived"
    if state.status in ("approved", "verified"):
        if stale:
            return f"approve again: {', '.join(stale)} changed since the approval"
        if any(found.severity == "ERROR" for found in findings):  # a base that moved, a spec that no longer reads
            return f"fix what `adk-spec validate {cid}` lists"
        if state.status == "verified" or state.tier == "lean":
            step = "run" if state.status == "verified" else "implement tasks.md, then run"
            return f"{step} `adk-spec archive {cid}`"
        return f"implement tasks.md, then run `adk-spec verify {cid}`"
    return _next_of_a_draft(state, findings, check)


def _next_of_a_draft(state: ChangeState, findings: Sequence[Finding], check: Sequence[Finding]) -> str:
    cid = state.id
    blockers = approve_blockers(state, findings)
    errors = any(found.severity == "ERROR" for found in findings)
    codes = {found.code for found in blockers}
    if not errors and "change.missing-tasks" in codes and codes <= {"change.missing-tasks", "delta.base-missing"}:
        return f"run `adk-spec plan {cid}`"
    if not errors and any(found.code == "delta.base-missing" for found in blockers):
        return f"run `adk-spec rebase {cid}`"
    if blockers:
        return f"fix what `adk-spec validate {cid}` lists"
    if any(owed.code == "check.blocking" for owed in check):
        return f"fix what reports/check.md lists, then run `adk-spec check {cid}`"
    if check:
        return f"run `adk-spec check {cid}`"
    return f"run `adk-spec approve {cid}`"
