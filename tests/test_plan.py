"""`adk-spec plan`: a draft change's tasks, and its design where one is owed, drafted behind gates and written whole."""

from __future__ import annotations

import pytest
from conftest import (
    API,
    CANNED_REVIEW,
    CANNED_TASKS,
    approved,
    beside,
    between,
    on_the_fake,
    repository,
    run,
    seeded,
    sent_to,
    state_of,
)
from samples import DELTA, SPEC, tasks_for

from adk_spec.domain.spec_md import parse_spec
from adk_spec.interfaces.cli import main
from adk_spec.workspace.files import read_text, write_text
from adk_spec.workspace.layout import Workspace
from adk_spec.workspace.source import repositories_named

DESIGN, TASKS = "You write the design of a change", "You break a change into tasks"
SCOUT, SURVEY = "You choose what to read", "You read parts of a repository's code"
REVIEW = "You review what a reading of a repository's code found"


def openings(fake_provider) -> list[str]:
    known = (DESIGN, TASKS, SCOUT, SURVEY, REVIEW)
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
    assert ".spec/changes/passkeys/tasks.md" in out and "tokens    120 in 1 call\n" in out and "approve passkeys" in out
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
    assert run(tmp_path, "plan", "passkeys", "--replace") == 1
    said = capsys.readouterr().err
    assert "approved" in said and fake_provider.requests == []
    # Found by the fourth audit: the refusal named no way to change what an approved change asks.
    assert 'adk-spec propose "<what changes>" --id passkeys' in said and "tasks.md" in said


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
    assert openings(fake_provider)[-2:] == [DESIGN, TASKS]
    design, tasks = (between(str(r.config.system_instruction), "tree") for r in fake_provider.requests[-2:])
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


def test_the_fakes_default_tasks_serve_what_the_requests_deltas_owe() -> None:
    """The fake's one answer that is fitted to its request. Unpinned, a change to a delta's headings or to what is
    owed would show as some fifty failed plans, far from the cause."""
    from conftest import CANNED_TASKS, tasks_serving

    from adk_spec.orchestration.stages import BOUNDARY

    def shown(deltas: str) -> str:
        return f"## The requirement deltas\n<<< deltas {BOUNDARY}\n{deltas}\n>>> deltas {BOUNDARY}\n"

    def named(tasks: dict) -> set[str]:
        return {req for group in tasks["groups"] for task in group["tasks"] for req in task["requirements"]}

    assert tasks_serving(shown(DELTA)) is CANNED_TASKS, "the sample change owes what the canned tasks name"
    other = "# Delta: billing-export\n\n## ADDED Requirements\n\n### REQ-BILLING-EXPORT-007: Export\n\n"
    other += "## MODIFIED Requirements\n\n### REQ-AUTH-002: Lock\n\n## REMOVED Requirements\n\n### REQ-AUTH-001: Old\n"
    owed = {"REQ-BILLING-EXPORT-007", "REQ-AUTH-002", "REQ-AUTH-001"}
    assert named(tasks_serving(shown(other))) == owed, "what is removed is owed the task that takes it out"
    assert tasks_serving("no deltas are shown here") is CANNED_TASKS


def test_the_plan_is_shown_no_excluded_file(tmp_path, fake_provider) -> None:
    seeded(tmp_path)
    repository(tmp_path, {"src/app.py": "x = 1\n", "vendor/lib.py": "y = 2\n"})
    project = '[project]\ndefault_tier = "lean"\n\n[repository]\n'
    write_text(tmp_path / ".spec/config.toml", project + 'exclude = ["vendor/**"]\n')
    assert run(tmp_path, "plan", "passkeys", "--replace") == 0
    shown = between(str(fake_provider.requests[0].config.system_instruction), "tree")
    assert "src/app.py" in shown and "vendor" not in shown


# The plan reads the code first: brownfield, part 1.

CONTEXT = ".spec/changes/passkeys/context.md"
STATED = "- `src/app.py:2` Sign-in is decided here.\n  in: def login():\n  > return password()"


def stages(fake_provider) -> list[str]:
    """The stage each request went to, in order."""
    names = {SCOUT: "scout", SURVEY: "survey", REVIEW: "review", TASKS: "tasks", DESIGN: "design"}
    return [names[opening] for opening in openings(fake_provider)]


