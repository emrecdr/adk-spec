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
from .validate import UNREAD, finding

#: Findings that block an approval whatever their severity: an open point, or no plan. A base that is missing does
#: not: an approval records it, since it is a function of the delta and the living spec as they stand.
BLOCKS_APPROVAL = frozenset({"brief.marker-unresolved", "change.missing-tasks", "change.missing-design"})
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


def kept_bases(held: Mapping[str, str], deltas: Mapping[str, Delta], living: Mapping[str, Spec]) -> dict[str, str]:
    """The bases of a change revised: each requirement its deltas still modify or remove keeps the base recorded
    for it in `held`, whether it still holds or not, as `missing_bases` says; one newly aimed at is recorded as the
    living spec holds it now. Found by the fourth audit: a revision recorded every base afresh."""
    return {req: held.get(req, now) for req, now in capture_bases(deltas, living).items()}


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


@dataclass(frozen=True)
class Demands:
    """What a tier asks of a change: the one place each rule of a tier is written."""

    #: A brief's open points are put to the person as questions; on lean, the brief states what it assumes.
    asks: bool
    #: A check is owed before the approval, and a verification before the archive.
    checked: bool
    verified: bool
    #: A design is owed, whatever the brief says.
    design: bool
    #: `propose` writes the brief and the specs and stops, for a person to read them before the plan.
    read_first: bool
    #: How many different names approve it.
    approvers: int
    #: A warning blocks its approval as an error does, and a blocking finding of its check may not be set aside.
    warnings_block: bool
    override: bool

    @property
    def closing(self) -> str:
        """The command a change's work ends on: `verify` where a verification is owed, `archive` where none is."""
        return "verify" if self.verified else "archive"


DEMANDS: Mapping[str, Demands] = {
    "lean": Demands(False, False, False, False, False, 1, False, True),
    "standard": Demands(True, True, True, False, False, 1, False, True),
    "strict": Demands(True, True, True, True, True, 2, True, False),
}


def first_of_two(state: ChangeState, stale: Sequence[str]) -> Approval | None:
    """The first approval of a change two names approve, where it is given and still covers the files and the
    bases: the next, by another name, approves the change. None where there is none, or an edit voided it."""
    if DEMANDS[state.tier].approvers < 2 or state.status != "draft" or stale:
        return None
    return state.approval


def approver_blockers(state: ChangeState, stale: Sequence[str], by: str) -> list[str]:
    """Why `by` cannot approve a change two names approve, a sentence; empty where they can: they gave its first
    approval, or two names approved it already and nothing changed since. One name is one person, whatever its case."""
    if (first := first_of_two(state, stale)) and same_name(first.by, by):
        return [f"`{state.id}` is approved once already, by {first.by}: another name approves it next"]
    if (held := _approved_by_two(state, stale)) and held.second:
        return [f"`{state.id}` is approved already, by {held.by} and {held.second.by}, and nothing changed since"]
    return []


def same_name(one: str, other: str) -> bool:
    """Whether two approvers' names are one person's: compared without case and the spaces around them."""
    return one.strip().casefold() == other.strip().casefold()


def _approved_by_two(state: ChangeState, stale: Sequence[str]) -> Approval | None:
    """The approval two names gave a change, where it still covers its files: approving again changes nothing."""
    held = state.approval
    approved = state.status in ("approved", "verified") and not stale
    return held if approved and held is not None and held.second is not None else None


def owes_design(tier: str, said: bool = False) -> bool:
    """Whether a change owes a design before its tasks: where its brief `said` so, and always where its tier does."""
    return said or DEMANDS[tier].design


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
    stale = approval_stale(state, files)
    # A verification stands for the files it was made of: found by the code review, one of an earlier version was
    # still read for the unmet step, and its evidence folded, after the change was revised and approved again.
    kept = {"drafted": drafted, "verification": None if stale else state.verification}
    if DEMANDS[state.tier].approvers > 1:  # the first of two names is recorded, and the change is a draft
        if _approved_by_two(state, stale):  # approved already, and as it stands: nothing to record
            return state
        first = first_of_two(state, stale)
        if first is None or same_name(first.by, by):
            return state.model_copy(update={"status": "draft", "approval": approval, **kept})
        approval = first.model_copy(update={"second": Seconded(by=by, at=at)})
    began = state.base_commit or commit
    commits = {**(others or {}), **state.base_commits}
    update = {"status": "approved", "approval": approval, "base_commit": began, "base_commits": commits, **kept}
    return state.model_copy(update=update)


def check_stands(state: ChangeState, files: Mapping[str, str]) -> bool:
    """Whether the change's last check was made by a model, of these same files. A check by code alone then adds
    nothing and must not replace it: it would count the code's findings alone, and a blocking finding of the
    model's would be gone with nothing fixed."""
    return state.check is not None and state.check.model is not None and state.check.files == dict(files)


