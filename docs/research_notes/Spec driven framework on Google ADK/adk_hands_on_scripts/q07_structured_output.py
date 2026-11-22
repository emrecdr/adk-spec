"""Q7: LLM agent with output_schema (Pydantic) + fake model. What happens on valid JSON, fenced JSON,
invalid JSON and JSON that fails validation: exception, automatic retry, or an event with the bad
text? What does output_key store? Tested as a root agent and as a Workflow node."""
import asyncio
import logging

from pydantic import BaseModel, Field

from google.adk import Agent, Runner, Workflow
from google.adk.sessions import InMemorySessionService
from google.adk.workflow import RetryConfig

from fake_llm import FakeLlm, describe, user

logging.getLogger("google_adk").setLevel(logging.CRITICAL)   # ADK logs full tracebacks at ERROR; keep output short


class Task(BaseModel):
    id: str
    title: str
    depends_on: list[str] = []


class TaskList(BaseModel):
    tasks: list[Task] = Field(min_length=1)
    note: str | None = None


VALID = '{"tasks": [{"id": "T-1", "title": "Login form"}]}'
CASES = {
    "valid JSON": [VALID],
    "valid JSON in a ```json fence": [f"```json\n{VALID}\n```"],
    "NOT JSON": ["Sure! Here are the tasks: T-1 Login form", VALID],
    "JSON failing validation (tasks: [])": ['{"tasks": []}', VALID],
    "JSON failing validation (missing title)": ['{"tasks": [{"id": "T-1"}]}', VALID],
}

SEEN = {}


def downstream(ctx, node_input):
    SEEN["node_input"] = node_input
    return "downstream ran"


async def run(label, replies, *, as_node, retry=None, output_key="tasks"):
    llm = FakeLlm(replies=list(replies))
    kwargs = dict(retry_config=retry) if retry else {}
    if output_key:
        kwargs["output_key"] = output_key
    agent = Agent(name="task_breaker", model=llm, instruction="Break the plan into tasks.",
                  output_schema=TaskList, **kwargs)
    ss = InMemorySessionService()
    if as_node:
        runner = Runner(node=Workflow(name="wf", edges=[("START", agent, downstream)]), session_service=ss)
    else:
        runner = Runner(agent=agent, app_name="q7", session_service=ss)
    s = await ss.create_session(app_name=runner.app_name, user_id="u")
    where = "workflow node" if as_node else "root agent"
    print(f"\n=== {label} [{where}{', retry_config=' + repr(retry.max_attempts) + ' attempts' if retry else ''}"
          f"{'' if output_key else ', NO output_key'}]")
    SEEN.clear()
    n = 0
    try:
        async for ev in runner.run_async(user_id="u", session_id=s.id, new_message=user("plan")):
            n += 1
            print(f"  [{n:02d}] {describe(ev)}")
        outcome = "completed without exception"
    except Exception as e:  # noqa: BLE001
        outcome = f"RAISED {type(e).__module__}.{type(e).__name__}: {str(e).splitlines()[0]} ..."
    got = await ss.get_session(app_name=runner.app_name, user_id="u", session_id=s.id)
    v = got.state.get("tasks", "<absent>")
    print(f"  outcome            : {outcome}")
    print(f"  model calls        : {llm.calls} (of {len(replies)} scripted)")
    print(f"  state['tasks']     : {v!r} (type {type(v).__name__})")
    persisted = [("user" if e.author == "user" else "error" if e.error_code else "text" if e.content else "other")
                 for e in got.events]
    bad_text_persisted = any(e.author != "user" and e.content and e.content.parts and e.content.parts[0].text
                             and e.content.parts[0].text == replies[0] for e in got.events)
    print(f"  persisted events   : {persisted}; first model reply text stored in an event: {bad_text_persisted}")
    if as_node:
        print(f"  downstream got     : {SEEN.get('node_input', '<downstream did not run>')!r}")
    if llm.calls > 1:
        for i, req in enumerate(llm.requests, 1):
            print(f"  request {i} contents : {[(c.role, [p.text for p in c.parts]) for c in req.contents]}")
    if llm.requests:
        cfg = llm.requests[0].config
        print(f"  request config     : response_schema={'set' if cfg.response_schema else None} "
              f"response_mime_type={cfg.response_mime_type!r} "
              f"tools={[fd.name for t in (cfg.tools or []) for fd in (t.function_declarations or [])]}")


async def main():
    for label, replies in CASES.items():
        await run(label, replies, as_node=False)
    for label, replies in CASES.items():
        await run(label, replies, as_node=True)
    await run("JSON failing validation, then a valid reply", ['{"tasks": []}', VALID], as_node=True,
              retry=RetryConfig(max_attempts=2, initial_delay=0.01))
    await run("NOT JSON", CASES["NOT JSON"], as_node=False, output_key=None)
    await run("NOT JSON", CASES["NOT JSON"], as_node=True, output_key=None)


asyncio.run(main())