def test_plan_reads_the_code_and_the_tasks_are_shown_what_it_found(tmp_path, capsys, fake_provider) -> None:
    seeded(tmp_path)
    repository(tmp_path)
    capsys.readouterr()
    assert run(tmp_path, "plan", "passkeys", "--replace") == 0
    context = read_text(tmp_path / CONTEXT)
    assert context.startswith("# Context: passkeys\n\nRead from the repository at commit ")
    assert "## Where the change plugs in\n\n" + STATED in context and "- src/app.py (whole)" in context
    assert stages(fake_provider) == ["scout", "survey", "review", "tasks"]
    shown = between(str(fake_provider.requests[-1].config.system_instruction), "context")
    assert shown == context.rstrip("\n"), "the tasks stage reads the file as it was written"
    out = capsys.readouterr().out
    assert "explored  1 file: 1 statement kept" in out and CONTEXT in out
    assert "tokens    480 in 4 calls\n" in out


def test_a_context_that_is_there_is_kept_and_read(tmp_path, fake_provider) -> None:
    seeded(tmp_path)
    repository(tmp_path)
    mine = "# Context: passkeys\n\nSign-in lives in src/app.py, and I checked it myself.\n"
    write_text(tmp_path / CONTEXT, mine)
    assert run(tmp_path, "plan", "passkeys", "--replace") == 0
    assert stages(fake_provider) == ["tasks"] and read_text(tmp_path / CONTEXT) == mine
    assert "I checked it myself." in between(str(fake_provider.requests[0].config.system_instruction), "context")


def test_no_explore_reads_nothing(tmp_path, fake_provider) -> None:
    seeded(tmp_path)
    repository(tmp_path)
    assert run(tmp_path, "plan", "passkeys", "--replace", "--no-explore") == 0
    assert stages(fake_provider) == ["tasks"] and not (tmp_path / CONTEXT).exists()


def test_outside_a_repository_nothing_is_read_and_the_plan_is_drafted(tmp_path, fake_provider) -> None:
    seeded(tmp_path)
    assert run(tmp_path, "plan", "passkeys", "--replace") == 0
    assert stages(fake_provider) == ["tasks"] and not (tmp_path / CONTEXT).exists()


def test_a_reading_that_fails_does_not_stop_the_plan(tmp_path, capsys, fake_provider) -> None:
    """A reading is a help to the plan and no gate of it: the plan is drafted without it, and the command says so."""
    ws = seeded(tmp_path)
    repository(tmp_path)
    fake_provider.raises_when(SURVEY, RuntimeError("the provider fell over"))
    capsys.readouterr()
    assert run(tmp_path, "plan", "passkeys", "--replace") == 0
    said = capsys.readouterr()
    assert "explored  nothing: " in said.out and "the provider fell over" in said.out
    assert not (tmp_path / CONTEXT).exists() and ws.load_change("passkeys").change.tasks
    assert stages(fake_provider)[-1] == "tasks"


def test_a_scout_that_finds_nothing_to_read_says_so_and_the_plan_is_drafted(tmp_path, capsys, fake_provider) -> None:
    seeded(tmp_path)
    repository(tmp_path, {"lib/other.py": "x = 1\n"})
    fake_provider.answers_when(SCOUT, {"files": ["src/gone.py"], "folders": [], "searches": [], "reason": "A guess."})
    capsys.readouterr()
    assert run(tmp_path, "plan", "passkeys", "--replace") == 0
    assert "explored  nothing: nothing the scout named could be read" in capsys.readouterr().out
    assert stages(fake_provider) == ["scout", "tasks"] and not (tmp_path / CONTEXT).exists()


def test_a_ceiling_holds_the_reading_to_half_and_keeps_what_it_read(tmp_path, capsys, fake_provider) -> None:
    """The reading spends at most half of what is left, keeps what it read by then, and the plan is drafted."""
    seeded(tmp_path)
    repository(tmp_path)
    write_text(tmp_path / ".spec/config.toml", '[project]\ndefault_tier = "lean"\n\n[limits]\nmax_tokens = 480\n')
    capsys.readouterr()
    assert run(tmp_path, "plan", "passkeys", "--replace") == 0, "the scout and the survey spent its half"
    assert STATED in read_text(tmp_path / CONTEXT), "what was read is kept"
    assert stages(fake_provider) == ["scout", "survey", "tasks"]
    assert "the reading's share of the run's token ceiling of 480" in capsys.readouterr().out


