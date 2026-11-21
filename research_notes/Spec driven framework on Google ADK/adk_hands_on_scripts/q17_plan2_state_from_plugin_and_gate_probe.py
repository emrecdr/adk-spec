"""Offline probe for plan 2: can a plugin leave its reason in state, and can a gate clear a refused answer?"""
import asyncio, json, os
os.environ["GOOGLE_API_KEY"] = "offline"
from google.adk.agents import LlmAgent
from google.adk.agents.context import Context
from google.adk.apps.app import App
from google.adk.events import Event
from google.adk.models.google_llm import Gemini
from google.adk.models.llm_response import LlmResponse
from google.adk.models.registry import LLMRegistry
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.runners import InMemoryRunner
from google.adk.utils._schema_utils import validate_schema
from google.adk.utils.content_utils import extract_text_from_content
from google.adk.workflow import FunctionNode, Workflow
from google.genai import types
from pydantic import BaseModel, Field, ValidationError

class Brief(BaseModel):
    title: str = Field(description="t")

REPLIES: list[str] = []; SEEN: list[str] = []
class Fake(Gemini):
    model: str = "fake"
    @classmethod
    def supported_models(cls): return [r"fake.*"]
    async def generate_content_async(self, llm_request, stream=False):
        SEEN.append(str(llm_request.config.system_instruction))
        yield LlmResponse(content=types.ModelContent(REPLIES.pop(0)))
LLMRegistry.register(Fake)

class Mismatch(BasePlugin):
    def __init__(self): super().__init__(name="mismatch"); self.schemas = {}
    async def before_model_callback(self, *, callback_context, llm_request):
        if callback_context.state.get("spent"):                      # a ceiling: refuse before the call is sent
            callback_context.state["stage_error"] = "CEILING: spent"
            return LlmResponse(error_code="CEILING", error_message="spent")
        self.schemas[callback_context.agent_name] = llm_request.config.response_schema
        return None
    async def after_model_callback(self, *, callback_context, llm_response):
        schema = self.schemas.get(callback_context.agent_name)
        text = extract_text_from_content(llm_response.content)
        try: validate_schema(schema, text)
        except ValidationError as exc:
            callback_context.state["stage_error"] = f"the answer did not fit its schema: {exc.errors()[0]['msg']}"
            return LlmResponse(error_code="SCHEMA_MISMATCH", error_message="x")
        return None

def gate(ctx: Context, node_input=None):
    tries = ctx.state.get("tries_brief", 0) + 1
    held, why = ctx.state.get("brief"), ctx.state.get("stage_error")
    print(f"    gate try {tries}: brief={held!r} stage_error={why!r}")
    if held is None:
        if (why or "").startswith("CEILING") or tries >= 3:
            return Event(route="GIVE_UP", state={"tries_brief": tries, "failure": f"brief: {why}", "stage_error": None})
        return Event(route="AGAIN", state={"tries_brief": tries, "findings": why, "stage_error": None})
    if held["title"] == "bad":
        return Event(route="AGAIN", state={"tries_brief": tries, "findings": "the title is bad", "brief": None})
    return Event(route="OK", state={"tries_brief": tries, "findings": None})

async def run(title, replies, state):
    print(f"\n=== {title}"); REPLIES[:] = replies; SEEN.clear()
    b = LlmAgent(model="fake", name="brief", instruction="Brief for {request}. Findings: {findings?}", include_contents="none", output_schema=Brief, output_key="brief")
    g = FunctionNode(func=gate, name="brief_gate")
    def done(): return Event(output="ok")
    def lost(): return Event(output="lost")
    wf = Workflow(name="w", edges=[("START", b, g), (g, {"AGAIN": b, "OK": done, "GIVE_UP": lost})])
    r = InMemoryRunner(app=App(name="w", root_agent=wf, plugins=[Mismatch()]))
    ids = dict(app_name=r.app_name, user_id="u", session_id="s")
    await r.session_service.create_session(**ids, state=state)
    failure = None
    try:
        async for _ in r.run_async(user_id="u", session_id="s", new_message=types.UserContent("go")): pass
    except Exception as exc: failure = f"{type(exc).__name__}: {str(exc)[:80]}"
    s = await r.session_service.get_session(**ids)
    print(f"    calls={len(SEEN)} failure={failure} state={ {k: v for k, v in s.state.items() if k != 'request'} }")
    print(f"    findings each call saw: {[i.split('Findings: ')[1] for i in SEEN]}")

async def main():
    await run("A. a refused answer is cleared, then a mismatch: the stale answer must not be seen", [json.dumps({"title": "bad"}), "not json", json.dumps({"title": "good"})], {"request": "x"})
    await run("B. the ceiling is spent: said once, not asked again", [], {"request": "x", "spent": True})
asyncio.run(main())
