"""Clarifying questions on the standard tier: bounded, put to the person between two runs, each answer kept beside
the question that was shown, and never taken for a new request."""

from __future__ import annotations

import io

import pytest
from conftest import BRIEF_WITH_A_MARKER, CANNED_BRIEF, CANNED_QUESTIONS, on_the_fake, run, seeded
from google.adk.apps.app import App
from google.adk.events.request_input import RequestInput
from google.adk.workflow import Workflow

from adk_spec.domain.brief_md import markers
from adk_spec.orchestration.run import run_seeded
from adk_spec.workspace.files import read_text

REQUEST = "Let users sign in with a passkey."
TRIAGE, BRIEF, QUESTIONS = "You size a change request", "You write the brief of a change", "You word the open points"


def proposed(root, *argv: str) -> int:
    return run(root, "propose", REQUEST, *argv)


def asked(fake_provider, opening: str) -> list[str]:
    """The instruction of each request the fake was sent that opens with `opening`."""
    sent = (str(r.config.system_instruction) for r in fake_provider.requests)
    return [instruction for instruction in sent if instruction.startswith(opening)]


@pytest.fixture(autouse=True)
def _fake_arm(monkeypatch) -> None:
    on_the_fake(monkeypatch)


def test_a_marker_becomes_a_question_and_the_answer_reaches_the_next_brief(
    tmp_path, monkeypatch, capsys, fake_provider
) -> None:
    seeded(tmp_path)
    fake_provider.answers_each_time(BRIEF, iter([BRIEF_WITH_A_MARKER, CANNED_BRIEF]))
    monkeypatch.setattr("sys.stdin", io.StringIO("Chrome and Firefox\n"))
    assert proposed(tmp_path, "--tier", "standard", "--id", "asked") == 0
    first, second = asked(fake_provider, BRIEF)
    assert "Which browsers are in scope? -> Chrome and Firefox" in second and "Chrome and Firefox" not in first
    assert markers(read_text(tmp_path / ".spec/changes/asked/brief.md")) == []
    out = capsys.readouterr().out
    assert "Which browsers are in scope?" in out and "Evergreen browsers only" in out
    assert "The brief leaves 1 point open." in out
    assert len(asked(fake_provider, QUESTIONS)) == 1 and len(asked(fake_provider, TRIAGE)) == 1


def test_the_suggestion_is_taken_with_an_equals_sign(tmp_path, monkeypatch, fake_provider) -> None:
    seeded(tmp_path)
    fake_provider.answers_each_time(BRIEF, iter([BRIEF_WITH_A_MARKER, CANNED_BRIEF]))
    monkeypatch.setattr("sys.stdin", io.StringIO("=\n"))
    assert proposed(tmp_path, "--tier", "standard", "--id", "taken") == 0
    assert "Which browsers are in scope? -> Evergreen browsers only" in asked(fake_provider, BRIEF)[1]


def test_no_answer_leaves_the_point_open_and_ends_the_asking(tmp_path, monkeypatch, fake_provider) -> None:
    seeded(tmp_path)
    fake_provider.answers_when(BRIEF, BRIEF_WITH_A_MARKER)
    monkeypatch.setattr("sys.stdin", io.StringIO(""))  # the input has ended: no terminal, or a pipe that closed
    assert proposed(tmp_path, "--tier", "standard", "--id", "open") == 0
    assert len(markers(read_text(tmp_path / ".spec/changes/open/brief.md"))) == 1
    assert len(asked(fake_provider, TRIAGE)) == 1, "an answer is never taken for a new request"
    assert len(asked(fake_provider, QUESTIONS)) == 1, "a round nobody answered is not asked again"