def test_a_secret_in_a_tracked_file_reaches_no_request_no_recording_and_no_context(tmp_path, fake_provider) -> None:
    from adk_spec.workspace.layout import Workspace
    from adk_spec.workspace.runs import listed

    key = "AKIA" + "IOSFODNN7EXAMPLE"
    seeded(tmp_path)
    repository(tmp_path, {"src/app.py": f'def login():\n    return password()\n\n\nAPI = "{key}"\n'})
    leaked = {"kind": "risk", "file": "src/app.py", "quote": f'API = "{key}"', "note": "A key is in the code."}
    real = {"kind": "touches", "file": "src/app.py", "quote": "return password()", "note": "Sign-in is decided here."}
    answer = {"statements": [leaked, real], "more_files": [], "more_folders": [], "more_searches": []}
    fake_provider.answers_when(SURVEY, answer)
    assert run(tmp_path, "plan", "passkeys", "--replace") == 0
    assert all(key not in str(r.config.system_instruction) for r in fake_provider.requests)
    assert "[REDACTED" in between(str(fake_provider.requests[1].config.system_instruction), "material")
    assert all(key not in read_text(path) for path in listed(Workspace.find(tmp_path)))
    context = read_text(tmp_path / CONTEXT)
    assert key not in context and STATED in context and "Left out: 1 statement" in context


@pytest.mark.usefixtures("fake_provider")
def test_context_md_is_no_part_of_an_approval(tmp_path, capsys) -> None:
    from conftest import state_of

    seeded(tmp_path)
    repository(tmp_path)
    assert (
        run(tmp_path, "plan", "passkeys", "--replace") == 0 and run(tmp_path, "approve", "passkeys", "--by", "r") == 0
    )
    assert "context.md" not in state_of(tmp_path)["approval"]["files"]
    write_text(tmp_path / CONTEXT, read_text(tmp_path / CONTEXT) + "\nA note of mine.\n")
    capsys.readouterr()
    assert run(tmp_path, "status") == 0 and "approve again" not in capsys.readouterr().out


def test_a_context_that_is_no_text_is_said_and_not_read_as_none(tmp_path, capsys, fake_provider) -> None:
    """Found by the cleanup review: a `context.md` saved in another encoding was read as nothing, and being there
    it also stopped the code from being read."""
    seeded(tmp_path)
    repository(tmp_path)
    (tmp_path / CONTEXT).write_bytes(bytes([0xFF, 0xFE, 0x43, 0x00]))
    assert run(tmp_path, "plan", "passkeys", "--replace") == 2
    assert "context.md is not UTF-8" in capsys.readouterr().err and fake_provider.requests == []


# The other repositories a change spans: phase 7.

ROUTES = {
    "kind": "touches",
    "file": "api/src/routes.py",
    "quote": "return start_session(request.user)",
    "note": "Here.",
}


@pytest.mark.usefixtures("fake_provider")
def test_plan_with_adds_a_repository_and_a_name_given_again_takes_its_new_path(tmp_path) -> None:
    root = beside(tmp_path)
    repository(tmp_path / "api-2", API)
    repository(tmp_path / "web", {"index.js": "export const x = 1;\n"})
    assert run(root, "plan", "passkeys", "--replace", "--no-explore", "--with", "../api") == 0
    assert state_of(root, "passkeys")["repositories"] == {"api": "../api"}
    assert run(root, "plan", "passkeys", "--replace", "--no-explore", "--with", "api=../api-2", "--with", "../web") == 0
    assert state_of(root, "passkeys")["repositories"] == {"api": "../api-2", "web": "../web"}


def test_the_scout_is_shown_each_repository_and_a_statement_may_name_one(tmp_path, fake_provider) -> None:
    root = beside(tmp_path)
    fake_provider.answers_when(SCOUT, {"files": ["api/src/routes.py"], "folders": [], "searches": [], "reason": "API."})
    fake_provider.answers_when(
        SURVEY, {"statements": [ROUTES], "more_files": [], "more_folders": [], "more_searches": []}
    )
    assert run(root, "plan", "passkeys", "--replace", "--with", "../api") == 0
    assert "=== api (1 file)\napi/src/routes.py" in between(
        str(fake_provider.requests[0].config.system_instruction), "tree"
    )
    assert (
        "- `api/src/routes.py:2` Here.\n  in: def sign_in(request):\n  > return start_session(request.user)"
        in read_text(root / CONTEXT)
    )


