"""`adk-spec plan`: a draft change's tasks, and its design where one is owed, drafted behind gates and written whole."""

from __future__ import annotations

import pytest
from conftest import CANNED_TASKS, approved, between, on_the_fake, repository, run, seeded
from samples import SPEC, tasks_for

from adk_spec.domain.spec_md import parse_spec
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
    assert run(tmp_path, "plan", "passkeys", "--replace") == 0
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
    assert run(tmp_path, "plan", "passkeys", "--replace") == 0
    sent = str(fake_provider.requests[0].config.system_instruction)
    assert "# Sign in with a passkey" in sent and "### REQ-AUTH-004: Sign in with a passkey" in sent
    assert "Every change ships with a test." in sent and "REQ-AUTH-001: Sign in with email" in sent


def test_a_change_that_needs_a_design_gets_one_first(tmp_path, fake_provider) -> None:
    ws = seeded(tmp_path)
    ws.save_state(ws.load_change("passkeys").change.state.model_copy(update={"needs_design": True}))
    assert run(tmp_path, "plan", "passkeys", "--replace") == 0
    design = read_text(tmp_path / ".spec/changes/passkeys/design.md")
    assert design.startswith("# Design\n\n## Context\n\nSign-in is one handler") and "## Risks" in design
    assert openings(fake_provider) == [DESIGN, TASKS]
    assert "WebAuthn through the platform API" in str(fake_provider.requests[1].config.system_instruction)


def test_plan_refuses_a_change_that_is_no_draft_and_spends_nothing(tmp_path, capsys, fake_provider) -> None:
    seeded(tmp_path)
    approved(tmp_path)
    capsys.readouterr()
    assert run(tmp_path, "plan", "passkeys", "--replace") == 1 and "approved" in capsys.readouterr().err
    assert fake_provider.requests == []


def test_plan_refuses_a_change_whose_brief_or_deltas_have_an_error(tmp_path, capsys, fake_provider) -> None:
    seeded(tmp_path)
    delta = tmp_path / ".spec/changes/passkeys/specs/auth/spec.md"
    write_text(delta, read_text(delta).replace("### REQ-AUTH-002", "### REQ-AUTH-099"))
    assert run(tmp_path, "plan", "passkeys", "--replace") == 1
    assert "delta.target-missing" in capsys.readouterr().out and fake_provider.requests == []


def test_a_task_list_with_no_task_is_sent_back_then_given_up(tmp_path, capsys, fake_provider) -> None:
    seeded(tmp_path)
    before = read_text(tmp_path / ".spec/changes/passkeys/tasks.md")
    fake_provider.answers_when(TASKS, {"groups": []})
    assert run(tmp_path, "plan", "passkeys", "--replace") == 3
    assert read_text(tmp_path / ".spec/changes/passkeys/tasks.md") == before
    assert "no task" in capsys.readouterr().err and openings(fake_provider) == [TASKS] * 3


def test_plan_holds_the_lock_and_lets_it_go(tmp_path, capsys) -> None:
    seeded(tmp_path)
    (tmp_path / ".spec/.lock").write_text("another run", encoding="utf-8")
    assert run(tmp_path, "plan", "passkeys", "--replace") == 2 and ".spec/.lock" in capsys.readouterr().err
    (tmp_path / ".spec/.lock").unlink()
    assert run(tmp_path, "plan", "passkeys", "--replace") == 0 and not (tmp_path / ".spec/.lock").exists()


def test_plan_replaces_a_task_list_that_does_not_parse(tmp_path, fake_provider) -> None:
    """Found by review: `plan` refused a change over the very file it was about to replace."""
    ws = seeded(tmp_path)
    write_text(tmp_path / ".spec/changes/passkeys/tasks.md", "# Tasks\n\n- [ ] no group, no number\n")
    assert ws.load_change("passkeys").problems != [], "the premise: the file does not parse"
    assert run(tmp_path, "plan", "passkeys", "--replace") == 0
    assert ws.load_change("passkeys").problems == [] and len(fake_provider.requests) == 1


def test_a_task_naming_what_is_no_requirement_id_is_told_which(tmp_path, capsys, fake_provider) -> None:
    """Found by the cleanup review: the read-back ran before the validator, so the model was told to keep each line
    short, three times, and never which ID was wrong."""
    seeded(tmp_path)
    group = CANNED_TASKS["groups"][0]
    bad = {"groups": [{**group, "tasks": [{**group["tasks"][0], "requirements": ["[REQ-AUTH-004]"]}]}]}
    fake_provider.answers_when(TASKS, bad)
    assert run(tmp_path, "plan", "passkeys", "--replace") == 3
    assert "tasks.bad-requirement-id" in capsys.readouterr().err


def test_a_plan_that_serves_only_one_requirement_is_sent_back(tmp_path, capsys, fake_provider) -> None:
    """The change adds REQ-AUTH-004 and modifies REQ-AUTH-002: a task list for the first alone is half a plan."""
    seeded(tmp_path)
    before = read_text(tmp_path / ".spec/changes/passkeys/tasks.md")
    group = CANNED_TASKS["groups"][0]
    fake_provider.answers_when(TASKS, {"groups": [{**group, "tasks": [group["tasks"][0]]}]})
    assert run(tmp_path, "plan", "passkeys", "--replace") == 3
    err = capsys.readouterr().err
    assert "check.requirement-no-task" in err and "REQ-AUTH-002" in err
    assert read_text(tmp_path / ".spec/changes/passkeys/tasks.md") == before and openings(fake_provider) == [TASKS] * 3