def test_the_asking_stops_after_three_rounds(tmp_path, monkeypatch, fake_provider) -> None:
    seeded(tmp_path)
    fake_provider.answers_when(BRIEF, BRIEF_WITH_A_MARKER)  # the model never settles the point
    monkeypatch.setattr("sys.stdin", io.StringIO("Chrome\nChrome\nChrome\nChrome\nChrome\n"))
    assert proposed(tmp_path, "--tier", "standard", "--id", "stubborn") == 0
    assert len(asked(fake_provider, QUESTIONS)) == 3 and len(asked(fake_provider, BRIEF)) == 4
    assert asked(fake_provider, BRIEF)[-1].count("Which browsers are in scope? -> Chrome") == 3


def test_no_input_asks_nothing_and_the_lean_tier_asks_nothing(tmp_path, fake_provider) -> None:
    seeded(tmp_path)
    fake_provider.answers_when(BRIEF, BRIEF_WITH_A_MARKER)
    assert proposed(tmp_path, "--tier", "standard", "--no-input", "--id", "quiet") == 0
    assert proposed(tmp_path, "--tier", "lean", "--id", "lean-one") == 0
    assert asked(fake_provider, QUESTIONS) == []


def test_at_most_five_questions_are_asked(tmp_path, monkeypatch, capsys, fake_provider) -> None:
    seeded(tmp_path)
    fake_provider.answers_each_time(BRIEF, iter([BRIEF_WITH_A_MARKER, CANNED_BRIEF]))
    seven = [{**CANNED_QUESTIONS["questions"][0], "question": f"Question {n}?"} for n in range(1, 8)]
    fake_provider.answers_when(QUESTIONS, {"questions": seven})
    monkeypatch.setattr("sys.stdin", io.StringIO("a\n" * 7))
    assert proposed(tmp_path, "--tier", "standard", "--id", "many") == 0
    out = capsys.readouterr().out
    assert "Question 5?" in out and "Question 6?" not in out


def test_more_markers_than_the_budget_send_the_brief_back(tmp_path, capsys, fake_provider) -> None:
    seeded(tmp_path)
    fake_provider.answers_when(BRIEF, {**CANNED_BRIEF, "assumptions": "[NEEDS CLARIFICATION] " * 4})
    assert proposed(tmp_path, "--no-input", "--id", "many") == 3
    assert "brief.markers-over-budget" in capsys.readouterr().err and len(asked(fake_provider, BRIEF)) == 3


@pytest.mark.asyncio
async def test_a_pause_with_nobody_to_answer_ends_the_run_and_restarts_nothing() -> None:
    ran: list[int] = []

    def ask(node_input=None):  # noqa: ARG001 -- the node's contract
        ran.append(1)
        yield RequestInput(message="?", payload={})

    app = App(name="t", root_agent=Workflow(name="t", edges=[("START", ask)]), plugins=[])
    result = await run_seeded(app, state={}, prompt="go")
    assert result.failure == "the run asked a question and none could be answered" and ran == [1]


TWO_MARKERS = {
    **CANNED_BRIEF,
    "assumptions": "[NEEDS CLARIFICATION: which browsers?] [NEEDS CLARIFICATION: how long is a session?]",
}
TWO_QUESTIONS = {
    "questions": [
        {"marker": "[NEEDS CLARIFICATION: which browsers?]", "question": "Which browsers?", "recommended": "Evergreen"},
        {
            "marker": "[NEEDS CLARIFICATION: how long is a session?]",
            "question": "How long is a session?",
            "recommended": "8 h",
        },
    ]
}


def test_an_answer_is_kept_beside_the_question_the_person_was_shown(tmp_path, monkeypatch, fake_provider) -> None:
    """Found by review: a pause inside a run made ADK re-run, unseen, a stage that had answered off its schema, and
    the person's answers were attached to that second set of questions."""
    seeded(tmp_path)
    fake_provider.answers_each_time(BRIEF, iter([TWO_MARKERS, CANNED_BRIEF]))
    swapped = {"questions": TWO_QUESTIONS["questions"][::-1]}
    fake_provider.answers_each_time(QUESTIONS, iter(["not json", TWO_QUESTIONS, swapped, swapped]))
    monkeypatch.setattr("sys.stdin", io.StringIO("Chrome and Firefox\n30 minutes\n"))
    assert proposed(tmp_path, "--tier", "standard", "--id", "paired") == 0
    told = asked(fake_provider, BRIEF)[1]
    assert "Which browsers? -> Chrome and Firefox" in told and "How long is a session? -> 30 minutes" in told
    assert len(asked(fake_provider, QUESTIONS)) == 2, "one answer off its schema, one good: no stage is run unseen"


