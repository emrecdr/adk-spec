"""Q5a: pause a model-free Workflow on RequestInput and resume it, in one process.
Variants: no App at all (resumability_config=None); App with ResumabilityConfig(is_resumable=True);
different reply payload shapes; a plain-text reply instead of a function response."""
import asyncio

from google.genai import types

from google.adk import Runner
from google.adk.apps import App, ResumabilityConfig
from google.adk.sessions import InMemorySessionService

import hitl_flow
from fake_llm import run_and_print, user


async def scenario(label, *, resumable, reply):
    print(f"\n=== {label}")
    ss = InMemorySessionService()
    if resumable is None:
        runner = Runner(node=hitl_flow.build_workflow(), session_service=ss)
    else:
        app = App(name="sdd_gate", root_agent=hitl_flow.build_workflow(),
                  resumability_config=ResumabilityConfig(is_resumable=resumable))
        runner = Runner(app=app, session_service=ss)
    print(f"  runner.resumability_config = {runner.resumability_config}")
    s = await ss.create_session(app_name=runner.app_name, user_id="u")
    hitl_flow.EXECUTIONS.clear()

    ev1 = await run_and_print(runner, user_id="u", session_id=s.id, new_message=user("Login page"),
                              label="run 1 (expected to pause at the gate)")
    interrupt_id, call = hitl_flow.find_interrupt(ev1)
    print(f"  paused: interrupt_id={interrupt_id!r} call.name={call.name!r}")
    print(f"  call.args={dict(call.args)}")
    print(f"  invocation_id of run 1 = {ev1[-1].invocation_id}")
    print(f"  node bodies executed so far: {hitl_flow.EXECUTIONS}")

    if isinstance(reply, str):
        msg = user(reply)
        how = f"plain text {reply!r}"
    else:
        msg = types.Content(role="user", parts=[types.Part(function_response=types.FunctionResponse(
            id=interrupt_id, name="adk_request_input", response=reply))])
        how = f"FunctionResponse(id=interrupt_id, name='adk_request_input', response={reply!r})"
    try:
        ev2 = await run_and_print(runner, user_id="u", session_id=s.id, new_message=msg,
                                  label=f"run 2: resume with {how}")
        print(f"  invocation_id of run 2 = {ev2[-1].invocation_id if ev2 else None} "
              f"(same as run 1: {bool(ev2) and ev2[-1].invocation_id == ev1[-1].invocation_id})")
    except Exception as e:  # noqa: BLE001
        print(f"  RAISED {type(e).__name__}: {e}")
    got = await ss.get_session(app_name=runner.app_name, user_id="u", session_id=s.id)
    print(f"  node bodies executed in total: {hitl_flow.EXECUTIONS}")
    print(f"  final state: {dict(got.state)}")


async def main():
    await scenario("1. NO App / no resumability config; reply {'answer': 'yes'}", resumable=None, reply={"answer": "yes"})
    await scenario("2. App(resumability_config=ResumabilityConfig(is_resumable=True)); reply {'answer': 'no'}",
                   resumable=True, reply={"answer": "no"})
    await scenario("3. App with is_resumable=False; reply {'result': 'yes'}", resumable=False, reply={"result": "yes"})
    await scenario("4. NO App; reply is PLAIN TEXT 'yes' instead of a function response", resumable=None, reply="yes")


asyncio.run(main())