def model_holds(state: ChangeState, files: Mapping[str, str]) -> bool:
    """Whether a check by code alone leaves the change's last check as it is: a model's that stands, or, on a tier
    that owes a check, a model's that found something blocking, files edited since or not. Found by the fourth
    audit: after any edit, a check by code alone replaced the model's, and the approval went through with its
    blocking finding never fixed, on the strict tier too. Only a model clears what a model found."""
    held = state.check
    if held is None or held.model is None:
        return False
    # The model's own count alone: one an older adk-spec recorded held the code's findings too, and is not known.
    return check_stands(state, files) or (DEMANDS[state.tier].checked and bool(held.model_blocking))


def checked(
    state: ChangeState,
    findings: Sequence[Finding],
    *,
    files: Mapping[str, str],
    at: str,
    model: str | None = None,
    judged: Sequence[Finding] = (),
) -> ChangeState:
    """The state with a check recorded: the fingerprints of the files it read, how many of `findings` block an
    approval, the model that judged, none where code alone did, and of a model's check how many of the blocking
    findings are the model's own, `judged`: what holds a check by code alone back, by `model_holds`. A check by code
    alone records nothing over a model's that `model_holds` keeps."""
    if model is None and model_holds(state, files):
        return state
    own = len(blocking(state, judged)) if model is not None else None
    held = Checked(at=at, files=dict(files), blocking=len(blocking(state, findings)), model=model, model_blocking=own)
    return state.model_copy(update={"check": held})


def blocking(state: ChangeState, findings: Sequence[Finding]) -> list[Finding]:
    """The findings of a change's check that block its approval: every ERROR, and every WARNING on a tier whose
    warnings block."""
    stops = {"ERROR", "WARNING"} if DEMANDS[state.tier].warnings_block else {"ERROR"}
    return [found for found in findings if found.severity in stops]


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
    is true: the check it would answer is made in the same run, or, where a model's cannot be, the one shown before."""
    return any(owed.code in _MADE_BY_APPROVAL for owed in check)


def check_stops(check: Sequence[Finding], *, override: bool = False) -> list[Finding]:
    """What of a change's check stops its approval: all that `check_blockers` gives, less a blocking finding where
    a person set it aside with `override`. A check never made, or made of other files, is not a finding to set
    aside: an approval makes it first, as `approval_checks_first` says, and only where a model's check that found
    something blocking cannot be made again does a reason set that aside, said where the check is made."""
    return [owed for owed in check if not (override and owed.code == "check.blocking")]


def check_blockers(state: ChangeState, files: Mapping[str, str]) -> list[Finding]:
    """What a change's check still owes its approval, as one finding or none. A lean change owes no check. Any
    other owes one of its files as they stand now (`files`, their fingerprints), with nothing blocking in it. A
    check that is missing or stale is a signal to the approval, which makes it and is read by its code: no command
    prints those two sentences. A blocking one is printed."""
    cid = state.id
    if not DEMANDS[state.tier].checked:
        return []
    if state.check is None:
        why = ("check.missing", f"`{cid}` has not been checked: `adk-spec approve {cid}` checks it first.")
    elif state.check.files != dict(files):
        why = ("check.stale", f"A file of `{cid}` changed since its check: `adk-spec approve {cid}` checks it again.")
    elif state.check.blocking:
        why = (
            "check.blocking",
            f"The check of `{cid}` found {state.check.blocking} blocking: reports/check.md lists them. Fix them and "
            f"approve again{', or approve with --override and your reason' if DEMANDS[state.tier].override else ''}.",
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
        if found.severity == "ERROR"
        or found.code in BLOCKS_APPROVAL
        or ((strict or DEMANDS[state.tier].warnings_block) and found.severity == "WARNING")
    ]


def _unready(state: ChangeState, stale: Sequence[str]) -> list[str]:
    """Why work on a change's approved files cannot go on, a sentence; empty where it can: it is archived, it is
    not approved, or its approval no longer covers its files."""
    cid = state.id
    if state.status == "archived":
        return [f"`{cid}` is archived already"]
    if first := first_of_two(state, stale):
        return [f"`{cid}` is approved once, by {first.by}: it owes a second approval, by another name"]
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
    verified = DEMANDS[state.tier].verified
    if verified and state.status != "verified":
        return [f"`{cid}` is a {state.tier} change and is not verified: run `adk-spec verify {cid}` first"]
    if verified and drifted:
        return [_DRIFTED.format(cid=cid)]
    return []


