"""Shared workflow for Q5: write spec -> human approval gate (RequestInput) -> route -> plan / rejected.
No model anywhere."""
from google.adk import Context, Event, Workflow
from google.adk.events import RequestInput

EXECUTIONS: list[str] = []   # which node bodies ran in THIS process


def write_spec(node_input: str):
    EXECUTIONS.append("write_spec")
    spec = f"# Spec: {node_input}\n## Requirements\n- R1\n"
    yield Event(state={"spec_md": spec})
    yield Event(output=spec)


def approve_spec(node_input: str):
    """Human gate. rerun_on_resume defaults to False for function nodes, so the human's reply
    becomes this node's output."""
    EXECUTIONS.append("approve_spec")
    yield RequestInput(message="Approve the spec before planning? (yes/no)", payload={"spec_md": node_input})


def route_on_answer(ctx: Context, node_input):
    EXECUTIONS.append("route_on_answer")
    print(f"    route_on_answer  got node_input={node_input!r} (type {type(node_input).__name__})")
    answer = node_input.get("answer") if isinstance(node_input, dict) else node_input
    approved = str(answer).strip().lower() in ("yes", "y", "true", "approve", "approved")
    return Event(route="APPROVED" if approved else "REJECTED", state={"spec_approved": approved})


def plan(spec_md: str):                       # spec_md is bound from session state
    EXECUTIONS.append("plan")
    return f"PLAN for -> {spec_md.splitlines()[0]}"


def rejected():
    EXECUTIONS.append("rejected")
    return "Spec rejected; planning skipped."


def build_workflow() -> Workflow:
    return Workflow(
        name="sdd_gate",
        edges=[
            ("START", write_spec, approve_spec, route_on_answer),
            (route_on_answer, {"APPROVED": plan, "REJECTED": rejected}),
        ],
    )


def find_interrupt(events):
    """Returns (interrupt_id, function_call) of the adk_request_input call in a list of events."""
    for ev in events:
        for call in ev.get_function_calls():
            if ev.long_running_tool_ids and call.id in ev.long_running_tool_ids:
                return call.id, call
    return None, None
