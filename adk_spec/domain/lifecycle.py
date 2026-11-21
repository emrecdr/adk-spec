"""The lifecycle's rules, as functions of a change's state: what a base is, what an approval records and what voids
it, what blocks approval and archive, and what a person does next.

An approval is a recorded fact, not a conversation: who, when, the fingerprint of each approved file and the bases
the deltas were approved against. Any later edit to one of those files voids it, except ticking a task's box: the
task list is fingerprinted with every box empty.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from .model import Approval, ChangeState, Checked, Delta, Finding, GrammarError, Spec, Verification
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
    state: ChangeState,
    *,
    files: Mapping[str, str],
    by: str,
    at: str,
    override: str | None = None,
    commit: str | None = None,
) -> ChangeState:
    """The state with the approval recorded: who, when, each file's fingerprint and the bases as they stand, and
    the reason where the approver set a blocking finding of the check aside. `commit` is what is checked out now:
    it is kept as where the work began only where none is kept yet, so approving again does not move it."""
    approval = Approval(by=by, at=at, files=dict(files), bases=dict(state.bases), override=override)
    began = state.base_commit or commit
    return state.model_copy(update={"status": "approved", "approval": approval, "base_commit": began})


def checked(
    state: ChangeState, findings: Sequence[Finding], *, files: Mapping[str, str], at: str, model: str | None = None
) -> ChangeState:
    """The state with a check recorded: the fingerprints of the files it read, how many of its findings block an
    approval, and the model that judged, none where code alone did."""
    blocking = sum(found.severity == "ERROR" for found in findings)
    return state.model_copy(update={"check": Checked(at=at, files=dict(files), blocking=blocking, model=model)})


def verified(
    state: ChangeState,
    verdicts: Mapping[str, str],
    *,
    base: str,
    diff: str,
    at: str,
    model: str | None = None,
    override: str | None = None,
) -> ChangeState:
    """The state with a verification recorded. The change is `verified` where every requirement's verdict is `met`,
    or a person says so with a reason, which is kept only where it was needed. Otherwise it is `approved`, also
    where it was verified before: the newest judgement is the one that stands."""
    met = all(verdict == "met" for verdict in verdicts.values())
    reason = None if met else (override or None)
    held = Verification(at=at, base=base, diff=diff, verdicts=dict(verdicts), override=reason, model=model)
    status = "verified" if met or reason else "approved"
    return state.model_copy(update={"verification": held, "status": status})


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


def approve_blockers(
    state: ChangeState,
    findings: Sequence[Finding],
    *,
    strict: bool = False,
    check: Sequence[Finding] = (),
    override: bool = False,
) -> list[Finding]:
    """What blocks an approval: every ERROR, every finding of `BLOCKS_APPROVAL`, under `strict` every WARNING, and
    what the change's check still owes, which is `check`, as `check_blockers` gives it. With `override`, a blocking
    finding of a current check is set aside, and nothing else: a check never run, or run on other files, is still
    owed. An archived change is approved no more."""
    if state.status == "archived":
        return [Finding(severity="ERROR", code="change.archived", message=f"`{state.id}` is archived already.")]
    held = [
        found
        for found in findings
        if found.severity == "ERROR" or found.code in BLOCKS_APPROVAL or (strict and found.severity == "WARNING")
    ]
    return held + [owed for owed in check if not (override and owed.code == "check.blocking")]


def _unready(state: ChangeState, stale: Sequence[str]) -> list[str]:
    """Why work on a change's approved files cannot go on, a sentence; empty where it can: it is archived, it is
    not approved, or its approval no longer covers its files."""
    cid = state.id
    if state.status == "archived":
        return [f"`{cid}` is archived already"]
    if state.approval is None or state.status == "draft":
        return [f"`{cid}` is not approved: run `adk-spec approve {cid}`"]
    if stale:
        return [
            f"the approval of `{cid}` is void: {', '.join(stale)} changed since. Run `adk-spec approve {cid}` again"
        ]
    return []


def verify_blockers(state: ChangeState, stale: Sequence[str]) -> list[str]:
    """Why a change's work cannot be verified yet, a sentence; empty where it can."""
    return _unready(state, stale)


def archive_blockers(state: ChangeState, stale: Sequence[str]) -> list[str]:
    """Why a change cannot be archived yet, a sentence each; empty where it can. A lean change is archived once
    approved; a standard or strict one once verified."""
    if unready := _unready(state, stale):
        return unready
    if state.tier != "lean" and state.status != "verified":
        cid = state.id
        return [f"`{cid}` is a {state.tier} change and is not verified: run `adk-spec verify {cid}` first"]
    return []


Actor = Literal["you", "run", "done"]


@dataclass(frozen=True)
class Step:
    """What happens next with a change, and who makes it happen: `you` where it takes a person's work or decision,
    `run` where it is one command, `done` where nothing is left."""

    actor: Actor
    phrase: str


#: What stands for "a finding of the change is an ERROR" among the codes below.
_ERROR = "an ERROR"
#: What holds a draft, the first that applies first: the code of what holds it, who acts on it, and the phrase, in
#: which `{cid}` is the change. An ERROR comes before everything, since the files it is in will change; an open
#: point before the plan, since its answer shapes the tasks; the plan before the base, and the base before the
#: check, which reads what the two leave.
_HOLDS: tuple[tuple[str, Actor, str], ...] = (
    (_ERROR, "you", "fix what `adk-spec validate {cid}` lists"),
    ("brief.marker-unresolved", "you", "settle the open point in brief.md"),
    ("change.missing-tasks", "run", "run `adk-spec plan {cid}`"),
    ("delta.base-missing", "run", "run `adk-spec rebase {cid}`"),
    ("check.blocking", "you", "fix what reports/check.md lists, then run `adk-spec check {cid}`"),
    ("check.missing", "run", "run `adk-spec check {cid}`"),
    ("check.stale", "run", "run `adk-spec check {cid}`"),
)


def next_step(
    state: ChangeState, findings: Sequence[Finding], stale: Sequence[str], *, check: Sequence[Finding] = ()
) -> Step:
    """What happens next with a change, and who makes it happen. `check` is what `check_blockers` gives for it."""
    cid = state.id
    if state.status == "archived":
        return Step("done", "nothing: archived")
    errors = any(found.severity == "ERROR" for found in findings)
    if state.status in ("approved", "verified"):
        if stale:  # the edit that voided the approval made a check of the old files stale as well
            first = f"run `adk-spec check {cid}`, then " if check else ""
            return Step("you", f"{first}approve again: {', '.join(stale)} changed since the approval")
        if errors:  # a base that moved, a spec that no longer reads
            return Step("you", f"fix what `adk-spec validate {cid}` lists")
        if state.status == "verified":
            return Step("run", f"run `adk-spec archive {cid}`")
        last = "archive" if state.tier == "lean" else "verify"
        return Step("you", f"implement tasks.md, then run `adk-spec {last} {cid}`")
    held = {found.code for found in (*findings, *check)} | ({_ERROR} if errors else set())
    for code, actor, phrase in _HOLDS:
        if code in held:
            return Step(actor, phrase.format(cid=cid))
    if approve_blockers(state, findings, check=check):  # what blocks an approval and has no step of its own
        return Step("you", f"fix what `adk-spec validate {cid}` lists")
    return Step("you", f"run `adk-spec approve {cid}`")


def next_action(
    state: ChangeState, findings: Sequence[Finding], stale: Sequence[str], *, check: Sequence[Finding] = ()
) -> str:
    """What a person does next with a change, in one phrase."""
    return next_step(state, findings, stale, check=check).phrase
