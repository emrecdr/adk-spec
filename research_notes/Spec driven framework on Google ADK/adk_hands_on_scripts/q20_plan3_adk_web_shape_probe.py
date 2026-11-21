"""Offline probe for plan 3 on the pinned pair: what the shape `adk web` loads has to be. No server is started and
nothing is sent: ADK's own loader is called directly, and one run goes through an in-memory runner with no model.

Asked: does the loader find an `app` in `<package>/agent.py`; what does the first node after START receive when a
person types a message; and does text a function node emits reach the event stream as a message.
"""
import asyncio, sys, tempfile, textwrap
from pathlib import Path

from google.adk.cli.utils.agent_loader import AgentLoader
from google.adk.runners import InMemoryRunner
from google.genai import types

folder = Path(tempfile.mkdtemp())
(folder / "probe_pkg").mkdir()
(folder / "probe_pkg" / "__init__.py").write_text('"""Imports nothing."""\n')
(folder / "probe_pkg" / "agent.py").write_text(textwrap.dedent('''
    from google.adk.agents.context import Context
    from google.adk.apps.app import App
    from google.adk.events import Event
    from google.adk.workflow import Workflow
    from google.genai import types

    SEEN = []

    def opened(ctx: Context, node_input=None) -> Event:
        SEEN.append((type(node_input).__name__, getattr(node_input, "parts", None) and node_input.parts[0].text))
        text = node_input.parts[0].text if hasattr(node_input, "parts") else str(node_input)
        return Event(state={"request": text})

    def shown(ctx: Context) -> Event:
        return Event(content=types.ModelContent("drafted: " + ctx.state["request"]))

    app = App(name="probe_pkg", root_agent=Workflow(name="probe_pkg", edges=[("START", opened, shown)]), plugins=[])
    root_agent = app.root_agent
'''))

loaded = AgentLoader(str(folder)).load_agent("probe_pkg")
print("the loader found:", type(loaded).__name__, "| names:", AgentLoader(str(folder)).list_agents())

async def main() -> None:
    runner = InMemoryRunner(app=loaded)
    await runner.session_service.create_session(app_name=runner.app_name, user_id="u", session_id="s")
    texts = []
    async for event in runner.run_async(user_id="u", session_id="s", new_message=types.UserContent("Let users sign in.")):
        parts = event.content.parts if event.content and event.content.parts else []
        texts += [(event.author, part.text) for part in parts if part.text]
    module = sys.modules["probe_pkg.agent"]
    print("the first node received:", module.SEEN)
    print("messages in the stream:", texts)

asyncio.run(main())
