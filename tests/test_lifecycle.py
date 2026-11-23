"""The lifecycle's rules: what a base is, what an approval records and what voids it, what blocks each gate, and
the next step of every state."""

from __future__ import annotations

import pytest
from samples import BRIEF, DELTA, SPEC, TASKS

from adk_spec.domain.delta_md import parse_delta
from adk_spec.domain.lifecycle import (
    approval_files,
    approval_stale,
    approve,
    approve_blockers,
    archive_blockers,
    capture_bases,
    check_stops,
    next_action,
)
from adk_spec.domain.model import ChangeState, Delta, Finding
from adk_spec.domain.spec_md import fingerprint, parse_spec

TEXTS = {"brief.md": BRIEF, "tasks.md": TASKS, "specs/auth/spec.md": DELTA}
DRAFT = ChangeState(id="passkeys", tier="lean", bases={"REQ-AUTH-002": "sha256:" + "a" * 64})
AT = "2026-11-21T10:00:00+00:00"
ERROR = Finding(severity="ERROR", code="spec.no-scenario", message="m")
NO_BASE = Finding(severity="WARNING", code="delta.base-missing", message="m")
NO_TASKS = Finding(severity="WARNING", code="change.missing-tasks", message="m")
MARKER = Finding(severity="WARNING", code="brief.marker-unresolved", message="m")
OTHER = Finding(severity="WARNING", code="spec.no-shall", message="m")
#: Errors of the task list alone, which `plan` settles: measured live after a revision, and found by review.
NO_TASK = Finding(severity="ERROR", code="check.requirement-no-task", message="m", path="tasks.md")
TASKS_SYNTAX = Finding(severity="ERROR", code="syntax", message="m", path="tasks.md")


def approved(tier: str = "lean") -> ChangeState:
    return approve(DRAFT.model_copy(update={"tier": tier}), files=approval_files(TEXTS), by="reviewer", at=AT)


def test_bases_are_the_fingerprints_of_what_a_delta_changes_or_removes() -> None:
    one, two = parse_spec(SPEC).requirements
    held = capture_bases({"auth": parse_delta(DELTA)}, {"auth": parse_spec(SPEC)})
    assert held == {"REQ-AUTH-002": fingerprint(two), "REQ-AUTH-001": fingerprint(one)}
    assert capture_bases({"search": Delta(capability="search", purpose="p")}, {}) == {}


def test_an_approval_records_who_when_each_file_and_the_bases() -> None:
    state = approved()
    assert state.status == "approved" and (state.approval.by, state.approval.at) == ("reviewer", AT)
    assert set(state.approval.files) == set(TEXTS) and state.approval.bases == DRAFT.bases


def test_ticking_a_task_keeps_the_approval_and_any_other_edit_voids_it() -> None:
    ticked = {**TEXTS, "tasks.md": TASKS.replace("- [ ] T001", "- [x] T001").replace("\n", "\r\n")}
    assert approval_stale(approved(), approval_files(ticked)) == []
    reworded = {**TEXTS, "tasks.md": TASKS.replace("Write the failing", "Skip the")}
    assert approval_stale(approved(), approval_files(reworded)) == ["tasks.md"]
    assert approval_stale(approved(), approval_files({**TEXTS, "design.md": "# Design\n"})) == ["design.md"]
    without_brief = {k: v for k, v in TEXTS.items() if k != "brief.md"}
    assert approval_stale(approved(), approval_files(without_brief)) == ["brief.md"]


def test_a_tasks_file_off_its_grammar_is_hashed_as_it_stands() -> None:
    broken = {**TEXTS, "tasks.md": "no tasks here\n"}
    assert approval_files(broken)["tasks.md"] != approval_files(TEXTS)["tasks.md"]
    assert approval_files(broken) == approval_files(dict(broken))


def test_new_bases_void_an_approval_and_no_approval_is_stale() -> None:
    rebased = approved().model_copy(update={"bases": {"REQ-AUTH-002": "sha256:" + "b" * 64}})
    assert approval_stale(rebased, approval_files(TEXTS)) == ["bases"]
    assert approval_stale(DRAFT, approval_files(TEXTS)) == ["approval"]


def test_what_blocks_an_approval() -> None:
    assert approve_blockers(DRAFT, [OTHER]) == [] and approve_blockers(DRAFT, [ERROR, MARKER, OTHER]) == [ERROR, MARKER]
    assert approve_blockers(DRAFT, [OTHER], strict=True) == [OTHER]
    archived = DRAFT.model_copy(update={"status": "archived"})
    assert [f.code for f in approve_blockers(archived, [])] == ["change.archived"]


