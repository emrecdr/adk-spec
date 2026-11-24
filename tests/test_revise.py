"""`adk-spec propose "<instruction>" --id <change>`: an open change revised in place, its hand edits kept, its IDs
kept by name, and what changed said."""

from __future__ import annotations

import pytest
from conftest import (
    BRIEF_WITH_A_MARKER,
    CANNED_BRIEF,
    CANNED_DELTAS,
    approved,
    asked,
    between,
    on_the_fake,
    repository,
    run,
    seeded,
    sent_to,
    shut,
    state_of,
)
from samples import tasks_for

from adk_spec.workspace.files import read_text, write_text

BRIEF, DELTAS = "You write the brief of a change", "You write the requirement deltas"
TASKS_STAGE, TRIAGE = "You break a change into tasks", "You size a change request"
TASKS = ".spec/changes/passkeys/tasks.md"
DELTA = ".spec/changes/passkeys/specs/auth/spec.md"
PASSKEY = CANNED_DELTAS["deltas"][0]["added"][0]
BACKUP = {
    **PASSKEY,
    "name": "Sign in with a backup code",
    "statement": "The system SHALL let a user sign in with a one-time backup code.",
}
LOCK = {**PASSKEY, "name": "Lock after failures", "statement": "The system MUST lock an account after three."}
#: The seeded change's delta with its passkey requirement alone, as the canned deltas answer restates it.
PASSKEY_ALONE = """\
# Delta: auth

## ADDED Requirements

### REQ-AUTH-004: Sign in with a passkey

The system SHALL let a user sign in with a passkey.

#### Scenario: Registered passkey

- WHEN the user presents a registered passkey
- THEN the system starts a session
"""


@pytest.fixture(autouse=True)
def _fake_arm(monkeypatch) -> None:
    on_the_fake(monkeypatch)


def unticked(root):
    """The seeded change, with no task ticked: one a revision may plan again."""
    ws = seeded(root)
    write_text(root / TASKS, tasks_for("REQ-AUTH-004", "REQ-AUTH-002"))
    return ws


def moved_base(ws, fake_provider) -> None:
    """The seeded change with a base for REQ-AUTH-002 the living spec no longer holds, and a deltas answer that keeps
    modifying it and removes REQ-AUTH-001, which has none recorded."""
    ws.save_state(ws.load_change("passkeys").change.state.model_copy(update={"bases": {"REQ-AUTH-002": "b0"}}))
    removed = [{"id": "REQ-AUTH-001", "reason": "Passwords are retired."}]
    modified = [{"id": "REQ-AUTH-002", "requirement": LOCK}]
    delta = {"capability": "auth", "purpose": "", "added": [PASSKEY], "modified": modified, "removed": removed}
    fake_provider.answers_when(DELTAS, {"deltas": [delta]})


def revised(root, *argv: str, instruction: str = "Also let users sign in with a backup code.") -> int:
    return run(root, "propose", instruction, "--id", "passkeys", "--no-input", *argv)


def adding(*requirements: dict, capability: str = "auth", purpose: str = "") -> dict:
    """A deltas answer that adds `requirements` to `capability`, and does nothing else."""
    added = list(requirements)
    return {"deltas": [{"capability": capability, "purpose": purpose, "added": added, "modified": [], "removed": []}]}


@pytest.mark.usefixtures("fake_provider")
def test_a_revision_keeps_each_requirements_id_by_its_name_and_says_what_changed(tmp_path, capsys) -> None:
    unticked(tmp_path)
    capsys.readouterr()
    assert revised(tmp_path) == 0
    out = capsys.readouterr().out
    assert "revising  passkeys, a lean draft" in out
    assert "revised   added nothing; changed nothing; dropped REQ-AUTH-001, REQ-AUTH-002" in out
    delta = read_text(tmp_path / DELTA)
    assert "### REQ-AUTH-004: Sign in with a passkey" in delta and "REQ-AUTH-005" not in delta


def test_a_new_requirement_gets_a_new_id_and_none_is_reused(tmp_path, capsys, fake_provider) -> None:
    unticked(tmp_path)
    fake_provider.answers_when(DELTAS, adding(PASSKEY, BACKUP))
    capsys.readouterr()
    assert revised(tmp_path) == 0
    assert "revised   added REQ-AUTH-005; changed nothing;" in capsys.readouterr().out


