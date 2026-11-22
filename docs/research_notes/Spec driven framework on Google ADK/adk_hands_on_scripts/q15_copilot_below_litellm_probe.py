"""Below LiteLLM: what the pinned LiteLLM 1.106.2 sends for a Copilot model, with only the network replaced.

No provider is contacted: httpx.AsyncClient.send is replaced, and a fake token and key are cached in a temp folder.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Literal

folder = Path(tempfile.mkdtemp())
os.environ["LITELLM_MODE"] = "PRODUCTION"
os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] = "True"
os.environ["GITHUB_COPILOT_TOKEN_DIR"] = str(folder)
(folder / "access-token").write_text("a token", encoding="utf-8")
key = {"token": "a key", "expires_at": time.time() + 3600, "endpoints": {"api": "https://copilot.invalid"}}
(folder / "api-key.json").write_text(json.dumps(key), encoding="utf-8")

import httpx  # noqa: E402
import litellm  # noqa: E402
from google.adk.models.lite_llm import LiteLlm  # noqa: E402
from google.adk.models.llm_request import LlmRequest  # noqa: E402
from google.genai import types  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402

litellm.suppress_debug_info = True
ANSWER = '{"tier":"lean","capabilities":["auth"],"reason":"small"}'


class Triage(BaseModel):
    """How much ceremony a change request needs."""

    tier: Literal["none", "lean", "standard", "strict"] = Field(description="The smallest tier that fits.")
    capabilities: list[str] = Field(description="Kebab-case capability slugs the request touches.")
    reason: str = Field(description="One sentence: why this tier.")


SENT: list[tuple[str, dict]] = []


async def send(_client, request, *_args, **_kwargs):
    body = json.loads(request.content) if request.content else {}
    SENT.append((str(request.url), body))
    if str(request.url).rstrip("/").endswith("/responses"):
        reply = {
            "id": "resp_1", "object": "response", "created_at": 1, "status": "completed", "model": body.get("model"),
            "output": [{"type": "message", "id": "msg_1", "status": "completed", "role": "assistant",
                        "content": [{"type": "output_text", "text": ANSWER, "annotations": []}]}],
            "usage": {"input_tokens": 100, "output_tokens": 20, "total_tokens": 120},
        }
    else:
        choice = {"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": ANSWER}}
        reply = {"id": "1", "object": "chat.completion", "created": 1, "model": body.get("model"), "choices": [choice],
                 "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120}}
    return httpx.Response(200, json=reply, request=request)


httpx.AsyncClient.send = send


async def call(name: str, flag: bool) -> None:
    litellm.disable_copilot_system_to_assistant = flag
    SENT.clear()
    model = LiteLlm(model=f"github_copilot/{name}", max_retries=2, _skip_mcp_handler=True)
    config = types.GenerateContentConfig(
        system_instruction="You size a change request.", http_options=types.HttpOptions(timeout=180_000),
        response_schema=Triage, response_mime_type="application/json",
    )
    request = LlmRequest(model=model.model, contents=[types.UserContent("triage")], config=config)
    try:
        answers = [r async for r in model.generate_content_async(request)]
        text = answers[-1].content.parts[0].text if answers and answers[-1].content else None
        usage = answers[-1].usage_metadata.total_token_count if answers and answers[-1].usage_metadata else None
        outcome = f"answered text={text!r} total_tokens={usage}"
    except Exception as exc:  # noqa: BLE001
        outcome = f"RAISED {type(exc).__name__}: {str(exc)[:200]!r}"
    print(f"\n--- {name}, disable_copilot_system_to_assistant={flag}: {outcome}")
    for url, body in SENT:
        roles = [m.get("role") for m in body.get("messages", [])] if "messages" in body else None
        shape = {k: (type(v).__name__ if k in ("messages", "input", "tools") else v) for k, v in body.items()
                 if k not in ("response_format", "text")}
        print("  url:", url)
        print("  message roles:", roles, "| instructions:", repr(body.get("instructions"))[:60])
        print("  body keys:", shape)
        fmt = body.get("response_format") or body.get("text")
        print("  schema carrier:", "response_format" if "response_format" in body else "text" if "text" in body else None,
              "|", json.dumps(fmt)[:170] if fmt else None)


async def main() -> None:
    await call("claude-sonnet-5.5", True)
    await call("claude-sonnet-5.5", False)
    await call("gpt-5.3-codex", True)
    await call("gpt-6-luna", True)


asyncio.run(main())

print("\n=== LiteLLM logger")
log = logging.getLogger("LiteLLM")
print("propagate:", log.propagate, "| handlers:", [type(h).__name__ for h in log.handlers], "| level:", log.level)
print("python:", sys.version.split()[0])
