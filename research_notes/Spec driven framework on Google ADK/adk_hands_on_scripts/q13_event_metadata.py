"""Q13: what token-usage and timing metadata appears on events?
The fake model attaches usage_metadata to its response (a real provider would do the same)."""
import asyncio
import json

from google.adk import Agent, Runner, Workflow
from google.adk.sessions import InMemorySessionService

from fake_llm import FakeLlm, user


def after(node_input: str):
    return node_input.upper()


async def main():
    llm = FakeLlm(replies=["spec text"], usage=True)
    wf = Workflow(name="wf", edges=[("START", Agent(name="writer", model=llm, instruction="write"), after)])
    ss = InMemorySessionService()
    runner = Runner(node=wf, session_service=ss)
    s = await ss.create_session(app_name=runner.app_name, user_id="u")
    events = [e async for e in runner.run_async(user_id="u", session_id=s.id, new_message=user("go"))]
    for i, ev in enumerate(events, 1):
        d = json.loads(ev.model_dump_json(exclude_none=True))
        print(f"--- event {i} ({ev.node_info.path}) top-level keys: {sorted(d)}")
        for k in ("usage_metadata", "model_version", "timestamp", "invocation_id", "id", "finish_reason",
                  "custom_metadata", "cache_metadata", "node_info"):
            if k in d:
                print(f"    {k}: {d[k]}")
    stored = await ss.get_session(app_name=runner.app_name, user_id="u", session_id=s.id)
    ts = [e.timestamp for e in stored.events]
    print(f"\nper-event wall-clock timestamps (epoch seconds): {[round(t, 4) for t in ts]}")
    print(f"deltas between consecutive events (ms): {[round((b - a) * 1000, 2) for a, b in zip(ts, ts[1:])]}")
    print("duration fields on Event:", [f for f in type(events[0]).model_fields if "duration" in f or "latency" in f or "elapsed" in f] or "none")

    print("\n--- same run, model returns NO usage metadata")
    llm2 = FakeLlm(replies=["spec text"])
    r2 = Runner(node=Workflow(name="wf", edges=[("START", Agent(name="writer", model=llm2, instruction="write"))]),
                session_service=ss)
    s2 = await ss.create_session(app_name=r2.app_name, user_id="u")
    e2 = [e async for e in r2.run_async(user_id="u", session_id=s2.id, new_message=user("go"))]
    print("    usage_metadata on the agent event:", e2[0].usage_metadata)


asyncio.run(main())
