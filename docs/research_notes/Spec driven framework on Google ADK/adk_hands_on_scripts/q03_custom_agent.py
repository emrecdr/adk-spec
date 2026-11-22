"""Q3: is a custom BaseAgent._run_async_impl executed in 2.15.0 when the agent is
(a) the root agent of a Runner, (b) a node inside a Workflow, (c) a sub-agent of an LLM agent?
A module-level counter and a state key written by the override prove execution."""
import asyncio
import warnings
from typing import AsyncGenerator

from google.adk import Agent, Runner, Workflow
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions
from google.adk.sessions import InMemorySessionService

from fake_llm import FakeLlm, fc, run_and_print, user

CALLS: list[str] = []


class SpecGate(BaseAgent):
    """Deterministic custom agent: no model, writes a verdict to state."""

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        CALLS.append(self.name)
        print(f"    >>> SpecGate._run_async_impl EXECUTED (name={self.name}, ctx={type(ctx).__name__}, "
              f"user_content={ctx.user_content.parts[0].text if ctx.user_content and ctx.user_content.parts and ctx.user_content.parts[0].text else None!r})")
        yield Event(
            invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
            content={"role": "model", "parts": [{"text": f"gate verdict from {self.name}"}]},
            actions=EventActions(state_delta={f"{self.name}_ran": True}),
        )


def before_cb(callback_context):
    print(f"    before_agent_callback fired for {callback_context.agent_name}")


def after_cb(callback_context):
    print(f"    after_agent_callback fired for {callback_context.agent_name}")


async def run(label, runner_kwargs, ss=None):
    ss = ss or InMemorySessionService()
    runner = Runner(session_service=ss, **runner_kwargs)
    s = await ss.create_session(app_name=runner.app_name, user_id="u")
    print(f"\n=== {label}")
    before = len(CALLS)
    try:
        await run_and_print(runner, user_id="u", session_id=s.id, new_message=user("check my spec"))
    except Exception as e:  # noqa: BLE001
        print(f"  RAISED {type(e).__name__}: {e}")
    got = await ss.get_session(app_name=runner.app_name, user_id="u", session_id=s.id)
    print(f"  _run_async_impl executions in this run: {len(CALLS) - before}; state={dict(got.state)}")


def upstream(node_input: str):
    return {"spec": node_input}


def downstream(ctx, node_input):
    print(f"    downstream node got node_input={node_input!r} state={dict(ctx.state.to_dict())}")
    return "downstream done"


async def main():
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")

        # (a) root agent through a Runner
        await run("(a) custom BaseAgent as ROOT agent: Runner(agent=..., app_name=...)",
                  dict(agent=SpecGate(name="gate_root", before_agent_callback=before_cb, after_agent_callback=after_cb),
                       app_name="q3a"))

        # (b) node inside a Workflow
        gate_node = SpecGate(name="gate_node", before_agent_callback=before_cb, after_agent_callback=after_cb)
        await run("(b) custom BaseAgent as a NODE inside a Workflow",
                  dict(node=Workflow(name="q3b", edges=[("START", upstream, gate_node, downstream)])))

        # (c) sub-agent of an LLM agent: the fake model asks to transfer to it
        llm = FakeLlm(replies=[fc("transfer_to_agent", {"agent_name": "gate_sub"}), "coordinator final text"])
        coordinator = Agent(
            name="coordinator", model=llm, instruction="Route spec checks to gate_sub.",
            sub_agents=[SpecGate(name="gate_sub", description="Checks specs deterministically.",
                                 before_agent_callback=before_cb, after_agent_callback=after_cb)],
        )
        await run("(c) custom BaseAgent as SUB-AGENT of an LLM agent (fake model emits transfer_to_agent)",
                  dict(agent=coordinator, app_name="q3c"))
        print(f"  fake model calls: {llm.calls}; tools offered to the model on call 1: "
              f"{[fd.name for t in (llm.requests[0].config.tools or []) for fd in (t.function_declarations or [])]}")

        print("\nwarnings during Q3:", [(x.category.__name__, str(x.message)[:200]) for x in w])
    print("total _run_async_impl executions:", CALLS)


asyncio.run(main())
