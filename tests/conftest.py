"""Shared test plumbing: a fake model registered with ADK, and an environment no test inherits anything from.

The fake goes through ADK's own resolution path: `LLMRegistry` maps a model name to a class by regex, so registering
`FakeModel` for `fake.*` and setting `SPEC_MODEL=fake` on the Gemini arm makes the real `build_model()` hand its
agents the fake. Nothing in the package is patched: the real runner, workflow and agents all run. The fake answers
the canned answer the request's schema accepts, a sentence where there is no schema, and what a test told it for a
request whose instruction contains a text.
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncGenerator, Iterator
from pathlib import Path

import pytest
from google.adk.models.google_llm import Gemini
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.models.registry import LLMRegistry
from google.genai import types
from pydantic import BaseModel, ValidationError

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "adk_spec"

#: The answers the fake gives by default, one a schema: the first one a request's schema accepts.
CANNED: tuple[dict, ...] = ({"tier": "lean", "capabilities": ["auth"], "reason": "one small change"},)


def canned_for(schema: type[BaseModel]) -> dict:
    """The canned answer `schema` accepts: the fake answers as the schema requires, whichever schema it is."""
    for payload in CANNED:
        try:
            schema.model_validate(payload)
        except ValidationError:
            continue
        return payload
    raise AssertionError(f"no canned answer fits {schema.__name__}")


class FakeProvider:
    """What the fake does for a request whose instruction contains a text, per test, and every request it was sent."""

    def __init__(self) -> None:
        self.rules: list[tuple[str, Exception | dict | str]] = []
        self.requests: list[LlmRequest] = []

    def clear(self) -> None:
        self.rules.clear()
        self.requests.clear()

    def raises_when(self, text: str, exc: Exception) -> None:
        self.rules.append((text, exc))

    def answers_when(self, text: str, payload: dict | str) -> None:
        """`payload` in place of the canned answer; as a str, the text itself."""
        self.rules.append((text, payload))

    def answer(self, llm_request: LlmRequest) -> dict | str | None:
        instruction = str(llm_request.config.system_instruction or "")
        for text, rule in self.rules:
            if text in instruction:
                if isinstance(rule, Exception):
                    raise rule
                return rule
        return None


PROVIDER = FakeProvider()  # process-wide, like the registry below; the fixture clears it around each test


class FakeModel(Gemini):
    """Answers instantly and offline. A Gemini model, as the Gemini arm, where it runs, requires one."""

    model: str = "fake"

    @classmethod
    def supported_models(cls) -> list[str]:
        return [r"fake.*"]

    async def generate_content_async(
        self,
        llm_request: LlmRequest,
        stream: bool = False,  # noqa: ARG002 -- the BaseLlm contract
    ) -> AsyncGenerator[LlmResponse]:
        PROVIDER.requests.append(llm_request)
        payload = PROVIDER.answer(llm_request)
        schema = llm_request.config.response_schema
        if payload is None and schema is not None:
            payload = canned_for(schema)
        if isinstance(payload, str):
            text = payload
        else:
            text = json.dumps(payload) if payload is not None else "Hello from the fake model."
        yield LlmResponse(
            content=types.ModelContent(text),
            usage_metadata=types.GenerateContentResponseUsageMetadata(
                prompt_token_count=100, candidates_token_count=20, total_token_count=120
            ),
        )


LLMRegistry.register(FakeModel)  # process-wide, once; `fake.*` matches nothing a real run would name


@pytest.fixture
def fake_provider() -> Iterator[FakeProvider]:
    """The fake's behaviour for one test; whatever a test sets is gone before the next."""
    PROVIDER.clear()
    yield PROVIDER
    PROVIDER.clear()


def pytest_configure() -> None:
    """Before any test module imports LiteLLM, which in its default mode reads the nearest `.env` into the process
    and fetches its model map from the network."""
    os.environ["LITELLM_MODE"] = "PRODUCTION"
    os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"


