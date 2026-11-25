"""Clarifying questions on the standard tier: read by code from the open points a brief names, bounded, put to the
person between two runs, each answer kept beside the question that was shown, and never taken for a new request.
No model is asked to word a question: the brief's own stage names each open point and the answer it would suggest.
"""

from __future__ import annotations

import io

import pytest
from conftest import BRIEF_WITH_A_MARKER, CANNED_BRIEF, CANNED_TRIAGE, OPEN_POINT, between, on_the_fake, run, seeded

from adk_spec.domain.brief_md import markers
from adk_spec.workspace.files import read_text, write_text

REQUEST = "Let users sign in with a passkey."
#: Triage's own call for the standard tier: a tier given by hand is not asked of the model at all.
STANDARD = {**CANNED_TRIAGE, "tier": "standard"}
TRIAGE, BRIEF = "You size a change request", "You write the brief of a change"
ASKED = OPEN_POINT["question"]


def proposed(root, *argv: str) -> int:
    return run(root, "propose", REQUEST, *argv)


def asked(fake_provider, opening: str) -> list[str]:
    """The instruction of each request the fake was sent that opens with `opening`."""
    sent = (str(r.config.system_instruction) for r in fake_provider.requests)
    return [instruction for instruction in sent if instruction.startswith(opening)]


def brief_md(root, change: str) -> str:
    return read_text(root / f".spec/changes/{change}/brief.md")


@pytest.fixture(autouse=True)
def _fake_arm(monkeypatch) -> None:
    on_the_fake(monkeypatch)


def test_an_open_point_becomes_a_question_with_no_model_asked_to_word_it(
    tmp_path, monkeypatch, capsys, fake_provider
) -> None:
    seeded(tmp_path)
    fake_provider.answers_when(TRIAGE, STANDARD)
    fake_provider.answers_each_time(BRIEF, iter([BRIEF_WITH_A_MARKER, CANNED_BRIEF]))
    monkeypatch.setattr("sys.stdin", io.StringIO("Chrome and Firefox\n"))
    assert proposed(tmp_path, "--id", "asked") == 0
    first, second = asked(fake_provider, BRIEF)
    assert f"{ASKED} -> Chrome and Firefox" in second and "Chrome and Firefox" not in first
    assert markers(brief_md(tmp_path, "asked")) == []
    out = capsys.readouterr().out
    assert f"1. {ASKED}" in out and "suggested: Evergreen browsers only" in out
    assert "The brief leaves 1 point open." in out
    assert "triage 120 in 1 call, brief 240 in 2 calls, deltas 120 in 1 call, tasks 120 in 1 call: 600 total" in out
    assert len(fake_provider.requests) == 5, "triage, two briefs, the deltas and the tasks: no call words a question"


def test_the_suggestion_is_taken_with_an_equals_sign(tmp_path, monkeypatch, fake_provider) -> None:
    seeded(tmp_path)
    fake_provider.answers_each_time(BRIEF, iter([BRIEF_WITH_A_MARKER, CANNED_BRIEF]))
    monkeypatch.setattr("sys.stdin", io.StringIO("=\n"))
    assert proposed(tmp_path, "--tier", "standard", "--id", "taken") == 0
    assert f"{ASKED} -> Evergreen browsers only" in asked(fake_provider, BRIEF)[1]


def test_an_open_point_with_nothing_suggested_is_asked_without_one_and_equals_takes_nothing(
    tmp_path, monkeypatch, capsys, fake_provider
) -> None:
    seeded(tmp_path)
    fake_provider.answers_when(BRIEF, {**CANNED_BRIEF, "open_points": [{**OPEN_POINT, "suggested": ""}]})
    monkeypatch.setattr("sys.stdin", io.StringIO("=\n"))
    assert proposed(tmp_path, "--tier", "standard", "--id", "unsuggested") == 0
    out = capsys.readouterr().out
    assert "suggested: (none)" in out
    assert "nothing is suggested: the point stays open" in out, "found by the code review: `=` did nothing, unsaid"
    assert len(asked(fake_provider, BRIEF)) == 1, "nothing was taken for an answer, so the brief stands"
    assert len(markers(brief_md(tmp_path, "unsuggested"))) == 1


