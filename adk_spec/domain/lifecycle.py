"""The lifecycle's rules, as functions of a change's state: what a base is, what an approval records and what voids
it, what blocks approval and archive, and what a person does next.

An approval is a recorded fact, not a conversation: who, when, the fingerprint of each approved file and the bases
the deltas were approved against. Any later edit to one of those files voids it, except ticking a task's box: the
task list is fingerprinted with every box empty.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from .model import PASSED, Approval, ChangeState, Checked, Delta, Finding, GrammarError, Seconded, Spec, Verification
from .spec_md import fingerprint
from .tasks_md import parse_tasks, render_tasks
from .text import sha256_of

#: Findings that block an approval whatever their severity: an open point, or no plan. A base that is missing does
#: not: an approval records it, since it is a function of the delta and the living spec as they stand.
BLOCKS_APPROVAL = frozenset({"brief.marker-unresolved", "change.missing-tasks"})
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


def missing_bases(state: ChangeState, deltas: Mapping[str, Delta], living: Mapping[str, Spec]) -> dict[str, str]:
    """The base of each requirement a delta modifies or removes that has none recorded, as the living spec holds
    it now. A base that is recorded is never among them, whether it still holds or not: one that moved is the
    guard against two changes to one requirement, and a person must read what the requirement says now."""
    return {req: held for req, held in capture_bases(deltas, living).items() if req not in state.bases}


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


def awaiting_second(state: ChangeState, files: Mapping[str, str]) -> bool:
    """Whether a strict change holds the first of its two approvals, and it still covers `files` and the bases: the
    next approval, by another name, approves the change. An edit since voids it, as any approval."""
    return state.tier == "strict" and state.status == "draft" and not approval_stale(state, files)


def owes_design(tier: str, said: bool = False) -> bool:
    """Whether a change owes a design before its tasks: where its brief `said` so, and always on the strict tier."""
    return said or tier == "strict"


def edited_drafts(state: ChangeState, files: Mapping[str, str]) -> list[str]:
    """Each file of `files`, fingerprints by path, that adk-spec drafted and a person changed since: a correction
    later drafts could follow. Ticking a box is no change, as an approval takes it."""
    return sorted(name for name, mark in files.items() if state.drafted.get(name, mark) != mark)


def reopened(state: ChangeState, **update: Any) -> ChangeState:
    """`state` a draft again, with `update`, and its approval void: a command wrote its files anew, a rebase or a
    revision, and what was approved is no longer what it says. It is approved again."""
    return state.model_copy(update={**update, "status": "draft", "approval": None})


def approve(
    state: ChangeState,
    *,
    files: Mapping[str, str],
    by: str,
    at: str,
    override: str | None = None,
    commit: str | None = None,
    others: Mapping[str, str] | None = None,
) -> ChangeState:
    """The state with the approval recorded: who, when, each file's fingerprint and the bases as they stand, and
    the reason where the approver set a blocking finding of the check aside. `commit` is what is checked out now,
    and `others` what is checked out in each other repository of the change: each is kept as where the work began
    only where none is kept yet, so approving again does not move it."""
    approval = Approval(by=by, at=at, files=dict(files), bases=dict(state.bases), override=override)
    # A draft a person corrected is named once: the approved fingerprint then stands for what was drafted.
    drafted = {name: files.get(name, mark) for name, mark in state.drafted.items()}
    if state.tier == "strict":  # two names approve it: the first is recorded, and the change stays a draft
        first = state.approval if awaiting_second(state, files) else None
        if first is None:
            return state.model_copy(update={"approval": approval, "drafted": drafted})
        approval = first.model_copy(update={"second": Seconded(by=by, at=at)})
    began = state.base_commit or commit
    commits = {**(others or {}), **state.base_commits}
    update = {"status": "approved", "approval": approval, "base_commit": began, "base_commits": commits}
    update["drafted"] = drafted
    return state.model_copy(update=update)


def check_stands(state: ChangeState, files: Mapping[str, str]) -> bool:
    """Whether the change's last check was made by a model, of these same files. A check by code alone then adds
    nothing and must not replace it: it would count the code's findings alone, and a blocking finding of the
    model's would be gone with nothing fixed."""
    return state.check is not None and state.check.model is not None and state.check.files == dict(files)


