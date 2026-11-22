"""Probe of the pinned pair (google-adk 2.14.1, litellm 1.106.2) for the facts the foundation plan asserts.

No provider is contacted: a fake Gemini model through ADK's registry, and ADK's LiteLLM client replaced.
"""

from __future__ import annotations

import asyncio
import json
import ntpath
import os
import time
from typing import Literal

os.environ["LITELLM_MODE"] = "PRODUCTION"
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
os.environ["GOOGLE_API_KEY"] = "offline"

from google.adk.agents import LlmAgent  # noqa: E402
from google.adk.apps.app import App  # noqa: E402
from google.adk.models import FallbackModel  # noqa: E402
from google.adk.models.google_llm import Gemini  # noqa: E402
from google.adk.models.lite_llm import LiteLlm, LiteLLMClient, _to_litellm_response_format  # noqa: E402
from google.adk.models.llm_request import LlmRequest  # noqa: E402
from google.adk.models.llm_response import LlmResponse  # noqa: E402
from google.adk.models.registry import LLMRegistry  # noqa: E402
from google.adk.runners import InMemoryRunner  # noqa: E402
from google.adk.workflow import Workflow  # noqa: E402
from google.genai import types  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402


class Triage(BaseModel):
    """How much ceremony a change request needs."""

    tier: Literal["none", "lean", "standard", "strict"] = Field(description="The smallest tier that fits.")
    capabilities: list[str] = Field(description="Kebab-case capability slugs the request touches.")
    reason: str = Field(description="One sentence: why this tier.")


def section(title: str) -> None:
    print(f"\n=== {title}")


section("1. LiteLlm keeps extra keywords")
model = LiteLlm(model="github_copilot/gpt-5.3-codex", max_retries=2, _skip_mcp_handler=True)
print("model.model:", model.model)
print("_additional_args:", getattr(model, "_additional_args", "<no such attribute>"))

section("2. LiteLLM 1.106.2 bundled map: Copilot candidates")
import litellm  # noqa: E402

for name in ("gpt-5.3-codex", "claude-sonnet-5.5", "gpt-6-luna", "claude-haiku-5.5", "gpt-6.1-terra", "gpt-4.1", "gpt-99-none"):
    entry = litellm.model_cost.get(f"github_copilot/{name}")
    if entry is None:
        print(f"  {name}: NOT IN MAP")
        continue
    keys = ("mode", "supports_response_schema", "supports_reasoning", "max_input_tokens", "supported_endpoints")
    print(f"  {name}:", {k: entry.get(k) for k in keys})
print("  copilot entries:", sum(1 for k in litellm.model_cost if k.startswith("github_copilot/")))
print("  disable_copilot_system_to_assistant default:", litellm.disable_copilot_system_to_assistant)

section("3. FallbackModel")
print("DEFAULT_STATUS_CODES:", sorted(FallbackModel.DEFAULT_STATUS_CODES))
fb = FallbackModel(models=["gemini-3.8-flash", "gemini-4-hydrogen"], retriable_status_codes=FallbackModel.DEFAULT_STATUS_CODES | {408})
print("retriable_status_codes attr:", sorted(fb.retriable_status_codes))

section("4. Strict schema as ADK writes it for the Copilot arm")
fmt = _to_litellm_response_format(Triage, "github_copilot/gpt-5.3-codex")
print(json.dumps(fmt, indent=1)[:900])

section("5. What ADK passes LiteLLM when the request carries no temperature")
called: dict = {}


