"""Q5c (extras): (i) DatabaseSessionService without the `db` extra; (ii) resuming with only
invocation_id (the form shown on the docs' Resume page) and no message; (iii) the approval gate
inside a dynamic workflow (orchestrator node + ctx.run_node), to see which bodies re-run on resume."""
import asyncio

from google.genai import types

from google.adk import Context, Event, Runner, Workflow
from google.adk.apps import App, ResumabilityConfig
from google.adk.events import RequestInput
from google.adk.sessions import InMemorySessionService
from google.adk.workflow import node

import hitl_flow
from fake_llm import run_and_print, user

print("=== (i) from google.adk.sessions import DatabaseSessionService (sqlalchemy not installed)")
try:
    from google.adk.sessions import DatabaseSessionService  # noqa: F401
    print("  import ok")
except Exception as e:  # noqa: BLE001
    print(f"  RAISED {type(e).__name__}: {e}")

RAN: list[str] = []


@node
def write(node_input: str) -> str:
    RAN.append("write")
    return f"# Spec: {node_input}"


@node(rerun_on_resume=False)
async def approve(node_input: str):
    RAN.append("approve")
    yield RequestInput(message="Approve this spec? (yes/no)", payload=node_input)


@node
def make_plan(node_input: str) -> str:
    RAN.append("make_plan")
    return f"PLAN for {node_input}"


@node(rerun_on_resume=True)
async def orchestrator(ctx: Context, node_input: str):
    RAN.append("orchestrator")
    spec = await ctx.run_node(write, node_input)
    answer = await ctx.run_node(approve, spec)
    print(f"    orchestrator: approve returned {answer!r}")
    if str(answer).strip().lower() != "yes":
        yield Event(output="Spec rejected")
        return
    yield Event(output=await ctx.run_node(make_plan, spec))


async def invocation_id_only(resumable):
    print(f"\n=== (ii) resume a paused Workflow with invocation_id only, no new_message (resumable={resumable})")
    ss = InMemorySessionService()
    if resumable:
        runner = Runner(app=App(name="sdd_gate", root_agent=hitl_flow.build_workflow(),
                                resumability_config=ResumabilityConfig(is_resumable=True)), session_service=ss)
    else:
        runner = Runner(node=hitl_flow.build_workflow(), session_service=ss)
    s = await ss.create_session(app_name=runner.app_name, user_id="u")
    ev = [e async for e in runner.run_async(user_id="u", session_id=s.id, new_message=user("Login"))]
    interrupt_id, _ = hitl_flow.find_interrupt(ev)
    print(f"  paused with interrupt {interrupt_id[:8]}..., invocation {ev[-1].invocation_id}")
    try:
        ev2 = await run_and_print(runner, user_id="u", session_id=s.id, invocation_id=ev[-1].invocation_id,
                                  label="run_async(user_id, session_id, invocation_id=<paused id>)")
        i2, _ = hitl_flow.find_interrupt(ev2)
        print(f"  -> {len(ev2)} events; still waiting on the same interrupt: {i2 == interrupt_id}")
    except Exception as e:  # noqa: BLE001
        print(f"  RAISED {type(e).__name__}: {e}")


async def dynamic_gate():
    print("\n=== (iii) approval gate inside a dynamic workflow (no App, no resumability config)")
    ss = InMemorySessionService()
    runner = Runner(node=Workflow(name="dyn_gate", edges=[("START", orchestrator)]), session_service=ss)
    s = await ss.create_session(app_name=runner.app_name, user_id="u")
    ev = await run_and_print(runner, user_id="u", session_id=s.id, new_message=user("Login"), label="run 1")
    interrupt_id, _ = hitl_flow.find_interrupt(ev)
    print(f"  bodies executed in run 1: {RAN}")
    RAN.clear()
    reply = types.Content(role="user", parts=[types.Part(function_response=types.FunctionResponse(
        id=interrupt_id, name="adk_request_input", response={"result": "yes"}))])
    await run_and_print(runner, user_id="u", session_id=s.id, new_message=reply, label="run 2 (resume, answer 'yes')")
    print(f"  bodies executed in run 2: {RAN}")


async def main():
    await invocation_id_only(False)
    await invocation_id_only(True)
    await dynamic_gate()


asyncio.run(main())
