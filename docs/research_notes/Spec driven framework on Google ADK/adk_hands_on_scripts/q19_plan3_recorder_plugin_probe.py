"""Offline probe for plan 3 on the pinned pair: what a recorder plugin sees of each model call, standing first in
the roster. The suite's fake model; nothing is sent.

Asked: is the instruction it is handed already filled from state; does it see the answer before the mismatch plugin
replaces it; does it see a call the ledger refused; and by what name does it know the stage.
Run from the repository root: `uv run python "<this file>"`.
"""
import asyncio, os, sys, tempfile
sys.path.insert(0, "tests")
os.environ.update(SPEC_PROVIDER="gemini", SPEC_MODEL="fake", GOOGLE_API_KEY="offline",
                  GITHUB_COPILOT_TOKEN_DIR=tempfile.mkdtemp())
import conftest  # noqa: F401  registers the fake model
from conftest import PROVIDER
from google.adk.plugins.base_plugin import BasePlugin
from google.adk.utils.content_utils import extract_text_from_content
from adk_spec.orchestration.graph import Known, build_propose_app
from adk_spec.orchestration.plugins import UsageLedger
from adk_spec.orchestration.run import run_seeded
from adk_spec.orchestration.stages import CAPABILITIES, CONSTITUTION, REQUEST

class Recorder(BasePlugin):
    def __init__(self): super().__init__(name="recorder"); self.seen = []
    async def before_model_callback(self, *, callback_context, llm_request):
        text = str(llm_request.config.system_instruction or "")
        self.seen.append(("before", callback_context.agent_name, "{request}" not in text and "PASSKEY-REQUEST" in text,
                          [p.text for c in llm_request.contents for p in c.parts]))
        return None
    async def after_model_callback(self, *, callback_context, llm_response):
        self.seen.append(("after", callback_context.agent_name, llm_response.error_code,
                          (extract_text_from_content(llm_response.content) or "")[:40]))
        return None

async def once(label, ceiling):
    recorder, ledger = Recorder(), UsageLedger(ceiling)
    app = build_propose_app(Known(living={}, taken=frozenset()), ask=False, entry="triage", ledger=ledger)
    app.plugins.insert(0, recorder)
    run = await run_seeded(app, state={REQUEST: "PASSKEY-REQUEST", CAPABILITIES: "", CONSTITUTION: ""}, prompt="propose")
    print(label, "| plugins:", [p.name for p in app.plugins], "| failure:", (run.state.get("failure") or run.failure))
    for row in recorder.seen:
        print("   ", row)

async def main():
    PROVIDER.clear(); PROVIDER.answers_each_time("You size a change request", iter(["not json", None]))
    await once("A. triage off its schema once, then a whole lean run", None)
    PROVIDER.clear()
    await once("B. a ceiling of 200 tokens: the third call is refused", 200)

asyncio.run(main())
