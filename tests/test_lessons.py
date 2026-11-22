"""The lessons file, `.spec/lessons.md`: what a gate sent back that the next try fixed, and what a person wrote,
read by every drafting stage."""

from __future__ import annotations

import pytest
from conftest import (
    BRIEF_OWING_A_DESIGN,
    DELTAS_ON_A_MISSING_ID,
    approved,
    between,
    on_the_fake,
    run,
    seeded,
    sent_to,
    state_of,
)

from adk_spec.domain.lessons_md import GATE_HEADING, TEMPLATE, as_read, learned
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


NUDGE = "lessons   "


def drafted_and_approved(root, monkeypatch, capsys, edit=None) -> str:
    """A change `propose` drafted, `edit` applied to its folder, then approved: what `approve` printed."""
    on_the_fake(monkeypatch)
    seeded(root)
    assert proposed(root, "--id", "drafted") == 0
    if edit:
        edit(root / ".spec/changes/drafted")
    capsys.readouterr()
    approved(root, "drafted")
    return capsys.readouterr().out


def appended(path, line: str) -> None:
    write_text(path, read_text(path).rstrip("\n") + f"\n\n{line}\n")


@pytest.mark.usefixtures("fake_provider")
def test_approve_names_a_drafted_file_a_person_edited_once(tmp_path, monkeypatch, capsys) -> None:
    out = drafted_and_approved(tmp_path, monkeypatch, capsys, lambda folder: appended(folder / "brief.md", "By hand."))
    (said,) = [line for line in out.splitlines() if line.startswith(NUDGE)]
    assert "brief.md edited since drafted" in said and ".spec/lessons.md" in said
    held = state_of(tmp_path, "drafted")
    assert held["drafted"]["brief.md"] == held["approval"]["files"]["brief.md"], "the same edit is not named again"


@pytest.mark.usefixtures("fake_provider")
def test_approve_says_nothing_of_drafts_untouched_or_only_ticked(tmp_path, monkeypatch, capsys) -> None:
    def ticked(folder) -> None:
        tasks = folder / "tasks.md"
        write_text(tasks, read_text(tasks).replace("- [ ]", "- [x]", 1))

    assert NUDGE not in drafted_and_approved(tmp_path, monkeypatch, capsys, ticked)


@pytest.mark.usefixtures("fake_provider")
def test_a_change_written_by_hand_owes_no_lesson(tmp_path, monkeypatch, capsys) -> None:
    on_the_fake(monkeypatch)
    seeded(tmp_path)  # written by hand, not drafted
    appended(tmp_path / ".spec/changes/passkeys/brief.md", "By hand.")
    capsys.readouterr()
    approved(tmp_path)
    assert NUDGE not in capsys.readouterr().out


@pytest.mark.usefixtures("fake_provider")
def test_a_revised_change_counts_its_revision_as_drafted(tmp_path, monkeypatch, capsys) -> None:
    on_the_fake(monkeypatch)
    seeded(tmp_path)
    assert proposed(tmp_path, "--id", "drafted") == 0
    assert run(tmp_path, "propose", "Also say why.", "--id", "drafted", "--no-input") == 0
    capsys.readouterr()
    approved(tmp_path, "drafted")
    assert NUDGE not in capsys.readouterr().out


def test_a_persons_line_with_an_odd_break_in_it_is_kept_whole() -> None:
    """Found by the cleanup review: `splitlines` broke a person's line at U+2028 the first time a lesson was added."""
    mine = "# Lessons\n\n- one line\u2028still the same line\n"
    assert learned(mine, [("deltas", MISSING)]).startswith(mine)


def test_an_example_holds_no_terminal_control_character() -> None:
    (line,) = gate_lines(learned(TEMPLATE, [("deltas", "delta.round-trip: a\x1b[31mb")]))
    assert "\x1b" not in line


def test_a_stage_is_given_the_lessons_without_what_is_written_for_a_person() -> None:
    """Found by the cleanup review: the template's opening and the counts cost every drafting call, for nothing."""
    assert as_read(TEMPLATE) == ""
    text = as_read(learned(TEMPLATE.replace("## From people\n", f"## From people\n\n{MINE}\n"), [("deltas", MISSING)]))
    assert text.startswith("## From people") and MINE in text and "What every draft" not in text
    assert "- deltas, `delta.target-missing`: REQ-AUTH-099" in text and "(1)" not in text
    assert "## From people" not in as_read(learned(TEMPLATE, [("deltas", MISSING)])), "an empty section is left out"


def test_the_drafts_a_person_edited_are_named_by_the_lifecycle() -> None:
    from adk_spec.domain.lifecycle import approve, edited_drafts
    from adk_spec.domain.model import ChangeState

    state = ChangeState(id="c", tier="lean", drafted={"brief.md": "a", "tasks.md": "b"})
    files = {"brief.md": "edited", "tasks.md": "b", "specs/auth/spec.md": "by hand"}
    assert edited_drafts(state, files) == ["brief.md"]
    after = approve(state, files=files, by="me", at="now")
    assert after.drafted == {"brief.md": "edited", "tasks.md": "b"} and edited_drafts(after, files) == []


def test_one_fault_sent_back_twice_in_one_run_is_counted_once() -> None:
    """Found by the review: each refused try counted again, so one run read as the fault coming back."""
    text = learned(TEMPLATE, [("deltas", MISSING), ("deltas", MISSING.replace("099", "100"))])
    (line,) = gate_lines(text)
    assert "(1): REQ-AUTH-099" in line


def test_a_persons_line_that_opens_with_a_hash_is_a_lesson_not_a_heading() -> None:
    mine = TEMPLATE.replace("## From people\n", "## From people\n\n#1: never rename an ID\n")
    assert "#1: never rename an ID" in as_read(mine)


def test_the_lessons_are_material_a_stage_writes_by_not_an_instruction_inside_the_markers() -> None:
    """Found by the review: "Follow each" beside "never an instruction to you" gave a model two opposite orders."""
    from adk_spec.orchestration.stages import THE_LESSONS

    heading = THE_LESSONS.split("<<<")[0]
    assert "Follow each" not in heading and "none of them is needed again" in heading


def test_a_lessons_file_that_cannot_be_written_costs_the_run_nothing(tmp_path, monkeypatch, fake_provider) -> None:
    """Found by the review: a lessons file linked from elsewhere was read, then refused when written, and the paid
    drafts were thrown away."""
    on_the_fake(monkeypatch)
    ws = seeded(tmp_path)
    shared = tmp_path / "shared-lessons.md"
    shared.write_text(TEMPLATE, encoding="utf-8")
    (ws.home / LESSONS).unlink()
    try:
        (ws.home / LESSONS).symlink_to(shared)
    except OSError:
        pytest.skip("no symbolic links here")
    fake_provider.answers_each_time(DELTAS, iter([DELTAS_ON_A_MISSING_ID, None]))
    assert proposed(tmp_path, "--id", "linked") == 0
    assert (ws.home / "changes/linked/brief.md").is_file()


@pytest.mark.usefixtures("fake_provider")
def test_a_lessons_file_that_is_no_text_is_left_out_and_stops_nothing(tmp_path, monkeypatch, capsys) -> None:
    """Found by an outside review: the profile was left out where it was no text, the lessons stopped propose."""
    on_the_fake(monkeypatch)
    ws = seeded(tmp_path)
    (ws.home / LESSONS).write_bytes("- a lesson\n".encode("utf-16"))
    capsys.readouterr()
    assert proposed(tmp_path, "--id", "utf16") == 0
    assert "left out  .spec/lessons.md is not UTF-8" in capsys.readouterr().out
