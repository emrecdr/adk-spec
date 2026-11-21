"""Offline probe for plan 2 on the pinned pair: a schema mismatch turned into an error by a plugin, a route back
bounded by a counter, and a RequestInput pause answered in the same process. A fake Gemini model; nothing is sent."""
import asyncio, json, os
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

class Brief(BaseModel):
    title: str = Field(description="t")
    why: str = Field(description="w")

REPLIES: list[str] = []
CALLS = [0]

class Fake(Gemini):
    model: str = "fake"
    @classmethod
    def supported_models(cls): return [r"fake.*"]
    async def generate_content_async(self, llm_request, stream=False):
        CALLS[0] += 1
        yield LlmResponse(content=types.ModelContent(REPLIES.pop(0)),
                          usage_metadata=types.GenerateContentResponseUsageMetadata(prompt_token_count=10, candidates_token_count=5, total_token_count=15))
LLMRegistry.register(Fake)

class Mismatch(BasePlugin):
    """A reply off its schema becomes that stage's own error, where ADK alone would raise and end the run."""
    def __init__(self): super().__init__(name="mismatch"); self.schemas = {}
    async def before_model_callback(self, *, callback_context, llm_request):
        s = llm_request.config.response_schema
        if isinstance(s, type) and issubclass(s, BaseModel): self.schemas[callback_context.agent_name] = s
        return None
    async def after_model_callback(self, *, callback_context, llm_response):
        s = self.schemas.get(callback_context.agent_name)
        text = "".join(p.text or "" for p in (llm_response.content.parts if llm_response.content else []) )
        if s is None or not text.strip(): return None
        try: s.model_validate_json(text)
        except ValidationError as exc:
            return LlmResponse(error_code="SCHEMA_MISMATCH", error_message=exc.errors()[0]["msg"], usage_metadata=llm_response.usage_metadata)
        return None

def agent():
    return LlmAgent(model="fake", name="brief", instruction="Write a brief for: {request}. Findings so far: {findings?}",
                    include_contents="none", output_schema=Brief, output_key="brief")

def gate(ctx: Context, node_input=None):
    tries = ctx.state.get("tries", 0) + 1
    held = ctx.state.get("brief")
    print(f"    gate ran: try {tries}, node_input={node_input!r}, state.brief={held!r}")
    if held is None:
        if tries >= 3: return Event(route="GIVE_UP", state={"tries": tries})
        return Event(route="AGAIN", state={"tries": tries, "findings": "the last answer did not fit the schema"})
    return Event(route="OK", state={"tries": tries})

def ask(ctx: Context, node_input=None):
    yield RequestInput(message="Which browsers are in scope?", payload={"n": 1})

def wrote(ctx: Context, node_input=None):
    print(f"    wrote ran: answer={node_input!r}")
    return Event(output="written", state={"answer": node_input})

def gave_up(ctx: Context): return Event(output="gave up")

async def run(title, replies, plugins, with_question=False):
    print(f"\n=== {title}")
    REPLIES[:] = replies; CALLS[0] = 0
    b = agent()
    tail = (ask, wrote) if with_question else (wrote,)
    wf = Workflow(name="propose", edges=[("START", b, gate), (gate, {"AGAIN": b, "OK": tail[0], "GIVE_UP": gave_up}), *([(ask, wrote)] if with_question else [])])
    runner = InMemoryRunner(app=App(name="propose", root_agent=wf, plugins=plugins))
    ids = dict(app_name=runner.app_name, user_id="u", session_id="s")
    await runner.session_service.create_session(**ids, state={"request": "passkeys"})
    async def drain(message):
        pause = None; failure = None
        try:
            async for ev in runner.run_async(user_id="u", session_id="s", new_message=message):
                path = ev.node_info.path if ev.node_info else "-"
                if ev.error_code: print(f"    event {path}: ERROR {ev.error_code}: {str(ev.error_message)[:60]} (author={ev.author})")
                for part in (ev.content.parts if ev.content and ev.content.parts else []):
                    if part.function_call and part.function_call.name == "adk_request_input":
                        pause = part.function_call.id; print(f"    event {path}: PAUSE {part.function_call.args.get('message')!r}")
        except Exception as exc: failure = f"{type(exc).__name__}: {str(exc)[:90]}"
        return pause, failure
    pause, failure = await drain(types.UserContent("go"))
    if pause:
        reply = types.Content(role="user", parts=[types.Part(function_response=types.FunctionResponse(id=pause, name="adk_request_input", response={"answer": "evergreen only"}))])
        pause2, failure = await drain(reply)
    s = await runner.session_service.get_session(**ids)
    print(f"    model calls={CALLS[0]} failure={failure} state={ {k: v for k, v in s.state.items() if k != 'request'} }")

GOOD = json.dumps({"title": "Passkeys", "why": "safer"})
async def main():
    await run("A. no plugin, bad reply: what ADK does alone", ["not json"], [])
    await run("B. plugin, bad then good: does the workflow go on to the gate and route back?", ["not json", GOOD], [Mismatch()])
    await run("C. plugin, three bad replies: bounded by the gate's own counter", ["x", "y", "z"], [Mismatch()])
    await run("D. good reply, then a question answered in the same process", [GOOD], [Mismatch()], with_question=True)
asyncio.run(main())
