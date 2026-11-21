"""Q2: a Workflow made only of plain Python function nodes.

Covers: node_input hand-off, ctx.state read/write, Event(state=...), parameter binding from
state by name, a conditional route, a loop bounded by a counter kept in state, and how the run
is started through a Runner (no App, no model).
"""
import asyncio

from google.adk import Context, Event, Runner, Workflow
from google.adk.sessions import InMemorySessionService

from fake_llm import run_and_print, user

MAX_ATTEMPTS = 3


def intake(node_input: str):
    # node_input of the first node = the user's message (types.Content coerced to str)
    print(f"    intake           got node_input={node_input!r} type={type(node_input).__name__}")
    return {"title": node_input.strip(), "words": len(node_input.split())}  # plain return -> output


def draft(ctx: Context, node_input: dict):
    # reads state through ctx.state, writes it through a yielded Event(state=...)
    attempt = ctx.state.get("attempts", 0) + 1
    print(f"    draft            got node_input={node_input!r} attempts-in-state={ctx.state.get('attempts')}")
    text = f"spec for {node_input['title']} (attempt {attempt})"
    yield Event(state={"attempts": attempt, "draft_text": text})
    yield Event(output={"title": node_input["title"], "text": text, "attempt": attempt})


def check(node_input: dict, attempts: int, draft_text: str):
    # `attempts` and `draft_text` are NOT special names: they are bound from session state by name
    print(f"    check            got node_input.attempt={node_input['attempt']} state.attempts={attempts} state.draft_text={draft_text!r}")
    if attempts >= MAX_ATTEMPTS:
        return Event(route="GIVE_UP", output=node_input)
    if node_input["attempt"] < 2:           # deterministic "needs work" on the first pass
        return Event(route="RETRY", output={"title": node_input["title"]})
    return Event(route="OK", output=node_input)


def publish(ctx: Context, node_input: dict):
    ctx.state["published"] = True            # direct ctx.state write (no Event(state=...))
    print(f"    publish          got node_input={node_input!r}")
    return Event(output=f"PUBLISHED: {node_input['text']}", message="done (user-facing message)")


def give_up(node_input: dict):
    return f"GAVE UP after {node_input['attempt']} attempts"


def build(check_fn=check):
    return Workflow(
        name="spec_flow",
        edges=[
            ("START", intake, draft, check_fn),
            (check_fn, {"RETRY": draft, "OK": publish, "GIVE_UP": give_up}),
        ],
    )


def always_retry(node_input: dict, attempts: int):
    """Variant of `check` that never approves, to prove the bound holds."""
    print(f"    always_retry     state.attempts={attempts}")
    if attempts >= MAX_ATTEMPTS:
        return Event(route="GIVE_UP", output=node_input)
    return Event(route="RETRY", output={"title": node_input["title"]})


async def run(label, wf, text):
    session_service = InMemorySessionService()
    runner = Runner(node=wf, session_service=session_service)   # app_name defaults to node.name
    print(f"\n=== {label}: runner.app_name={runner.app_name!r} resumability_config={runner.resumability_config}")
    session = await session_service.create_session(app_name=runner.app_name, user_id="u1")
    events = await run_and_print(runner, user_id="u1", session_id=session.id, new_message=user(text))
    stored = await session_service.get_session(app_name=runner.app_name, user_id="u1", session_id=session.id)
    print("  final session.state :", dict(stored.state))
    print("  events persisted    :", len(stored.events), "(incl. the user message event)")
    return events


async def main():
    events = await run("A. route OK after one RETRY", build(), "Login page")
    print("\n  full dump of one function-node event (exclude_none):")
    ev = [e for e in events if e.output is not None][0]
    print("  ", ev.model_dump_json(exclude_none=True))
    await run("B. loop bounded at MAX_ATTEMPTS=3", build(always_retry), "Payments")


asyncio.run(main())
