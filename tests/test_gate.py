"""The gate node: a stage's answer is checked, asked for again with what was wrong at most twice, then given up."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

import pytest
from google.adk.apps.app import App
from google.adk.events import Event
from google.adk.workflow import Workflow

from adk_spec.orchestration.gate import AGAIN, FAILURE, GIVE_UP, OK, SENT_BACK, checked
from adk_spec.orchestration.plugins import UsageLedger, roster
from adk_spec.orchestration.run import run_seeded
from adk_spec.orchestration.stages.triage import build_triage

STATE = {"request": "Let users sign in with a passkey."}


@pytest.fixture(autouse=True)
def _on_the_fake(monkeypatch) -> None:
    monkeypatch.setenv("SPEC_PROVIDER", "gemini")
    monkeypatch.setenv("SPEC_MODEL", "fake")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")


def flow(check: Callable[[Mapping[str, Any]], list[str]], ceiling: int | None = None, *, learns: bool = False) -> App:
    """Triage, its gate, and where each of the gate's three routes ends."""
    agent, gate = build_triage(), checked("triage", check, learns=learns)

    def done():
        return Event(output="done")

    def lost():
        return Event(output="lost")

    edges = [("START", agent, gate), (gate, {OK: done, AGAIN: agent, GIVE_UP: lost})]
    return App(name="t", root_agent=Workflow(name="t", edges=edges), plugins=roster(UsageLedger(ceiling)))


@pytest.mark.asyncio
async def test_an_answer_that_passes_goes_on_at_once(fake_provider) -> None:
    run = await run_seeded(flow(lambda _state: []), state=dict(STATE), prompt="go")
    assert len(fake_provider.requests) == 1 and run.state["tries_triage"] == 1 and run.state.get(FAILURE) is None
    assert run.state["triage"]["tier"] == "lean"


@pytest.mark.asyncio
async def test_a_refused_answer_is_asked_again_with_what_was_wrong(fake_provider) -> None:
    refused = iter([["name a capability"], []])
    run = await run_seeded(flow(lambda _state: next(refused)), state=dict(STATE), prompt="go")
    assert len(fake_provider.requests) == 2 and run.state["tries_triage"] == 2 and run.state.get(FAILURE) is None
    assert "name a capability" not in str(fake_provider.requests[0].config.system_instruction)
    assert "to put right: name a capability" in str(fake_provider.requests[1].config.system_instruction)


@pytest.mark.asyncio
async def test_three_refusals_end_the_run_with_the_reason(fake_provider) -> None:
    run = await run_seeded(flow(lambda _state: ["still wrong", "and this"]), state=dict(STATE), prompt="go")
    assert len(fake_provider.requests) == 3 and run.failure is None
    assert run.state[FAILURE] == "triage: still wrong; and this"


@pytest.mark.asyncio
async def test_an_answer_off_its_schema_counts_as_a_try_and_a_stale_answer_is_never_checked(fake_provider) -> None:
    seen: list[object] = []

    def check(state: Mapping[str, Any]) -> list[str]:
        seen.append(state["triage"])
        return ["refused once"] if len(seen) == 1 else []

    answers = iter([None, "not json", "not json either"])
    fake_provider.answers_each_time("You size a change request", answers)
    run = await run_seeded(flow(check), state=dict(STATE), prompt="go")
    assert len(seen) == 1, "the answer refused on the first try was not checked again after a broken one"
    assert run.state[FAILURE].startswith("triage: the answer did not fit its schema: ")
    assert len(fake_provider.requests) == 3


@pytest.mark.asyncio
async def test_a_spent_ceiling_is_said_once_and_not_asked_again(fake_provider) -> None:
    run = await run_seeded(flow(lambda _state: [], ceiling=0), state=dict(STATE), prompt="go")
    assert fake_provider.requests == [] and run.state[FAILURE].startswith("triage: CEILING: ")
    assert run.state["tries_triage"] == 1


@pytest.mark.asyncio
@pytest.mark.usefixtures("fake_provider")
async def test_a_learning_gate_hands_on_what_it_sent_back_once_the_next_try_passes() -> None:
    refused = iter([["brief.no-title: one", "the answer did not match its schema."], ["delta.empty: two"], []])
    run = await run_seeded(flow(lambda _state: next(refused), learns=True), state=dict(STATE), prompt="go")
    assert run.state[SENT_BACK] == [
        ["triage", "brief.no-title: one"],
        ["triage", "the answer did not match its schema."],
        ["triage", "delta.empty: two"],
    ]


@pytest.mark.asyncio
@pytest.mark.usefixtures("fake_provider")
async def test_a_stage_given_up_or_a_gate_that_does_not_learn_hands_on_nothing() -> None:
    given_up = await run_seeded(flow(lambda _state: ["brief.no-title: x"], learns=True), state=dict(STATE), prompt="go")
    refused = iter([["brief.no-title: once"], []])
    unlearned = await run_seeded(flow(lambda _state: next(refused)), state=dict(STATE), prompt="go")
    assert not given_up.state.get(SENT_BACK) and not unlearned.state.get(SENT_BACK)


def test_every_sentence_a_drafting_gate_says_opens_with_its_code() -> None:
    """A lesson is the same lesson in the next change only where its problem has a code, as the validator's have."""
    from adk_spec.domain.lessons_md import learned
    from adk_spec.orchestration import graph

    said = [
        *graph._check_brief(
            {
                "brief": {
                    "title": "",
                    "why": "",
                    "what_changes": "",
                    "non_goals": "",
                    "capabilities": [],
                    "impact": "",
                    "assumptions": "",
                    "open_points": [],
                    "design_needed": False,
                    "design_reason": "",
                }
            }
        ),
        *graph._check_design({"design": dict.fromkeys(graph.DESIGN_SECTIONS, "")}),
    ]
    assert said and all(learned("", [("x", sentence)]) for sentence in said)