def test_what_an_archive_waits_for() -> None:
    assert archive_blockers(approved(), []) == []
    assert "tasks.md" in archive_blockers(approved(), ["tasks.md"])[0]
    assert "approve" in archive_blockers(DRAFT, ["approval"])[0]
    assert "verify" in archive_blockers(approved("standard"), [])[0]
    assert archive_blockers(approved("standard").model_copy(update={"status": "verified"}), []) == []
    assert "already" in archive_blockers(approved().model_copy(update={"status": "archived"}), [])[0]


#: What a draft holding an open point waits on, where the plan is still owed.
SETTLE_THEN_PLAN = "settle the open point in brief.md, then run `adk-spec plan passkeys`"


@pytest.mark.parametrize(
    ("state", "findings", "stale", "said"),
    [
        (DRAFT, [ERROR], ["approval"], "fix what `adk-spec validate passkeys` lists"),
        (DRAFT, [NO_BASE], ["approval"], "run `adk-spec approve passkeys`"),  # `approve` records it itself
        (DRAFT, [NO_TASKS], ["approval"], "run `adk-spec plan passkeys`"),
        (DRAFT, [NO_TASKS, MARKER], ["approval"], SETTLE_THEN_PLAN),
        (DRAFT, [ERROR, MARKER, NO_TASKS], ["approval"], "fix what `adk-spec validate passkeys` lists"),
        (DRAFT, [NO_TASKS, ERROR], ["approval"], "fix what `adk-spec validate passkeys` lists"),
        (DRAFT, [MARKER], ["approval"], "settle the open point in brief.md, then run `adk-spec approve passkeys`"),
        (DRAFT, [NO_TASK, MARKER], ["approval"], SETTLE_THEN_PLAN),
        (DRAFT, [NO_TASK], ["approval"], "run `adk-spec plan passkeys`"),
        (DRAFT, [TASKS_SYNTAX], ["approval"], "fix what `adk-spec validate passkeys` lists"),  # a hand edit: theirs
        (DRAFT, [NO_TASK, ERROR], ["approval"], "fix what `adk-spec validate passkeys` lists"),
        (DRAFT, [OTHER], ["approval"], "run `adk-spec approve passkeys`"),
        (DRAFT, [], ["approval"], "run `adk-spec approve passkeys`"),
        (approved(), [], ["tasks.md"], "tasks.md changed since the approval: run `adk-spec approve passkeys` again"),
        (approved(), [], [], "implement tasks.md, then run `adk-spec archive passkeys`"),
        (approved(), [ERROR], [], "fix what `adk-spec validate passkeys` lists"),
        (approved(), [OTHER], [], "implement tasks.md, then run `adk-spec archive passkeys`"),
        (approved("standard"), [], [], "implement tasks.md, then run `adk-spec verify passkeys`"),
        (approved("standard").model_copy(update={"status": "verified"}), [], [], "run `adk-spec archive passkeys`"),
        (approved().model_copy(update={"status": "archived"}), [], [], "nothing: archived"),
    ],
)
def test_the_next_step_is_named_for_every_state(state, findings, stale, said) -> None:
    assert next_action(state, findings, stale) == said


def test_a_line_slipped_in_above_an_approved_one_voids_the_approval() -> None:
    first = "  - verify: uv run pytest tests/test_passkey.py\n"
    shadowed = {**TEXTS, "tasks.md": TASKS.replace(first, "  - verify: skip the tests\n" + first)}
    assert approval_stale(approved(), approval_files(shadowed)) == ["tasks.md"]


# The check a standard change owes before its approval.

FILES = {"brief.md": "sha256:a", "tasks.md": "sha256:b"}


def test_a_lean_change_owes_no_check_and_a_standard_one_owes_a_current_clean_one() -> None:
    from adk_spec.domain.lifecycle import check_blockers
    from adk_spec.domain.model import Checked

    never = ChangeState(id="passkeys", tier="standard")
    assert check_blockers(ChangeState(id="passkeys", tier="lean"), FILES) == []
    assert [f.code for f in check_blockers(never, FILES)] == ["check.missing"]
    clean = never.model_copy(update={"check": Checked(at="t", files=FILES, blocking=0)})
    assert check_blockers(clean, FILES) == []
    assert [f.code for f in check_blockers(clean, {**FILES, "brief.md": "sha256:z"})] == ["check.stale"]
    assert [f.code for f in check_blockers(clean, {"brief.md": "sha256:a"})] == ["check.stale"], "a file was removed"
    found = never.model_copy(update={"check": Checked(at="t", files=FILES, blocking=2)})
    (blocking,) = check_blockers(found, FILES)
    assert (blocking.code, blocking.severity) == ("check.blocking", "ERROR") and "2 blocking" in blocking.message


