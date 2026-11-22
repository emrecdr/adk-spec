"""`adk-spec propose "<instruction>" --id <change>`: an open change revised in place, its hand edits kept, its IDs
kept by name, and what changed said."""

from __future__ import annotations

import pytest
from conftest import (
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


def test_the_change_keeps_its_tier_and_no_sizing_is_asked(tmp_path, fake_provider) -> None:
    ws = unticked(tmp_path)
    ws.save_state(ws.load_change("passkeys").change.state.model_copy(update={"tier": "standard"}))
    assert revised(tmp_path, "--tier", "lean", instruction="Fix the typo in the passkey requirement.") == 0
    assert state_of(tmp_path)["tier"] == "standard" and asked(fake_provider, TRIAGE) == 0


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


@pytest.mark.parametrize("status", ["verified", "archived"])
def test_a_verified_or_archived_change_is_not_revised(tmp_path, capsys, fake_provider, status) -> None:
    ws = unticked(tmp_path)
    ws.save_state(ws.load_change("passkeys").change.state.model_copy(update={"status": status}))
    assert revised(tmp_path) == 1
    assert f"`passkeys` is {status}" in capsys.readouterr().err and fake_provider.requests == []
