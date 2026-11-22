"""Clarifying questions on the standard tier: read by code from the open points a brief names, bounded, put to the
person between two runs, each answer kept beside the question that was shown, and never taken for a new request.
No model is asked to word a question: the brief's own stage names each open point and the answer it would suggest.
"""

from __future__ import annotations

import io

import pytest
from conftest import BRIEF_WITH_A_MARKER, CANNED_BRIEF, CANNED_TRIAGE, OPEN_POINT, between, on_the_fake, run, seeded

from adk_spec.domain.brief_md import markers
from adk_spec.workspace.files import read_text

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
    assert "triage 120 in 1 call, brief 240 in 2 calls, deltas 120 in 1 call: 480 total" in out
    assert len(fake_provider.requests) == 4, "triage, two briefs and the deltas: no call words a question"


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
    assert "suggested: (none)" in capsys.readouterr().out
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
    assert "A line answers" not in capsys.readouterr().out and len(fake_provider.requests) == 4
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