def test_a_draft_with_nothing_else_owed_is_sent_to_its_approval_which_checks_first() -> None:
    from adk_spec.domain.lifecycle import check_blockers
    from adk_spec.domain.model import Checked

    never = ChangeState(id="passkeys", tier="standard")
    assert next_action(never, [], ["approval"], check=check_blockers(never, FILES)) == "run `adk-spec approve passkeys`"
    found = never.model_copy(update={"check": Checked(at="t", files=FILES, blocking=1)})
    step = next_action(found, [], ["approval"], check=check_blockers(found, FILES))
    assert step == "fix what reports/check.md lists, then run `adk-spec approve passkeys`"
    clean = never.model_copy(update={"check": Checked(at="t", files=FILES, blocking=0)})
    assert next_action(clean, [], ["approval"], check=check_blockers(clean, FILES)) == "run `adk-spec approve passkeys`"


@pytest.mark.parametrize(
    ("state", "findings", "actor"),
    [
        (DRAFT, [ERROR], "you"),
        (DRAFT, [MARKER], "you"),
        (DRAFT, [NO_TASKS], "run"),
        (DRAFT, [NO_BASE], "you"),
        (DRAFT, [], "you"),  # an approval is a person's decision
        (approved(), [], "you"),  # the work itself
        (approved("standard").model_copy(update={"status": "verified"}), [], "run"),
        (approved().model_copy(update={"status": "archived"}), [], "done"),
    ],
)
def test_each_next_step_says_who_takes_it(state, findings, actor) -> None:
    from adk_spec.domain.lifecycle import next_step

    stale = [] if state.approval else ["approval"]
    step = next_step(state, findings, stale)
    assert step.actor == actor and step.phrase == next_action(state, findings, stale)


def test_a_check_that_is_owed_is_the_approvals_to_make_and_one_that_blocks_is_yours() -> None:
    from adk_spec.domain.lifecycle import check_blockers, next_step
    from adk_spec.domain.model import Checked

    never = ChangeState(id="passkeys", tier="standard")
    assert next_step(never, [], ["approval"], check=check_blockers(never, FILES)).actor == "you", "an approval"
    found = never.model_copy(update={"check": Checked(at="t", files=FILES, blocking=1)})
    assert next_step(found, [], ["approval"], check=check_blockers(found, FILES)).actor == "you"


def test_whatever_blocks_an_approval_has_a_next_step_of_its_own_or_falls_to_validate() -> None:
    """Found by the cleanup review: what blocks an approval and what the next step says were decided by two lists,
    so a code added to one made `status` say to approve what `approve` then refused."""
    from adk_spec.domain import lifecycle

    for code in lifecycle.BLOCKS_APPROVAL:  # each has a step of its own, never the approval it blocks
        held = Finding(severity="WARNING", code=code, message="m")
        assert next_action(DRAFT, [held], ["approval"]) != "run `adk-spec approve passkeys`", code
    unlisted = Finding(severity="WARNING", code="a.code-with-no-step", message="m")
    assert next_action(DRAFT, [unlisted], ["approval"]) == "run `adk-spec approve passkeys`"
    lifecycle_blocks = lifecycle.BLOCKS_APPROVAL
    try:
        lifecycle.BLOCKS_APPROVAL = frozenset({*lifecycle_blocks, "a.code-with-no-step"})
        assert next_action(DRAFT, [unlisted], ["approval"]) == "fix what `adk-spec validate passkeys` lists"
    finally:
        lifecycle.BLOCKS_APPROVAL = lifecycle_blocks


def test_the_lifecycle_decides_what_a_check_and_a_verification_record() -> None:
    from adk_spec.domain.lifecycle import approve_blockers, check_blockers, checked, verified, verify_blockers

    draft = ChangeState(id="passkeys", tier="standard")
    held = checked(draft, [ERROR, MARKER], files=FILES, at="t", model="a model")
    assert (held.check.blocking, held.check.model, held.check.files) == (1, "a model", FILES)
    owed = check_blockers(held, FILES)
    assert [f.code for f in check_stops(owed)] == ["check.blocking"] and check_stops(owed, override=True) == []
    assert approve_blockers(held, []) == [], "what the check stops is asked apart from what the files block"
    never = check_blockers(draft, FILES)
    assert [f.code for f in check_stops(never, override=True)] == ["check.missing"]

    approved_state = approved("standard")
    assert verify_blockers(approved_state, []) == [] and "void" in verify_blockers(approved_state, ["tasks.md"])[0]
    assert "not approved" in verify_blockers(draft, ["approval"])[0]
    met = verified(approved_state, {"REQ-A-001": "met"}, base="c0", diff="sha256:d", at="t", override="unused")
    assert (met.status, met.verification.override) == ("verified", None), "a reason is kept only where it was needed"
    short = verified(met, {"REQ-A-001": "unclear"}, base="c0", diff="sha256:d", at="t")
    assert short.status == "approved", "the newest judgement stands"
    by_hand = verified(approved_state, {"REQ-A-001": "unmet"}, base="c0", diff="sha256:d", at="t", override="covered")
    assert (by_hand.status, by_hand.verification.override) == ("verified", "covered")


