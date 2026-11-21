"""Q6: fill the same workflow step first with an LLM Agent (fake model), then with a plain function
node producing the same output and the same state key. What is the minimal code difference and do
downstream nodes notice?"""
import asyncio

from google.adk import Agent, Event, Runner, Workflow
from google.adk.sessions import InMemorySessionService

from fake_llm import FakeLlm, describe, user

SPEC = "# Spec: Login page\n## Requirements\n- R1\n"
SEEN: dict[str, dict] = {}
VARIANT = ""


def intake(node_input: str):
    return f"Feature request: {node_input}"


def downstream(ctx, node_input):
    """Identical in both variants: records exactly what it can observe."""
    SEEN[VARIANT] = {"node_input": node_input, "node_input_type": type(node_input).__name__,
                     "state": ctx.state.to_dict()}
    return f"PLAN based on: {str(node_input).splitlines()[0]}"


# ---- variant 1: the step is an LLM agent --------------------------------------------------
llm = FakeLlm(replies=[SPEC])
spec_writer_llm = Agent(
    name="spec_writer", model=llm,
    instruction="Write a markdown spec for the feature request.",
    output_key="spec_md",
)


# ---- variant 2: the step is plain Python --------------------------------------------------
def spec_writer(node_input: str):
    yield Event(output=SPEC, state={"spec_md": SPEC})


def build(step):
    return Workflow(name="pipeline", edges=[("START", intake, step, downstream)])


async def run(variant, step):
    global VARIANT
    VARIANT = variant
    ss = InMemorySessionService()
    runner = Runner(node=build(step), session_service=ss)
    s = await ss.create_session(app_name=runner.app_name, user_id="u")
    print(f"\n=== variant: {variant}")
    events = []
    async for ev in runner.run_async(user_id="u", session_id=s.id, new_message=user("Login page")):
        events.append(ev)
        print(f"  [{len(events):02d}] {describe(ev)}")
    return events


async def main():
    e1 = await run("LLM agent step", spec_writer_llm)
    print(f"  fake model calls: {llm.calls}")
    req = llm.requests[0]
    print(f"  what the model was sent: system_instruction={req.config.system_instruction!r}")
    for c in req.contents:
        print(f"     content role={c.role} parts={[p.text for p in c.parts]}")
    e2 = await run("Python function step", spec_writer)

    print("\n=== what the unchanged downstream node observed")
    for k, v in SEEN.items():
        print(f"  {k:<22}: {v}")
    print("  node_input identical:", SEEN["LLM agent step"]["node_input"] == SEEN["Python function step"]["node_input"])
    print("  state identical     :", SEEN["LLM agent step"]["state"] == SEEN["Python function step"]["state"])

    print("\n=== differences in the event stream of the swapped step")
    for label, evs in (("LLM", e1), ("Python", e2)):
        step_events = [e for e in evs if "spec_writer" in e.node_info.path]
        for e in step_events:
            print(f"  {label:<6}: author={e.author!r} path={e.node_info.path!r} has_content={e.content is not None} "
                  f"output={'set' if e.output is not None else None} state_delta={sorted(e.actions.state_delta)} "
                  f"output_for={e.node_info.output_for} message_as_output={e.node_info.message_as_output}")


asyncio.run(main())
