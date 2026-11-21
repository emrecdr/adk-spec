"""Clarifying questions on the standard tier: bounded, answered in the same run, and never taken for a new request."""

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
