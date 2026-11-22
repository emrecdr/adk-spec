"""Q12: a Workflow containing a fake-model LLM agent, run under pytest with an in-memory runner.

Run:  .venv/bin/python -m pytest test_q12_pytest.py -v
"""
import pydantic
import pytest
from google.genai import types
from pydantic import BaseModel

from google.adk import Agent, Event, Workflow
from google.adk.runners import InMemoryRunner

import hitl_flow
from fake_llm import FakeLlm

SPEC = "# Spec: Add login\n## Requirements\n- R1\n## Acceptance Criteria\n- A1\n"


def intake(node_input: str):
    return f"Feature request: {node_input}"


def validate_spec(node_input: str):
    missing = [h for h in ("## Requirements", "## Acceptance Criteria") if h not in node_input]
    return Event(output={"ok": not missing, "missing": missing}, state={"spec_ok": not missing})


def build_workflow(spec_step):
    return Workflow(name="pipeline", edges=[("START", intake, spec_step, validate_spec)])


def llm_spec_writer(llm):
    return Agent(name="spec_writer", model=llm, instruction="Write the spec.", output_key="spec_md")


def python_spec_writer(node_input: str):
    yield Event(output=SPEC, state={"spec_md": SPEC})


async def final_state(runner, session_id="debug_session_id", user_id="debug_user_id"):
    s = await runner.session_service.get_session(app_name=runner.app_name, user_id=user_id, session_id=session_id)
    return s.state


@pytest.mark.asyncio
async def test_workflow_with_fake_llm_agent_run_debug():
    llm = FakeLlm(replies=[SPEC])
    runner = InMemoryRunner(node=build_workflow(llm_spec_writer(llm)), app_name="t")
    events = await runner.run_debug("Add login", quiet=True)

    assert llm.calls == 1                                             # exactly one model call
    assert llm.requests[0].contents[-1].parts[0].text == "Feature request: Add login"   # node_input reached the model
    assert events[-1].output == {"ok": True, "missing": []}           # validator node ran in Python
    state = await final_state(runner)
    assert state["spec_md"] == SPEC and state["spec_ok"] is True


@pytest.mark.asyncio
async def test_workflow_run_async_with_explicit_session():
    llm = FakeLlm(replies=["# Spec without the required sections"])
    runner = InMemoryRunner(node=build_workflow(llm_spec_writer(llm)), app_name="t")
    session = await runner.session_service.create_session(app_name="t", user_id="u")
    msg = types.Content(role="user", parts=[types.Part(text="Add login")])
    events = [e async for e in runner.run_async(user_id="u", session_id=session.id, new_message=msg)]

    assert [e.node_info.path.split("/")[-1] for e in events] == ["intake@1", "spec_writer@1", "validate_spec@1"]
    assert events[-1].output["missing"] == ["## Requirements", "## Acceptance Criteria"]


@pytest.mark.asyncio
async def test_python_replacement_makes_no_model_call_and_same_result():
    llm = FakeLlm(replies=[SPEC])
    with_llm = InMemoryRunner(node=build_workflow(llm_spec_writer(llm)), app_name="t")
    with_py = InMemoryRunner(node=build_workflow(python_spec_writer), app_name="t")
    out_llm = (await with_llm.run_debug("Add login", quiet=True))[-1].output
    out_py = (await with_py.run_debug("Add login", quiet=True))[-1].output

    assert out_llm == out_py
    assert dict(await final_state(with_llm)) == dict(await final_state(with_py))
    assert llm.calls == 1


@pytest.mark.asyncio
async def test_invalid_structured_output_raises_validation_error():
    class Verdict(BaseModel):
        ok: bool

    llm = FakeLlm(replies=["not json"])
    agent = Agent(name="judge", model=llm, instruction="judge", output_schema=Verdict, output_key="verdict")
    runner = InMemoryRunner(node=Workflow(name="wf", edges=[("START", agent)]), app_name="t")
    with pytest.raises(pydantic.ValidationError):
        await runner.run_debug("x", quiet=True)


@pytest.mark.asyncio
async def test_human_gate_pauses_and_resumes():
    runner = InMemoryRunner(node=hitl_flow.build_workflow(), app_name="t")
    session = await runner.session_service.create_session(app_name="t", user_id="u")
    msg = types.Content(role="user", parts=[types.Part(text="Login page")])
    first = [e async for e in runner.run_async(user_id="u", session_id=session.id, new_message=msg)]
    interrupt_id, call = hitl_flow.find_interrupt(first)
    assert call.name == "adk_request_input" and "spec_approved" not in await final_state(runner, session.id, "u")

    reply = types.Content(role="user", parts=[types.Part(function_response=types.FunctionResponse(
        id=interrupt_id, name="adk_request_input", response={"answer": "yes"}))])
    second = [e async for e in runner.run_async(user_id="u", session_id=session.id, new_message=reply)]
    assert second[-1].output.startswith("PLAN for")
    assert (await final_state(runner, session.id, "u"))["spec_approved"] is True
