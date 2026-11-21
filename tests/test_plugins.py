"""The two plugins every app carries: an answer off its schema is the stage's own error, and a ledger counts each
stage's tokens and refuses a call past the ceiling."""

from __future__ import annotations

import pytest
from google.adk.agents import LlmAgent
from google.adk.apps.app import App
from google.adk.workflow import Workflow

from adk_spec.domain.drafts import Triage
from adk_spec.orchestration.models import build_model, request_config
from adk_spec.orchestration.plugins import STAGE_ERROR, SchemaMismatch, UsageLedger, roster
from adk_spec.orchestration.run import run_seeded
from adk_spec.orchestration.stages.triage import build_triage

STATE = {"request": "Let users sign in with a passkey."}


@pytest.fixture(autouse=True)
def _on_the_fake(monkeypatch) -> None:
    monkeypatch.setenv("SPEC_PROVIDER", "gemini")
    monkeypatch.setenv("SPEC_MODEL", "fake")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")


def build_triage_again() -> LlmAgent:
    """A second schema-bound stage, for a graph of two."""
    return LlmAgent(
        model=build_model(),
        name="triage_again",
        instruction="You size it once more.",
        include_contents="none",
        generate_content_config=request_config(),
        output_schema=Triage,
        output_key="triage_again",
    )


@pytest.mark.asyncio
async def test_an_answer_off_its_schema_is_the_stages_own_error_and_the_run_goes_on(fake_provider) -> None:
    fake_provider.answers_when("You size a change request", "Sure! It is lean.")
    reached: list[object] = []

    def after(node_input=None):
        reached.append(node_input)

    app = App(
        name="t", root_agent=Workflow(name="t", edges=[("START", build_triage(), after)]), plugins=roster(UsageLedger())
    )
    run = await run_seeded(app, state=dict(STATE), prompt="go")
    assert run.failure is None and reached == [None] and "triage" not in run.state
    assert run.errors["triage"].startswith("SCHEMA_MISMATCH")
    assert run.state[STAGE_ERROR].startswith("the answer did not fit its schema: ")


@pytest.mark.asyncio
async def test_the_ledger_counts_each_stage_and_refuses_past_the_ceiling(fake_provider) -> None:
    ledger = UsageLedger(ceiling=100)
    wf = Workflow(name="t", edges=[("START", build_triage(), build_triage_again())])  # 120 tokens a call
    run = await run_seeded(App(name="t", root_agent=wf, plugins=[ledger]), state=dict(STATE), prompt="go")
    assert ledger.total.total == 120 and ledger.spent["triage"].calls == 1 and len(fake_provider.requests) == 1
    assert run.errors["triage_again"].startswith("CEILING") and run.state[STAGE_ERROR].startswith("CEILING: ")


@pytest.mark.asyncio
async def test_with_no_ceiling_every_stage_is_counted_under_its_own_name(fake_provider) -> None:
    ledger = UsageLedger()
    wf = Workflow(name="t", edges=[("START", build_triage(), build_triage_again())])
    await run_seeded(App(name="t", root_agent=wf, plugins=[ledger]), state=dict(STATE), prompt="go")
    assert sorted(ledger.spent) == ["triage", "triage_again"] and ledger.total.total == 240 and ledger.total.calls == 2
    assert len(fake_provider.requests) == 2


@pytest.mark.asyncio
async def test_an_answer_off_its_schema_is_still_paid_for_and_counted(fake_provider) -> None:
    fake_provider.answers_when("You size a change request", "Sure! It is lean.")
    plugins = roster(UsageLedger())
    app = App(name="t", root_agent=Workflow(name="t", edges=[("START", build_triage())]), plugins=plugins)
    await run_seeded(app, state=dict(STATE), prompt="go")
    ledger = next(plugin for plugin in plugins if isinstance(plugin, UsageLedger))
    assert ledger.total.total == 120, "the ledger reads the answer before the mismatch replaces it"
    assert [type(plugin) for plugin in plugins] == [UsageLedger, SchemaMismatch]
