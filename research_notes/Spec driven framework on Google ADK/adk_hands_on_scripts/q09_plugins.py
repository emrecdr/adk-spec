"""Q9: register a plugin on the App and record which plugin hooks fire for
(1) a plain function node, (2) an LLM agent node, (3) a tool call made by an LLM agent,
plus (4) a failing function node and (5) Runner(plugins=...) (documented as deprecated)."""
import asyncio
import logging
import warnings

from google.adk import Agent, Runner, Workflow
from google.adk.apps import App
from google.adk.plugins import BasePlugin
from google.adk.sessions import InMemorySessionService

from fake_llm import FakeLlm, fc, user

logging.getLogger("google_adk").setLevel(logging.CRITICAL)


class Recorder(BasePlugin):
    """Overrides every BasePlugin hook and records (hook, subject)."""

    def __init__(self):
        super().__init__(name="recorder")
        self.log: list[str] = []

    def _add(self, hook, subject=""):
        self.log.append(f"{hook}({subject})" if subject else hook)

    async def on_user_message_callback(self, *, invocation_context, user_message):
        self._add("on_user_message_callback")

    async def before_run_callback(self, *, invocation_context):
        self._add("before_run_callback")

    async def on_event_callback(self, *, invocation_context, event):
        what = ("error" if event.error_code else "function_call" if event.get_function_calls()
                else "function_response" if event.get_function_responses()
                else "text" if event.content else "output" if event.output is not None else "other")
        self._add("on_event_callback", f"{event.node_info.path or event.author}:{what}")

    async def after_run_callback(self, *, invocation_context):
        self._add("after_run_callback")

    async def before_agent_callback(self, *, agent, callback_context):
        self._add("before_agent_callback", agent.name)

    async def after_agent_callback(self, *, agent, callback_context):
        self._add("after_agent_callback", agent.name)

    async def before_model_callback(self, *, callback_context, llm_request):
        self._add("before_model_callback", callback_context.agent_name)

    async def after_model_callback(self, *, callback_context, llm_response):
        self._add("after_model_callback", callback_context.agent_name)

    async def on_model_error_callback(self, *, callback_context, llm_request, error):
        self._add("on_model_error_callback", type(error).__name__)

    async def before_tool_callback(self, *, tool, tool_args, tool_context):
        self._add("before_tool_callback", f"{tool.name} args={tool_args}")

    async def after_tool_callback(self, *, tool, tool_args, tool_context, result):
        self._add("after_tool_callback", f"{tool.name} result={result}")

    async def on_tool_error_callback(self, *, tool, tool_args, tool_context, error):
        self._add("on_tool_error_callback", type(error).__name__)

    async def on_agent_error_callback(self, *, agent, callback_context, error):
        self._add("on_agent_error_callback", f"{agent.name}:{type(error).__name__}")

    async def on_run_error_callback(self, *, invocation_context, error):
        self._add("on_run_error_callback", type(error).__name__)


def plain_step(node_input: str):
    return f"plain:{node_input}"


def failing_step(node_input: str):
    raise RuntimeError("boom")


def count_words(text: str) -> dict:
    """Counts the words in a text.

    Args:
      text: The text to count.
    """
    return {"status": "success", "words": len(text.split())}


async def run(label, build_root, *, via_runner_plugins=False):
    rec = Recorder()
    ss = InMemorySessionService()
    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        if via_runner_plugins:
            runner = Runner(node=build_root(), plugins=[rec], session_service=ss)
        else:
            runner = Runner(app=App(name="q9", root_agent=build_root(), plugins=[rec]), session_service=ss)
    s = await ss.create_session(app_name=runner.app_name, user_id="u")
    print(f"\n=== {label}")
    for x in w:
        print(f"  WARNING at Runner construction: {x.category.__name__}: {x.message}")
    try:
        async for _ in runner.run_async(user_id="u", session_id=s.id, new_message=user("hello world")):
            pass
    except Exception as e:  # noqa: BLE001
        print(f"  run raised {type(e).__name__}: {e}")
    for line in rec.log:
        print("   ", line)
    hooks = sorted({l.split("(")[0] for l in rec.log})
    print(f"  distinct hooks fired: {hooks}")


async def main():
    await run("1. Workflow with ONE plain function node",
              lambda: Workflow(name="wf", edges=[("START", plain_step)]))
    await run("2. Workflow with ONE LLM agent node (fake model, no tools)",
              lambda: Workflow(name="wf", edges=[("START", Agent(name="writer", model=FakeLlm(replies=["text"]),
                                                               instruction="write"))]))
    await run("3. Workflow with an LLM agent node that calls a function tool",
              lambda: Workflow(name="wf", edges=[("START", Agent(
                  name="counter", instruction="count",
                  model=FakeLlm(replies=[fc("count_words", {"text": "a b c"}), "three words"]),
                  tools=[count_words]))]))
    await run("4. Workflow with a function node that raises",
              lambda: Workflow(name="wf", edges=[("START", failing_step)]))
    await run("5. Same as 1, but plugin passed as Runner(plugins=[...]) instead of App(plugins=[...])",
              lambda: Workflow(name="wf", edges=[("START", plain_step)]), via_runner_plugins=True)


asyncio.run(main())