def test_no_answer_leaves_the_point_open_and_ends_the_asking(tmp_path, monkeypatch, fake_provider) -> None:
    seeded(tmp_path)
    fake_provider.answers_when(TRIAGE, STANDARD)
    fake_provider.answers_when(BRIEF, BRIEF_WITH_A_MARKER)
    monkeypatch.setattr("sys.stdin", io.StringIO(""))  # the input has ended: no terminal, or a pipe that closed
    assert proposed(tmp_path, "--id", "open") == 0
    assert markers(brief_md(tmp_path, "open")) == [f"[NEEDS CLARIFICATION: {ASKED}]"]
    assert len(asked(fake_provider, TRIAGE)) == 1, "an answer is never taken for a new request"
    assert len(asked(fake_provider, BRIEF)) == 1, "a round nobody answered keeps the brief that passed its gate"


def test_the_asking_stops_after_three_rounds(tmp_path, monkeypatch, capsys, fake_provider) -> None:
    seeded(tmp_path)
    fake_provider.answers_when(BRIEF, BRIEF_WITH_A_MARKER)  # the model never settles the point
    monkeypatch.setattr("sys.stdin", io.StringIO("Chrome\nChrome\nChrome\nChrome\nChrome\n"))
    assert proposed(tmp_path, "--tier", "standard", "--id", "stubborn") == 0
    assert len(asked(fake_provider, BRIEF)) == 4 and capsys.readouterr().out.count(f"1. {ASKED}") == 3
    assert asked(fake_provider, BRIEF)[-1].count(f"{ASKED} -> Chrome") == 3


def test_no_input_asks_nothing_and_the_lean_tier_asks_nothing(tmp_path, capsys, fake_provider) -> None:
    seeded(tmp_path)
    fake_provider.answers_when(BRIEF, BRIEF_WITH_A_MARKER)
    assert proposed(tmp_path, "--tier", "standard", "--no-input", "--id", "quiet") == 0
    assert proposed(tmp_path, "--tier", "lean", "--id", "lean-one") == 0
    assert "A line answers" not in capsys.readouterr().out
    assert len(fake_provider.requests) == 4, "a brief and the deltas, twice: no plan is drafted on a point left open"
    for change in ("quiet", "lean-one"):
        assert len(markers(brief_md(tmp_path, change))) == 1, "the point stands in the file, for a person to settle"


def test_more_open_points_than_the_budget_send_the_brief_back(tmp_path, capsys, fake_provider) -> None:
    seeded(tmp_path)
    four = [{"question": f"Question {n}?", "suggested": ""} for n in range(1, 5)]
    fake_provider.answers_when(BRIEF, {**CANNED_BRIEF, "open_points": four})
    assert proposed(tmp_path, "--no-input", "--id", "many") == 3
    assert "brief.markers-over-budget" in capsys.readouterr().err and len(asked(fake_provider, BRIEF)) == 3


def test_three_open_points_are_three_questions_each_answered_in_its_turn(tmp_path, monkeypatch, fake_provider) -> None:
    seeded(tmp_path)
    three = [{"question": f"Question {n}?", "suggested": f"Answer {n}"} for n in range(1, 4)]
    fake_provider.answers_each_time(BRIEF, iter([{**CANNED_BRIEF, "open_points": three}, CANNED_BRIEF]))
    monkeypatch.setattr("sys.stdin", io.StringIO("first\n\n=\n"))
    assert proposed(tmp_path, "--tier", "standard", "--id", "three") == 0
    told = between(asked(fake_provider, BRIEF)[1], "answers")
    assert told == "Question 1? -> first\nQuestion 3? -> Answer 3", "the second was left open, and is not told"


def test_an_answer_is_kept_beside_the_question_the_person_was_shown(tmp_path, monkeypatch, fake_provider) -> None:
    """Found by review, while a model worded the questions: a pause inside a run made ADK run that stage again,
    unseen, and the answers were attached to its second set of questions. The questions are code's now, read from
    the brief that passed its gate: a brief off its schema first changes nothing of what is asked."""
    seeded(tmp_path)
    two = [
        {"question": "Which browsers?", "suggested": "Evergreen"},
        {"question": "How long is a session?", "suggested": "8 h"},
    ]
    drafts = iter(["not json", {**CANNED_BRIEF, "open_points": two}, CANNED_BRIEF])
    fake_provider.answers_each_time(BRIEF, drafts)
    monkeypatch.setattr("sys.stdin", io.StringIO("Chrome and Firefox\n30 minutes\n"))
    assert proposed(tmp_path, "--tier", "standard", "--id", "paired") == 0
    told = between(asked(fake_provider, BRIEF)[2], "answers")
    assert told == "Which browsers? -> Chrome and Firefox\nHow long is a session? -> 30 minutes"
    assert len(asked(fake_provider, BRIEF)) == 3, "one draft off its schema, one asked about, one settled"


