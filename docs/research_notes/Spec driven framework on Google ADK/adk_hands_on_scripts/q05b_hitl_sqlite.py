"""Q5b: can a run paused on RequestInput be resumed from a NEW Python process when sessions
are stored in SQLite?

  python q05b_hitl_sqlite.py start  <tag> [resumable]   # process 1: run until the gate pauses
  python q05b_hitl_sqlite.py resume <tag> [resumable]   # process 2: fresh interpreter, resume

SqliteSessionService (aiosqlite, a core dependency) is used. Data goes to $SPIKE_DATA (default ./data).
"""
import asyncio
import json
import os
import sys
from pathlib import Path

from google.genai import types

from google.adk import Runner
from google.adk.apps import App, ResumabilityConfig
from google.adk.sessions.sqlite_session_service import SqliteSessionService

import hitl_flow
from fake_llm import run_and_print, user

mode, tag = sys.argv[1], sys.argv[2]
resumable = len(sys.argv) > 3 and sys.argv[3] == "resumable"
DATA = Path(os.environ.get("SPIKE_DATA", "data"))
DATA.mkdir(parents=True, exist_ok=True)
DB = DATA / f"q05_sessions_{tag}.db"
HANDOFF = DATA / f"q05_handoff_{tag}.json"


def make_runner():
    ss = SqliteSessionService(str(DB))
    if resumable:
        app = App(name="sdd_gate", root_agent=hitl_flow.build_workflow(),
                  resumability_config=ResumabilityConfig(is_resumable=True))
        return Runner(app=app, session_service=ss), ss
    return Runner(node=hitl_flow.build_workflow(), session_service=ss), ss


async def start():
    for f in (DB, HANDOFF):
        f.unlink(missing_ok=True)
    runner, ss = make_runner()
    s = await ss.create_session(app_name=runner.app_name, user_id="u")
    events = await run_and_print(runner, user_id="u", session_id=s.id, new_message=user("Login page"),
                                 label=f"process {os.getpid()} START (resumable={resumable})")
    interrupt_id, call = hitl_flow.find_interrupt(events)
    HANDOFF.write_text(json.dumps({"session_id": s.id, "interrupt_id": interrupt_id, "pid": os.getpid(),
                                   "invocation_id": events[-1].invocation_id}))
    print(f"  node bodies executed in this process: {hitl_flow.EXECUTIONS}")
    print(f"  paused; handoff file written: {HANDOFF.name} -> {HANDOFF.read_text()}")
    print(f"  sqlite file: {DB.name} ({DB.stat().st_size} bytes)")


async def resume():
    h = json.loads(HANDOFF.read_text())
    print(f"--- process {os.getpid()} RESUME (started by pid {h['pid']}; resumable={resumable})")
    runner, ss = make_runner()
    before = await ss.get_session(app_name=runner.app_name, user_id="u", session_id=h["session_id"])
    print(f"  session loaded from SQLite: {len(before.events)} events, state keys={sorted(before.state)}")
    reply = types.Content(role="user", parts=[types.Part(function_response=types.FunctionResponse(
        id=h["interrupt_id"], name="adk_request_input", response={"answer": "yes"}))])
    events = await run_and_print(runner, user_id="u", session_id=h["session_id"], new_message=reply)
    after = await ss.get_session(app_name=runner.app_name, user_id="u", session_id=h["session_id"])
    print(f"  node bodies executed in this process: {hitl_flow.EXECUTIONS}")
    print(f"  resumed invocation_id == paused invocation_id: {events[-1].invocation_id == h['invocation_id']}")
    print(f"  final state: {dict(after.state)}")
    print(f"  events now in SQLite: {len(after.events)}")


asyncio.run(start() if mode == "start" else resume())
