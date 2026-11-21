"""`adk-spec models`: what the chosen arm serves, asked with the arm's own credentials and no model call."""

from __future__ import annotations

import json
import time
from types import SimpleNamespace

import httpx
import pytest
from conftest import cached_copilot_token

from adk_spec.interfaces.cli import main
from adk_spec.orchestration.catalog import list_models, shown

ENTRY = {"id": "model-a", "vendor": "v", "model_picker_enabled": True, "policy": {"state": "enabled"}}


def _copilot_answers(monkeypatch, tmp_path, status: int, body: object) -> list[httpx.Request]:
    """A cached token and key, and Copilot's model list answering `body`: no network in the suite."""
    key = {"token": "a key", "expires_at": time.time() + 3600, "endpoints": {"api": "https://copilot.invalid"}}
    (tmp_path / "api-key.json").write_text(json.dumps(key), encoding="utf-8")
    cached_copilot_token(monkeypatch, tmp_path)
    asked: list[httpx.Request] = []

    def send(_client, request, *_args, **_kwargs):
        asked.append(request)
        if isinstance(body, str):
            return httpx.Response(status, text=body, request=request)
        return httpx.Response(status, json=body, request=request)

    monkeypatch.setattr(httpx.Client, "send", send)
    return asked


def test_the_copilot_list_is_asked_with_litellms_own_key_base_and_headers(monkeypatch, tmp_path) -> None:
    asked = _copilot_answers(monkeypatch, tmp_path, 200, {"data": [ENTRY]})
    models = list_models()
    assert str(asked[0].url) == "https://copilot.invalid/models" and asked[0].method == "GET"
    assert asked[0].headers["copilot-integration-id"] == "vscode-chat"
    assert asked[0].headers["authorization"] == "Bearer a key"
    assert shown(models) == ["model-a  vendor=v  model_picker_enabled=True  policy.state=enabled"]


def test_a_body_of_another_shape_is_shown_and_not_guessed_at(monkeypatch, tmp_path) -> None:
    _copilot_answers(monkeypatch, tmp_path, 200, {"models": ["x"]})
    models = list_models()
    assert models == [{"models": ["x"]}] and shown(models) == ["(no id)  keys=models"]


def test_models_prints_one_line_a_model_and_json_on_request(monkeypatch, tmp_path, capsys) -> None:
    _copilot_answers(monkeypatch, tmp_path, 200, {"data": [ENTRY, {"id": "model-b"}]})
    assert main(["models"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "model-a  vendor=v  model_picker_enabled=True  policy.state=enabled",
        "model-b",
    ]
    assert main(["models", "--json"]) == 0 and json.loads(capsys.readouterr().out)["models"][1] == {"id": "model-b"}


def test_models_is_a_sentence_where_the_arm_is_not_ready(capsys) -> None:
    assert main(["models"]) == 2 and "adk-spec login" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("body", "said"), [({"error": {"message": "no access"}}, "no access"), ("<html>bad gateway</html>", "HTTP 403")]
)
def test_a_refusal_from_copilot_is_said_in_its_own_words(monkeypatch, tmp_path, capsys, body, said) -> None:
    _copilot_answers(monkeypatch, tmp_path, 403, body)
    assert main(["models"]) == 3
    err = capsys.readouterr().err
    assert said in err and "Traceback" not in err


def test_the_gemini_list_names_each_model(monkeypatch) -> None:
    class Client:
        def __init__(self, **_kwargs) -> None:
            listed = [SimpleNamespace(name="models/gemini-x", display_name="X")]
            self.models = SimpleNamespace(list=lambda: listed)

    monkeypatch.setattr("google.genai.Client", Client)
    monkeypatch.setenv("SPEC_PROVIDER", "gemini")
    assert list_models() == [{"id": "gemini-x", "display_name": "X"}] and shown(list_models()) == ["gemini-x"]
