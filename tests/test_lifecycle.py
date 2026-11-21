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


@pytest.mark.parametrize(
    ("state", "findings", "stale", "said"),
    [
        (DRAFT, [ERROR], ["approval"], "fix what `adk-spec validate passkeys` lists"),
        (DRAFT, [NO_BASE], ["approval"], "run `adk-spec rebase passkeys`"),
        (DRAFT, [NO_TASKS], ["approval"], "run `adk-spec plan passkeys`"),
        (DRAFT, [NO_TASKS, NO_BASE], ["approval"], "run `adk-spec plan passkeys`"),
        (DRAFT, [NO_TASKS, MARKER], ["approval"], "settle the open point in brief.md"),
        (DRAFT, [MARKER, NO_TASKS, NO_BASE], ["approval"], "settle the open point in brief.md"),
        (DRAFT, [ERROR, MARKER, NO_TASKS], ["approval"], "fix what `adk-spec validate passkeys` lists"),
        (DRAFT, [NO_TASKS, ERROR], ["approval"], "fix what `adk-spec validate passkeys` lists"),
        (DRAFT, [MARKER], ["approval"], "settle the open point in brief.md"),
        (DRAFT, [OTHER], ["approval"], "run `adk-spec approve passkeys`"),
        (DRAFT, [], ["approval"], "run `adk-spec approve passkeys`"),
        (approved(), [], ["tasks.md"], "approve again: tasks.md changed since the approval"),
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


def test_a_draft_with_nothing_else_owed_is_sent_to_its_check_first() -> None:
    from adk_spec.domain.lifecycle import check_blockers
    from adk_spec.domain.model import Checked

    never = ChangeState(id="passkeys", tier="standard")
    assert next_action(never, [], ["approval"], check=check_blockers(never, FILES)) == "run `adk-spec check passkeys`"
    found = never.model_copy(update={"check": Checked(at="t", files=FILES, blocking=1)})
    step = next_action(found, [], ["approval"], check=check_blockers(found, FILES))
    assert step == "fix what reports/check.md lists, then run `adk-spec check passkeys`"
    clean = never.model_copy(update={"check": Checked(at="t", files=FILES, blocking=0)})
    assert next_action(clean, [], ["approval"], check=check_blockers(clean, FILES)) == "run `adk-spec approve passkeys`"


@pytest.mark.parametrize(
    ("state", "findings", "actor"),
    [
        (DRAFT, [ERROR], "you"),
        (DRAFT, [MARKER], "you"),
        (DRAFT, [NO_TASKS], "run"),
        (DRAFT, [NO_BASE], "run"),
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


def test_a_check_that_is_owed_is_a_command_to_run_and_one_that_blocks_is_yours() -> None:
    from adk_spec.domain.lifecycle import check_blockers, next_step
    from adk_spec.domain.model import Checked

    never = ChangeState(id="passkeys", tier="standard")
    assert next_step(never, [], ["approval"], check=check_blockers(never, FILES)).actor == "run"
    found = never.model_copy(update={"check": Checked(at="t", files=FILES, blocking=1)})
    assert next_step(found, [], ["approval"], check=check_blockers(found, FILES)).actor == "you"