def test_where_the_work_began_is_kept_however_often_a_change_is_approved() -> None:
    from adk_spec.domain.lifecycle import approve

    once = approve(DRAFT, files=FILES, by="a", at="t", commit="c0")
    again = approve(once, files=FILES, by="a", at="t2", commit="c1")
    assert (once.base_commit, again.base_commit) == ("c0", "c0")
    assert approve(DRAFT, files=FILES, by="a", at="t").base_commit is None


def test_a_standard_change_edited_after_approval_is_sent_to_approve_again_which_checks_first() -> None:
    """Seen in a hand-run, while the check was a command of its own: `status` said to approve again, and `approve`
    then refused, the check being stale too. The approval makes the check now, so one step is the whole answer."""
    from adk_spec.domain.lifecycle import check_blockers
    from adk_spec.domain.model import Checked

    state = approved("standard").model_copy(update={"check": Checked(at="t", files=FILES, blocking=0)})
    owed = check_blockers(state, {**FILES, "tasks.md": "sha256:edited"})
    said = next_action(state, [], ["tasks.md"], check=owed)
    assert said == "tasks.md changed since the approval: run `adk-spec approve passkeys` again", (
        "`approve` checks first, by itself"
    )


def test_an_approval_makes_a_check_that_is_missing_or_stale_and_no_other() -> None:
    """One rule, stated once: the command asks it, and the next step follows it."""
    from adk_spec.domain.lifecycle import approval_checks_first, check_blockers, check_stops
    from adk_spec.domain.model import Checked

    never = ChangeState(id="passkeys", tier="standard")
    stale = never.model_copy(update={"check": Checked(at="t", files={}, blocking=0)})
    found = never.model_copy(update={"check": Checked(at="t", files=FILES, blocking=1)})
    assert approval_checks_first(check_blockers(never, FILES)) and approval_checks_first(check_blockers(stale, FILES))
    owed = check_blockers(found, FILES)
    assert not approval_checks_first(owed) and not approval_checks_first([])
    assert check_stops(owed) == owed and check_stops(owed, override=True) == []
    assert check_stops(check_blockers(never, FILES), override=True), (
        "a reason answers a finding, not a check never made"
    )


def test_a_check_code_no_rule_knows_is_never_sent_to_an_approval_that_would_refuse_it() -> None:
    """Found by the cleanup review: the step said to approve where the approval then refused, for a code of the
    check that neither the step table nor the approval's own list held."""
    from adk_spec.domain.model import Finding

    odd = Finding(severity="ERROR", code="check.some-new-code", message="m")
    never = ChangeState(id="passkeys", tier="standard")
    assert next_action(never, [], ["approval"], check=[odd]) == "fix what `adk-spec validate passkeys` lists"


def test_an_approved_change_edited_and_found_blocking_is_sent_to_the_report_not_to_approve_again() -> None:
    """Found by the code review: after an approval made its check again and refused on what it found, the step
    still said "approve again", which was refused again."""
    from adk_spec.domain.lifecycle import check_blockers
    from adk_spec.domain.model import Checked

    edited = {**FILES, "tasks.md": "sha256:edited"}
    state = approved("standard").model_copy(update={"check": Checked(at="t", files=edited, blocking=2)})
    said = next_action(state, [], ["tasks.md"], check=check_blockers(state, edited))
    assert said == "fix what reports/check.md lists, then run `adk-spec approve passkeys`"


def test_a_task_list_with_a_ticked_box_is_fixed_by_hand_not_by_plan() -> None:
    """Found by review: after a revision of a change whose task was ticked, the next line said `plan`, which a
    ticked task refuses: drafting the list again would throw the work away."""
    from adk_spec.domain.lifecycle import next_step

    assert next_step(DRAFT, [NO_TASK], ["approval"]).phrase == "run `adk-spec plan passkeys`"
    begun = next_step(DRAFT, [NO_TASK], ["approval"], started=True).phrase
    assert begun == "fix what `adk-spec validate passkeys` lists"
