"""`adk-spec propose "<instruction>" --id <change>`: an open change revised in place, its hand edits kept, its IDs
kept by name, and what changed said."""

from __future__ import annotations

import pytest
from conftest import CANNED_BRIEF, CANNED_DELTAS, between, on_the_fake, run, seeded, state_of
from samples import tasks_for

from adk_spec.workspace.files import read_text, write_text

BRIEF, DELTAS = "You write the brief of a change", "You write the requirement deltas"
TASKS = ".spec/changes/passkeys/tasks.md"
PASSKEY = CANNED_DELTAS["deltas"][0]["added"][0]
BACKUP = {
    "name": "Sign in with a backup code",
    "statement": "The system SHALL let a user sign in with a one-time backup code.",
    "scenarios": [
        {
            "name": "A code is used",
            "steps": ["GIVEN a user with a backup code", "WHEN they enter it", "THEN they are signed in"],
        }
    ],
}


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


def sent(fake_provider, opening: str) -> str:
    (text,) = [
        str(r.config.system_instruction)
        for r in fake_provider.requests
        if str(r.config.system_instruction).startswith(opening)
    ]
    return text


@pytest.mark.usefixtures("fake_provider")
def test_a_revision_keeps_each_requirements_id_by_its_name_and_says_what_changed(tmp_path, capsys) -> None:
    unticked(tmp_path)
    capsys.readouterr()
    assert revised(tmp_path) == 0
    out = capsys.readouterr().out
    assert "revising  passkeys, a lean draft" in out
    assert "revised   added nothing; changed nothing; dropped REQ-AUTH-001, REQ-AUTH-002" in out
    delta = read_text(tmp_path / ".spec/changes/passkeys/specs/auth/spec.md")
    assert "### REQ-AUTH-004: Sign in with a passkey" in delta and "REQ-AUTH-005" not in delta


def test_a_new_requirement_gets_a_new_id_and_none_is_reused(tmp_path, capsys, fake_provider) -> None:
    unticked(tmp_path)
    added = {
        "deltas": [{"capability": "auth", "purpose": "", "added": [PASSKEY, BACKUP], "modified": [], "removed": []}]
    }
    fake_provider.answers_when(DELTAS, added)
    capsys.readouterr()
    assert revised(tmp_path) == 0
    assert "revised   added REQ-AUTH-005; changed nothing;" in capsys.readouterr().out


def test_the_stages_are_given_the_files_as_they_stand_hand_edits_and_all(tmp_path, fake_provider) -> None:
    unticked(tmp_path)
    brief = tmp_path / ".spec/changes/passkeys/brief.md"
    write_text(brief, read_text(brief).rstrip("\n") + "\n\nA sentence the person wrote by hand.\n")
    assert revised(tmp_path) == 0
    assert "A sentence the person wrote by hand." in between(sent(fake_provider, BRIEF), "replaces")
    assert "### REQ-AUTH-004: Sign in with a passkey" in between(sent(fake_provider, DELTAS), "current deltas")
    assert "Also let users sign in with a backup code." in between(sent(fake_provider, BRIEF), "request")


def test_the_change_keeps_its_tier_and_no_sizing_is_asked(tmp_path, fake_provider) -> None:
    ws = unticked(tmp_path)
    ws.save_state(ws.load_change("passkeys").change.state.model_copy(update={"tier": "standard"}))
    assert revised(tmp_path, instruction="Fix the typo in the passkey requirement.") == 0
    assert state_of(tmp_path)["tier"] == "standard"
    assert not any(
        str(r.config.system_instruction).startswith("You size a change request") for r in fake_provider.requests
    )


@pytest.mark.usefixtures("fake_provider")
def test_a_ticked_task_keeps_tasks_md_as_it_is(tmp_path, capsys) -> None:
    seeded(tmp_path)  # its T002 is ticked
    before = read_text(tmp_path / TASKS)
    capsys.readouterr()
    assert revised(tmp_path) == 0
    assert read_text(tmp_path / TASKS) == before and "kept      tasks.md: a task is ticked" in capsys.readouterr().out


