"""Q3 (extra): how does a custom BaseAgent node hand data to the next Workflow node?
Variant 1 yields only content (text); variant 2 also sets Event.output."""
import asyncio
from typing import AsyncGenerator

from google.adk import Runner, Workflow
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.sessions import InMemorySessionService

from fake_llm import run_and_print, user


class TextOnly(BaseAgent):
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        yield Event(invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
                    content={"role": "model", "parts": [{"text": "verdict as text"}]})


class WithOutput(BaseAgent):
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        yield Event(invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
                    output={"ok": True, "missing": []})


def upstream(node_input: str):
    return {"spec": node_input}


def downstream(node_input):
    print(f"    downstream got node_input={node_input!r}")
    return "done"


async def main():
    for cls in (TextOnly, WithOutput):
        ss = InMemorySessionService()
        runner = Runner(node=Workflow(name="wf", edges=[("START", upstream, cls(name="gate"), downstream)]),
                        session_service=ss)
        s = await ss.create_session(app_name=runner.app_name, user_id="u")
        await run_and_print(runner, user_id="u", session_id=s.id, new_message=user("spec"), label=cls.__name__)


asyncio.run(main())