@pytest.mark.usefixtures("fake_provider")
def test_a_missing_repository_is_said_and_the_plan_goes_on(tmp_path, capsys) -> None:
    root = beside(tmp_path)
    holding(root, api="../api", web="../web")  # recorded in the change, and not on this machine
    capsys.readouterr()
    assert run(root, "plan", "passkeys", "--replace") == 0
    out = capsys.readouterr().out
    assert "left out  web: no git repository at ../web\n" in out and ".spec/changes/passkeys/tasks.md" in out


@pytest.mark.parametrize(
    "given", [["--with", ".."], ["--with", "9x=../a"], ["--with", "api=../a", "--with", "api=../b"]]
)
def test_a_with_whose_name_cannot_be_made_is_refused(tmp_path, fake_provider, given) -> None:
    root = beside(tmp_path)
    assert run(root, "plan", "passkeys", "--replace", *given) == 2
    assert fake_provider.requests == [] and not state_of(root, "passkeys").get("repositories")


def test_a_path_typed_with_backslashes_is_recorded_with_slashes() -> None:
    assert repositories_named(["..\\api"], {}) == {"api": "../api"}


def test_plan_with_on_a_change_that_has_a_context_keeps_it_and_says_how_to_read_again(
    tmp_path, capsys, fake_provider
) -> None:
    root = beside(tmp_path)
    write_text(root / CONTEXT, "# Context: passkeys\n\nRead by hand.\n")
    capsys.readouterr()
    assert run(root, "plan", "passkeys", "--replace", "--with", "../api") == 0
    assert "delete it to read again" in capsys.readouterr().out and stages(fake_provider) == ["tasks"]


def test_propose_says_how_many_repositories_and_unknowns(tmp_path, capsys, fake_provider) -> None:
    root = beside(tmp_path)
    app = {"kind": "touches", "file": "src/app.py", "quote": "return password()", "note": "Sign-in."}
    invented = {**app, "quote": "return no_such_call()"}
    fake_provider.answers_when(
        SCOUT, {"files": ["src/app.py", "api/src/routes.py"], "folders": [], "searches": [], "reason": "Both."}
    )
    fake_provider.answers_when(
        SURVEY, {"statements": [app, ROUTES, invented], "more_files": [], "more_folders": [], "more_searches": []}
    )
    fake_provider.answers_when(REVIEW, {**CANNED_REVIEW, "unknown": [{"question": "Who ends a session?", "where": ""}]})
    capsys.readouterr()
    assert run(root, "plan", "passkeys", "--replace", "--with", "../api") == 0
    assert "explored  2 files in 2 repositories: 2 statements kept, 1 left out, 1 unknown\n" in capsys.readouterr().out
    assert "## What is still unknown\n\n- Who ends a session?\n" in read_text(root / CONTEXT)


def test_a_review_that_disputes_every_statement_writes_no_context_and_says_so(tmp_path, capsys, fake_provider) -> None:
    seeded(tmp_path)
    repository(tmp_path)
    fake_provider.answers_when(
        REVIEW, {**CANNED_REVIEW, "unknown": [], "disputed": [{"statement": 1, "reason": "No."}]}
    )
    capsys.readouterr()
    assert run(tmp_path, "plan", "passkeys", "--replace") == 0
    assert "explored  nothing: the review disputed every statement\n" in capsys.readouterr().out
    assert not (tmp_path / CONTEXT).exists()


def test_design_and_tasks_are_told_not_to_plan_on_an_unknown(tmp_path, fake_provider) -> None:
    ws = seeded(tmp_path)
    ws.save_state(ws.load_change("passkeys").change.state.model_copy(update={"needs_design": True}))
    assert run(tmp_path, "plan", "passkeys", "--replace", "--no-explore") == 0
    rule = "do not plan on it as if it were known: a task that depends on it says so"
    assert all(rule in " ".join(str(request.config.system_instruction).split()) for request in fake_provider.requests)


