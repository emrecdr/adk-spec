"""Q10: FunctionTool declarations under Python 3.14, with and without
`from __future__ import annotations`, and a real invocation through an agent (fake model)."""
import asyncio
import json
import logging
import sys

from google.adk import Agent, Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import FunctionTool

import q10_tools_future
import q10_tools_plain
from fake_llm import FakeLlm, fc, user

logging.getLogger("google_adk").setLevel(logging.CRITICAL)
print("python", sys.version.split()[0])
print("raw __annotations__ of save_spec (plain module)  :",
      {k: (v if isinstance(v, str) else getattr(v, '__name__', repr(v))) for k, v in list(q10_tools_plain.save_spec.__annotations__.items())[:4]}, "...")
print("raw __annotations__ of save_spec (future module) :",
      dict(list(q10_tools_future.save_spec.__annotations__.items())[:4]), "...")


def decl(func):
    d = FunctionTool(func)._get_declaration()
    return d.model_dump(exclude_none=True, mode="json")


results = {}
for label, mod in (("plain", q10_tools_plain), ("future", q10_tools_future)):
    for fn in ("save_spec", "list_tasks"):
        try:
            results[(label, fn)] = decl(getattr(mod, fn))
        except Exception as e:  # noqa: BLE001
            results[(label, fn)] = f"RAISED {type(e).__name__}: {e}"

print("\n=== declaration for save_spec (module WITHOUT the future import)")
print(json.dumps(results[("plain", "save_spec")], indent=1))
print("\n=== declaration for list_tasks (module WITHOUT the future import)")
print(json.dumps(results[("plain", "list_tasks")], indent=1))
for fn in ("save_spec", "list_tasks"):
    same = results[("plain", fn)] == results[("future", fn)]
    print(f"\n=== {fn}: declaration with `from __future__ import annotations` identical to plain: {same}")
    if not same:
        print(json.dumps(results[("future", fn)], indent=1))


async def invoke(label, mod):
    args = {"filename": "spec.md", "markdown": "# S", "tags": ["a", "b"], "reviewer": None,
            "task": {"title": "Login", "estimate_hours": 2}, "priority": "high", "mode": "final"}
    llm = FakeLlm(replies=[fc("save_spec", args), "done"])
    agent = Agent(name="writer", model=llm, instruction="save", tools=[mod.save_spec])
    ss = InMemorySessionService()
    runner = Runner(agent=agent, app_name="q10", session_service=ss)
    s = await ss.create_session(app_name="q10", user_id="u")
    print(f"\n=== invoke save_spec through an agent ({label} module); model-supplied args={args}")
    try:
        async for ev in runner.run_async(user_id="u", session_id=s.id, new_message=user("save it")):
            for fr in ev.get_function_responses():
                print("  tool returned:", json.dumps(fr.response))
        sent = [fd.name for t in (llm.requests[0].config.tools or []) for fd in (t.function_declarations or [])]
        print("  declarations sent to the model:", sent)
    except Exception as e:  # noqa: BLE001
        print(f"  RAISED {type(e).__name__}: {e}")


async def main():
    await invoke("plain", q10_tools_plain)
    await invoke("future", q10_tools_future)


asyncio.run(main())
