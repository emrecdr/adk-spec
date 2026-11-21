"""One seeded run through ADK's engine, guarded.

A session is created in memory with the state the stages' instructions read, one user message starts the run, every
event is drained, and the state is read back whatever happened. Whatever escapes the engine is caught here and
returned as the run's failure, so what finished is still in the state and what failed is named, never a traceback.
The session is thrown away: the files under `.spec/` are the record.

A run may pause to ask the person something. Run on the pinned engine: the pause is a function call named
`adk_request_input`, and the run goes on only when a function response with that call's id is sent. Plain text sent
instead starts the whole graph again, in silence. So an answer never travels as text here: `answer` is given the
question's payload and its result goes back as that function response.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from collections.abc import Callable
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


def _pause_of(event: Any) -> tuple[str, dict[str, Any]] | None:
    """The pause an event is, as its id and its payload, or None."""
    for part in event.content.parts if event.content and event.content.parts else ():
        call = part.function_call
        if call is not None and call.name == REQUEST_INPUT and call.id:
            return call.id, dict((call.args or {}).get("payload") or {})
    return None


class _Drain:
    """One session's run, a stretch at a time: what each author ended with and what the calls spent, kept across
    stretches."""

    def __init__(self, runner: InMemoryRunner, session_id: str) -> None:
        self.runner, self.session_id = runner, session_id
        self.errors: dict[str, str] = {}
        self.spent = [0, 0, 0, 0]  # calls, prompt, output, total

    async def stretch(self, message: types.Content) -> tuple[str, dict[str, Any]] | None:
        """The run from `message` to its end or its next pause: the pause, or None. The deadline is the stretch's
        own, so the time a person takes to answer counts against none."""
        pause = None
        async with asyncio.timeout(RUN_DEADLINE_S):
            async for event in self.runner.run_async(user_id=USER, session_id=self.session_id, new_message=message):
                if event.error_code:
                    self.errors[event.author] = f"{event.error_code}: {event.error_message}"
                if used := event.usage_metadata:
                    asked, said_back = used.prompt_token_count or 0, used.candidates_token_count or 0
                    counted = (1, asked, said_back, used.total_token_count or asked + said_back)
                    self.spent = [held + more for held, more in zip(self.spent, counted, strict=True)]
                pause = _pause_of(event) or pause
        return pause


async def run_seeded(
    app: App, *, state: dict[str, Any], prompt: str, answer: Callable[[dict[str, Any]], dict[str, Any]] | None = None
) -> Run:
    """One run of `app` over a new session seeded with `state`, started by `prompt`. Where the run pauses to ask,
    `answer` is called with the question's payload and its result is sent back; with no `answer` the run ends there."""
    runner = InMemoryRunner(app=app)
    ids = {"app_name": runner.app_name, "user_id": USER, "session_id": uuid.uuid4().hex}
    await runner.session_service.create_session(**ids, state=state)
    drain = _Drain(runner, ids["session_id"])
    failure: str | None = None
    started = time.perf_counter()
    try:
        pause = await drain.stretch(types.UserContent(prompt))
        while pause is not None and answer is not None:
            reply = types.FunctionResponse(id=pause[0], name=REQUEST_INPUT, response=answer(pause[1]))
            pause = await drain.stretch(types.Content(role="user", parts=[types.Part(function_response=reply)]))
        failure = UNANSWERED if pause is not None else None
    except TimeoutError:
        failure = f"the run did not finish within {RUN_DEADLINE_S:g} s"
    except Exception as exc:  # noqa: BLE001 -- the engine itself: a reply off its schema, or a provider that raised
        failure = f"{type(exc).__name__}: {said(exc)}"
    seconds = time.perf_counter() - started
    session = await runner.session_service.get_session(**ids)
    usage = Usage(*drain.spent)
    if session is None:
        gone = "the run's session was gone when its answers were read"
        return Run({}, drain.errors, failure or gone, usage, seconds)
    return Run(dict(session.state), drain.errors, failure, usage, seconds)
