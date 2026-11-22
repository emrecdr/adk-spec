"""Q6 (extra): the same swap with STRUCTURED output. An LLM agent with output_schema versus a Python
node that returns the Pydantic model (or a dict). What do an untyped and a typed downstream node
receive in each case? Also: what does the FIRST node receive when node_input has no annotation?"""
import asyncio

from pydantic import BaseModel

from google.adk import Agent, Event, Runner, Workflow
from google.adk.sessions import InMemorySessionService

from fake_llm import FakeLlm, user


class Task(BaseModel):
    id: str
    title: str


class TaskList(BaseModel):
    tasks: list[Task]


JSON = '{"tasks": [{"id": "T-1", "title": "Login form"}]}'
MODEL = TaskList(tasks=[Task(id="T-1", title="Login form")])
SEEN: dict = {}


def untyped_downstream(ctx, node_input):
    SEEN["untyped"] = f"{type(node_input).__name__}: {node_input!r}"
    SEEN["state"] = f"{type(ctx.state.get('tasks')).__name__}: {ctx.state.get('tasks')!r}"


def typed_downstream(node_input: TaskList):
    SEEN["typed"] = f"{type(node_input).__name__}: {node_input!r}"


def py_returns_model(node_input: str):
    yield Event(output=MODEL, state={"tasks": MODEL.model_dump()})


def py_returns_dict(node_input: str):
    yield Event(output=MODEL.model_dump(), state={"tasks": MODEL.model_dump()})


def py_plain_return_model(node_input: str) -> TaskList:
    return MODEL


def first_untyped(node_input):
    SEEN["first_untyped"] = type(node_input).__name__
    return "x"


def first_typed(node_input: str):
    SEEN["first_typed"] = f"{type(node_input).__name__}: {node_input!r}"
    return "x"


async def run(label, step):
    SEEN.clear()
    wf = Workflow(name="wf", edges=[("START", step), (step, untyped_downstream), (step, typed_downstream)])
    ss = InMemorySessionService()
    runner = Runner(node=wf, session_service=ss)
    s = await ss.create_session(app_name=runner.app_name, user_id="u")
    out_types = []
    async for ev in runner.run_async(user_id="u", session_id=s.id, new_message=user("plan")):
        if ev.output is not None:
            out_types.append(type(ev.output).__name__)
    print(f"\n=== step = {label}")
    print(f"  type of Event.output in the stream : {out_types}")
    for k in ("untyped", "typed", "state"):
        print(f"  {k:<8} downstream saw            : {SEEN.get(k)}")


async def main():
    await run("LLM Agent(output_schema=TaskList, output_key='tasks')",
              Agent(name="task_breaker", model=FakeLlm(replies=[JSON]), instruction="break down",
                    output_schema=TaskList, output_key="tasks"))
    await run("Python node: yield Event(output=<TaskList instance>, state={'tasks': dict})", py_returns_model)
    await run("Python node: yield Event(output=<dict>, state={'tasks': dict})", py_returns_dict)
    await run("Python node: plain `return <TaskList instance>` (no state write)", py_plain_return_model)

    print("\n=== what the FIRST node after START receives")
    for fn in (first_untyped, first_typed):
        ss = InMemorySessionService()
        runner = Runner(node=Workflow(name="wf", edges=[("START", fn)]), session_service=ss)
        s = await ss.create_session(app_name=runner.app_name, user_id="u")
        async for _ in runner.run_async(user_id="u", session_id=s.id, new_message=user("hello")):
            pass
    print(f"  node_input without annotation : {SEEN['first_untyped']}")
    print(f"  node_input annotated `str`    : {SEEN['first_typed']}")


asyncio.run(main())
