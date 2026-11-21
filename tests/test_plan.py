"""`adk-spec plan`: a draft change's tasks, and its design where one is owed, drafted behind gates and written whole."""

from __future__ import annotations

import pytest
from conftest import approved, on_the_fake, run, seeded

from adk_spec.workspace.files import read_text, write_text

DESIGN, TASKS = "You write the design of a change", "You break a change into tasks"


def openings(fake_provider) -> list[str]:
    known = (DESIGN, TASKS)
    sent = (str(r.config.system_instruction) for r in fake_provider.requests)
    return [next((opening for opening in known if instruction.startswith(opening)), "?") for instruction in sent]


@pytest.fixture(autouse=True)
def _fake_arm(monkeypatch) -> None:
    on_the_fake(monkeypatch)


def test_plan_writes_tasks_a_person_can_then_approve(tmp_path, capsys, fake_provider) -> None:
    ws = seeded(tmp_path)
    (tmp_path / ".spec/changes/passkeys/tasks.md").unlink()
    assert run(tmp_path, "status") == 0 and "run `adk-spec plan passkeys`" in capsys.readouterr().out
    assert run(tmp_path, "plan", "passkeys") == 0
    loaded = ws.load_change("passkeys")
    assert loaded.problems == [] and loaded.change.design is None
    assert [task.id for group in loaded.change.tasks for task in group.tasks] == ["T001", "T002"]
    assert not any(task.done for group in loaded.change.tasks for task in group.tasks)
    assert openings(fake_provider) == [TASKS]
    out = capsys.readouterr().out
    assert ".spec/changes/passkeys/tasks.md" in out and "120 total" in out and "rebase passkeys" in out
    approved(tmp_path)


def test_the_tasks_stage_reads_the_brief_the_deltas_and_the_rules(tmp_path, fake_provider) -> None:
    seeded(tmp_path)
    write_text(tmp_path / ".spec/constitution.md", "# Constitution\n\nEvery change ships with a test.\n")
    assert run(tmp_path, "plan", "passkeys") == 0
    sent = str(fake_provider.requests[0].config.system_instruction)
    assert "# Sign in with a passkey" in sent and "### REQ-AUTH-004: Sign in with a passkey" in sent
    assert "Every change ships with a test." in sent and "REQ-AUTH-001: Sign in with email" in sent


def test_a_change_that_needs_a_design_gets_one_first(tmp_path, fake_provider) -> None:
    ws = seeded(tmp_path)
    ws.save_state(ws.load_change("passkeys").change.state.model_copy(update={"needs_design": True}))
    assert run(tmp_path, "plan", "passkeys") == 0
    design = read_text(tmp_path / ".spec/changes/passkeys/design.md")
    assert design.startswith("# Design\n\n## Context\n\nSign-in is one handler") and "## Risks" in design
    assert openings(fake_provider) == [DESIGN, TASKS]
    assert "WebAuthn through the platform API" in str(fake_provider.requests[1].config.system_instruction)


def test_plan_refuses_a_change_that_is_no_draft_and_spends_nothing(tmp_path, capsys, fake_provider) -> None:
    seeded(tmp_path)
    approved(tmp_path)
    capsys.readouterr()
    assert run(tmp_path, "plan", "passkeys") == 1 and "approved" in capsys.readouterr().err
    assert fake_provider.requests == []


def test_plan_refuses_a_change_whose_brief_or_deltas_have_an_error(tmp_path, capsys, fake_provider) -> None:
    seeded(tmp_path)
    delta = tmp_path / ".spec/changes/passkeys/specs/auth/spec.md"
    write_text(delta, read_text(delta).replace("### REQ-AUTH-002", "### REQ-AUTH-099"))
    assert run(tmp_path, "plan", "passkeys") == 1
    assert "delta.target-missing" in capsys.readouterr().out and fake_provider.requests == []


def test_a_task_list_with_no_task_is_sent_back_then_given_up(tmp_path, capsys, fake_provider) -> None:
    seeded(tmp_path)
    before = read_text(tmp_path / ".spec/changes/passkeys/tasks.md")
    fake_provider.answers_when(TASKS, {"groups": []})
    assert run(tmp_path, "plan", "passkeys") == 3
    assert read_text(tmp_path / ".spec/changes/passkeys/tasks.md") == before
    assert "no task" in capsys.readouterr().err and openings(fake_provider) == [TASKS] * 3


def test_plan_holds_the_lock_and_lets_it_go(tmp_path, capsys) -> None:
    seeded(tmp_path)
    (tmp_path / ".spec/.lock").write_text("another run", encoding="utf-8")
    assert run(tmp_path, "plan", "passkeys") == 2 and ".spec/.lock" in capsys.readouterr().err
    (tmp_path / ".spec/.lock").unlink()
    assert run(tmp_path, "plan", "passkeys") == 0 and not (tmp_path / ".spec/.lock").exists()


def test_plan_replaces_a_task_list_that_does_not_parse(tmp_path, fake_provider) -> None:
    """Found by review: `plan` refused a change over the very file it was about to replace."""
    ws = seeded(tmp_path)
    write_text(tmp_path / ".spec/changes/passkeys/tasks.md", "# Tasks\n\n- [ ] no group, no number\n")
    assert ws.load_change("passkeys").problems != [], "the premise: the file does not parse"
    assert run(tmp_path, "plan", "passkeys") == 0
    assert ws.load_change("passkeys").problems == [] and len(fake_provider.requests) == 1
