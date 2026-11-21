"""Q8: when before_agent_callback or before_model_callback returns content so the model is not
called, is the agent's output_key still written to state? Tested as root agent and workflow node."""
import asyncio

from google.genai import types

from google.adk import Agent, Runner, Workflow
from google.adk.models.llm_response import LlmResponse
from google.adk.sessions import InMemorySessionService

from fake_llm import FakeLlm, describe, user

SEEN = {}


def text(s):
    return types.Content(role="model", parts=[types.Part(text=s)])


def skip_agent(callback_context):
    return text("FROM before_agent_callback")


def skip_agent_and_write_key(callback_context):
    callback_context.state["spec_md"] = "written by the callback itself"
    return text("FROM before_agent_callback")


def skip_model(callback_context, llm_request):
    return LlmResponse(content=text("FROM before_model_callback"))


def downstream(ctx, node_input):
    SEEN["node_input"] = node_input
    return "downstream ran"


async def run(label, *, as_node, in_sequential=False, **cb):
    llm = FakeLlm(replies=["FROM THE MODEL"])
    agent = Agent(name="spec_writer", model=llm, instruction="write", output_key="spec_md", **cb)
    ss = InMemorySessionService()
    if as_node:
        runner = Runner(node=Workflow(name="wf", edges=[("START", agent, downstream)]), session_service=ss)
    elif in_sequential:
        import warnings
        from google.adk.agents import SequentialAgent
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            runner = Runner(agent=SequentialAgent(name="seq", sub_agents=[agent]), app_name="q8", session_service=ss)
    else:
        runner = Runner(agent=agent, app_name="q8", session_service=ss)
    s = await ss.create_session(app_name=runner.app_name, user_id="u")
    SEEN.clear()
    where = "workflow node" if as_node else "sub-agent of a (deprecated) SequentialAgent" if in_sequential else "root agent"
    print(f"\n=== {label} [{where}]")
    n = 0
    async for ev in runner.run_async(user_id="u", session_id=s.id, new_message=user("go")):
        n += 1
        print(f"  [{n:02d}] {describe(ev)}")
    got = await ss.get_session(app_name=runner.app_name, user_id="u", session_id=s.id)
    print(f"  model calls: {llm.calls}   state['spec_md'] = {got.state.get('spec_md', '<ABSENT>')!r}"
          + (f"   downstream node_input = {SEEN.get('node_input', '<did not run>')!r}" if as_node else ""))


async def main():
    for as_node in (False, True):
        await run("baseline, no callback", as_node=as_node)
        await run("before_agent_callback returns Content", as_node=as_node, before_agent_callback=skip_agent)
        await run("before_agent_callback writes the key itself and returns Content", as_node=as_node,
                  before_agent_callback=skip_agent_and_write_key)
        await run("before_model_callback returns LlmResponse", as_node=as_node, before_model_callback=skip_model)
    await run("before_agent_callback returns Content", as_node=False, in_sequential=True, before_agent_callback=skip_agent)
    await run("before_model_callback returns LlmResponse", as_node=False, in_sequential=True, before_model_callback=skip_model)


asyncio.run(main())
