"""What code says of a change's files against each other, with no model: which requirement no task serves, and
which task names a requirement nothing holds."""

from __future__ import annotations

from conftest import seeded
from samples import DELTA, SPEC, TASKS

from adk_spec.domain.check import coverage, coverage_of, nameable, owed
from adk_spec.domain.delta_md import parse_delta
from adk_spec.domain.spec_md import parse_spec
from adk_spec.domain.tasks_md import parse_tasks
from adk_spec.domain.validate import validate_delta
from adk_spec.workspace.files import read_text, write_text
from adk_spec.workspace.layout import findings_of

DELTAS = {"auth": parse_delta(DELTA)}  # adds 004, modifies 002, removes 001
LIVING = {"auth": parse_spec(SPEC)}  # holds 001 and 002, has retired 003
ALL = nameable(DELTAS, LIVING)


def test_a_change_owes_a_task_for_what_it_adds_and_what_it_modifies() -> None:
    assert owed(DELTAS) == {"REQ-AUTH-004", "REQ-AUTH-002"}
    may = nameable(DELTAS, LIVING)
    assert may == {"REQ-AUTH-004", "REQ-AUTH-002", "REQ-AUTH-001"}, "a task may name what the change removes too"


def test_the_sample_task_list_covers_the_sample_delta() -> None:
    assert coverage(parse_tasks(TASKS), owed=owed(DELTAS), nameable=ALL) == []


def test_a_requirement_no_task_names_is_found() -> None:
    wanted = frozenset({"REQ-AUTH-004", "REQ-AUTH-002", "REQ-AUTH-009"})
    found = coverage(parse_tasks(TASKS), owed=wanted, nameable=ALL | wanted)
    assert [(f.code, f.severity) for f in found] == [("check.requirement-no-task", "ERROR")]
    assert "REQ-AUTH-009" in found[0].message


def test_a_task_naming_an_id_nothing_holds_is_found() -> None:
    found = coverage(parse_tasks(TASKS), owed=frozenset(), nameable=frozenset({"REQ-AUTH-004"}))
    assert [(f.code, f.severity) for f in found] == [("check.task-unknown-requirement", "ERROR")]
    assert "T002" in found[0].message and "REQ-AUTH-002" in found[0].message


def test_a_change_with_no_task_yet_owes_no_coverage(tmp_path) -> None:
    ws = seeded(tmp_path)
    (tmp_path / ".spec/changes/passkeys/tasks.md").unlink()
    loaded = ws.load_change("passkeys")
    assert coverage_of(loaded.change, ws.specs()[0]) == []
    assert [f.code for f in findings_of(loaded, ws.specs()[0]) if f.path == "tasks.md"] == ["change.missing-tasks"]


def test_every_command_that_reads_a_change_sees_its_coverage(tmp_path) -> None:
    ws = seeded(tmp_path)
    delta = tmp_path / ".spec/changes/passkeys/specs/auth/spec.md"
    more = (
        "### REQ-AUTH-005: Sign out everywhere\n\nThe system SHALL end every session of a user on request.\n\n"
        "#### Scenario: Asked\n\n- WHEN the user asks to sign out everywhere\n- THEN every session ends\n\n"
    )
    write_text(delta, read_text(delta).replace("## MODIFIED Requirements\n", more + "## MODIFIED Requirements\n"))
    found = [f for f in findings_of(ws.load_change("passkeys"), ws.specs()[0]) if f.code.startswith("check.")]
    assert [(f.code, f.path) for f in found] == [("check.requirement-no-task", "tasks.md")]
    assert "REQ-AUTH-005" in found[0].message


def test_a_modified_requirement_that_did_not_change_is_a_warning() -> None:
    living = LIVING["auth"]
    same = parse_delta(DELTA).model_copy(update={"modified": (living.requirements[1],), "added": (), "removed": ()})
    found = validate_delta(same, living, {})
    assert ("delta.modified-unchanged", "WARNING") in [(f.code, f.severity) for f in found]
    assert not any(f.code == "delta.modified-unchanged" for f in validate_delta(DELTAS["auth"], living, {}))
