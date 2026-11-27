"""`adk-spec login`: GitHub's device flow for the Copilot arm, with no network and no wait."""

from __future__ import annotations

import os
import stat

import httpx
import pytest
from conftest import cached_copilot_token, device_flow, github_answers
from litellm.llms.github_copilot.authenticator import Authenticator
from litellm.llms.github_copilot.common_utils import GetAPIKeyError

from adk_spec.interfaces.cli import main


def test_a_cached_token_is_said_and_no_login_starts(monkeypatch, tmp_path, capsys) -> None:
    cached_copilot_token(monkeypatch, tmp_path)
    assert main(["login"]) == 0
    assert "already authenticated" in capsys.readouterr().out


def test_the_token_github_grants_is_cached_and_exchanged_once(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setenv("GITHUB_COPILOT_TOKEN_DIR", str(tmp_path))
    device_flow(monkeypatch)
    github_answers(monkeypatch, {"access_token": "granted"})
    exchanged: list[int] = []
    monkeypatch.setattr(Authenticator, "get_api_key", lambda _self: exchanged.append(1) or "key")
    assert main(["login"]) == 0
    assert (tmp_path / "access-token").read_text(encoding="utf-8") == "granted" and exchanged == [1]
    assert "ABCD-1234" in capsys.readouterr().out


def test_a_refusal_at_github_is_a_sentence_and_exit_1(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setenv("GITHUB_COPILOT_TOKEN_DIR", str(tmp_path))
    device_flow(monkeypatch)
    github_answers(monkeypatch, {"error": "access_denied", "error_description": "The user denied it"})
    assert main(["login"]) == 1
    assert "access_denied" in capsys.readouterr().err and not (tmp_path / "access-token").exists()


def test_a_page_where_json_should_be_is_a_sentence(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setenv("GITHUB_COPILOT_TOKEN_DIR", str(tmp_path))
    device_flow(monkeypatch)
    github_answers(monkeypatch, httpx.Response(502, text="<html>bad gateway</html>"))
    assert main(["login"]) == 1
    assert "HTTP 502" in capsys.readouterr().err


def test_an_account_copilot_serves_no_key_keeps_no_token(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setenv("GITHUB_COPILOT_TOKEN_DIR", str(tmp_path))
    device_flow(monkeypatch)
    github_answers(monkeypatch, {"access_token": "granted"})

    def no_seat(_self):
        raise GetAPIKeyError(status_code=403, message="no seat")

    monkeypatch.setattr(Authenticator, "get_api_key", no_seat)
    assert main(["login"]) == 1
    assert not (tmp_path / "access-token").exists() and "no Copilot seat" in capsys.readouterr().err


def test_force_logs_in_again_over_a_cached_token(monkeypatch, tmp_path) -> None:
    cached_copilot_token(monkeypatch, tmp_path, "an old token")
    device_flow(monkeypatch)
    github_answers(monkeypatch, {"access_token": "granted"})
    monkeypatch.setattr(Authenticator, "get_api_key", lambda _self: "key")
    assert main(["login", "--force"]) == 0
    assert (tmp_path / "access-token").read_text(encoding="utf-8") == "granted"


def test_help_starts_no_login(monkeypatch) -> None:
    monkeypatch.setattr(Authenticator, "_get_device_code", lambda _self: pytest.fail("a login began"))
    with pytest.raises(SystemExit) as stopped:
        main(["login", "--help"])
    assert stopped.value.code == 0


def test_the_login_finds_every_litellm_name_it_uses() -> None:
    """The canary for a LiteLLM bump: 1.110.0 removed three of these."""
    from litellm.llms.github_copilot.authenticator import DEFAULT_GITHUB_ACCESS_TOKEN_URL, DEFAULT_GITHUB_CLIENT_ID
    from litellm.llms.github_copilot.common_utils import GetDeviceCodeError

    assert DEFAULT_GITHUB_ACCESS_TOKEN_URL and DEFAULT_GITHUB_CLIENT_ID and GetAPIKeyError and GetDeviceCodeError
    for name in ("_get_device_code", "_get_github_headers", "_ensure_token_dir", "get_api_key"):
        assert hasattr(Authenticator, name), name
    assert hasattr(Authenticator(), "api_key_file")
    from litellm.llms.github_copilot.common_utils import get_copilot_default_headers

    assert hasattr(Authenticator, "get_api_base") and "Authorization" in get_copilot_default_headers("k")


@pytest.mark.skipif(os.name == "nt", reason="a Windows file has no owner, group and other modes to narrow")
def test_the_token_is_its_owners_alone(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("GITHUB_COPILOT_TOKEN_DIR", str(tmp_path))
    device_flow(monkeypatch)
    github_answers(monkeypatch, {"access_token": "granted"})
    monkeypatch.setattr(Authenticator, "get_api_key", lambda _self: "key")
    assert main(["login"]) == 0
    assert stat.S_IMODE((tmp_path / "access-token").stat().st_mode) == 0o600


def test_login_tells_litellm_it_runs_in_production_before_it_is_imported(monkeypatch, tmp_path) -> None:
    """The audit of 25 November (S8): imported as it stood, LiteLLM read a `.env` up from its own folder and fetched a
    price list from the network."""
    monkeypatch.delenv("LITELLM_MODE", raising=False)
    monkeypatch.delenv("LITELLM_LOCAL_MODEL_COST_MAP", raising=False)
    monkeypatch.setenv("GITHUB_COPILOT_TOKEN_DIR", str(tmp_path))
    device_flow(monkeypatch)
    github_answers(monkeypatch, {"access_token": "granted"})
    monkeypatch.setattr(Authenticator, "get_api_key", lambda _self: "key")
    assert main(["login"]) == 0
    assert (os.environ["LITELLM_MODE"], os.environ["LITELLM_LOCAL_MODEL_COST_MAP"]) == ("PRODUCTION", "True")