def test_a_plan_may_not_name_a_requirement_nothing_holds(tmp_path, capsys, fake_provider) -> None:
    seeded(tmp_path)
    group = CANNED_TASKS["groups"][0]
    stray = {**group["tasks"][1], "requirements": ["REQ-AUTH-004", "REQ-AUTH-002", "REQ-AUTH-042"]}
    fake_provider.answers_when(TASKS, {"groups": [{**group, "tasks": [group["tasks"][0], stray]}]})
    assert run(tmp_path, "plan", "passkeys", "--replace") == 3
    err = capsys.readouterr().err
    assert "check.task-unknown-requirement" in err and "REQ-AUTH-042" in err


def test_plans_stages_are_shown_the_repositorys_files(tmp_path, fake_provider) -> None:
    """The first live run: file paths in the tasks were invented, and differed between two changes of one repository."""
    ws = seeded(tmp_path)
    ws.save_state(ws.load_change("passkeys").change.state.model_copy(update={"needs_design": True}))
    repository(tmp_path, {"src/app.py": "x = 1\n", "tests/test_app.py": "def test_x(): ...\n"})
    assert run(tmp_path, "plan", "passkeys", "--replace") == 0
    design, tasks = (between(str(r.config.system_instruction), "tree") for r in fake_provider.requests)
    assert design == tasks == "src/app.py\ntests/test_app.py", "what git tracks, and nothing of .spec/"


def test_outside_a_repository_the_stages_are_shown_no_files(tmp_path, fake_provider) -> None:
    seeded(tmp_path)
    assert run(tmp_path, "plan", "passkeys", "--replace") == 0
    assert between(str(fake_provider.requests[0].config.system_instruction), "tree") == ""


def test_plan_reads_a_design_written_by_hand(tmp_path, fake_provider) -> None:
    seeded(tmp_path)
    write_text(tmp_path / ".spec/changes/passkeys/design.md", "# Design\n\nPasskeys go through the platform API.\n")
    assert run(tmp_path, "plan", "passkeys", "--replace") == 0
    assert openings(fake_provider) == [TASKS], "no design is drafted where the brief owes none"
    held = between(str(fake_provider.requests[0].config.system_instruction), "design")
    assert held == "# Design\n\nPasskeys go through the platform API."
    assert "platform API" in read_text(tmp_path / ".spec/changes/passkeys/design.md"), "and it is left as it was"


def test_plan_does_not_replace_a_task_list_someone_has_started(tmp_path, capsys, fake_provider) -> None:
    seeded(tmp_path)  # the sample task list has T002 ticked
    before = read_text(tmp_path / ".spec/changes/passkeys/tasks.md")
    assert run(tmp_path, "plan", "passkeys") == 1
    assert "--replace" in capsys.readouterr().err and fake_provider.requests == []
    assert read_text(tmp_path / ".spec/changes/passkeys/tasks.md") == before
    assert run(tmp_path, "plan", "passkeys", "--replace") == 0


def test_plan_says_when_it_replaced_a_file(tmp_path, capsys, fake_provider) -> None:
    seeded(tmp_path)
    tasks = tmp_path / ".spec/changes/passkeys/tasks.md"
    write_text(tasks, tasks_for("REQ-AUTH-004", "REQ-AUTH-002"))  # no box ticked: nothing was started
    assert run(tmp_path, "plan", "passkeys") == 0
    assert "replaced  .spec/changes/passkeys/tasks.md" in capsys.readouterr().out
    tasks.unlink()
    assert run(tmp_path, "plan", "passkeys") == 0
    assert "wrote     .spec/changes/passkeys/tasks.md" in capsys.readouterr().out and len(fake_provider.requests) == 2


def test_plan_does_not_replace_a_started_list_that_no_longer_parses(tmp_path, capsys, fake_provider) -> None:
    """Found by the code review: a task list off its grammar reads as no list, so its ticked boxes were not seen
    and it was replaced unasked."""
    seeded(tmp_path)
    tasks = tmp_path / ".spec/changes/passkeys/tasks.md"
    write_text(tasks, read_text(tasks).replace("## 1. Passkey sign-in", "### 1. Passkey sign-in"))
    before = read_text(tasks)
    assert run(tmp_path, "plan", "passkeys") == 1
    assert "--replace" in capsys.readouterr().err and fake_provider.requests == [] and read_text(tasks) == before


def test_plan_waits_for_every_living_spec_to_read(tmp_path, capsys, fake_provider) -> None:
    ws = seeded(tmp_path)
    ws.write_specs({"billing": parse_spec(SPEC.replace("# auth", "# billing").replace("REQ-AUTH", "REQ-BILLING"))})
    spec = tmp_path / ".spec/specs/billing/spec.md"
    write_text(spec, read_text(spec).replace("## Requirements", "## Requirments"))
    assert run(tmp_path, "plan", "passkeys", "--replace") == 1
    assert "living spec does not read" in capsys.readouterr().err and fake_provider.requests == []