@pytest.fixture(autouse=True)
def _umask_kept() -> Iterator[None]:
    """No test leaves its umask to the next: the login sets 0o077 for its whole process."""
    umask = os.umask
    mask = umask(0o022)
    umask(mask)
    yield
    umask(mask)


@pytest.fixture(autouse=True)
def _nothing_from_the_shell(monkeypatch: pytest.MonkeyPatch, tmp_path_factory: pytest.TempPathFactory) -> None:
    """No test inherits a provider, a model, a key or where an arm's calls go, nor reads the developer's Copilot
    login: its folder is one no test made. Each test sets what it runs on."""
    for name in [name for name in os.environ if name.startswith("SPEC_")] + [
        "GOOGLE_GENAI_USE_ENTERPRISE",
        "GOOGLE_GENAI_USE_VERTEXAI",
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_CLOUD_PROJECT",
        "GOOGLE_CLOUD_LOCATION",
        "GITHUB_COPILOT_API_BASE",
        "GITHUB_COPILOT_ACCESS_TOKEN_FILE",
        "GITHUB_COPILOT_API_KEY_FILE",
    ]:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("GITHUB_COPILOT_TOKEN_DIR", str(tmp_path_factory.getbasetemp() / "no-copilot-login"))


def cached_copilot_token(monkeypatch: pytest.MonkeyPatch, folder: Path, text: str | None = "a token") -> None:
    """The Copilot arm's token cache in `folder`, holding `text`, or holding no token where `text` is None."""
    if text is not None:
        (folder / "access-token").write_text(text, encoding="utf-8")
    monkeypatch.setenv("GITHUB_COPILOT_TOKEN_DIR", str(folder))


@pytest.fixture(autouse=True)
def _no_dotenv(monkeypatch: pytest.MonkeyPatch) -> None:
    """No test reads the developer's `.env`: the command's one loader is replaced."""
    from adk_spec.interfaces import cli

    monkeypatch.setattr(cli, "_load_env", lambda: None)


def device_flow(monkeypatch: pytest.MonkeyPatch) -> None:
    """The Copilot login's device flow with no network and no wait: GitHub's code for the person to enter, then each
    poll answered as `github_answers` says."""
    import importlib

    from litellm.llms.github_copilot import authenticator

    code = {"device_code": "d", "user_code": "ABCD-1234", "verification_uri": "https://github.com/login/device"}
    monkeypatch.setattr(authenticator.Authenticator, "_get_device_code", lambda _self: code)
    monkeypatch.setattr(importlib.import_module("adk_spec.interfaces.login").time, "sleep", lambda _seconds: None)


def github_answers(monkeypatch: pytest.MonkeyPatch, reply: object) -> None:
    """GitHub's token endpoint, answering `reply` to each poll of the login: no network in the suite. A dict is the
    JSON object GitHub sends; an `httpx.Response` is handed over as it is, a page that is no JSON among them."""
    from types import SimpleNamespace

    import httpx

    class Client:
        def __init__(self, **_kwargs) -> None: ...

        def __enter__(self):
            return self

        def __exit__(self, *_exc) -> bool:
            return False

        def post(self, *_args, **_kwargs):
            return reply if isinstance(reply, httpx.Response) else SimpleNamespace(json=lambda: reply)

    monkeypatch.setattr(httpx, "Client", Client)  # the login imports httpx and resolves Client at the call


def seeded(root: Path):
    """A workspace at `root` holding the sample living spec of `auth` and one lean draft change, `passkeys`, with
    its brief, tasks and delta: where most tests of the workspace and the command start."""
    from samples import BRIEF, DELTA, SPEC, TASKS

    from adk_spec.domain.spec_md import parse_spec
    from adk_spec.workspace.files import write_text
    from adk_spec.workspace.layout import Workspace

    workspace = Workspace.init(root)
    workspace.write_specs({"auth": parse_spec(SPEC)})
    folder = workspace.new_change("passkeys", "lean")
    write_text(folder / "brief.md", BRIEF)
    write_text(folder / "tasks.md", TASKS)
    write_text(folder / "specs" / "auth" / "spec.md", DELTA)
    return workspace
