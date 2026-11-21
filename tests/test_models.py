"""The two provider arms: what the environment names, which model the factory builds, and when an arm is ready."""

from __future__ import annotations

import importlib
import logging
import os
import subprocess
import sys

import litellm
import pytest
from conftest import ROOT, cached_copilot_token
from google.adk.models import FallbackModel
from google.adk.models.lite_llm import LiteLlm, LiteLLMClient
from google.adk.models.llm_request import LlmRequest
from google.genai import types


def _fresh(name: str):
    """The module imported anew, as each test sets its own environment."""
    sys.modules.pop(f"adk_spec.orchestration.{name}", None)
    return importlib.import_module(f"adk_spec.orchestration.{name}")


@pytest.mark.parametrize(
    ("provider", "expected"), [("gemini", str), ("copilot", LiteLlm), (None, LiteLlm), ("", LiteLlm), ("  ", LiteLlm)]
)
def test_both_arms_build_a_model(provider, expected, monkeypatch) -> None:
    if provider is not None:
        monkeypatch.setenv("SPEC_PROVIDER", provider)
    if provider == "gemini":
        monkeypatch.setenv("SPEC_MODEL", "fake")
    assert isinstance(_fresh("models").build_model(), expected)


def test_the_copilot_arm_names_the_model_as_litellm_does(monkeypatch) -> None:
    monkeypatch.setenv("SPEC_MODEL", "claude-sonnet-5.5")
    model = _fresh("models").build_model()
    assert model.model == "github_copilot/claude-sonnet-5.5"
    assert model._additional_args == {"max_retries": 2, "_skip_mcp_handler": True}


def test_the_copilot_arm_defaults_to_the_model_that_answered_live(monkeypatch) -> None:
    """`docs/confirmation/2026-11-smoke.md`: the first model on the owner's seat to answer in the schema."""
    monkeypatch.delenv("SPEC_MODEL", raising=False)
    assert _fresh("settings").model_pick() == ("SPEC_MODEL", "gpt-4.1")
    assert _fresh("models").build_model().model == "github_copilot/gpt-4.1"


def test_a_roles_own_model_wins_over_everyones(monkeypatch) -> None:
    monkeypatch.setenv("SPEC_PROVIDER", "gemini")
    monkeypatch.setenv("SPEC_MODEL", "gemini-3.8-flash")
    monkeypatch.setenv("SPEC_TRIAGE_MODEL", "fake")
    settings = _fresh("settings")
    assert settings.model_pick("triage") == ("SPEC_TRIAGE_MODEL", "fake")
    assert settings.model_pick("brief") == ("SPEC_MODEL", "gemini-3.8-flash")
    assert settings.model_pick() == ("SPEC_MODEL", "gemini-3.8-flash")


def test_a_provider_no_arm_answers_to_is_a_sentence(monkeypatch) -> None:
    monkeypatch.setenv("SPEC_PROVIDER", "openai")
    assert "SPEC_PROVIDER must be one of ['copilot', 'gemini']" in _fresh("models").require_ready()


def test_the_copilot_arm_is_not_ready_without_a_cached_token() -> None:
    assert "adk-spec login" in _fresh("models").require_ready()


def test_the_copilot_arm_refuses_a_model_its_pinned_map_does_not_hold(monkeypatch, tmp_path) -> None:
    cached_copilot_token(monkeypatch, tmp_path)
    monkeypatch.setenv("SPEC_MODEL", "gpt-99-none")
    why = _fresh("models").require_ready()
    assert "SPEC_MODEL=gpt-99-none" in why and "model map" in why


def test_the_copilot_arm_is_ready_with_a_token_and_a_model_the_map_holds(monkeypatch, tmp_path) -> None:
    cached_copilot_token(monkeypatch, tmp_path)
    assert _fresh("models").require_ready(roles=("triage",)) is None


