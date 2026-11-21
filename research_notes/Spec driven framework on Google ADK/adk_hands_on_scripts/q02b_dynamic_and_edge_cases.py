"""Q2 (extras): dynamic workflow with a bounded Python loop, and three edge cases the notes left open:
two output events from one node, a missing state key for a bound parameter, and run_debug()."""
import asyncio
import traceback

from google.adk import Context, Event, Runner, Workflow
from google.adk.runners import InMemoryRunner
from google.adk.sessions import InMemorySessionService
from google.adk.workflow import node

from fake_llm import run_and_print, user


@node
def write_spec(node_input: str) -> str:
    return f"# Spec: {node_input}\n## Requirements\n"


@node
def validate_spec(node_input: str) -> list[str]:
    return [h for h in ("## Requirements", "## Acceptance Criteria") if h not in node_input]


@node
def fix_spec(node_input: dict) -> str:
    return node_input["spec"] + "".join(f"{h}\n" for h in node_input["issues"])


@node(rerun_on_resume=True)
async def pipeline(ctx: Context, node_input: str):
    spec = await ctx.run_node(write_spec, node_input)
    for i in range(3):                                   # explicit bound, in code
        issues = await ctx.run_node(validate_spec, spec)
        print(f"    pipeline loop {i}: issues={issues}")
        if not issues:
            break
        spec = await ctx.run_node(fix_spec, {"spec": spec, "issues": issues})
    yield Event(state={"spec_md": spec})
    yield Event(output=spec)


def two_outputs(node_input: str):
    yield Event(output="first")
    yield Event(output="second")


def needs_missing_key(node_input: str, not_in_state: int):
    return not_in_state


async def run(label, wf, text="Login"):
    ss = InMemorySessionService()
    runner = Runner(node=wf, session_service=ss)
    s = await ss.create_session(app_name=runner.app_name, user_id="u")
    print(f"\n=== {label}")
    try:
        await run_and_print(runner, user_id="u", session_id=s.id, new_message=user(text))
        got = await ss.get_session(app_name=runner.app_name, user_id="u", session_id=s.id)
        print("  state:", dict(got.state))
    except Exception as e:  # noqa: BLE001
        print(f"  RAISED {type(e).__module__}.{type(e).__name__}: {e}")
        traceback.print_exc(limit=0)


async def main():
    await run("A. dynamic workflow: orchestrator node + ctx.run_node children, for-loop bound",
              Workflow(name="dyn", edges=[("START", pipeline)]))
    await run("B. two Event(output=...) from one node",
              Workflow(name="two_out", edges=[("START", two_outputs)]))
    await run("C. function parameter bound from state, key missing, no default",
              Workflow(name="missing", edges=[("START", needs_missing_key)]))

    print("\n=== D. InMemoryRunner(node=...) + run_debug (session auto-created)")
    r = InMemoryRunner(node=Workflow(name="dbg", edges=[("START", write_spec, validate_spec)]), app_name="dbg_app")
    events = await r.run_debug("Checkout", quiet=True)
    print("  run_debug returned", len(events), "events; outputs:", [e.output for e in events])


asyncio.run(main())