def holding(root, **repositories: str) -> None:
    """The change's repositories as its state records them, set by hand."""
    ws = Workspace.find(root)
    state = ws.load_change("passkeys").change.state
    ws.save_state(state.model_copy(update={"repositories": repositories}))


@pytest.mark.usefixtures("fake_provider")
def test_every_other_repository_read_is_named(tmp_path, capsys) -> None:
    """A change's state is a file a teammate may commit: a repository read on the strength of it is said."""
    root = beside(tmp_path)
    holding(root, api="../api")
    capsys.readouterr()
    assert run(root, "plan", "passkeys", "--replace") == 0
    assert "with      api from ../api\n" in capsys.readouterr().out


@pytest.mark.usefixtures("fake_provider")
def test_a_plan_with_that_is_refused_changes_nothing_and_a_new_path_drops_its_old_start(tmp_path) -> None:
    root = beside(tmp_path)
    assert run(root, "plan", "passkeys", "--with", "../api") == 1, "a task is ticked: no --replace, no plan"
    assert not state_of(root).get("repositories")
    ws = Workspace.find(root)
    state = ws.load_change("passkeys").change.state
    ws.save_state(state.model_copy(update={"repositories": {"api": "../api"}, "base_commits": {"api": "c0ffee"}}))
    repository(tmp_path / "api-2", API)
    assert run(root, "plan", "passkeys", "--replace", "--no-explore", "--with", "api=../api-2") == 0
    assert (state_of(root)["repositories"], state_of(root)["base_commits"]) == ({"api": "../api-2"}, {})


@pytest.mark.usefixtures("fake_provider")
def test_a_relative_with_is_read_from_the_folder_the_command_runs_in(tmp_path) -> None:
    root = beside(tmp_path)
    (root / "web").mkdir()
    assert (
        main(["--root", str(root / "web"), "plan", "passkeys", "--replace", "--no-explore", "--with", "../../api"]) == 0
    )
    assert state_of(root)["repositories"] == {"api": "../api"}


@pytest.mark.usefixtures("fake_provider")
def test_a_reading_without_a_repository_of_the_change_is_partial(tmp_path) -> None:
    """context.md is kept and used by every later plan: one written without a repository of the change says so,
    and a later plan says to read again."""
    root = beside(tmp_path)
    holding(root, api="../api", web="../web")
    assert run(root, "plan", "passkeys", "--replace") == 0
    assert "This reading is partial: web: no git repository at ../web." in read_text(root / CONTEXT)


def test_a_with_that_names_no_repository_is_refused_before_any_call(tmp_path, capsys, fake_provider) -> None:
    root = beside(tmp_path)
    assert run(root, "plan", "passkeys", "--replace", "--with", "../apl") == 2
    assert "apl: no git repository at ../apl" in capsys.readouterr().err and fake_provider.requests == []
    assert not state_of(root).get("repositories")


# Phase 8: every change's reading starts from the repository's profile.


def test_the_scout_and_the_plan_are_shown_the_profile(tmp_path, fake_provider) -> None:
    ws = seeded(tmp_path)
    ws.save_state(ws.load_change("passkeys").change.state.model_copy(update={"needs_design": True}))
    repository(tmp_path)
    write_text(tmp_path / ".spec/profile.md", "# This repository\n\nTests stand beside the code.\n")
    assert run(tmp_path, "plan", "passkeys", "--replace") == 0
    for opening in (SCOUT, DESIGN, TASKS):
        assert (
            between(sent_to(fake_provider, opening), "profile") == "# This repository\n\nTests stand beside the code."
        )


def test_with_no_profile_no_stage_is_shown_one(tmp_path, fake_provider) -> None:
    seeded(tmp_path)
    repository(tmp_path)
    assert run(tmp_path, "plan", "passkeys", "--replace") == 0
    assert between(sent_to(fake_provider, SCOUT), "profile") == "" == between(sent_to(fake_provider, TASKS), "profile")