def test_a_renamed_requirement_gets_a_new_id_and_the_old_one_is_dropped(tmp_path, capsys, fake_provider) -> None:
    unticked(tmp_path)
    fake_provider.answers_when(DELTAS, adding({**PASSKEY, "name": "Sign in with a security key"}))
    capsys.readouterr()
    assert revised(tmp_path) == 0
    out = capsys.readouterr().out
    assert "added REQ-AUTH-005; changed nothing; dropped REQ-AUTH-001, REQ-AUTH-002, REQ-AUTH-004" in out


def test_the_stages_are_given_the_files_as_they_stand_hand_edits_and_all(tmp_path, fake_provider) -> None:
    unticked(tmp_path)
    brief = tmp_path / ".spec/changes/passkeys/brief.md"
    write_text(brief, read_text(brief).rstrip("\n") + "\n\nA sentence the person wrote by hand.\n")
    assert revised(tmp_path) == 0
    assert "A sentence the person wrote by hand." in between(sent_to(fake_provider, BRIEF), "replaces")
    assert "### REQ-AUTH-004: Sign in with a passkey" in between(sent_to(fake_provider, DELTAS), "current deltas")
    assert "Also let users sign in with a backup code." in between(sent_to(fake_provider, BRIEF), "request")


def test_a_hand_edit_the_model_keeps_is_written_back_and_not_listed_as_changed(tmp_path, capsys, fake_provider) -> None:
    unticked(tmp_path)
    edited = "The system SHALL let a user sign in with a passkey on any device."
    write_text(tmp_path / DELTA, read_text(tmp_path / DELTA).replace(PASSKEY["statement"], edited))
    fake_provider.answers_when(DELTAS, adding({**PASSKEY, "statement": edited}))
    capsys.readouterr()
    assert revised(tmp_path) == 0
    assert "added nothing; changed nothing;" in capsys.readouterr().out and edited in read_text(tmp_path / DELTA)


def test_the_change_keeps_its_tier_and_no_sizing_is_asked(tmp_path, capsys, fake_provider) -> None:
    ws = unticked(tmp_path)
    ws.save_state(ws.load_change("passkeys").change.state.model_copy(update={"tier": "standard"}))
    capsys.readouterr()
    assert revised(tmp_path, "--tier", "lean", instruction="Fix the typo in the passkey requirement.") == 0
    assert state_of(tmp_path)["tier"] == "standard" and asked(fake_provider, TRIAGE) == 0
    assert "`--tier lean` is not used: a change keeps its tier" in capsys.readouterr().out


@pytest.mark.usefixtures("fake_provider")
def test_a_ticked_task_keeps_tasks_md_as_it_is(tmp_path, capsys) -> None:
    seeded(tmp_path)  # its T002 is ticked
    before = read_text(tmp_path / TASKS)
    capsys.readouterr()
    assert revised(tmp_path) == 0
    assert read_text(tmp_path / TASKS) == before and "kept      tasks.md: a task is ticked" in capsys.readouterr().out


@pytest.mark.usefixtures("fake_provider")
def test_a_ticked_box_in_a_task_list_off_its_grammar_is_kept_too(tmp_path, capsys) -> None:
    """Found by the cleanup review: a list off its grammar reads as none, and its ticked box went unseen."""
    seeded(tmp_path)
    write_text(tmp_path / TASKS, "# Tasks\n\nWritten by hand, off the grammar.\n\n- [x] the first step, done\n")
    before = read_text(tmp_path / TASKS)
    capsys.readouterr()
    assert revised(tmp_path) == 0
    assert read_text(tmp_path / TASKS) == before and "kept      tasks.md: a task is ticked" in capsys.readouterr().out


def test_a_revision_that_changes_no_requirement_keeps_the_tasks_and_drafts_none(
    tmp_path, capsys, fake_provider
) -> None:
    """Found by the cleanup review: a revision of the brief alone paid for the tasks again."""
    unticked(tmp_path)
    write_text(tmp_path / DELTA, PASSKEY_ALONE)
    write_text(tmp_path / TASKS, tasks_for("REQ-AUTH-004"))
    capsys.readouterr()
    assert revised(tmp_path, instruction="Say why passkeys matter more plainly.") == 0
    assert asked(fake_provider, TASKS_STAGE) == 0
    assert "kept      tasks.md: no requirement changed" in capsys.readouterr().out


