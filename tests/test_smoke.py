"""`adk-spec smoke`: the triage stage alone, through the real engine, on the fake model and on both arms' own paths."""

from __future__ import annotations

import json
import os
import re
import time

import httpx
import litellm
import pytest
from conftest import CANNED, cached_copilot_token
from google.adk.models.lite_llm import LiteLLMClient
from google.adk.models.llm_request import LlmRequest
from google.genai import types

from adk_spec.domain.drafts import Triage
from adk_spec.interfaces.cli import main
from adk_spec.orchestration.models import build_model, request_config
from adk_spec.orchestration.stages.triage import BOUNDARY, build_triage

REQUEST = "Let users sign in with a passkey."


def _on_the_fake(monkeypatch) -> None:
    monkeypatch.setenv("SPEC_PROVIDER", "gemini")
    monkeypatch.setenv("SPEC_MODEL", "fake")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")


@pytest.mark.usefixtures("fake_provider")
def test_smoke_runs_triage_through_the_real_engine(monkeypatch, capsys) -> None:
    _on_the_fake(monkeypatch)
    assert main(["smoke", "--request", REQUEST, "--json"]) == 0
    said = json.loads(capsys.readouterr().out)
    assert said["model"] == "fake on gemini" and said["schema"] == "valid"
    assert said["triage"] == {"tier": "lean", "capabilities": ["auth"], "reason": "one small change"}
    assert said["tokens"] == {"calls": 1, "prompt": 100, "output": 20, "total": 120}


def test_the_triage_agent_reads_only_its_instruction_and_answers_in_its_schema(monkeypatch) -> None:
    _on_the_fake(monkeypatch)
    agent = build_triage()
    assert agent.include_contents == "none" and agent.output_schema is Triage and agent.output_key == "triage"
    assert agent.tools == [] and agent.generate_content_config.temperature is None


def test_every_placeholder_names_a_key_the_command_seeds(monkeypatch) -> None:
    _on_the_fake(monkeypatch)
    assert set(re.findall(r"\{(\w+)\??\}", build_triage().instruction)) == {"request", "capabilities"}


def test_the_request_reaches_the_model_between_the_markers_and_is_not_expanded(monkeypatch, fake_provider) -> None:
    _on_the_fake(monkeypatch)
    assert main(["smoke", "--request", "Add {braces} and `{request}`"]) == 0
    instruction = str(fake_provider.requests[0].config.system_instruction)
    assert f"<<< request {BOUNDARY}\nAdd {{braces}} and `{{request}}`\n>>> request {BOUNDARY}" in instruction
    assert [part.text for part in fake_provider.requests[0].contents[-1].parts] == ["triage"]


def test_an_answer_off_the_schema_is_reported_and_never_a_traceback(monkeypatch, capsys, fake_provider) -> None:
    _on_the_fake(monkeypatch)
    fake_provider.answers_when("You size a change request", "Sure! It is lean.")
    assert main(["smoke", "--request", REQUEST]) == 3
    out = capsys.readouterr()
    assert "schema    INVALID" in out.out and "Traceback" not in out.out + out.err


def test_a_provider_that_fails_is_a_sentence_and_exit_3(monkeypatch, capsys, fake_provider) -> None:
    _on_the_fake(monkeypatch)
    fake_provider.raises_when("You size a change request", RuntimeError("429 quota exceeded"))
    assert main(["smoke", "--request", REQUEST]) == 3
    assert "429 quota exceeded" in capsys.readouterr().out


def test_an_arm_that_is_not_ready_is_a_sentence_and_exit_2(capsys) -> None:
    assert main(["smoke"]) == 2
    assert "adk-spec login" in capsys.readouterr().err