@pytest.mark.usefixtures("fake_provider")
def test_a_profile_that_is_no_text_is_said_and_the_plan_goes_on(tmp_path, capsys) -> None:
    """Re-saved by Windows PowerShell 5.1, the profile is UTF-16: optional material, it stops no plan."""
    seeded(tmp_path)
    (tmp_path / ".spec/profile.md").write_bytes("# This repository\n".encode("utf-16"))
    capsys.readouterr()
    assert run(tmp_path, "plan", "passkeys", "--replace") == 0
    assert "left out  .spec/profile.md is not UTF-8: no stage reads it" in capsys.readouterr().out


def test_plans_own_reading_looks_into_the_installed_libraries_as_proposes_does(tmp_path, fake_provider) -> None:
    """Found by review of phase 15: a change with no context.md, read by `plan`, was read without the installed
    libraries `propose` reads: one reading, one scope."""
    from conftest import python_environment, repository

    seeded(tmp_path)
    repository(tmp_path, {".gitignore": ".venv/\n", "src/app.py": "import httpx\n"})
    python_environment(tmp_path)
    assert run(tmp_path, "plan", "passkeys", "--replace") == 0
    scout = next(
        str(r.config.system_instruction)
        for r in fake_provider.requests
        if str(r.config.system_instruction).startswith("You choose what to read")
    )
    assert "httpx 0.28.1" in scout


@pytest.mark.usefixtures("fake_provider")
def test_a_plan_with_nothing_to_read_asks_after_no_reading_model(tmp_path, monkeypatch) -> None:
    """Found by review: the reading's models were asked after before anything showed there was code to read, and a
    plan outside a repository failed on a model it would never call."""
    seeded(tmp_path)
    monkeypatch.setenv("SPEC_SCOUT_MODEL", "gpt-4.1")  # one the fake arm cannot run on
    assert run(tmp_path, "plan", "passkeys", "--replace") == 0


def test_the_plan_command_after_a_stop_reads_the_code_where_no_context_was_written(tmp_path) -> None:
    """Found by review: it always said --no-explore, also where propose's reading wrote no context.md."""
    from adk_spec.interfaces.cli import _plan_command

    seeded(tmp_path)
    ws = Workspace(tmp_path)
    assert _plan_command(ws, "passkeys", None, False) == "`adk-spec plan passkeys`"
    assert _plan_command(ws, "passkeys", None, True) == "`adk-spec plan passkeys --no-explore`"
    (tmp_path / ".spec/changes/passkeys/context.md").write_text("# Context: passkeys\n", encoding="utf-8")
    # A context.md there makes `plan` skip the reading: the flag would say it twice (the audit of 25 November, U9).
    assert _plan_command(ws, "passkeys", None, False) == "`adk-spec plan passkeys`"
    assert _plan_command(ws, "passkeys", None, True) == "`adk-spec plan passkeys`"


def test_plan_on_a_verified_change_names_a_new_change_not_a_revision(tmp_path, capsys, fake_provider) -> None:
    """Found by the code review: the refusal named `propose --id`, which refuses a verified change in its turn."""
    ws = seeded(tmp_path)
    ws.save_state(ws.load_change("passkeys").change.state.model_copy(update={"status": "verified"}))
    capsys.readouterr()
    assert run(tmp_path, "plan", "passkeys") == 1
    said = capsys.readouterr().err
    assert "--id" not in said and "Propose a new change" in said and fake_provider.requests == []


def test_the_plan_is_told_what_imports_and_tests_the_files_the_reading_found(tmp_path, fake_provider) -> None:
    """A lead from the code graph, which the tasks stage weighs: it reads names and imports, not the code."""
    from conftest import between

    from adk_spec.domain.context_md import render_context
    from adk_spec.domain.model import Statement

    seeded(tmp_path)
    repository(
        tmp_path,
        {"src/app.py": "def login():\n    return password()\n", "tests/test_app.py": "from src.app import login\n"},
    )
    found = Statement(kind="touches", path="src/app.py", line=2, quote="return password()", note="Sign-in.")
    context = render_context("Context: passkeys", at="today", commit=None, statements=[found], read=["src/app.py"])
    write_text(tmp_path / ".spec/changes/passkeys/context.md", context)
    assert run(tmp_path, "plan", "passkeys", "--replace", "--no-explore") == 0
    tasks = next(
        text
        for text in (str(r.config.system_instruction) for r in fake_provider.requests)
        if text.startswith("You break a change")
    )
    assert between(tasks, "reach") == "- src/app.py: tested by tests/test_app.py"