@pytest.mark.parametrize(("installed", "ready"), [(False, False), (True, True)])
def test_a_copilot_gpt_model_needs_the_mcp_package_on_the_pinned_litellm(
    monkeypatch, tmp_path, installed, ready
) -> None:
    """Run on the pinned pair: LiteLLM 1.106.2 imports its MCP gateway on every Responses call, whatever the flag."""
    cached_copilot_token(monkeypatch, tmp_path)
    monkeypatch.setenv("SPEC_MODEL", "gpt-5.3-codex")
    models = _fresh("models")
    monkeypatch.setattr(models, "_has_mcp", lambda: installed)
    why = models.require_ready()
    assert (why is None) is ready
    assert ready or ("SPEC_MODEL=gpt-5.3-codex" in why and "Responses API" in why and "mcp" in why)


def test_the_gemini_arm_refuses_a_model_adk_would_send_elsewhere(monkeypatch) -> None:
    monkeypatch.setenv("SPEC_PROVIDER", "gemini")
    monkeypatch.setenv("SPEC_MODEL", "gpt-5.3-codex")
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key")
    assert "is no Gemini model" in _fresh("models").require_ready()


def test_no_request_carries_a_temperature_and_each_carries_the_deadline() -> None:
    config = _fresh("models").request_config()
    assert config.temperature is None and config.http_options.timeout == 180_000


def test_a_fallback_moves_on_from_a_timeout_too(monkeypatch) -> None:
    monkeypatch.setenv("SPEC_PROVIDER", "gemini")
    monkeypatch.setenv("SPEC_MODEL", "fake")
    monkeypatch.setenv("SPEC_FALLBACK_MODEL", "fake-2")
    model = _fresh("models").build_model()
    assert isinstance(model, FallbackModel) and sorted(model.retriable_status_codes) == [408, 429, 500, 502, 503, 504]


def test_the_copilot_arm_tells_litellm_what_the_factory_decided(monkeypatch, tmp_path) -> None:
    for home in ("HOME", "USERPROFILE"):
        monkeypatch.setenv(home, str(tmp_path))
    monkeypatch.setenv("GITHUB_COPILOT_TOKEN_DIR", "~/tokens")
    monkeypatch.delenv("LITELLM_LOCAL_MODEL_COST_MAP", raising=False)
    _fresh("models").build_model()

    assert litellm.disable_copilot_system_to_assistant is True
    assert os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] == "True" and os.environ["LITELLM_MODE"] == "PRODUCTION"
    assert os.environ["GITHUB_COPILOT_TOKEN_DIR"] == str(tmp_path / "tokens")


@pytest.mark.asyncio
async def test_adk_hands_litellm_the_sdks_retries_one_deadline_and_no_temperature() -> None:
    models = _fresh("models")
    called: dict = {}

    class Capture(LiteLLMClient):
        async def acompletion(self, **kwargs):
            called.update(kwargs)
            return litellm.ModelResponse(choices=[{"message": {"role": "assistant", "content": "ok"}}])

    model = models.build_model()
    model.llm_client = Capture()
    request = LlmRequest(model=model.model, contents=[types.UserContent("x")], config=models.request_config())
    async for _response in model.generate_content_async(request):
        pass
    assert called["max_retries"] == 2 and called.get("num_retries") is None
    assert called["timeout"] == 180.0 and "temperature" not in called


def test_a_bearer_token_never_reaches_a_log_line(caplog) -> None:
    _fresh("models").build_model()
    with caplog.at_level(logging.DEBUG, logger="LiteLLM"):
        logging.getLogger("LiteLLM").debug("headers: {'Authorization': 'Bearer abc123'}")
    assert "abc123" not in caplog.text and "[REDACTED]" in caplog.text


def test_reading_the_settings_loads_no_engine() -> None:
    probe = (
        "import sys; import adk_spec.orchestration.settings\n"
        "print(sorted(m for m in sys.modules if m.startswith(('google.adk', 'litellm'))))\n"
    )
    done = subprocess.run([sys.executable, "-c", probe], cwd=ROOT, capture_output=True, encoding="utf-8", check=False)
    assert done.returncode == 0 and done.stdout.strip() == "[]", done.stderr
