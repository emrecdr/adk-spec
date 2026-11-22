"""Q4: do SequentialAgent, LoopAgent and ParallelAgent still run in 2.15.0, and what do they warn?"""
import asyncio
import warnings
from typing import AsyncGenerator

from google.adk import Agent, Runner
from google.adk.agents import BaseAgent, LoopAgent, ParallelAgent, SequentialAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.sessions import InMemorySessionService

from fake_llm import FakeLlm, run_and_print, user


class Step(BaseAgent):
    """Deterministic sub-agent; escalates when state['count'] reaches `stop_at`."""
    stop_at: int = 0

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        n = ctx.session.state.get("count", 0) + 1
        yield Event(invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
                    content={"role": "model", "parts": [{"text": f"{self.name} n={n}"}]},
                    actions=EventActions(state_delta={"count": n, f"{self.name}_seen": n},
                                         escalate=bool(self.stop_at and n >= self.stop_at)))


def construct(label, factory):
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        agent = factory()
    print(f"\n=== {label}: constructed {type(agent).__name__}")
    for x in w:
        print(f"  WARNING at construction -> {x.category.__name__}: {x.message}")
        print(f"     reported at {x.filename.split('/')[-1]}:{x.lineno}")
    if not w:
        print("  no warning at construction")
    return agent


async def run(agent, app_name):
    ss = InMemorySessionService()
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        runner = Runner(agent=agent, app_name=app_name, session_service=ss)
        s = await ss.create_session(app_name=app_name, user_id="u")
        await run_and_print(runner, user_id="u", session_id=s.id, new_message=user("go"))
    got = await ss.get_session(app_name=app_name, user_id="u", session_id=s.id)
    print("  state:", dict(got.state))
    print("  warnings while running:", [(x.category.__name__, str(x.message)[:160]) for x in w] or "none")


async def main():
    llm = FakeLlm(replies=["draft text from fake model"])
    seq = construct("SequentialAgent", lambda: SequentialAgent(
        name="seq", sub_agents=[Agent(name="writer", model=llm, instruction="write", output_key="draft"),
                                Step(name="s1"), Step(name="s2")]))
    await run(seq, "q4seq")

    loop = construct("LoopAgent(max_iterations=5), sub-agent escalates at count 3", lambda: LoopAgent(
        name="loop", max_iterations=5, sub_agents=[Step(name="worker"), Step(name="checker", stop_at=3)]))
    await run(loop, "q4loop")

    loop2 = construct("LoopAgent(max_iterations=2), nobody escalates", lambda: LoopAgent(
        name="loop2", max_iterations=2, sub_agents=[Step(name="w2")]))
    await run(loop2, "q4loop2")

    par = construct("ParallelAgent", lambda: ParallelAgent(
        name="par", sub_agents=[Step(name="p1"), Step(name="p2"), Step(name="p3")]))
    await run(par, "q4par")

    print("\n=== default warning filter (what a user sees without -W): run `python -c` separately")


asyncio.run(main())