def test_a_stage_off_its_schema_early_does_not_break_a_later_round(tmp_path, monkeypatch, fake_provider) -> None:
    """Found by review: after one answer off its schema, the second answered round ended the run with a replay
    error and lost both rounds of answers."""
    seeded(tmp_path)
    fake_provider.answers_each_time(TRIAGE, iter(["not json", STANDARD]))
    fake_provider.answers_each_time(BRIEF, iter([BRIEF_WITH_A_MARKER, BRIEF_WITH_A_MARKER, CANNED_BRIEF]))
    monkeypatch.setattr("sys.stdin", io.StringIO("one\ntwo\n"))
    assert proposed(tmp_path, "--id", "two-rounds") == 0
    assert len(asked(fake_provider, TRIAGE)) == 2 and len(asked(fake_provider, BRIEF)) == 3
    last = asked(fake_provider, BRIEF)[-1]
    assert f"{ASKED} -> one" in last and f"{ASKED} -> two" in last


def test_a_marker_the_model_wrote_in_a_section_is_asked_as_well(tmp_path, monkeypatch, capsys, fake_provider) -> None:
    seeded(tmp_path)
    by_hand = {**CANNED_BRIEF, "assumptions": "EU only. [NEEDS CLARIFICATION: which regions?]"}
    fake_provider.answers_each_time(BRIEF, iter([by_hand, CANNED_BRIEF]))
    monkeypatch.setattr("sys.stdin", io.StringIO("EU and UK\n"))
    assert proposed(tmp_path, "--tier", "standard", "--id", "by-hand") == 0
    assert "1. which regions?" in capsys.readouterr().out
    assert "which regions? -> EU and UK" in asked(fake_provider, BRIEF)[1]


def test_no_terminal_at_all_is_no_answer(tmp_path, monkeypatch, fake_provider) -> None:
    seeded(tmp_path)
    fake_provider.answers_when(BRIEF, BRIEF_WITH_A_MARKER)
    monkeypatch.setattr("sys.stdin", None)
    assert proposed(tmp_path, "--tier", "standard", "--id", "headless") == 0
    assert len(markers(brief_md(tmp_path, "headless"))) == 1


def test_ctrl_c_at_a_question_stops_at_once_and_leaves_nothing_behind(tmp_path, monkeypatch, fake_provider) -> None:
    """The question is put between two runs, outside the engine's event loop, so a Ctrl-C there is Python's own and
    is not swallowed once, as it was while the engine held the read."""

    class Interrupted(io.StringIO):
        def readline(self, *_args) -> str:
            raise KeyboardInterrupt

    seeded(tmp_path)
    fake_provider.answers_when(BRIEF, BRIEF_WITH_A_MARKER)
    monkeypatch.setattr("sys.stdin", Interrupted())
    with pytest.raises(KeyboardInterrupt):
        proposed(tmp_path, "--tier", "standard", "--id", "stopped")
    assert not (tmp_path / ".spec/changes/stopped").exists() and not (tmp_path / ".spec/.lock").exists()
    assert len(asked(fake_provider, BRIEF)) == 1


def test_an_answer_that_is_no_text_is_no_answer(tmp_path, monkeypatch, fake_provider) -> None:
    """Found by review: bytes that are no UTF-8 ended the run with a Python exception's name, three calls spent."""
    seeded(tmp_path)
    fake_provider.answers_when(BRIEF, BRIEF_WITH_A_MARKER)
    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(bytes([0xFF, 0xFE, 0x0A])), encoding="utf-8"))
    assert proposed(tmp_path, "--tier", "standard", "--id", "bytes") == 0
    assert len(markers(brief_md(tmp_path, "bytes"))) == 1


def test_piped_bytes_that_are_no_text_are_no_answer_in_the_installed_command(
    tmp_path, monkeypatch, fake_provider
) -> None:
    """Found by the code review: the installed command read what was typed with bad bytes replaced, so a UTF-16 file
    piped in was taken for an answer, and the test above could not see it: it calls `main`, not `run`."""
    from adk_spec.interfaces import cli

    seeded(tmp_path)
    fake_provider.answers_when(BRIEF, BRIEF_WITH_A_MARKER)
    utf16 = bytes([0xFF, 0xFE, 0x43, 0x00, 0x0A, 0x00])
    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(utf16), encoding="cp1252"))
    argv = ["adk-spec", "--root", str(tmp_path), "propose", REQUEST, "--tier", "standard", "--id", "bytes"]
    monkeypatch.setattr("sys.argv", argv)
    assert cli.run() == 0
    assert len(asked(fake_provider, BRIEF)) == 1, "nothing was taken for an answer"
    assert len(markers(brief_md(tmp_path, "bytes"))) == 1