def checked(
    state: ChangeState, findings: Sequence[Finding], *, files: Mapping[str, str], at: str, model: str | None = None
) -> ChangeState:
    """The state with a check recorded: the fingerprints of the files it read, how many of its findings block an
    approval, and the model that judged, none where code alone did. A check by code alone of files a model has
    judged records nothing: the model's check stands, with whatever it found."""
    if model is None and check_stands(state, files):
        return state
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
    bases: Mapping[str, str] | None = None,
    tests: Mapping[str, str] | None = None,
) -> ChangeState:
    """The state with a verification recorded. The change is `verified` where every requirement's verdict is `met`
    and every run of the project's tests passed, or a person says so with a reason, which is kept only where it was
    needed. Otherwise it is `approved`, also where it was verified before: the newest judgement is the one that
    stands."""
    ran = dict(tests or {})
    met = all(verdict == "met" for verdict in verdicts.values()) and all(one == PASSED for one in ran.values())
    reason = None if met else (override or None)
    held = Verification(
        at=at,
        base=base,
        diff=diff,
        verdicts=dict(verdicts),
        override=reason,
        model=model,
        bases=dict(bases or {}),
        tests=ran,
    )
    status = "verified" if met or reason else "approved"
    return state.model_copy(update={"verification": held, "status": status})


#: What a change's check can owe that an approval settles by itself: it makes the check where none is current.
_MADE_BY_APPROVAL = frozenset({"check.missing", "check.stale"})


def approval_checks_first(check: Sequence[Finding]) -> bool:
    """Whether an approval makes a change's check before it decides: `check` is what `check_blockers` gives, and
    the check is missing or stale. The one statement of that rule: the command asks it, and the next step follows
    it. A reason given with `--override` answers only a check a person was shown, so it is not applied where this
    is true: the check it would answer is made in the same run."""
    return any(owed.code in _MADE_BY_APPROVAL for owed in check)


def check_stops(check: Sequence[Finding], *, override: bool = False) -> list[Finding]:
    """What of a change's check stops its approval: all that `check_blockers` gives, less a blocking finding where
    a person set it aside with `override`. A check never made, or made of other files, is not a finding to set
    aside: an approval makes it first, as `approval_checks_first` says."""
    return [owed for owed in check if not (override and owed.code == "check.blocking")]