@pytest.mark.usefixtures("fake_provider")
def test_an_approved_change_revised_must_be_approved_again(tmp_path, capsys) -> None:
    unticked(tmp_path)
    assert run(tmp_path, "approve", "passkeys", "--by", "reviewer") == 0
    capsys.readouterr()
    assert revised(tmp_path) == 0
    held = state_of(tmp_path)
    assert (held["status"], held["approval"]) == ("draft", None)
    assert "the approval is void: read what changed" in capsys.readouterr().out


@pytest.mark.parametrize("status", ["verified", "archived"])
def test_a_verified_or_archived_change_is_not_revised(tmp_path, capsys, fake_provider, status) -> None:
    ws = unticked(tmp_path)
    ws.save_state(ws.load_change("passkeys").change.state.model_copy(update={"status": status}))
    assert revised(tmp_path) == 1
    assert f"`passkeys` is {status}" in capsys.readouterr().err and fake_provider.requests == []


def auth_adding(*requirements: dict) -> dict:
    return {
        "deltas": [{"capability": "auth", "purpose": "", "added": list(requirements), "modified": [], "removed": []}]
    }


def test_a_renamed_requirement_gets_a_new_id_and_the_old_one_is_dropped(tmp_path, capsys, fake_provider) -> None:
    unticked(tmp_path)
    fake_provider.answers_when(DELTAS, auth_adding({**PASSKEY, "name": "Sign in with a security key"}))
    capsys.readouterr()
    assert revised(tmp_path) == 0
    assert "added REQ-AUTH-005; changed nothing; dropped REQ-AUTH-001, REQ-AUTH-002, REQ-AUTH-004" in (
        capsys.readouterr().out
    )


def test_a_hand_edit_the_model_keeps_is_written_back_and_not_listed_as_changed(tmp_path, capsys, fake_provider) -> None:
    unticked(tmp_path)
    delta = tmp_path / ".spec/changes/passkeys/specs/auth/spec.md"
    edited = "The system SHALL let a user sign in with a passkey on any device."
    write_text(delta, read_text(delta).replace("The system SHALL let a user sign in with a passkey.", edited))
    steps = ["WHEN the user presents a registered passkey", "THEN the system starts a session"]
    kept = {
        "name": "Sign in with a passkey",
        "statement": edited,
        "scenarios": [{"name": "Registered passkey", "steps": steps}],
    }
    fake_provider.answers_when(DELTAS, auth_adding(kept))
    capsys.readouterr()
    assert revised(tmp_path) == 0
    assert "added nothing; changed nothing;" in capsys.readouterr().out and edited in read_text(delta)


def test_a_capability_the_revision_no_longer_touches_loses_its_delta(tmp_path, fake_provider) -> None:
    seeded(tmp_path)  # a task is ticked: tasks.md is kept, and no plan is drafted
    fake_provider.answers_when(BRIEF, {**CANNED_BRIEF, "capabilities": ["sessions"]})
    session = {**BACKUP, "name": "Keep a session", "statement": "The system SHALL keep a session for a day."}
    moved = {
        "capability": "sessions",
        "purpose": "How sessions are kept.",
        "added": [session],
        "modified": [],
        "removed": [],
    }
    fake_provider.answers_when(DELTAS, {"deltas": [moved]})
    assert revised(tmp_path) == 0
    specs = tmp_path / ".spec/changes/passkeys/specs"
    assert not (specs / "auth").exists() and (specs / "sessions/spec.md").is_file()


def test_two_requirements_of_one_name_are_not_given_one_id() -> None:
    from adk_spec.domain.convert import to_deltas
    from adk_spec.domain.drafts import DeltasDraft

    draft = DeltasDraft.model_validate(auth_adding(PASSKEY, PASSKEY))
    made = to_deltas(draft, {}, {"REQ-AUTH-004"}, {("auth", "sign in with a passkey"): "REQ-AUTH-004"})
    assert [req.id for req in made["auth"].added] == ["REQ-AUTH-004", "REQ-AUTH-005"]