_DRIFTED = "the work changed since `{cid}` was verified: run `adk-spec verify {cid}` again"
_UNCOMPARED = (
    "The work of `{cid}`: it could not be compared with what was verified: a shallow clone, a repository not there, "
    "or git or the config refused"
)


def merge_gate(state: ChangeState, stale: Sequence[str], drift: bool | None, *, record: str) -> list[Finding]:
    """What a merge gate reads of a change beyond its own findings, each path in the change's folder: an approval its
    files no longer match, and, where the tier owes a verification, work changed since it was verified (`drift`), or
    that could not be compared with it (None). `record` names the change's state file. Never among the change's own
    findings: there, `approve` would weigh a void approval's warning as blocking on the strict tier, and refuse the
    approval that is its one remedy."""
    found = []
    if stale and state.status in ("approved", "verified"):
        moved = [path for path in stale if path not in ("approval", "bases")]
        void = _unready(state, stale)
        found += [finding("change.approval-void", said, path=moved[0] if moved else record) for said in void]
    if DEMANDS[state.tier].verified and state.status == "verified" and drift is not False:
        code, said = ("change.drift-unknown", _UNCOMPARED) if drift is None else ("change.work-drifted", _DRIFTED)
        found.append(finding(code, said.format(cid=state.id), path=record))
    return found


Actor = Literal["you", "run", "done"]


@dataclass(frozen=True)
class Step:
    """What happens next with a change, and who makes it happen: `you` where it takes a person's work or decision,
    `run` where it is one command, `done` where nothing is left."""

    actor: Actor
    phrase: str


#: What stands among the codes below for "a finding of the change is an ERROR `plan` does not settle", and for "a
#: finding `plan` settles".
_ERROR = "an ERROR"
_PLAN = "what plan settles"
#: What `plan` drafts where a change owes it and has none.
_OWED_BY_PLAN = frozenset({"change.missing-tasks", "change.missing-design"})
#: The errors of a task list that no longer matches the requirements, which drafting it again settles.
_UNMATCHED = frozenset({"check.requirement-no-task", "check.task-unknown-requirement"})


def settled_by_plan(found: Finding, *, started: bool = False) -> bool:
    """Whether `plan` is the step that settles a finding: a task list or a design owed and missing, or a task list
    that no longer matches the requirements while none of its tasks is ticked. An error a person made in the list,
    or a list whose work has begun, is fixed by hand: drafting it again would throw their work away."""
    return found.code in _OWED_BY_PLAN or (found.code in _UNMATCHED and not started)


def plan_blockers(findings: Sequence[Finding]) -> list[Finding]:
    """The errors that stop a plan being drafted now: every ERROR but one about what `plan` writes, the task list,
    which it drafts again, or a design owed and missing. A list that was not read is no list a plan may draft over:
    its ticked boxes are unknown. One rule for `plan` and for the plan `propose` goes on to."""
    return [found for found in findings if found.severity == "ERROR" and not _of_the_plan(found)]


def _of_the_plan(found: Finding) -> bool:
    named = (found.path or "").rsplit("/", 1)[-1]
    return found.code != UNREAD and (found.code in _OWED_BY_PLAN or named == TASKS_FILE)


#: What a person does about a check that found something blocking, in which `{cid}` is the change.
_FIX_THE_CHECK = "fix what reports/check.md lists, then run `adk-spec approve {cid}`"
#: What a person does about what the files themselves block.
_FIX_THE_FILES = "fix what `adk-spec validate {cid}` lists"
#: What holds a draft, the first that applies first: the code of what holds it, who acts on it, and the phrase, in
#: which `{cid}` is the change. An ERROR comes before everything, since the files it is in will change; an open
#: point before the plan, since its answer shapes the design and the tasks; and the plan before the check, which
#: reads it. A check that is missing or stale holds nothing: the approval makes it.
_HOLDS: tuple[tuple[str, Actor, str], ...] = (
    (_ERROR, "you", _FIX_THE_FILES),
    ("brief.marker-unresolved", "you", "settle the open point in brief.md, then {after}"),
    (_PLAN, "run", "run `adk-spec plan {cid}`"),
    ("check.blocking", "you", _FIX_THE_CHECK),
)
#: Where an open point stands among the holds: what may hold a draft once it is settled are the holds after it.
_POINT = [code for code, _actor, _phrase in _HOLDS].index("brief.marker-unresolved")
#: The holds of a tier whose change is read before it is planned: the plan is then the person's step. Found by the
#: fourth audit: the stop before a strict change's plan was listed as ready to run.
_READ_FIRST: tuple[str, Actor, str] = (_PLAN, "you", "read brief.md and the specs, then run `adk-spec plan {cid}`")
_HOLDS_READ_FIRST = tuple(_READ_FIRST if hold[0] == _PLAN else hold for hold in _HOLDS)