def check_blockers(state: ChangeState, files: Mapping[str, str]) -> list[Finding]:
    """What a change's check still owes its approval, as one finding or none. A lean change owes no check. Any
    other owes one of its files as they stand now (`files`, their fingerprints), with nothing blocking in it. A
    check that is missing or stale is a signal to the approval, which makes it and is read by its code: no command
    prints those two sentences. A blocking one is printed."""
    cid = state.id
    if state.tier == "lean":
        return []
    if state.check is None:
        why = ("check.missing", f"`{cid}` has not been checked: `adk-spec approve {cid}` checks it first.")
    elif state.check.files != dict(files):
        why = ("check.stale", f"A file of `{cid}` changed since its check: `adk-spec approve {cid}` checks it again.")
    elif state.check.blocking:
        why = (
            "check.blocking",
            f"The check of `{cid}` found {state.check.blocking} blocking: reports/check.md lists them. Fix them and "
            "approve again, or approve with --override and your reason.",
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
    """What of a change's own files blocks its approval: every ERROR, every finding of `BLOCKS_APPROVAL`, and under
    `strict` every WARNING. An archived change is approved no more. What its check stops is `check_stops`: the two
    are asked apart, since an approval settles the first before it spends a model call on the second."""
    if state.status == "archived":
        return [Finding(severity="ERROR", code="change.archived", message=f"`{state.id}` is archived already.")]
    return [
        found
        for found in findings
        if found.severity == "ERROR" or found.code in BLOCKS_APPROVAL or (strict and found.severity == "WARNING")
    ]


def _unready(state: ChangeState, stale: Sequence[str]) -> list[str]:
    """Why work on a change's approved files cannot go on, a sentence; empty where it can: it is archived, it is
    not approved, or its approval no longer covers its files."""
    cid = state.id
    if state.status == "archived":
        return [f"`{cid}` is archived already"]
    if state.status == "draft" and state.tier == "strict" and state.approval is not None and not stale:
        by = state.approval.by
        return [f"`{cid}` is approved once, by {by}: a strict change owes a second approval, by another name"]
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


def archive_blockers(state: ChangeState, stale: Sequence[str], *, drifted: bool = False) -> list[str]:
    """Why a change cannot be archived yet, a sentence each; empty where it can. A lean change is archived once
    approved; a standard or strict one once verified, and only while the work is what was verified: `drifted` says
    it has changed since."""
    if unready := _unready(state, stale):
        return unready
    cid = state.id
    if state.tier != "lean" and state.status != "verified":
        return [f"`{cid}` is a {state.tier} change and is not verified: run `adk-spec verify {cid}` first"]
    if state.tier != "lean" and drifted:
        return [f"the work changed since `{cid}` was verified: run `adk-spec verify {cid}` again"]
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
#: What a person does about a check that found something blocking, in which `{cid}` is the change.
_FIX_THE_CHECK = "fix what reports/check.md lists, then run `adk-spec approve {cid}`"
#: What holds a draft, the first that applies first: the code of what holds it, who acts on it, and the phrase, in
#: which `{cid}` is the change. An ERROR comes before everything, since the files it is in will change; an open
#: point before the plan, since its answer shapes the tasks; and the plan before the check, which reads it. A
#: check that is missing or stale holds nothing: the approval makes it.
_HOLDS: tuple[tuple[str, Actor, str], ...] = (
    ("change.missing-design", "run", "run `adk-spec plan {cid}`"),  # an error, which `plan` settles
    (_ERROR, "you", "fix what `adk-spec validate {cid}` lists"),
    ("brief.marker-unresolved", "you", "settle the open point in brief.md"),
    ("change.missing-tasks", "run", "run `adk-spec plan {cid}`"),
    ("check.blocking", "you", _FIX_THE_CHECK),
)


def _after_approval(
    state: ChangeState, errors: bool, stale: Sequence[str], check: Sequence[Finding], drifted: bool
) -> Step:
    """The next step of a change that was approved: approved again where its files changed since, and then the
    work, its verification and its archive."""
    cid = state.id
    if stale and any(owed.code == "check.blocking" for owed in check):
        # The approval was asked again, made the check of the edited files, and was stopped by what it found.
        return Step("you", _FIX_THE_CHECK.format(cid=cid))
    if stale:  # the edit that voided the approval made a check stale as well, which the approval makes again
        return Step("you", f"approve again: {', '.join(stale)} changed since the approval")
    if errors:  # a base that moved, a spec that no longer reads
        return Step("you", f"fix what `adk-spec validate {cid}` lists")
    if state.status == "verified" and drifted and state.tier != "lean":
        return Step("run", f"run `adk-spec verify {cid}` again: the work changed since it was verified")
    if state.status == "verified":
        return Step("run", f"run `adk-spec archive {cid}`")
    if state.verification and not state.verification.tests_passed:
        return Step("you", f'the tests failed: fix them and run `adk-spec verify {cid}`, or verify --override "<why>"')
    last = "archive" if state.tier == "lean" else "verify"
    return Step("you", f"implement tasks.md, then run `adk-spec {last} {cid}`")


def next_step(
    state: ChangeState,
    findings: Sequence[Finding],
    stale: Sequence[str],
    *,
    check: Sequence[Finding] = (),
    drifted: bool = False,
) -> Step:
    """What happens next with a change, and who makes it happen. `check` is what `check_blockers` gives for it, and
    `drifted` whether the work changed since it was verified."""
    cid = state.id
    if state.status == "archived":
        return Step("done", "nothing: archived")
    errors = any(found.severity == "ERROR" for found in findings)
    if state.status in ("approved", "verified"):
        return _after_approval(state, errors, stale, check, drifted)
    held = {found.code for found in (*findings, *check)} | ({_ERROR} if errors else set())
    for code, actor, phrase in _HOLDS:
        if code in held:
            return Step(actor, phrase.format(cid=cid))
    # What blocks an approval and has no step of its own. A check the approval makes itself is no such thing.
    left = [owed for owed in check if owed.code not in _MADE_BY_APPROVAL]
    if approve_blockers(state, findings) or check_stops(left):
        return Step("you", f"fix what `adk-spec validate {cid}` lists")
    if state.tier == "strict" and state.approval is not None and not stale:  # the first of two approvals is given
        return Step("you", f"have someone other than {state.approval.by} run `adk-spec approve {cid}`")
    return Step("you", f"run `adk-spec approve {cid}`")


def next_action(
    state: ChangeState, findings: Sequence[Finding], stale: Sequence[str], *, check: Sequence[Finding] = ()
) -> str:
    """What a person does next with a change, in one phrase."""
    return next_step(state, findings, stale, check=check).phrase
