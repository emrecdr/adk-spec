"""Shared helpers for the ADK 2.15.0 spike: a fake model and an event printer.

No model provider is ever contacted: FakeLlm subclasses google.adk.models.base_llm.BaseLlm
and yields canned LlmResponse objects, the same technique as ADK's own MockModel
(tests/unittests/testing_utils.py in the repository).
"""
from __future__ import annotations

from typing import Any, AsyncGenerator

from google.genai import types
from pydantic import Field

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse


class FakeLlm(BaseLlm):
    """Returns scripted responses in order; records every request it receives."""

    model: str = "fake-model"
    replies: list[Any] = Field(default_factory=list)
    requests: list[Any] = Field(default_factory=list)
    calls: int = 0
    usage: bool = False  # attach fake usage_metadata when True

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        self.requests.append(llm_request)
        if self.calls >= len(self.replies):
            raise RuntimeError(
                f"FakeLlm exhausted: call #{self.calls + 1} but only {len(self.replies)} replies scripted"
            )
        reply = self.replies[self.calls]
        self.calls += 1
        if isinstance(reply, Exception):
            raise reply
        if isinstance(reply, LlmResponse):
            yield reply
            return
        if isinstance(reply, types.Part):
            parts = [reply]
        elif isinstance(reply, list):
            parts = reply
        else:
            parts = [types.Part(text=str(reply))]
        kwargs: dict[str, Any] = {}
        if self.usage:
            kwargs["usage_metadata"] = types.GenerateContentResponseUsageMetadata(
                prompt_token_count=11, candidates_token_count=7, total_token_count=18
            )
            kwargs["model_version"] = "fake-model-001"
        yield LlmResponse(content=types.Content(role="model", parts=parts), **kwargs)


def fc(name: str, args: dict, id: str | None = None) -> types.Part:
    """A scripted function-call part."""
    return types.Part(function_call=types.FunctionCall(name=name, args=args, id=id))


def user(text: str) -> types.Content:
    return types.Content(role="user", parts=[types.Part(text=text)])


def _short(v: Any, n: int = 110) -> str:
    s = repr(v)
    return s if len(s) <= n else s[: n - 3] + "..."


def describe(event) -> str:
    """One-line description of an ADK Event with the fields that matter here."""
    bits = [f"author={event.author!r}"]
    ni = getattr(event, "node_info", None)
    if ni is not None and ni.path:
        bits.append(f"node_path={ni.path!r}")
    if event.content and event.content.parts:
        for p in event.content.parts:
            if p.text is not None:
                bits.append(f"text={_short(p.text, 90)}")
            if p.function_call:
                bits.append(
                    f"function_call={p.function_call.name}(id={p.function_call.id!r}, args={_short(dict(p.function_call.args or {}), 120)})"
                )
            if p.function_response:
                bits.append(
                    f"function_response={p.function_response.name}(id={p.function_response.id!r}, response={_short(p.function_response.response, 100)})"
                )
    if event.output is not None:
        bits.append(f"output={_short(event.output)}")
    a = event.actions
    if a.state_delta:
        bits.append(f"state_delta={_short(dict(a.state_delta), 140)}")
    if a.artifact_delta:
        bits.append(f"artifact_delta={dict(a.artifact_delta)}")
    if getattr(a, "route", None) is not None:
        bits.append(f"route={a.route!r}")
    if a.escalate:
        bits.append("escalate=True")
    if a.transfer_to_agent:
        bits.append(f"transfer_to_agent={a.transfer_to_agent!r}")
    if getattr(a, "end_of_agent", None):
        bits.append("end_of_agent=True")
    if getattr(a, "agent_state", None):
        bits.append(f"agent_state={_short(a.agent_state, 100)}")
    if event.long_running_tool_ids:
        bits.append(f"long_running_tool_ids={sorted(event.long_running_tool_ids)}")
    if event.branch:
        bits.append(f"branch={event.branch!r}")
    if event.error_code or event.error_message:
        bits.append(f"error={event.error_code!r}:{_short(event.error_message, 160)}")
    if event.partial:
        bits.append("partial=True")
    return " | ".join(bits)


async def run_and_print(runner, *, user_id: str, session_id: str, label: str = "", **kwargs) -> list:
    """Drives runner.run_async(...) and prints one line per event."""
    events = []
    if label:
        print(f"--- {label}")
    async for ev in runner.run_async(user_id=user_id, session_id=session_id, **kwargs):
        events.append(ev)
        print(f"  [{len(events):02d}] {describe(ev)}")
    return events
