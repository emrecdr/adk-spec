"""Offline probe on the pinned pair: what a resume from a RequestInput pause does to a stage that had answered off
its schema earlier in the same run. A fake Gemini model; nothing is sent.

Two runs of one graph, `stage -> gate -> ask -> end`, each paused once and resumed once:
  A. the stage answers well at once;
  B. the stage answers off its schema first (a plugin turns that into the stage's own error), then well.
The count that matters is how often the model is called after the pause was answered. Nothing in the graph asks
the stage again after the pause, so any call there is one nobody sees and no gate checks.
"""
import asyncio, os
os.environ["GOOGLE_API_KEY"] = "offline"
from google.adk.agents import LlmAgent
from google.adk.agents.context import Context
from google.adk.apps.app import App
from google.adk.events import Event
from google.adk.events.request_input import RequestInput
from google.adk.models.google_llm import Gemini
from google.adk.models.llm_response import LlmResponse
from google.adk.models.registry import LLMRegistry
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.runners import InMemoryRunner
from google.adk.workflow import Workflow
from google.genai import types
from pydantic import BaseModel, Field, ValidationError

class Answer(BaseModel):
    word: str = Field(description="one word")

REPLIES: list[str] = []
CALLS: list[str] = []

class Fake(Gemini):
    model: str = "fake"
    @classmethod
    def supported_models(cls): return [r"fake.*"]
    async def generate_content_async(self, llm_request, stream=False):
        reply = REPLIES.pop(0) if REPLIES else '{"word": "unseen"}'
        CALLS.append(reply)
        yield LlmResponse(content=types.ModelContent(reply))
LLMRegistry.register(Fake)

class Mismatch(BasePlugin):
    """A reply off its schema becomes that stage's own error, where ADK alone would raise and end the run."""
    def __init__(self): super().__init__(name="mismatch")
    async def after_model_callback(self, *, callback_context, llm_response):
        text = "".join(p.text or "" for p in (llm_response.content.parts if llm_response.content else []))
        try:
            Answer.model_validate_json(text)
        except ValidationError:
            return LlmResponse(error_code="SCHEMA_MISMATCH", error_message="off its schema")
        return None

def build() -> App:
    stage = LlmAgent(model="fake", name="stage", instruction="Answer.", include_contents="none",
                     output_schema=Answer, output_key="stage")
    def gate(ctx: Context) -> Event:
        return Event(route="OK" if ctx.state.get("stage") else "AGAIN")
    def ask(ctx: Context):
        yield RequestInput(message="a question", payload={"shown": ctx.state.get("stage")})
    def end(ctx: Context, node_input=None) -> Event:
        return Event(state={"answered_with": node_input, "stage_at_the_end": ctx.state.get("stage")})
    edges = [("START", stage, gate), (gate, {"OK": ask, "AGAIN": stage}), (ask, end)]
    return App(name="probe", root_agent=Workflow(name="probe", edges=edges), plugins=[Mismatch()])

async def once(label: str, replies: list[str]) -> None:
    REPLIES[:] = replies; CALLS.clear()
    runner = InMemoryRunner(app=build())
    await runner.session_service.create_session(app_name="probe", user_id="u", session_id=label)
    pause, shown, failure = None, None, None
    async for ev in runner.run_async(user_id="u", session_id=label, new_message=types.UserContent("go")):
        for part in (ev.content.parts if ev.content and ev.content.parts else []):
            if part.function_call and part.function_call.name == "adk_request_input":
                pause, shown = part.function_call.id, part.function_call.args.get("payload")
    before = len(CALLS)
    reply = types.Content(role="user", parts=[types.Part(function_response=types.FunctionResponse(
        id=pause, name="adk_request_input", response={"answer": "yes"}))])
    try:
        async for ev in runner.run_async(user_id="u", session_id=label, new_message=reply):
            pass
    except Exception as exc:
        failure = f"{type(exc).__name__}: {str(exc)[:110]}"
    state = (await runner.session_service.get_session(app_name="probe", user_id="u", session_id=label)).state
    print(f"{label}")
    print(f"  model calls before the pause : {before}  {CALLS[:before]}")
    print(f"  the person was shown         : {shown}")
    print(f"  model calls after the answer : {len(CALLS) - before}  {CALLS[before:]}")
    print(f"  the stage's answer at the end: {state.get('stage_at_the_end')}")
    print(f"  the resume failed with       : {failure}")

async def main() -> None:
    import google.adk, litellm  # noqa: F401
    from importlib.metadata import version
    print(f"google-adk {version('google-adk')}\n")
    await once("A. the stage answers well at once", ['{"word": "first"}'])
    await once("B. the stage answers off its schema, then well", ["not json", '{"word": "second"}'])

asyncio.run(main())