@pytest.mark.usefixtures("fake_provider")
def test_model_names_the_model_for_this_run_alone(monkeypatch, capsys) -> None:
    monkeypatch.setenv("SPEC_PROVIDER", "gemini")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    assert main(["smoke", "--model", "fake", "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["model"] == "fake on gemini"
    assert "SPEC_TRIAGE_MODEL" not in os.environ and "SPEC_MODEL" not in os.environ, "nothing left for the next run"


def test_smoke_runs_on_the_copilot_arm_with_only_the_client_replaced(monkeypatch, capsys, tmp_path) -> None:
    sent: list[dict] = []

    async def answer(_client, model, **request):
        sent.append({"model": model, **request})
        return litellm.ModelResponse(
            choices=[{"message": {"role": "assistant", "content": json.dumps(CANNED[0])}}],
            usage={"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
        )

    monkeypatch.setattr(LiteLLMClient, "acompletion", answer)
    cached_copilot_token(monkeypatch, tmp_path)
    assert main(["smoke", "--request", REQUEST, "--json"]) == 0
    said = json.loads(capsys.readouterr().out)
    assert said["model"] == "claude-sonnet-5.5 on copilot" and said["schema"] == "valid"
    assert said["tokens"]["total"] == 120
    assert sent[0]["model"] == "github_copilot/claude-sonnet-5.5"
    assert sent[0]["response_format"]["type"] == "json_schema"
    assert sent[0]["messages"][0]["role"] == "system" and "temperature" not in sent[0]


@pytest.mark.asyncio
async def test_below_litellm_copilot_is_sent_a_system_turn_and_the_strict_schema(monkeypatch, tmp_path) -> None:
    """Only the network is replaced, so LiteLLM's own routing runs: a LiteLLM regression once passed every test
    above it."""
    key = {"token": "a key", "expires_at": time.time() + 3600, "endpoints": {"api": "https://copilot.invalid"}}
    (tmp_path / "api-key.json").write_text(json.dumps(key), encoding="utf-8")
    cached_copilot_token(monkeypatch, tmp_path)
    sent: list[tuple[str, dict]] = []

    async def send(_client, request, *_args, **_kwargs):
        sent.append((str(request.url), json.loads(request.content)))
        message = {"role": "assistant", "content": json.dumps(CANNED[0])}
        choice = {"index": 0, "finish_reason": "stop", "message": message}
        reply = {
            "id": "1",
            "object": "chat.completion",
            "created": 1,
            "model": "claude-sonnet-5.5",
            "choices": [choice],
        }
        return httpx.Response(200, json=reply, request=request)

    monkeypatch.setattr(httpx.AsyncClient, "send", send)
    model, config = build_model(), request_config()
    config.system_instruction, config.response_schema, config.response_mime_type = (
        "You size.",
        Triage,
        "application/json",
    )
    request = LlmRequest(model=model.model, contents=[types.UserContent("triage")], config=config)
    answered = [response async for response in model.generate_content_async(request)]
    ((url, body),) = sent
    assert url == "https://copilot.invalid/chat/completions" and body["model"] == "claude-sonnet-5.5"
    assert [m["role"] for m in body["messages"]] == ["system", "user"], "never an assistant turn"
    assert body["response_format"]["json_schema"]["strict"] is True and "temperature" not in body
    assert json.loads(answered[-1].content.parts[0].text) == CANNED[0]


def test_each_arm_is_sent_the_triage_schema_as_it_is_written() -> None:
    """ADK's own converters, private on purpose: an upgrade that moves them fails here at once."""
    from google.adk.models.lite_llm import _to_litellm_response_format
    from google.genai import Client, _transformers

    copilot = _to_litellm_response_format(Triage, "github_copilot/claude-sonnet-5.5")["json_schema"]
    assert copilot["strict"] is True and sorted(copilot["schema"]["required"]) == ["capabilities", "reason", "tier"]
    assert copilot["schema"]["properties"]["tier"]["enum"] == ["none", "lean", "standard", "strict"]
    gemini = _transformers.t_schema(Client(api_key="offline")._api_client, Triage).model_dump(
        exclude_none=True, by_alias=True, mode="json"
    )
    assert "additionalProperties" not in str(gemini)
    assert gemini["properties"]["reason"]["description"] == "One sentence: why this tier."


def test_check_says_whether_the_arm_is_ready_and_calls_no_model(monkeypatch, capsys, fake_provider) -> None:
    """Deferred by the review: a run meant to show "not ready" must never be able to spend a request."""
    _on_the_fake(monkeypatch)
    assert main(["smoke", "--check", "--json"]) == 0
    said = json.loads(capsys.readouterr().out)
    assert said == {"model": "fake on gemini", "ready": True, "why": None} and fake_provider.requests == []
    monkeypatch.delenv("SPEC_PROVIDER")
    assert main(["smoke", "--check"]) == 2
    assert "adk-spec login" in capsys.readouterr().err and fake_provider.requests == []


def test_a_providers_error_is_said_in_its_own_words(monkeypatch, capsys, fake_provider) -> None:
    """Deferred by the review: `said` had no caller. Seen live: LiteLLM's wrapping stood before Copilot's sentence."""
    _on_the_fake(monkeypatch)
    wrapped = RuntimeError("litellm.RuntimeError: Github_copilotException - The requested model is not supported.")
    fake_provider.raises_when("You size a change request", wrapped)
    assert main(["smoke", "--request", REQUEST]) == 3
    out = capsys.readouterr().out
    assert "INVALID: RuntimeError: The requested model is not supported." in out and "Github_copilot" not in out


@pytest.mark.usefixtures("fake_provider")
def test_the_engines_log_level_is_put_back_after_a_run(monkeypatch) -> None:
    """Deferred by the review: the engine's logger was quieted for a run and never restored."""
    import logging

    _on_the_fake(monkeypatch)
    log = logging.getLogger("google_adk")
    log.setLevel(logging.WARNING)
    assert main(["smoke", "--request", REQUEST]) == 0 and log.level == logging.WARNING