def test_a_stage_off_its_schema_early_does_not_break_a_later_round(tmp_path, monkeypatch, fake_provider) -> None:
    """Found by review: after one answer off its schema, the second answered round ended the run with a replay
    error and lost both rounds of answers."""
    seeded(tmp_path)
    fake_provider.answers_each_time(TRIAGE, iter(["not json", None]))
    fake_provider.answers_each_time(BRIEF, iter([BRIEF_WITH_A_MARKER, BRIEF_WITH_A_MARKER, CANNED_BRIEF]))
    monkeypatch.setattr("sys.stdin", io.StringIO("one\ntwo\n"))
    assert proposed(tmp_path, "--tier", "standard", "--id", "two-rounds") == 0
    assert len(asked(fake_provider, TRIAGE)) == 2 and len(asked(fake_provider, QUESTIONS)) == 2
    last = asked(fake_provider, BRIEF)[-1]
    assert "Which browsers are in scope? -> one" in last and "Which browsers are in scope? -> two" in last


def test_a_round_nobody_answered_keeps_the_brief_that_passed_its_gate(tmp_path, monkeypatch, fake_provider) -> None:
    """Found by review: an unanswered round threw the checked brief away and drafted another, which could fail its
    gate, or come back with the marker gone though nobody had answered."""
    seeded(tmp_path)
    fake_provider.answers_each_time(BRIEF, iter([BRIEF_WITH_A_MARKER, CANNED_BRIEF]))
    monkeypatch.setattr("sys.stdin", io.StringIO(""))
    assert proposed(tmp_path, "--tier", "standard", "--id", "kept") == 0
    assert len(asked(fake_provider, BRIEF)) == 1, "the brief is not drafted again"
    assert len(markers(read_text(tmp_path / ".spec/changes/kept/brief.md"))) == 1, "the marker stays: code decides it"


def test_questions_that_cannot_be_worded_do_not_lose_the_brief(tmp_path, capsys, fake_provider) -> None:
    seeded(tmp_path)
    fake_provider.answers_when(BRIEF, BRIEF_WITH_A_MARKER)
    fake_provider.answers_when(QUESTIONS, "not json")
    assert proposed(tmp_path, "--tier", "standard", "--id", "unworded") == 0
    assert len(markers(read_text(tmp_path / ".spec/changes/unworded/brief.md"))) == 1
    said = capsys.readouterr()
    assert len(asked(fake_provider, QUESTIONS)) == 3 and "Traceback" not in said.err
    assert "note      the brief's open points were not put to you" in said.out
    (deltas,) = asked(fake_provider, "You write the requirement deltas")
    assert "did not fit its schema" not in deltas, "the questions' findings are not told to the deltas stage"


def test_no_terminal_at_all_is_no_answer(tmp_path, monkeypatch, fake_provider) -> None:
    seeded(tmp_path)
    fake_provider.answers_when(BRIEF, BRIEF_WITH_A_MARKER)
    monkeypatch.setattr("sys.stdin", None)
    assert proposed(tmp_path, "--tier", "standard", "--id", "headless") == 0


def test_ctrl_c_at_a_question_stops_at_once_and_leaves_nothing_behind(tmp_path, monkeypatch, fake_provider) -> None:
    """Coverage the review asked for. The question is put between two runs, outside the engine's event loop, so a
    Ctrl-C there is Python's own and is not swallowed once, as it was while the engine held the read."""

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
    assert len(markers(read_text(tmp_path / ".spec/changes/bytes/brief.md"))) == 1
