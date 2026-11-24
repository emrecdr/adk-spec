"""The shape `adk web` loads: a chat that drafts a change from the message typed, as `propose --no-input` drafts
it, shows the drafts, and writes nothing."""

from __future__ import annotations

import importlib
import sys

import pytest
from conftest import ROOT, between, on_the_fake, seeded, sent_to, shut
from google.adk.apps.app import App
from google.adk.cli.utils.agent_loader import AgentLoader
from google.adk.runners import InMemoryRunner
from google.genai import types

from adk_spec.orchestration.stages import BOUNDARY
from adk_spec.workspace.layout import Workspace

REQUEST = "Let users sign in with a passkey."
DELTAS = "You write the requirement deltas"


@pytest.fixture(autouse=True)
def _fake_arm(monkeypatch) -> None:
    on_the_fake(monkeypatch)


def loaded(folder, monkeypatch) -> App:
    """The module imported anew with the process standing in `folder`, as ADK's loader finds it."""
    monkeypatch.chdir(folder)
    sys.modules.pop("adk_spec.agent", None)
    return importlib.import_module("adk_spec.agent").app


async def said(app: App, message: str) -> list[str]:
    runner = InMemoryRunner(app=app)
    await runner.session_service.create_session(app_name=runner.app_name, user_id="u", session_id="s")
    texts = []
    async for event in runner.run_async(user_id="u", session_id="s", new_message=types.UserContent(message)):
        parts = event.content.parts if event.content and event.content.parts else []
        texts += [part.text for part in parts if part.text and event.author == app.name]
    return texts


@pytest.mark.asyncio
async def test_the_chat_drafts_from_the_message_and_writes_nothing(tmp_path, monkeypatch, fake_provider) -> None:
    seeded(tmp_path)
    (text,) = await said(loaded(tmp_path, monkeypatch), REQUEST)
    assert "not written" in text and "# Sign in with a passkey" in text and "## ADDED Requirements" in text
    assert "REQ-AUTH-005" in text, "numbered past the living spec and the open change, as propose numbers"
    assert Workspace.find(tmp_path).changes() == ["passkeys"] and not (tmp_path / ".spec/runs").exists()
    triage = str(fake_provider.requests[0].config.system_instruction)
    assert f"<<< request {BOUNDARY}\n{REQUEST}\n>>> request {BOUNDARY}" in triage
    assert "auth: Sign-in and session handling." in triage, "the workspace the process stands in is read"


@pytest.mark.asyncio
async def test_a_draft_that_fails_its_gate_is_said_in_the_chat(tmp_path, monkeypatch, fake_provider) -> None:
    seeded(tmp_path)
    fake_provider.answers_when(DELTAS, "not json")
    (text,) = await said(loaded(tmp_path, monkeypatch), REQUEST)
    assert text.startswith("Nothing was drafted: deltas:") and "schema" in text


@pytest.mark.asyncio
async def test_a_request_that_owes_no_spec_is_said_in_the_chat(tmp_path, monkeypatch, fake_provider) -> None:
    seeded(tmp_path)
    fake_provider.answers_when("You size a change request", {"tier": "none", "capabilities": [], "reason": "A typo."})
    (text,) = await said(loaded(tmp_path, monkeypatch), "Fix the typo on the sign-in page.")
    assert text == "Nothing was drafted: no spec is owed. A typo." and len(fake_provider.requests) == 1


def test_adks_own_loader_finds_the_app_outside_a_workspace_too(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)  # no `.spec/` here: the chat still loads, and knows no capability
    sys.modules.pop("adk_spec.agent", None)
    found = AgentLoader(str(ROOT)).load_agent("adk_spec")
    assert isinstance(found, App) and found.name == "adk_spec" and found.root_agent.name == "adk_spec"


@pytest.mark.asyncio
async def test_a_second_message_starts_from_nothing_of_the_first(tmp_path, monkeypatch, fake_provider) -> None:
    """Found by the code review: one chat keeps one session, so a second message whose brief failed its gate was
    answered with the first message's drafts, and its stages were asked fewer times."""
    seeded(tmp_path)
    app = loaded(tmp_path, monkeypatch)
    runner = InMemoryRunner(app=app)
    await runner.session_service.create_session(app_name=runner.app_name, user_id="u", session_id="s")

    async def typed(message: str) -> str:
        texts = []
        async for event in runner.run_async(user_id="u", session_id="s", new_message=types.UserContent(message)):
            parts = event.content.parts if event.content and event.content.parts else []
            texts += [part.text for part in parts if part.text and event.author == app.name]
        return texts[-1]

    assert "# Sign in with a passkey" in await typed(REQUEST)
    asked_before = len(fake_provider.requests)
    fake_provider.answers_when("You write the brief of a change", "not json")
    second = await typed("Add rate limiting to the export API.")
    assert second.startswith("Nothing was drafted: brief:") and "passkey" not in second
    briefs = [
        r for r in fake_provider.requests[asked_before:] if "You write the brief" in str(r.config.system_instruction)
    ]
    assert len(briefs) == 3, "the second message has its own three tries"


@pytest.mark.asyncio
async def test_the_chat_drafts_with_the_lessons_as_propose_does(tmp_path, monkeypatch, fake_provider) -> None:
    from adk_spec.domain.lessons_md import TEMPLATE

    ws = seeded(tmp_path)
    (ws.home / "lessons.md").write_text(TEMPLATE.replace("## From people\n", "## From people\n\n- Mine.\n"))
    await said(loaded(tmp_path, monkeypatch), REQUEST)
    deltas = next(
        str(r.config.system_instruction) for r in fake_provider.requests if DELTAS in str(r.config.system_instruction)
    )
    assert "- Mine." in deltas


def test_the_chat_loads_where_the_profile_will_not_open(tmp_path, monkeypatch) -> None:
    """Found by the code review: the chat read the profile once it was given it, and one that would not open
    stopped it loading."""
    ws = seeded(tmp_path)
    profile = ws.home / "profile.md"
    profile.write_text("# This repository\n")
    with shut(profile):
        assert loaded(tmp_path, monkeypatch).root_agent is not None


def test_the_chat_loads_where_the_lessons_file_is_no_text(tmp_path, monkeypatch) -> None:
    """Found by the review: a lessons file written as UTF-16, as PowerShell 5.1 writes, stopped the chat loading."""
    ws = seeded(tmp_path)
    (ws.home / "lessons.md").write_bytes("- a lesson\n".encode("utf-16"))
    assert loaded(tmp_path, monkeypatch).root_agent is not None


@pytest.mark.asyncio
async def test_the_chat_tells_the_brief_what_triage_sized_as_propose_does(tmp_path, monkeypatch, fake_provider) -> None:
    """Found by the third audit: the chat drafted the brief without the capabilities triage found, which `propose`
    gives it, and one message's would have stayed for the next."""
    seeded(tmp_path)
    await said(loaded(tmp_path, monkeypatch), REQUEST)
    assert between(sent_to(fake_provider, "You write the brief"), "sized") == "auth"


@pytest.mark.asyncio
async def test_the_chat_drafts_with_the_profile_as_propose_does(tmp_path, monkeypatch, fake_provider) -> None:
    """Found by the fourth audit: `propose` gave the brief and the deltas the repository's profile, and the chat,
    which drafts as `propose --no-input` drafts, did not."""
    ws = seeded(tmp_path)
    (ws.home / "profile.md").write_text("# This repository\n\nSessions live in Redis, keyed by user.\n")
    await said(loaded(tmp_path, monkeypatch), REQUEST)
    assert "Sessions live in Redis, keyed by user." in str(sent_to(fake_provider, "You write the brief"))