def test_a_revision_does_not_read_the_code_again(tmp_path, fake_provider) -> None:
    """Found by the cleanup review: a change with no `context.md` was read again, up to seven calls, on each one."""
    unticked(tmp_path)
    repository(tmp_path)
    assert revised(tmp_path) == 0
    assert asked(fake_provider, "You choose what to read") == 0 and asked(fake_provider, TASKS_STAGE) == 1


@pytest.mark.usefixtures("fake_provider")
def test_an_approved_change_revised_must_be_approved_again(tmp_path, capsys) -> None:
    unticked(tmp_path)
    approved(tmp_path)
    capsys.readouterr()
    assert revised(tmp_path) == 0
    held = state_of(tmp_path)
    assert (held["status"], held["approval"]) == ("draft", None)
    assert "the approval is void: read what changed" in capsys.readouterr().out


def test_a_capability_the_revision_no_longer_touches_loses_its_delta(tmp_path, fake_provider) -> None:
    seeded(tmp_path)  # a task is ticked: tasks.md is kept, and no plan is drafted
    fake_provider.answers_when(BRIEF, {**CANNED_BRIEF, "capabilities": ["sessions"]})
    session = {**PASSKEY, "name": "Keep a session", "statement": "The system SHALL keep a session for a day."}
    fake_provider.answers_when(DELTAS, adding(session, capability="sessions", purpose="How sessions are kept."))
    assert revised(tmp_path) == 0
    specs = tmp_path / ".spec/changes/passkeys/specs"
    assert not (specs / "auth").exists() and (specs / "sessions/spec.md").is_file()


def test_a_revision_keeps_each_base_it_recorded_and_records_only_a_new_one(tmp_path, fake_provider) -> None:
    """Found by the fourth audit: a revision recorded every base afresh, so a requirement another change had since
    altered lost its stale base, its warning with it, and the archive wrote over the other change's words. A base
    is the guard against two changes to one requirement, and only `rebase` records one anew."""
    moved_base(seeded(tmp_path), fake_provider)
    assert revised(tmp_path) == 1, "the base that moved holds the plan until `rebase`"
    bases = state_of(tmp_path, "passkeys")["bases"]
    assert bases["REQ-AUTH-002"] == "b0" and bases["REQ-AUTH-001"] not in ("", "b0")


@pytest.mark.parametrize("status", ["verified", "archived"])
def test_a_verified_or_archived_change_is_not_revised(tmp_path, capsys, fake_provider, status) -> None:
    ws = unticked(tmp_path)
    ws.save_state(ws.load_change("passkeys").change.state.model_copy(update={"status": status}))
    assert revised(tmp_path) == 1
    assert f"`passkeys` is {status}" in capsys.readouterr().err and fake_provider.requests == []


def test_a_requirement_the_change_adds_restated_as_modified_stays_added(tmp_path, capsys, fake_provider) -> None:
    unticked(tmp_path)
    edited = {**PASSKEY, "statement": "The system SHALL let a user sign in with a passkey on any device."}
    restated = {"capability": "auth", "purpose": "", "added": [], "removed": []}
    fake_provider.answers_when(
        DELTAS, {"deltas": [{**restated, "modified": [{"id": "REQ-AUTH-004", "requirement": edited}]}]}
    )
    capsys.readouterr()
    assert revised(tmp_path) == 0
    assert "revised   added nothing; changed REQ-AUTH-004;" in capsys.readouterr().out
    delta = read_text(tmp_path / DELTA)
    assert delta.index("## ADDED Requirements") < delta.index("REQ-AUTH-004") and "MODIFIED" not in delta


def test_a_delta_off_its_grammar_holds_the_revision_and_is_never_deleted(tmp_path, capsys, fake_provider) -> None:
    """Found by the fourth audit: a delta a person was still writing did not read, so the revision knew nothing of
    it, deleted it with its folder, and said it dropped nothing. The first review had found it left behind: it is
    neither, and the person settles it first."""
    seeded(tmp_path)
    broken = tmp_path / ".spec/changes/passkeys/specs/sessions/spec.md"
    write_text(broken, "# Delta: sessions\n\nHalf written.\n")
    assert revised(tmp_path) == 1
    said = capsys.readouterr()
    assert "specs/sessions/spec.md:3" in said.out and "is not revised" in said.err and fake_provider.requests == []
    assert broken.is_file()