def test_a_question_cannot_write_to_the_terminal_what_is_no_text(tmp_path, monkeypatch, capsys, fake_provider) -> None:
    """Raised by two reviews: a model's question and suggestion were printed as they came, control sequences too."""
    seeded(tmp_path)
    clear, bell = chr(27) + "[2J", chr(7)
    hostile = {"question": f"Which browsers?{clear}", "suggested": f"All{bell}"}
    fake_provider.answers_each_time(BRIEF, iter([{**CANNED_BRIEF, "open_points": [hostile]}, CANNED_BRIEF]))
    monkeypatch.setattr("sys.stdin", io.StringIO("Chrome\n"))
    assert proposed(tmp_path, "--tier", "standard", "--id", "plain") == 0
    out = capsys.readouterr().out
    assert chr(27) not in out and bell not in out and "Which browsers?" in out and "suggested: All" in out


def test_a_new_draft_is_given_the_brief_it_replaces(tmp_path, monkeypatch, fake_provider) -> None:
    """The first live run: each new draft was written from the request and the answers alone, raised a new open
    point each time, and once contradicted an answer. A new draft now reads the brief it replaces."""
    seeded(tmp_path)
    fake_provider.answers_each_time(BRIEF, iter([BRIEF_WITH_A_MARKER, CANNED_BRIEF]))
    monkeypatch.setattr("sys.stdin", io.StringIO("Chrome and Firefox\n"))
    assert proposed(tmp_path, "--tier", "standard", "--id", "replaced") == 0
    first, second = (between(text, "replaces") for text in asked(fake_provider, BRIEF))
    assert first == "", "a first draft replaces nothing"
    assert second.startswith("# Sign in with a passkey\n") and f"[NEEDS CLARIFICATION: {ASKED}]" in second
    assert "## Assumptions" in second, "the brief as its file, whole"


def test_the_brief_is_told_where_an_open_point_goes(tmp_path, fake_provider) -> None:
    seeded(tmp_path)
    assert proposed(tmp_path, "--tier", "lean", "--id", "told") == 0
    (sent,) = asked(fake_provider, BRIEF)
    assert "goes in open_points" in sent and "Write no [NEEDS CLARIFICATION] marker yourself." in sent
    assert "On the lean tier no question is asked: leave open_points empty there" in sent
    assert "is a point that draft left open: do not copy it." in sent, "the brief it replaces shows its markers"


def test_a_spent_ceiling_asks_the_person_nothing(tmp_path, monkeypatch, capsys, fake_provider) -> None:
    """Found by the code review: asking costs no model call now, so the ceiling no longer refused it. The person was
    asked, answered, and the refusal of the next brief threw the answer away."""
    seeded(tmp_path)
    write_text(tmp_path / ".spec/config.toml", '[project]\ndefault_tier = "lean"\n\n[limits]\nmax_tokens = 100\n')
    fake_provider.answers_when(BRIEF, BRIEF_WITH_A_MARKER)  # one call is 120 tokens: the ceiling is spent by it
    monkeypatch.setattr("sys.stdin", io.StringIO("Chrome and Firefox\n"))
    assert proposed(tmp_path, "--tier", "standard", "--id", "spent") == 3
    told = capsys.readouterr()
    assert ASKED not in told.out and "A line answers" not in told.out
    assert "token ceiling of 100 is spent" in told.err and "open points were not put to you" in told.err
    assert "raise [limits] max_tokens in .spec/config.toml" in told.err, "found by the fourth audit: no fix was named"
    assert len(fake_provider.requests) == 1 and not (tmp_path / ".spec/changes/spent").exists()


def test_a_marker_left_unclosed_is_sent_back_and_swallows_no_question(
    tmp_path, monkeypatch, capsys, fake_provider
) -> None:
    """Found by two reviews: a marker written by hand and never closed ran on to the next `]`, which is the end of
    the marker code appends. The person was shown both as one garbled question, its suggestion lost."""
    seeded(tmp_path)
    unclosed = {**BRIEF_WITH_A_MARKER, "assumptions": "We assume. [NEEDS CLARIFICATION: which provider"}
    fake_provider.answers_each_time(BRIEF, iter([unclosed, BRIEF_WITH_A_MARKER, CANNED_BRIEF]))
    monkeypatch.setattr("sys.stdin", io.StringIO("=\n"))
    assert proposed(tmp_path, "--tier", "standard", "--id", "unclosed") == 0
    out = capsys.readouterr().out
    assert f"1. {ASKED}" in out and "which provider" not in out
    assert "brief.marker-malformed" in asked(fake_provider, BRIEF)[1], "the gate sent the first draft back"