class Capture(LiteLLMClient):
    async def acompletion(self, **kwargs):
        called.update(kwargs)
        return litellm.ModelResponse(
            choices=[{"message": {"role": "assistant", "content": '{"tier":"lean","capabilities":["auth"],"reason":"small"}'}}],
            usage={"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
        )


async def no_temperature() -> None:
    model.llm_client = Capture()
    config = types.GenerateContentConfig(
        http_options=types.HttpOptions(timeout=180_000), response_schema=Triage, response_mime_type="application/json"
    )
    request = LlmRequest(model=model.model, contents=[types.UserContent("triage")], config=config)
    answers = [r async for r in model.generate_content_async(request)]
    shown = {k: v for k, v in called.items() if k not in ("messages", "response_format")}
    print("kwargs (less messages/response_format):", shown)
    print("has temperature key:", "temperature" in called, "| response_format type:", (called.get("response_format") or {}).get("type"))
    print("usage on response:", answers[-1].usage_metadata)


asyncio.run(no_temperature())

section("6. One schema-bound LlmAgent in a Workflow, fake model through the registry, seeded state")
SEEN: list[LlmRequest] = []


class FakeModel(Gemini):
    model: str = "fake"
    reply: str = '{"tier":"lean","capabilities":["auth"],"reason":"one small change"}'

    @classmethod
    def supported_models(cls) -> list[str]:
        return [r"fake.*"]

    async def generate_content_async(self, llm_request, stream=False):
        SEEN.append(llm_request)
        yield LlmResponse(
            content=types.ModelContent(REPLY[0]),
            usage_metadata=types.GenerateContentResponseUsageMetadata(
                prompt_token_count=100, candidates_token_count=20, total_token_count=120
            ),
        )


REPLY = ['{"tier":"lean","capabilities":["auth"],"reason":"one small change"}']
LLMRegistry.register(FakeModel)


def build() -> App:
    agent = LlmAgent(
        model="fake",
        name="triage",
        description="Sizes a change request.",
        instruction="Size the request.\n<<< request abc\n{request}\n>>> request abc\nKnown capabilities: {capabilities?}",
        include_contents="none",
        generate_content_config=types.GenerateContentConfig(http_options=types.HttpOptions(timeout=180_000)),
        output_schema=Triage,
        output_key="triage",
    )
    return App(name="adk_spec", root_agent=Workflow(name="adk_spec", edges=[("START", agent)]), plugins=[])


async def run(reply: str, state: dict) -> None:
    REPLY[0] = reply
    SEEN.clear()
    runner = InMemoryRunner(app=build())
    ids = {"app_name": runner.app_name, "user_id": "u", "session_id": f"s{time.monotonic_ns()}"}
    await runner.session_service.create_session(**ids, state=state)
    errors, usage, failure = {}, [], None
    try:
        async for event in runner.run_async(user_id="u", session_id=ids["session_id"], new_message=types.UserContent("triage")):
            if event.error_code:
                errors[event.author] = f"{event.error_code}: {str(event.error_message)[:90]}"
            if event.usage_metadata:
                usage.append((event.author, event.usage_metadata.total_token_count))
    except Exception as exc:  # noqa: BLE001
        failure = f"{type(exc).__name__}: {str(exc)[:110]!r}"
    session = await runner.session_service.get_session(**ids)
    print("  state.triage:", session.state.get("triage"), "| errors:", errors, "| usage:", usage, "| failure:", failure)
    if SEEN:
        cfg = SEEN[0].config
        print("  system_instruction:", repr(str(cfg.system_instruction)[:160]))
        print("  contents:", [(c.role, [p.text for p in c.parts or []]) for c in SEEN[0].contents])
        print("  response_schema:", cfg.response_schema, "| mime:", cfg.response_mime_type, "| temperature:", cfg.temperature)


async def six() -> None:
    print("valid reply, request with braces in it:")
    await run(REPLY[0], {"request": "Add login {with braces} and a `{placeholder}`", "capabilities": "auth, billing"})
    print("valid reply, optional key missing:")
    await run(REPLY[0], {"request": "Add login"})
    print("reply that is not JSON:")
    await run("Sure! It is lean.", {"request": "Add login"})
    print("required key missing from state:")
    await run(REPLY[0], {})


asyncio.run(six())

section("7. Reserved names, asked on this platform through ntpath")
for name in ("con", "CON", "nul.md", "aux", "com1", "auth", "auth.", "auth ", "a:b", "CONIN$"):
    print(f"  {name!r}: {ntpath.isreserved(name)}")

section("8. LLMRegistry.resolve on names the Gemini arm must refuse")
for name in ("gemini-3.8-flash", "gemini-4-hydrogen", "gpt-5.3-codex", "fake", "claude-sonnet-5.5"):
    try:
        print(f"  {name}:", LLMRegistry.resolve(name).__name__)
    except Exception as exc:  # noqa: BLE001
        print(f"  {name}: {type(exc).__name__}: {str(exc).splitlines()[0][:100]}")
