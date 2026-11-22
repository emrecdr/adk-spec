"""The lessons file, `.spec/lessons.md`: what a gate sent back that the next try fixed, and what a person wrote,
read by every drafting stage."""

from __future__ import annotations

import pytest
from conftest import BRIEF_OWING_A_DESIGN, DELTAS_ON_A_MISSING_ID, between, on_the_fake, run, seeded, sent_to

from adk_spec.domain.lessons_md import GATE_HEADING, TEMPLATE, learned
from adk_spec.workspace.context import lessons_text
from adk_spec.workspace.files import read_text, write_text
from adk_spec.workspace.layout import LESSONS, Workspace

MISSING = "delta.target-missing: REQ-AUTH-099 is not in the living spec of `auth`. Modify only a living requirement."
TOKEN = "ghp_" + "a1B2c3D4" * 5


def gate_lines(text: str) -> list[str]:
    return [line for line in text.splitlines() if line.startswith("- ") and ", `" in line]


def test_a_problem_sent_back_is_added_under_the_gate_heading_by_its_stage_and_code() -> None:
    text = learned(TEMPLATE, [("deltas", MISSING)])
    assert gate_lines(text) == [
        "- deltas, `delta.target-missing` (1): REQ-AUTH-099 is not in the living spec of `auth`. Modify only a "
        "living requirement."
    ]
    assert text.index(GATE_HEADING) < text.index("- deltas")


def test_the_same_fault_again_is_counted_and_not_added() -> None:
    twice = learned(learned(TEMPLATE, [("deltas", MISSING)]), [("deltas", MISSING.replace("099", "100"))])
    (line,) = gate_lines(twice)
    assert line.startswith("- deltas, `delta.target-missing` (2): REQ-AUTH-099")


def test_the_same_code_from_another_stage_is_a_lesson_of_its_own() -> None:
    text = learned(TEMPLATE, [("deltas", MISSING), ("tasks", MISSING)])
    assert [line.split(" (")[0] for line in gate_lines(text)] == [
        "- deltas, `delta.target-missing`",
        "- tasks, `delta.target-missing`",
    ]


def test_an_engine_fault_with_no_code_is_no_lesson() -> None:
    faults = [("brief", "the answer did not match its schema."), ("deltas", "the answer repeats a marker line.")]
    assert learned(TEMPLATE, faults) == TEMPLATE


def test_a_persons_lines_are_kept_and_a_file_with_no_gate_heading_gains_one() -> None:
    mine = "# Lessons\n\n- Name a requirement after what the user does.\n- deltas, `delta.target-missing` (9): mine\n"
    text = learned(mine, [("deltas", MISSING)])
    assert text.startswith(mine) and GATE_HEADING in text
    assert "(9): mine" in text and "- deltas, `delta.target-missing` (1): REQ-AUTH-099" in text


def test_a_lesson_is_one_line_scrubbed_and_cut() -> None:
    long = f"delta.round-trip: the token {TOKEN} was in it\nand " + "a word " * 80
    (line,) = gate_lines(learned(TEMPLATE, [("deltas", long)]))
    assert TOKEN not in line and "\n" not in line and len(line) <= 260


def test_init_writes_the_lessons_file_and_a_workspace_without_one_gains_it(tmp_path) -> None:
    ws = Workspace.init(tmp_path / "new")
    assert read_text(ws.home / LESSONS) == TEMPLATE
    old = Workspace.init(tmp_path / "old")
    (old.home / LESSONS).unlink()
    assert lessons_text(old) == ""
    old.learn([("deltas", MISSING)])
    assert "delta.target-missing" in read_text(old.home / LESSONS) and "delta.target-missing" in lessons_text(old)


def test_nothing_learned_leaves_the_file_as_it_stands(tmp_path) -> None:
    ws = Workspace.init(tmp_path)
    write_text(ws.home / LESSONS, "# Mine\n")
    ws.learn([])
    ws.learn([("brief", "an engine fault.")])
    assert read_text(ws.home / LESSONS) == "# Mine\n"


BRIEF, DELTAS = "You write the brief of a change", "You write the requirement deltas"
DESIGN, TASKS = "You write the design of a change", "You break a change into tasks"
MINE = "- Name a requirement after what the user does, not after the screen."


def proposed(root, *argv: str) -> int:
    return run(
        root, "propose", "Let users sign in with a passkey.", "--tier", "lean", "--no-input", "--no-explore", *argv
    )


def test_a_stage_sent_back_and_then_put_right_teaches_the_workspace(tmp_path, monkeypatch, fake_provider) -> None:
    on_the_fake(monkeypatch)
    seeded(tmp_path)
    fake_provider.answers_each_time(DELTAS, iter([DELTAS_ON_A_MISSING_ID, None]))
    fake_provider.answers_each_time(TASKS, iter([{"groups": []}, None]))
    assert proposed(tmp_path, "--id", "taught") == 0
    lessons = read_text(tmp_path / ".spec" / LESSONS)
    assert "- deltas, `delta.target-missing` (1): REQ-AUTH-099" in lessons and "- tasks, `tasks.empty` (1)" in lessons


@pytest.mark.parametrize("stage", [BRIEF, DELTAS, DESIGN, TASKS])
def test_every_drafting_stage_reads_the_lessons(tmp_path, monkeypatch, fake_provider, stage) -> None:
    on_the_fake(monkeypatch)
    ws = seeded(tmp_path)
    write_text(ws.home / LESSONS, TEMPLATE.replace("## From people\n", f"## From people\n\n{MINE}\n"))
    fake_provider.answers_when(BRIEF, BRIEF_OWING_A_DESIGN)
    assert proposed(tmp_path, "--id", "read") == 0
    assert MINE in between(sent_to(fake_provider, stage), "lessons")


def test_a_workspace_with_no_lesson_yet_sends_none(tmp_path, monkeypatch, fake_provider) -> None:
    on_the_fake(monkeypatch)
    seeded(tmp_path)
    assert proposed(tmp_path, "--id", "none") == 0
    assert between(sent_to(fake_provider, BRIEF), "lessons") == ""