def test_a_brief_over_its_budget_is_told_what_its_stage_can_do_about_it(tmp_path, fake_provider) -> None:
    """Found by the code review: the gate passed on the validator's sentence, written for a person: "settle some
    with its author first". A model that named three points and kept a marker of the brief it replaces was sent
    back three times with nothing it could act on, after the person had answered a round."""
    seeded(tmp_path)
    three = [{"question": f"Question {n}?", "suggested": ""} for n in range(1, 4)]
    kept = {**CANNED_BRIEF, "assumptions": "A. [NEEDS CLARIFICATION: an old point?]", "open_points": three}
    fake_provider.answers_each_time(BRIEF, iter([kept, CANNED_BRIEF]))
    assert proposed(tmp_path, "--tier", "lean", "--id", "over") == 0
    again = asked(fake_provider, BRIEF)[1]  # the gate's findings are a line of the next instruction
    assert "brief.markers-over-budget: the brief leaves 4 points open, past the 3 it may" in again
    assert "1 of them written as a marker in a section. Write no marker there" in again
    assert "settle some with its author" not in again


def test_propose_drafts_no_plan_while_a_point_is_left_open(tmp_path, capsys, fake_provider) -> None:
    """Found by the cleanup review: the plan was drafted from a brief the tool itself marked unsettled, which is
    the largest call of the command spent on a guess. An open point comes before the plan, since its answer
    shapes the tasks: `propose` writes the brief and the specs, and says what it waits for."""
    seeded(tmp_path)
    fake_provider.answers_when(BRIEF, BRIEF_WITH_A_MARKER)
    assert proposed(tmp_path, "--tier", "standard", "--no-input", "--id", "open") == 0
    out = capsys.readouterr().out
    assert not (tmp_path / ".spec/changes/open/tasks.md").exists() and len(fake_provider.requests) == 2
    assert "plan      waits: the brief leaves 1 point open" in out
    # Found by the third audit: the editor's tools promised the open points in the output, and gave their count.
    assert f"open      {ASKED}\n          suggested: Evergreen browsers only" in out
    brief = tmp_path / ".spec/changes/open/brief.md"
    write_text(brief, read_text(brief).replace(f"[NEEDS CLARIFICATION: {ASKED}]", "Evergreen browsers only."))
    assert run(tmp_path, "status") == 0 and "run `adk-spec plan open`" in capsys.readouterr().out
    assert run(tmp_path, "plan", "open") == 0 and (tmp_path / ".spec/changes/open/tasks.md").is_file()


def test_the_persons_answers_are_kept_in_context_md(tmp_path, monkeypatch, fake_provider) -> None:
    """Phase 18: the answers lived only in the run, and the stages after the brief read the brief's words alone."""
    from conftest import repository

    seeded(tmp_path)
    repository(tmp_path)
    fake_provider.answers_each_time(BRIEF, iter([BRIEF_WITH_A_MARKER, CANNED_BRIEF]))
    monkeypatch.setattr("sys.stdin", io.StringIO("Chrome and Firefox\n"))
    assert proposed(tmp_path, "--tier", "standard", "--id", "kept") == 0
    context = read_text(tmp_path / ".spec/changes/kept/context.md")
    assert f"## The person's answers\n\n- {ASKED} -> Chrome and Firefox\n" in context
    assert context.index("## The person's answers") < context.index("## What was read")


def test_a_secret_in_an_answer_is_not_written_to_context_md(tmp_path, monkeypatch, fake_provider) -> None:
    """Phase 18: `context.md` is committed with the change, so an answer is scrubbed before it is kept there."""
    from conftest import repository

    seeded(tmp_path)
    repository(tmp_path)
    key = "AKIA" + "IOSFODNN7EXAMPLE"
    fake_provider.answers_each_time(BRIEF, iter([BRIEF_WITH_A_MARKER, CANNED_BRIEF]))
    monkeypatch.setattr("sys.stdin", io.StringIO(f"use {key}\n"))
    assert proposed(tmp_path, "--tier", "standard", "--id", "scrubbed") == 0
    context = read_text(tmp_path / ".spec/changes/scrubbed/context.md")
    assert key not in context and "[REDACTED" in context