def _after_approval(
    state: ChangeState, findings: Sequence[Finding], stale: Sequence[str], check: Sequence[Finding], drifted: bool
) -> Step:
    """The next step of a change that was approved: approved again where its files changed since, and then the
    work, its verification and its archive."""
    cid = state.id
    if stale and any(owed.code == "check.blocking" for owed in check):
        # The approval was asked again, made the check of the edited files, and was stopped by what it found.
        return Step("you", _FIX_THE_CHECK.format(cid=cid))
    if stale and approve_blockers(state, findings):  # found by the fourth audit: "approve again", refused, a loop
        return Step("you", f"{_FIX_THE_FILES.format(cid=cid)}, then run `adk-spec approve {cid}` again")
    if stale:  # the edit that voided the approval made a check stale as well, which the approval makes again
        return Step("you", f"{', '.join(stale)} changed since the approval: run `adk-spec approve {cid}` again")
    if any(found.severity == "ERROR" for found in findings):  # a base that moved, a spec that no longer reads
        return Step("you", _FIX_THE_FILES.format(cid=cid))
    if state.status == "verified" and drifted and DEMANDS[state.tier].verified:
        return Step("run", f"run `adk-spec verify {cid}` again: the work changed since it was verified")
    if state.status == "verified":
        return Step("run", f"run `adk-spec archive {cid}`")
    if state.verification and not state.verification.tests_passed:
        why = f'`adk-spec verify {cid} --override "<why>"`'
        return Step("you", f"the tests failed: fix them and run `adk-spec verify {cid}`, or {why}")
    if unmet := _unmet(state):
        return unmet
    return Step("you", f"implement tasks.md, then run `adk-spec {DEMANDS[state.tier].closing} {cid}`")


#: How many unmet requirements the next step names; `reports/remaining.md` holds every one.
UNMET_NAMED = 3


def _unmet(state: ChangeState) -> Step | None:
    """The step after a verification that did not show every requirement met: the work its report names. Found by
    the research on the tools compared: the step said "implement tasks.md" whatever the verdicts said."""
    held = state.verification
    if held is None or held.override:  # verified by override: its remaining list was removed (the code review)
        return None
    unmet = sorted(req_id for req_id, said in held.verdicts.items() if said != "met")
    if not unmet:
        return None
    more = len(unmet) - UNMET_NAMED
    named = ", ".join(unmet[:UNMET_NAMED]) + (f" and {more} more" if more > 0 else "")
    last = DEMANDS[state.tier].closing
    return Step("you", f"{named} unmet: work from reports/remaining.md, then run `adk-spec {last} {state.id}`")


def next_step(
    state: ChangeState,
    findings: Sequence[Finding],
    stale: Sequence[str],
    *,
    check: Sequence[Finding] = (),
    drifted: bool = False,
    started: bool = False,
) -> Step:
    """What happens next with a change, and who makes it happen. `check` is what `check_blockers` gives for it,
    `drifted` whether the work changed since it was verified, and `started` whether a task of it is ticked."""
    cid = state.id
    if state.status == "archived":
        return Step("done", "nothing: archived")
    if state.status in ("approved", "verified"):
        return _after_approval(state, findings, stale, check, drifted)
    # What `plan` settles holds a draft after an open point, whose answer the plan waits for, not before it.
    plan = [found for found in findings if settled_by_plan(found, started=started)]
    held = {found.code for found in (*findings, *check)} | ({_PLAN} if plan else set())
    held |= {_ERROR for found in findings if found.severity == "ERROR" and found not in plan}
    # Every next step names the command that comes after it, the hold after an open point included: found by the
    # third audit, three did not, and by the code review, "then approve" where a blocking check would refuse it.
    holds = _HOLDS_READ_FIRST if DEMANDS[state.tier].read_first else _HOLDS
    rest = [phrase for code, _actor, phrase in holds[_POINT + 1 :] if code in held]
    after = rest[0].format(cid=cid) if rest else f"run `adk-spec approve {cid}`"
    for code, actor, phrase in holds:
        if code in held:
            return Step(actor, phrase.format(cid=cid, after=after))
    # What blocks an approval and has no step of its own. A check the approval makes itself is no such thing.
    left = [owed for owed in check if owed.code not in _MADE_BY_APPROVAL]
    if approve_blockers(state, findings) or check_stops(left):
        return Step("you", _FIX_THE_FILES.format(cid=cid))
    if first := first_of_two(state, stale):
        return Step("you", f"have someone other than {first.by} run `adk-spec approve {cid}`")
    return Step("you", f"run `adk-spec approve {cid}`")