def test_a_delta_the_revision_takes_out_is_named(tmp_path, capsys, fake_provider) -> None:
    seeded(tmp_path)  # a task is ticked: tasks.md is kept, and no plan is drafted
    fake_provider.answers_when(BRIEF, {**CANNED_BRIEF, "capabilities": ["sessions"]})
    session = {**PASSKEY, "name": "Keep a session", "statement": "The system SHALL keep a session for a day."}
    fake_provider.answers_when(DELTAS, adding(session, capability="sessions", purpose="How sessions are kept."))
    capsys.readouterr()
    assert revised(tmp_path) == 0
    assert "removed   .spec/changes/passkeys/specs/auth/spec.md" in capsys.readouterr().out


@pytest.mark.usefixtures("fake_provider")
def test_a_revision_that_changes_nothing_keeps_the_approval(tmp_path, capsys) -> None:
    """Found by the review: an approval was voided by a revision that wrote every file as it stood."""
    seeded(tmp_path)
    assert run(tmp_path, "propose", "Let users sign in with a passkey.", "--id", "fresh", "--no-input") == 0
    approved(tmp_path, "fresh")
    capsys.readouterr()
    assert run(tmp_path, "propose", "Keep it as it is.", "--id", "fresh", "--no-input") == 0
    held = state_of(tmp_path, "fresh")
    assert held["status"] == "approved" and held["approval"] and "approval is void" not in capsys.readouterr().out


def test_a_kept_task_list_is_said_beside_a_point_left_open(tmp_path, capsys, fake_provider) -> None:
    seeded(tmp_path)  # a task is ticked
    fake_provider.answers_when(BRIEF, BRIEF_WITH_A_MARKER)
    capsys.readouterr()
    assert revised(tmp_path) == 0
    out = capsys.readouterr().out
    assert "plan      waits: the brief leaves 1 point open" in out and "kept      tasks.md: a task is ticked" in out


def test_a_file_that_will_not_open_is_never_written_over(tmp_path, capsys, fake_provider) -> None:
    """Found by the code review: a task list that would not open read as one with no box ticked, and a revision or
    a plan wrote over it, ticked work and all."""
    seeded(tmp_path)  # a task is ticked
    tasks = tmp_path / TASKS
    before = read_text(tasks)
    with shut(tasks):
        assert revised(tmp_path) == 1
        assert run(tmp_path, "plan", "passkeys", "--replace") == 1
    assert read_text(tasks) == before and "file.unreadable" in capsys.readouterr().out
    assert not any("You break a change into tasks" in str(r.config.system_instruction) for r in fake_provider.requests)


def test_a_task_list_that_is_no_utf8_text_is_never_drafted_over(tmp_path, capsys, fake_provider) -> None:
    """Found by the cleanup review: a list PowerShell 5.1 wrote as UTF-16 read as one with no box ticked, and a plan
    drafted over its ticked work, as over a list that would not open."""
    seeded(tmp_path)  # a task is ticked
    tasks = tmp_path / TASKS
    held = read_text(tasks).encode("utf-16")
    tasks.write_bytes(held)
    assert revised(tmp_path) == 1
    assert run(tmp_path, "plan", "passkeys", "--replace") == 1
    assert tasks.read_bytes() == held and "file.unreadable" in capsys.readouterr().out
    assert not any(TASKS_STAGE in str(r.config.system_instruction) for r in fake_provider.requests)


def test_a_revision_whose_base_moved_holds_its_plan_and_names_the_step(tmp_path, capsys, fake_provider) -> None:
    """Found by the code review: a kept base that no longer held was an error the plan refused, so the revision
    ended as an engine failure, exit 3, naming a `plan` that refused again until `rebase`."""
    moved_base(unticked(tmp_path), fake_provider)
    capsys.readouterr()
    assert revised(tmp_path) == 1
    out = capsys.readouterr().out
    assert "ERROR delta.base-stale .spec/changes/passkeys/specs/auth/spec.md" in out
    assert "next      fix what `adk-spec validate passkeys` lists" in out
    assert not any(TASKS_STAGE in str(r.config.system_instruction) for r in fake_provider.requests)


def test_a_delta_that_is_no_utf8_text_is_named_once(tmp_path, capsys, fake_provider) -> None:
    """Found by the cleanup review: a delta not read was both a delta's fault and a file not read, and said twice."""
    seeded(tmp_path)
    (tmp_path / DELTA).write_bytes(read_text(tmp_path / DELTA).encode("utf-16"))
    assert revised(tmp_path) == 1 and fake_provider.requests == []
    assert capsys.readouterr().out.count("ERROR file.unreadable .spec/changes/passkeys/specs/auth/spec.md") == 1
