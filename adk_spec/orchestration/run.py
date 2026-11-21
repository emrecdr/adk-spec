"""One seeded run through ADK's engine, guarded.

A session is created in memory with the state the stages' instructions read, one user message starts the run, every
event is drained, and the state is read back whatever happened. Whatever escapes the engine is caught here and
returned as the run's failure, so what finished is still in the state and what failed is named, never a traceback.
The session is thrown away: the files under `.spec/` are the record.

No run of this package pauses to ask a person anything. Found by review, and run on the pinned engine: when a paused
run is resumed, ADK replays the graph from its start and runs again, unseen, any node that had ended in an error
event, which a stage's answer off its schema is. So a command that needs an answer ends its run, asks, and starts a
new run seeded with the answer. A pause met here all the same ends the run and is said.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass
from typing import Any

from google.adk.apps.app import App
from google.adk.runners import InMemoryRunner
from google.genai import types

from .models import RUN_DEADLINE_S, said

USER = "adk-spec"
#: The name ADK gives the function call a `RequestInput` pause is.
REQUEST_INPUT = "adk_request_input"
UNANSWERED = "the run asked a question and none could be answered"


@dataclass(frozen=True)
class Usage:
    """What a run's model calls spent, as the provider counted it."""

    calls: int = 0
    prompt: int = 0
    output: int = 0
    total: int = 0


@dataclass(frozen=True)
class Run:
    """What one run left behind: the state, the error each author ended with, the engine's own failure, what the
    model calls spent, and how long it took."""

    state: dict[str, Any]
    errors: dict[str, str]  # author -> "<code>: <message>", from the error event it ended with
    failure: str | None  # what escaped the engine, if anything did
    usage: Usage
    seconds: float


def _paused(event: Any) -> bool:
    """Whether an event is a pause for a person's input."""
    parts = event.content.parts if event.content and event.content.parts else ()
    return any(part.function_call is not None and part.function_call.name == REQUEST_INPUT for part in parts)


async def run_seeded(app: App, *, state: dict[str, Any], prompt: str) -> Run:
    """One run of `app` over a new session seeded with `state`, started by `prompt`."""
    runner = InMemoryRunner(app=app)
    ids = {"app_name": runner.app_name, "user_id": USER, "session_id": uuid.uuid4().hex}
    await runner.session_service.create_session(**ids, state=state)
    errors: dict[str, str] = {}
    failure: str | None = None
    spent = [0, 0, 0, 0]  # calls, prompt, output, total
    started = time.perf_counter()
    try:
        async with asyncio.timeout(RUN_DEADLINE_S):
            async for event in runner.run_async(
                user_id=USER, session_id=ids["session_id"], new_message=types.UserContent(prompt)
            ):
                if event.error_code:
                    errors[event.author] = f"{event.error_code}: {event.error_message}"
                if used := event.usage_metadata:
                    asked, answered = used.prompt_token_count or 0, used.candidates_token_count or 0
                    counted = (1, asked, answered, used.total_token_count or asked + answered)
                    spent = [held + more for held, more in zip(spent, counted, strict=True)]
                if _paused(event):
                    failure = UNANSWERED
    except TimeoutError:
        failure = f"the run did not finish within {RUN_DEADLINE_S:g} s"
    except Exception as exc:  # noqa: BLE001 -- the engine itself: a reply off its schema, or a provider that raised
        failure = f"{type(exc).__name__}: {said(exc)}"
    seconds = time.perf_counter() - started
    session = await runner.session_service.get_session(**ids)
    usage = Usage(*spent)
    if session is None:
        return Run({}, errors, failure or "the run's session was gone when its answers were read", usage, seconds)
    return Run(dict(session.state), errors, failure, usage, seconds)
