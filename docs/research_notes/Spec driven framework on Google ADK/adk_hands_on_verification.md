# Google ADK for Python: hands-on verification on Python 3.14 (google-adk 2.15.0 and 2.14.1)

Every answer below comes from a script that was run, not from documentation. All 13 questions were tested on google-adk 2.15.0, and the same scripts were then re-run unchanged on google-adk 2.14.1. No model provider was contacted: wherever an LLM agent was needed, a fake model (a `BaseLlm` subclass returning canned responses) was used.

The short version: everything the plan needs works on both versions, and the two versions behaved the same in every experiment except one cosmetic difference in checkpoint events (see [Comparison with 2.14.1](#comparison-with-google-adk-2141)).

## Summary of answers

| # | Question | Answer | Status | Same on 2.14.1 |
|---|---|---|---|---|
| 1 | Installs and imports on Python 3.14? | Yes. 53 packages, zero warnings at import and at `adk --version`. | OBSERVED | Yes |
| 2 | Workflow of plain Python functions, with a route and a bounded loop? | Works. Output arrives as `node_input`; state through `ctx.state`, `Event(state=...)` or a parameter named after a state key. | OBSERVED | Yes |
| 3 | Is a custom `BaseAgent._run_async_impl` executed? | Yes in all three placements: root agent, workflow node, sub-agent of an LLM agent. | OBSERVED | Yes |
| 4 | Do `SequentialAgent`, `LoopAgent`, `ParallelAgent` still run? | Yes. Each emits a `DeprecationWarning` when constructed, none while running. | OBSERVED | Yes |
| 5 | Human approval gate with `RequestInput`, resumable? | Works with no model and no resumability configuration, including resume from a new process with SQLite sessions. | OBSERVED | Yes (one extra checkpoint event when resumability is switched on) |
| 6 | Swap an LLM step for Python? | One node definition changes; the workflow and the downstream node are untouched and see identical input and state. | OBSERVED | Yes |
| 7 | Invalid structured output? | `pydantic.ValidationError` is raised and an error event is emitted. No automatic retry, no event with the bad text. | OBSERVED | Yes |
| 8 | Is `output_key` written when a callback skips the model? | Yes, for both `before_agent_callback` and `before_model_callback`. | OBSERVED | Yes |
| 9 | Which plugin hooks fire? | Function node: run-level hooks and `on_event_callback` only. LLM agent adds agent and model hooks. Tool call adds tool hooks. | OBSERVED | Yes |
| 10 | Function tool declarations on Python 3.14? | Correct, and identical with and without `from __future__ import annotations`. | OBSERVED | Yes |
| 11 | Artifacts: versions and layout? | Versions are integers from 0. The file service writes plain files under `apps/<app>/users/<user>/sessions/<session>/artifacts/<name>/versions/<n>/`. | OBSERVED | Yes |
| 12 | Workflow with a fake-model agent under pytest? | Works: 5 tests pass in 0.6 s, also with every warning turned into an error. | OBSERVED | Yes |
| 13 | Event metadata and CLI subcommands? | `usage_metadata` and `model_version` appear on model events when the model supplies them; every event has a `timestamp`; no duration field. `adk eval` and `adk conformance` exist. | OBSERVED | Yes |

## Environment

Experiments were first run on 2026-11-20 between 23:45 and 23:58 CET. The recorded outputs in `out_2150/` and `out_2141/` come from a final run of all scripts on both versions on 2026-11-21, when this file was written.

| Item | Value |
|---|---|
| OS | macOS 26.5.1 (build 25F80), Apple silicon (arm64) |
| Python | CPython 3.14.10 (Homebrew, `/opt/homebrew/opt/python@3.14/bin/python3.14`) |
| uv | 0.13.9 (Homebrew 2026-11-17) |
| google-adk | 2.15.0 (main run) and 2.14.1 (comparison run), each in its own virtual environment |
| google-genai | 2.34.0 |
| pydantic / pydantic-core | 2.14.4 / 2.50.5 |
| fastapi / starlette / uvicorn | 0.165.0 / 1.10.0 / 0.54.0 |
| aiosqlite | 0.22.1 |
| opentelemetry-api / -sdk | 1.45.2 / 1.45.2 |
| google-auth / authlib | 2.62.2 / 1.9.10 |
| click / httpx / tenacity | 8.5.1 / 0.28.1 / 9.1.4 |
| typing-extensions / jsonschema / pyyaml | 4.16.0 / 4.26.0 / 6.0.3 |
| watchdog | 7.1.0 with 2.15.0, 6.0.0 with 2.14.1 (the only dependency that resolved differently) |
| pytest / pytest-asyncio | 9.2.0 / 1.5.0 |

Not installed by the core package, and therefore not exercised: `sqlalchemy`, `litellm`, `mcp`, `anthropic`, `google-cloud-aiplatform`.

### Where the scripts are

All scripts, both virtual environments and the recorded outputs are in:

`/private/tmp/claude-501/-Users-emrec-Projects-playground-adk-spec/7de6117d-4e2c-404c-9eeb-58fb288bc041/scratchpad/adk-spike`

This is a temporary directory that a reboot or routine cleanup can clear. Copy it somewhere durable if the scripts need to be kept as evidence.

| Path inside that directory | Content |
|---|---|
| `q01_*.py` to `q13_*.py`, `test_q12_pytest.py` | One small script per experiment |
| `fake_llm.py` | The fake model (`FakeLlm`) and an event printer shared by the scripts |
| `hitl_flow.py` | The approval-gate workflow shared by the question 5 scripts and the pytest suite |
| `run_all.sh` | Runs every script against one virtual environment and records the output |
| `out_2150/`, `out_2141/` | Recorded output of every script on each version |
| `data_2150/`, `data_2141/` | SQLite session files and the file-artifact tree the scripts wrote |
| `compare_versions.py`, `out_compare_2150_vs_2141.txt` | Diff of the two runs after masking IDs, timestamps and paths |
| `.venv/`, `.venv-2141/` | Virtual environments with google-adk 2.15.0 and 2.14.1 |

To reproduce:

```bash
cd <the directory above>
uv venv --python 3.14 && uv pip install google-adk==2.15.0 pytest pytest-asyncio
./run_all.sh .venv out_2150 data_2150
```

In the output excerpts below, UUIDs are shortened to `<id>` and long lines are cut with `...`.

### The fake model

Used wherever a question needs an LLM agent. It is the same technique as `MockModel` in ADK's own test suite.

```python
class FakeLlm(BaseLlm):                       # google.adk.models.base_llm.BaseLlm
    model: str = "fake-model"
    replies: list[Any] = Field(default_factory=list)
    requests: list[Any] = Field(default_factory=list)
    calls: int = 0

    async def generate_content_async(self, llm_request, stream=False):
        self.requests.append(llm_request)
        reply = self.replies[self.calls]; self.calls += 1
        parts = [reply] if isinstance(reply, types.Part) else [types.Part(text=str(reply))]
        yield LlmResponse(content=types.Content(role="model", parts=parts))
```

It is passed directly as `Agent(model=FakeLlm(replies=[...]))`. A scripted function call is `types.Part(function_call=types.FunctionCall(name=..., args=...))`.

## 1. Installation on Python 3.14

**Answer:** google-adk 2.15.0 installs and imports cleanly. No warning is raised at import or at `adk --version`. **Status: OBSERVED.**

Script: `q01_install.py` imports 23 ADK modules with `warnings.simplefilter("always")` and prints versions.

```text
$ uv venv --python 3.14
Using CPython 3.14.10 interpreter at: /opt/homebrew/opt/python@3.14/bin/python3.14
$ uv pip install google-adk==2.15.0 pytest pytest-asyncio
Resolved 53 packages in 391ms
Installed 53 packages in 85ms

python      : 3.14.10 (main, Oct 25 2026, 17:12:00) [Clang 21.0.0 (clang-2100.3.34.2)]
platform    : macOS-26.5.1-arm64-arm-64bit-Mach-O arm64
import ok   : google.adk            (and 22 more modules: agents, workflow, runners, apps, events,
                                     plugins, tools, sessions, artifacts, models, evaluation, cli)
warnings raised during imports: 0
google.adk.__version__ : 2.15.0
requires-python: >=3.11
classifiers py : ['Only', '3.11', '3.12', '3.13', '3.14', '3.15']

$ PYTHONWARNINGS=always adk --version
adk, version 2.15.0
```

Additional observations:

- `python -W error -c "from google.adk import Agent, Workflow, Event, Context, Runner"` also succeeds, so nothing in the import path raises a deprecation warning on 3.14.
- uv reported no source builds: two packages were downloaded and the rest came from its cache.
- `adk --help` lists: `api_server`, `conformance`, `create`, `deploy`, `eval`, `eval_set`, `generate_agent_card`, `migrate`, `optimize`, `run`, `telemetry`, `test`, `web`.
- Two ADK log lines (not Python warnings) appeared at run time in later experiments. `Skipping missing token usage metadata for agent <name> and model fake-model` is printed whenever the fake model answers without usage numbers. `App "<name>" can transfer between agents but has no context_cache_config ...` is printed for an LLM agent with sub-agents and no cache configuration.

## 2. Graph workflow made of plain Python functions

**Answer:** it works with no model, no `App` and no decorators. A function becomes a node by appearing in `edges`. **Status: OBSERVED.**

What was observed, point by point:

| Topic | Observed behavior |
|---|---|
| Previous node's output | Arrives in the parameter named `node_input`. A plain `return value` or `yield Event(output=value)` both set it. |
| First node | Receives the user message. Annotated `node_input: str` it gets the text; with no annotation it gets a `types.Content` object. |
| Reading state | `ctx.state.get("key")` on a parameter typed `Context`, or a parameter named after the state key (`def check(node_input, attempts: int)`). |
| Writing state | `yield Event(state={...})`, or `ctx.state["key"] = value` (the change lands in the `state_delta` of the node's next event). |
| Routing | `return Event(route="KEY", output=...)` plus an edge row `(node, {"KEY": target, ...})`. Route and output can be on the same event. |
| Bounded loop | A back-edge in the route map, bounded by a counter kept in state. The engine itself was not seen to impose a limit; the bound is the node's own check. |
| Events | One event per `return` or `yield`. `author` is the workflow name, `node_info.path` is `<workflow>@1/<node>@<run number>`, and the payload is in `output`, `actions.state_delta`, `actions.route` or `content`. |
| Starting a run | `Runner(node=workflow, session_service=...)`, create a session, then `runner.run_async(user_id=..., session_id=..., new_message=...)`. `app_name` defaults to the workflow name. |
| Persistence | The user message is stored as an event but not yielded by `run_async` (8 events yielded, 9 stored). |

Script (`q02_function_workflow.py`, trimmed):

```python
def intake(node_input: str):
    return {"title": node_input.strip(), "words": len(node_input.split())}

def draft(ctx: Context, node_input: dict):
    attempt = ctx.state.get("attempts", 0) + 1
    text = f"spec for {node_input['title']} (attempt {attempt})"
    yield Event(state={"attempts": attempt, "draft_text": text})
    yield Event(output={"title": node_input["title"], "text": text, "attempt": attempt})

def check(node_input: dict, attempts: int, draft_text: str):   # attempts, draft_text come from state
    if attempts >= MAX_ATTEMPTS:
        return Event(route="GIVE_UP", output=node_input)
    if node_input["attempt"] < 2:
        return Event(route="RETRY", output={"title": node_input["title"]})
    return Event(route="OK", output=node_input)

wf = Workflow(name="spec_flow", edges=[
    ("START", intake, draft, check),
    (check, {"RETRY": draft, "OK": publish, "GIVE_UP": give_up}),
])
runner = Runner(node=wf, session_service=session_service)
session = await session_service.create_session(app_name=runner.app_name, user_id="u1")
async for event in runner.run_async(user_id="u1", session_id=session.id,
        new_message=types.Content(role="user", parts=[types.Part(text="Login page")])):
    ...
```

Observed output (trimmed):

```text
=== A. route OK after one RETRY: runner.app_name='spec_flow' resumability_config=None
    intake           got node_input='Login page' type=str
  [01] author='spec_flow' | node_path='spec_flow@1/intake@1' | output={'title': 'Login page', 'words': 2}
  [02] author='spec_flow' | node_path='spec_flow@1/draft@1' | state_delta={'attempts': 1, 'draft_text': 'spec for Login page (attempt 1)'}
  [03] author='spec_flow' | node_path='spec_flow@1/draft@1' | output={'title': 'Login page', 'text': 'spec for Login page (attempt 1)', 'attempt': 1}
    check            got node_input.attempt=1 state.attempts=1 state.draft_text='spec for Login page (attempt 1)'
  [04] author='spec_flow' | node_path='spec_flow@1/check@1' | output={'title': 'Login page'} | route='RETRY'
  [05] author='spec_flow' | node_path='spec_flow@1/draft@2' | state_delta={'attempts': 2, ...}
  [07] author='spec_flow' | node_path='spec_flow@1/check@2' | output={...} | route='OK'
  [08] author='spec_flow' | node_path='spec_flow@1/publish@1' | text='done (user-facing message)' | output='PUBLISHED: spec for Login page (attempt 2)' | state_delta={'published': True}
  final session.state : {'attempts': 2, 'draft_text': 'spec for Login page (attempt 2)', 'published': True}
  events persisted    : 9 (incl. the user message event)

=== B. loop bounded at MAX_ATTEMPTS=3  (a check node that never approves)
  [04] ... always_retry@1 ... route='RETRY'
  [07] ... always_retry@2 ... route='RETRY'
  [10] author='spec_flow' | node_path='spec_flow@1/always_retry@3' | output={...} | route='GIVE_UP'
  [11] author='spec_flow' | node_path='spec_flow@1/give_up@1' | output='GAVE UP after 3 attempts'
```

Edge cases, from `q02b_dynamic_and_edge_cases.py`:

| Case | Observed result |
|---|---|
| Dynamic workflow: one `@node(rerun_on_resume=True)` orchestrator calling `await ctx.run_node(child, input)` inside `for i in range(3)` | Works. Child events carry paths such as `dyn@1/pipeline@1/validate_spec@2`; `ctx.run_node` returns the child's output. |
| One node yields `Event(output=...)` twice | The first output event is emitted, then an error event, then `run_async` raises `ValueError: Output already set. A node can produce at most one output.` |
| A parameter is bound from state but the key is missing and has no default | `google.adk.workflow._errors.WorkflowDataError: Missing value for parameter "not_in_state" of function "needs_missing_key". It was not found in state and has no default value.` |
| `InMemoryRunner(node=wf, app_name=...)` and `await runner.run_debug("text", quiet=True)` | Works, creates the session itself, returns the list of events. |

When a node raises, ADK logs the full traceback at ERROR level, emits an event with `error_code` and `error_message`, and re-raises the original exception from `run_async`.

## 3. Custom `BaseAgent` subclasses

**Answer:** `_run_async_impl` is executed in 2.15.0 in all three placements, and `before_agent_callback` / `after_agent_callback` fire around it. The migration page's statement that the override is bypassed and silently ignored does not match what happens. **Status: OBSERVED.**

Script (`q03_custom_agent.py`, trimmed):

```python
class SpecGate(BaseAgent):
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        CALLS.append(self.name)
        yield Event(invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
                    content={"role": "model", "parts": [{"text": f"gate verdict from {self.name}"}]},
                    actions=EventActions(state_delta={f"{self.name}_ran": True}))

Runner(agent=SpecGate(name="gate_root"), app_name="q3a", session_service=ss)                    # (a)
Runner(node=Workflow(name="q3b", edges=[("START", upstream, SpecGate(name="gate_node"), downstream)]),
       session_service=ss)                                                                       # (b)
Agent(name="coordinator", model=FakeLlm(replies=[fc("transfer_to_agent", {"agent_name": "gate_sub"}), "..."]),
      sub_agents=[SpecGate(name="gate_sub", description="Checks specs deterministically.")])    # (c)
```

Observed output (trimmed):

```text
=== (a) custom BaseAgent as ROOT agent: Runner(agent=..., app_name=...)
    before_agent_callback fired for gate_root
    >>> SpecGate._run_async_impl EXECUTED (name=gate_root, ctx=InvocationContext, user_content='check my spec')
  [01] author='gate_root' | text='gate verdict from gate_root' | state_delta={'gate_root_ran': True}
    after_agent_callback fired for gate_root

=== (b) custom BaseAgent as a NODE inside a Workflow
  [01] author='q3b' | node_path='q3b@1/upstream@1' | output={'spec': 'check my spec'}
    >>> SpecGate._run_async_impl EXECUTED (name=gate_node, ...)
  [02] author='gate_node' | node_path='q3b@1/gate_node@1' | text='gate verdict from gate_node' | state_delta={'gate_node_ran': True}
    downstream node got node_input=None state={'gate_node_ran': True}

=== (c) custom BaseAgent as SUB-AGENT of an LLM agent (fake model emits transfer_to_agent)
  [01] author='coordinator' | node_path='coordinator@1' | function_call=transfer_to_agent(id='adk-<id>', args={'agent_name': 'gate_sub'})
  [02] author='coordinator' | ... function_response=transfer_to_agent(...) | transfer_to_agent='gate_sub'
    >>> SpecGate._run_async_impl EXECUTED (name=gate_sub, ...)
  [03] author='gate_sub' | node_path='coordinator@1/gate_sub@1' | text='gate verdict from gate_sub' | state_delta={'gate_sub_ran': True}
total _run_async_impl executions: ['gate_root', 'gate_node', 'gate_sub']
```

Two limits seen when the custom agent is a workflow node:

- The override receives an `InvocationContext`, not the previous node's output. It can read session state and `ctx.user_content` only.
- The next node receives `node_input=None` unless the custom agent's event sets `output`. With `yield Event(..., output={"ok": True, "missing": []})` the next node received that dict (`q03b_custom_agent_output.py`).

A plain function node has neither limit, so it remains the simpler choice for deterministic steps inside a workflow.

## 4. Deprecated workflow agents

**Answer:** `SequentialAgent`, `LoopAgent` and `ParallelAgent` all still run. Each emits one `DeprecationWarning` when constructed and none while running. **Status: OBSERVED.**

The warning text, identical apart from the class name:

```text
DeprecationWarning: SequentialAgent is deprecated in favor of Workflow and will be removed in a future
version. Workflow cannot yet be used as an LlmAgent sub-agent.
```

Script: `q04_deprecated_agents.py` runs each class with deterministic custom sub-agents (plus one fake-model `Agent` in the sequence).

```text
=== SequentialAgent
  [01] author='writer' | text='draft text from fake model' | state_delta={'draft': 'draft text from fake model'}
  [02] author='s1' | text='s1 n=1' | state_delta={'count': 1, 's1_seen': 1}
  [03] author='s2' | text='s2 n=2' | state_delta={'count': 2, 's2_seen': 2}
=== LoopAgent(max_iterations=5), sub-agent escalates at count 3
  [01] worker n=1  [02] checker n=2  [03] worker n=3
  [04] author='checker' | text='checker n=4' | state_delta={...} | escalate=True        <- loop ends here
=== LoopAgent(max_iterations=2), nobody escalates
  [01] w2 n=1  [02] w2 n=2                                                           <- stops at max_iterations
=== ParallelAgent
  [01] author='p1' | ... state_delta={'count': 1, 'p1_seen': 1} | branch='par.p1'
  [02] author='p2' | ... state_delta={'count': 1, 'p2_seen': 1} | branch='par.p2'
  [03] author='p3' | ... state_delta={'count': 1, 'p3_seen': 1} | branch='par.p3'
  warnings while running: none
```

Under Python's default warning filter the warning is printed when the agent is constructed in the script being run (`q04b_default_filter.py`). With `python -W error` construction fails with that `DeprecationWarning`. Whether the warning is visible when the agent is constructed inside an imported module was not checked; Python's default filter hides deprecation warnings raised outside `__main__`, so it probably is not.

In the parallel run all three branches read `count` before any of them wrote it, so each wrote `count: 1`. Shared state keys written by parallel branches overwrite each other.

## 5. Human approval gate with `RequestInput`

**Answer:** a workflow pauses on `yield RequestInput(...)` and resumes when the client sends a function response carrying the interrupt ID. No model is involved and no resumability configuration is required. A paused run can be resumed from a new Python process when sessions are stored in SQLite. **Status: OBSERVED.**

Workflow (`hitl_flow.py`, trimmed):

```python
def approve_spec(node_input: str):
    yield RequestInput(message="Approve the spec before planning? (yes/no)", payload={"spec_md": node_input})

def route_on_answer(ctx: Context, node_input):
    answer = node_input.get("answer") if isinstance(node_input, dict) else node_input
    approved = str(answer).strip().lower() in ("yes", "y", "true", "approve", "approved")
    return Event(route="APPROVED" if approved else "REJECTED", state={"spec_approved": approved})

Workflow(name="sdd_gate", edges=[
    ("START", write_spec, approve_spec, route_on_answer),
    (route_on_answer, {"APPROVED": plan, "REJECTED": rejected}),
])
```

The pause appears as an event containing a function call named `adk_request_input`, whose `id` is the interrupt ID and is also listed in `event.long_running_tool_ids`. The exact resume call:

```python
reply = types.Content(role="user", parts=[types.Part(function_response=types.FunctionResponse(
    id=interrupt_id,               # id of the adk_request_input function call in the pause event
    name="adk_request_input",
    response={"answer": "yes"},    # becomes the gate node's output, so the next node's node_input
))])
async for event in runner.run_async(user_id="u", session_id=session.id, new_message=reply):
    ...
```

`invocation_id` does not have to be passed: the runner finds the paused invocation from the function response ID and continues under the same invocation ID.

Observed output, no `App` and no resumability configuration (`q05a_hitl_inmemory.py`, trimmed):

```text
--- run 1 (expected to pause at the gate)
  [01] author='sdd_gate' | node_path='sdd_gate@1/write_spec@1' | state_delta={'spec_md': '# Spec: Login page\n...'}
  [02] author='sdd_gate' | node_path='sdd_gate@1/write_spec@1' | output='# Spec: Login page\n## Requirements\n- R1\n'
  [03] author='sdd_gate' | node_path='sdd_gate@1/approve_spec@1' | function_call=adk_request_input(id='<id>', args={'interruptId': '<id>', 'payload': {'spec_md': ...}, 'message': 'Approve the spec before planning? (yes/no)', 'response_schema': None}) | long_running_tool_ids=['<id>']
  node bodies executed so far: ['write_spec', 'approve_spec']
--- run 2: resume with FunctionResponse(id=interrupt_id, name='adk_request_input', response={'answer': 'yes'})
    route_on_answer  got node_input={'answer': 'yes'} (type dict)
  [01] author='sdd_gate' | node_path='sdd_gate@1/route_on_answer@1' | state_delta={'spec_approved': True} | route='APPROVED'
  [02] author='sdd_gate' | node_path='sdd_gate@1/plan@1' | output='PLAN for -> # Spec: Login page'
  invocation_id of run 2 = e-<id> (same as run 1: True)
  node bodies executed in total: ['write_spec', 'approve_spec', 'route_on_answer', 'plan']
```

Resume from a new process with SQLite (`q05b_hitl_sqlite.py`, run as two separate interpreter processes):

```python
from google.adk.sessions.sqlite_session_service import SqliteSessionService
runner = Runner(node=hitl_flow.build_workflow(), session_service=SqliteSessionService("data/q05_sessions_plain.db"))
```

```text
--- process 85166 START (resumable=False)
  [03] ... function_call=adk_request_input(id='<id>', ...) | long_running_tool_ids=['<id>']
  node bodies executed in this process: ['write_spec', 'approve_spec']
  sqlite file: q05_sessions_plain.db (36864 bytes)
--- process 85181 RESUME (started by pid 85166; resumable=False)
  session loaded from SQLite: 4 events, state keys=['spec_md']
    route_on_answer  got node_input={'answer': 'yes'} (type dict)
  [01] ... route_on_answer@1 | state_delta={'spec_approved': True} | route='APPROVED'
  [02] ... plan@1 | output='PLAN for -> # Spec: Login page'
  node bodies executed in this process: ['route_on_answer', 'plan']
  resumed invocation_id == paused invocation_id: True
  final state: {'spec_approved': True, 'spec_md': '# Spec: Login page\n## Requirements\n- R1\n'}
```

The second process only needed the session ID and the interrupt ID. The SQLite file has four tables: `app_states`, `events`, `sessions`, `user_states`; after the resumed run its `events` table held 7 rows.

Variants and their results:

| Variant | Observed result |
|---|---|
| `App(resumability_config=ResumabilityConfig(is_resumable=True))` | Also works, in one process and across two. The stream gains checkpoint events (`actions.agent_state` with per-node status), the resumed run re-emits the outputs of completed nodes before continuing, and a final `end_of_agent=True` event is added. Completed node bodies are not executed again. |
| `App` with `is_resumable=False` | Same as no `App`. |
| Reply `{"result": "yes"}` | Unwrapped: the next node receives the string `'yes'`. Any other dict, such as `{"answer": "yes"}`, is passed through as a dict. |
| Reply sent as plain text (`"yes"`) instead of a function response | Does not resume. A new invocation starts from `START` with `"yes"` as the feature request, `spec_md` in state is overwritten, and a second pause is raised. No error is reported. |
| `run_async(user_id, session_id, invocation_id=<paused id>)` with no message | Does not resume. Without resumability: 0 events, no error. With resumability: 2 replay events, still paused. |
| Gate inside a dynamic workflow (`answer = await ctx.run_node(approve, spec)`) | Works. On resume the orchestrator body runs again from the top, completed children (`write`, `approve`) are replayed without executing, and `ctx.run_node(approve, ...)` returns the answer. |
| `from google.adk.sessions import DatabaseSessionService` | `ImportError: The 'sqlalchemy' package is required to use this feature. Please install it by running: pip install google-adk[db]` |

Consequence for the plan: the client must send approvals as function responses. A chat box that forwards the user's typed "yes" as text silently restarts the pipeline.

## 6. Swapping an LLM step for Python

**Answer:** only the definition of the step changes. The `Workflow` definition and the downstream node are byte-for-byte the same, and the downstream node receives the same `node_input` and the same state. **Status: OBSERVED.**

The minimal code difference (`q06_swap_llm_for_python.py`):

```python
# LLM version
spec_writer = Agent(name="spec_writer", model=llm,
                    instruction="Write a markdown spec for the feature request.", output_key="spec_md")

# Python version
def spec_writer(node_input: str):
    yield Event(output=SPEC, state={"spec_md": SPEC})

# unchanged in both
Workflow(name="pipeline", edges=[("START", intake, spec_writer, downstream)])
```

Observed output (trimmed):

```text
=== variant: LLM agent step
  [02] author='spec_writer' | node_path='pipeline@1/spec_writer@1' | text='# Spec: Login page\n...' | state_delta={'spec_md': '# Spec: Login page\n...'}
  fake model calls: 1
  what the model was sent: system_instruction='Write a markdown spec for the feature request.'
     content role=user parts=['Feature request: Login page']
=== variant: Python function step
  [02] author='pipeline' | node_path='pipeline@1/spec_writer@1' | output='# Spec: Login page\n...' | state_delta={'spec_md': '# Spec: Login page\n...'}
=== what the unchanged downstream node observed
  node_input identical: True
  state identical     : True
```

The LLM agent node receives the previous node's output as its user message, and its final text becomes the next node's `node_input`.

What does differ is visible only to code that reads the event stream:

| Event field | LLM agent step | Python step |
|---|---|---|
| `author` | the agent name (`spec_writer`) | the workflow name (`pipeline`) |
| Payload | `content` (text), `output` empty | `output`, `content` empty |
| `node_info.message_as_output` | `True` | not set |
| `node_info.path` | `pipeline@1/spec_writer@1` | the same |

With structured output there is one more difference (`q06b_typed_contract.py`):

| Step | Downstream node with no annotation receives | Downstream node annotated `node_input: TaskList` receives |
|---|---|---|
| `Agent(output_schema=TaskList, output_key="tasks")` | `dict` | `TaskList` instance |
| Python node, `yield Event(output=<TaskList instance>)` | `TaskList` instance | `TaskList` instance |
| Python node, `yield Event(output=<dict>)` | `dict` | `TaskList` instance |
| Python node declared `-> TaskList`, plain `return <TaskList instance>` | `dict` | `TaskList` instance |

So a downstream node notices nothing as long as it annotates `node_input` with the Pydantic type. An unannotated node can see a dict in one variant and a model instance in another.

## 7. Structured output with `output_schema`

**Answer:** when the model's text is not valid JSON or fails Pydantic validation, ADK raises `pydantic.ValidationError` out of `run_async` and emits an error event. It does not retry, and no event carries the bad text. In the valid case `output_key` stores a plain `dict`. **Status: OBSERVED.**

Script (`q07_structured_output.py`, trimmed):

```python
class TaskList(BaseModel):
    tasks: list[Task] = Field(min_length=1)
    note: str | None = None

agent = Agent(name="task_breaker", model=FakeLlm(replies=[...]), instruction="Break the plan into tasks.",
              output_schema=TaskList, output_key="tasks")
```

Results, the same for a root agent and for a workflow node unless stated:

| Model reply | Outcome | Model calls | `state["tasks"]` |
|---|---|---|---|
| Valid JSON | Completes | 1 | `{'tasks': [{'id': 'T-1', 'title': 'Login form', 'depends_on': []}]}` (a `dict`) |
| Valid JSON inside a ` ```json ` fence | Completes; the fence is stripped | 1 | The same dict |
| Text that is not JSON | Raises `pydantic_core.ValidationError` (`Invalid JSON: expected value at line 1 column 1`) | 1 of 2 scripted | absent |
| `{"tasks": []}` (violates `min_length=1`) | Raises `ValidationError` (`List should have at least 1 item`) | 1 of 2 scripted | absent |
| Missing required field | Raises `ValidationError` (`tasks.0.title Field required`) | 1 of 2 scripted | absent |

Details of the valid case:

- The stored dict is the validated model dumped with `exclude_none=True`: defaults are filled in (`depends_on: []`) and `None` fields are dropped (`note` is absent).
- As a workflow node, the same dict is also the event's `output` and the next node's `node_input`.
- The request sent to the model had `response_schema` set and `response_mime_type='application/json'`, with no extra tool.

Details of the failure case:

```text
=== NOT JSON [workflow node]
  [01] author='wf' | node_path='wf@1/task_breaker@1' | error='ValidationError':"1 validation error for TaskList\n  Invalid JSON: expected value at line 1 column 1 [type=json_invalid, input_value='Sure! Here are the tasks: T-1 Login form...
  outcome            : RAISED pydantic_core._pydantic_core.ValidationError: 1 validation error for TaskList ...
  model calls        : 1 (of 2 scripted)
  persisted events   : ['user', 'error']; first model reply text stored in an event: False
  downstream got     : '<downstream did not run>'
```

Two further findings:

- A retry is available per node but is off by default. With `Agent(..., retry_config=RetryConfig(max_attempts=2, initial_delay=0.01))` as a workflow node, the first invalid reply produced an error event, the model was called a second time, and the run completed with the valid reply. The second request had the same contents as the first (`[('user', ['plan'])]`): the validation error is not fed back to the model.
- A **root** agent with `output_schema` but **no** `output_key` does not validate at all: the non-JSON reply came back as an ordinary text event and the run completed without an exception. As a workflow node the same agent did raise `ValidationError`. Validation therefore happens when the value is stored (`output_key`) or handed to the next node, not when the model answers.

## 8. Skipping a model call with a callback

**Answer:** `output_key` is still written in both cases, with the content the callback returned. **Status: OBSERVED.**

Script (`q08_skip_model_call.py`, trimmed):

```python
def skip_agent(callback_context):
    return types.Content(role="model", parts=[types.Part(text="FROM before_agent_callback")])

def skip_model(callback_context, llm_request):
    return LlmResponse(content=types.Content(role="model", parts=[types.Part(text="FROM before_model_callback")]))

Agent(name="spec_writer", model=llm, instruction="write", output_key="spec_md", before_agent_callback=skip_agent)
```

| Callback | Model calls | `state["spec_md"]` | Next workflow node's `node_input` |
|---|---|---|---|
| none (baseline) | 1 | `'FROM THE MODEL'` | `'FROM THE MODEL'` |
| `before_agent_callback` returns `Content` | 0 | `'FROM before_agent_callback'` | `'FROM before_agent_callback'` |
| `before_agent_callback` writes `state["spec_md"]` itself, then returns `Content` | 0 | `'FROM before_agent_callback'` (the callback's own write is replaced) | `'FROM before_agent_callback'` |
| `before_model_callback` returns `LlmResponse` | 0 | `'FROM before_model_callback'` | `'FROM before_model_callback'` |

The result was the same in three placements: root agent, workflow node, and sub-agent of a `SequentialAgent`.

Consequence: a callback that replaces an agent should return the real output as its content. It cannot store a different value under the agent's own `output_key`, because the returned content overwrites it.

## 9. Plugins

**Answer:** a plugin registered with `App(plugins=[...])` sees every run. Which hooks fire depends on the node type. **Status: OBSERVED.**

Script: `q09_plugins.py` registers a `BasePlugin` subclass that overrides all 14 hooks.

```python
runner = Runner(app=App(name="q9", root_agent=workflow, plugins=[Recorder()]), session_service=ss)
```

| Hook | Plain function node | LLM agent node | LLM agent node calling a tool | Function node that raises |
|---|---|---|---|---|
| `on_user_message_callback` | fires | fires | fires | fires |
| `before_run_callback` | fires | fires | fires | fires |
| `on_event_callback` | once per event | once per event | once per event (call, response, text) | once (the error event) |
| `after_run_callback` | fires | fires | fires | does not fire |
| `before_agent_callback` / `after_agent_callback` | do not fire | fire | fire | do not fire |
| `before_model_callback` / `after_model_callback` | do not fire | fire | fire, twice (one per model call) | do not fire |
| `before_tool_callback` / `after_tool_callback` | do not fire | do not fire | fire | do not fire |
| `on_run_error_callback` | — | — | — | fires |

Observed order for the tool case:

```text
on_user_message_callback
before_run_callback
before_agent_callback(counter)
before_model_callback(counter)
after_model_callback(counter)
on_event_callback(wf@1/counter@1:function_call)
before_tool_callback(count_words args={'text': 'a b c'})
after_tool_callback(count_words result={'status': 'success', 'words': 3})
on_event_callback(wf@1/counter@1:function_response)
before_model_callback(counter)
after_model_callback(counter)
on_event_callback(wf@1/counter@1:text)
after_agent_callback(counter)
after_run_callback
```

No agent hook fires for the `Workflow` itself. Policy or logging that must cover plain function nodes can only use `on_event_callback` (after the node has produced an event) or the run-level hooks.

Passing the plugin as `Runner(plugins=[...])` still works and fires the same hooks, with `DeprecationWarning: The 'plugins' argument is deprecated. Please use the 'app' argument to provide plugins instead.`

## 10. Function tools under Python 3.14

**Answer:** the generated declarations are correct, and they are identical whether or not the module uses `from __future__ import annotations`. Calling the tool through an agent delivers correctly typed arguments in both cases. **Status: OBSERVED.**

Script: the same functions are defined in `q10_tools_plain.py` (no future import, so Python 3.14's deferred evaluation applies) and `q10_tools_future.py` (string annotations). `q10_function_tools.py` prints `FunctionTool(func)._get_declaration()` for both and invokes the tool through an agent.

```python
def save_spec(
    filename: str, markdown: str, tags: list[str], reviewer: str | None, task: TaskSpec,
    tool_context: ToolContext, section: Optional[str] = None, priority: Priority = Priority.LOW,
    mode: Literal["draft", "final"] = "draft", max_versions: int = 5,
) -> dict:
    """Saves a spec as markdown.

    Args:
      filename: Name of the spec file, for example "spec.md".
      ...
    """
```

Observed declaration (trimmed):

```text
"name": "save_spec",
"description": "Saves a spec as markdown.\n\nArgs:\n  filename: Name of the spec file, ...",   <- the whole docstring
"parameters_json_schema": {
  "$defs": { "Priority": {"enum": ["low", "high"], "type": "string"},
             "TaskSpec": {"description": "A task to add to the plan.",
                          "properties": {"title": {"description": "Short task title", "type": "string"},
                                         "estimate_hours": {"anyOf": [{"type": "number"}, {"type": "null"}], "default": null},
                                         "labels": {"default": [], "items": {"type": "string"}, "type": "array"}},
                          "required": ["title"], "type": "object"} },
  "properties": {
    "filename": {"type": "string"},
    "tags":     {"items": {"type": "string"}, "type": "array"},
    "reviewer": {"anyOf": [{"type": "string"}, {"type": "null"}]},
    "task":     {"$ref": "#/$defs/TaskSpec"},
    "section":  {"anyOf": [{"type": "string"}, {"type": "null"}], "default": null},
    "priority": {"$ref": "#/$defs/Priority", "default": "low"},
    "mode":     {"default": "draft", "enum": ["draft", "final"], "type": "string"},
    "max_versions": {"default": 5, "type": "integer"} },
  "required": ["filename", "markdown", "tags", "reviewer", "task"] }

=== save_spec: declaration with `from __future__ import annotations` identical to plain: True
=== list_tasks: declaration with `from __future__ import annotations` identical to plain: True
```

Points confirmed by the output:

| Point | Observed |
|---|---|
| `str \| None` without a default | Nullable and still **required** |
| `Optional[str] = None` | Nullable and optional |
| `list[str]` | `array` of `string` |
| Pydantic model parameter | Referenced through `$defs`; `Field(description=...)` inside the model is kept |
| `ToolContext` parameter | Absent from the schema, and injected at call time |
| Docstring | Becomes the single top-level `description`; no per-parameter descriptions are generated from it |
| Return annotation | Not part of the declaration |
| Schema field | `parameters_json_schema` (JSON Schema), not `parameters` |

Invocation through an agent, with the fake model supplying plain JSON arguments:

```text
tool returned: {"status": "success", "received": {"task_type": "TaskSpec", "task": {"title": "Login",
  "estimate_hours": 2.0, "labels": []}, "tags_type": "list", "reviewer": null, "priority_type": "Priority",
  "priority": "Priority.HIGH", "has_tool_context": true, "mode": "final", "section": null}}
```

The function received a `TaskSpec` instance and a `Priority` enum member, in both modules.

## 11. Artifacts

**Answer:** both services version an artifact with integers starting at 0, one new version per save of the same filename. The file service stores each version as a plain file plus a `metadata.json`. **Status: OBSERVED.**

Script (`q11_artifacts.py`, trimmed), using workflow function nodes:

```python
async def save_v0(ctx: Context, node_input: str):
    part = types.Part.from_bytes(data=f"# Spec: {node_input}\n\nv0 body\n".encode(), mime_type="text/markdown")
    version = await ctx.save_artifact("spec.md", part)          # -> 0; a second save returns 1

latest = await ctx.load_artifact("spec.md")                      # newest version
first  = await ctx.load_artifact("spec.md", version=0)           # a specific version
text   = latest.inline_data.data.decode()

runner = Runner(node=wf, session_service=ss, artifact_service=FileArtifactService(root_dir="data/q11_artifacts"))
```

On-disk layout written by `FileArtifactService`:

```text
apps/
  arts/                                   <- app name
    users/
      u1/                                 <- user id
        artifacts/                        <- user-scoped ("user:glossary.md")
          glossary.md/
            versions/0/  glossary.md, metadata.json
        sessions/
          sess-1/                         <- session id
            artifacts/
              spec.md/
                versions/
                  0/  spec.md (23 bytes), metadata.json
                  1/  spec.md (26 bytes), metadata.json
              specs/001-login/plan.md/    <- "/" in a filename creates nested directories
                versions/0/  plan.md, metadata.json
```

`versions/1/spec.md` is the markdown itself, readable with any editor. `metadata.json` for that version:

```json
{"version":1,"canonicalUri":"file:///.../apps/arts/users/u1/sessions/sess-1/artifacts/spec.md/versions/1/spec.md",
 "customMetadata":{"stage":"review"},"createTime":1795215185.76466,"mimeType":"text/markdown","fileName":"spec.md"}
```

Observed behavior, the same for `FileArtifactService` and `InMemoryArtifactService` unless stated:

| Operation | Result |
|---|---|
| `ctx.save_artifact("spec.md", part)` twice | Returns `0`, then `1`. The node's event carries `actions.artifact_delta={'spec.md': 1}`. |
| `ctx.load_artifact("spec.md")` | Version 1 (the latest), as a `Part` with `inline_data` and `mime_type='text/markdown'` |
| `ctx.load_artifact("spec.md", version=0)` | Version 0 |
| `ctx.load_artifact("spec.md", version=7)` | `None` |
| `ctx.list_artifacts()` | `['spec.md', 'specs/001-login/plan.md', 'user:glossary.md']` |
| `ctx.get_artifact_version("spec.md")` | Version, canonical URI, custom metadata, create time, MIME type |
| `service.list_versions(app_name=..., user_id=..., session_id=..., filename="spec.md")` | `[0, 1]` |
| Keys visible from another session of the same user | `['user:glossary.md']` only |
| An artifact saved with `types.Part.from_text(...)` | Loads back as a text part (`part.text`), not `inline_data` |
| Canonical URI, in-memory service | `memory://apps/arts/users/u1/sessions/sess-1/artifacts/spec.md/versions/1` |
| `ctx.save_artifact` with no artifact service on the `Runner` | `ValueError: Artifact service is not initialized.` |
| `{artifact.spec.md}` in an agent instruction | Replaced by the text of the latest version; a filename with a dot works |

## 12. Testing under pytest

**Answer:** a workflow containing a fake-model LLM agent runs under pytest with `InMemoryRunner`; no network, no credentials, 0.6 seconds for five tests. **Status: OBSERVED.**

Script (`test_q12_pytest.py`, trimmed):

```python
@pytest.mark.asyncio
async def test_workflow_with_fake_llm_agent_run_debug():
    llm = FakeLlm(replies=[SPEC])
    wf = Workflow(name="pipeline", edges=[("START", intake,
                  Agent(name="spec_writer", model=llm, instruction="Write the spec.", output_key="spec_md"),
                  validate_spec)])
    runner = InMemoryRunner(node=wf, app_name="t")
    events = await runner.run_debug("Add login", quiet=True)

    assert llm.calls == 1
    assert llm.requests[0].contents[-1].parts[0].text == "Feature request: Add login"
    assert events[-1].output == {"ok": True, "missing": []}
    session = await runner.session_service.get_session(app_name="t", user_id="debug_user_id", session_id="debug_session_id")
    assert session.state["spec_md"] == SPEC and session.state["spec_ok"] is True
```

```text
$ python -m pytest test_q12_pytest.py -v -o asyncio_default_fixture_loop_scope=function
platform darwin -- Python 3.14.10, pytest-9.2.0, pluggy-1.7.0
plugins: anyio-4.16.0, asyncio-1.5.0
test_q12_pytest.py::test_workflow_with_fake_llm_agent_run_debug PASSED   [ 20%]
test_q12_pytest.py::test_workflow_run_async_with_explicit_session PASSED [ 40%]
test_q12_pytest.py::test_python_replacement_makes_no_model_call_and_same_result PASSED [ 60%]
test_q12_pytest.py::test_invalid_structured_output_raises_validation_error PASSED [ 80%]
test_q12_pytest.py::test_human_gate_pauses_and_resumes PASSED            [100%]
============================== 5 passed in 0.60s ===============================

$ python -m pytest test_q12_pytest.py -q -o asyncio_default_fixture_loop_scope=function -W error
5 passed in 0.58s
```

The five tests cover: a full run through `run_debug`; a run through `run_async` with an explicit session; equality of output and state between the LLM step and its Python replacement; `pytest.raises(pydantic.ValidationError)` for invalid structured output; and pause and resume of the approval gate.

Practical notes:

- `run_debug` uses the fixed IDs `debug_user_id` and `debug_session_id`.
- pytest-asyncio 1.5.0 prints a configuration warning unless `asyncio_default_fixture_loop_scope` is set. That warning comes from the plugin, not from ADK.
- With `-W error`, ADK raised no warning of any kind during the five tests.
- The recorded `llm.requests` allow assertions on exactly what an agent would send to the model.

## 13. Event metadata and CLI subcommands

**Answer:** token usage appears on a model event only if the model returns it; timing is limited to one wall-clock timestamp per event. The `adk` tool lists both `eval` and `conformance`. **Status: OBSERVED** (with a fake model supplying made-up usage numbers; real values need a real model).

Script: `q13_event_metadata.py`, with the fake model attaching `usage_metadata` to its response.

```text
--- event 1 (wf@1/writer@1) top-level keys: ['actions', 'author', 'content', 'id', 'invocation_id', 'model_version', 'node_info', 'timestamp', 'usage_metadata']
    usage_metadata: {'candidates_token_count': 7, 'prompt_token_count': 11, 'total_token_count': 18}
    model_version: fake-model-001
    timestamp: 1795215232.884212
--- event 2 (wf@1/after@1) top-level keys: ['actions', 'author', 'id', 'invocation_id', 'node_info', 'output', 'timestamp']
duration fields on Event: none
--- same run, model returns NO usage metadata
    usage_metadata on the agent event: None
```

| Metadata | Where it appears |
|---|---|
| `usage_metadata` (prompt, candidates and total token counts) | On LLM agent events, copied from the model response. `None` when the model sends none. Never on function-node events. |
| `model_version` | On LLM agent events, when the model sends it |
| `timestamp` | On every event (epoch seconds, set when the event is created) |
| `invocation_id`, `id`, `node_info.path` | On every event |
| Duration or latency | No such field. Step duration has to be derived from consecutive timestamps or taken from OpenTelemetry. |

CLI, from `--help` output only (nothing was evaluated):

| Command | What the help text says |
|---|---|
| `adk eval AGENT_MODULE_FILE_PATH [EVAL_SET_FILE_PATH_OR_ID]...` | Options: `--config_file_path`, `--num_runs`, `--parallelism` (default 4), `--print_detailed_results`, `--eval_storage_uri`, `--enable_features`, `--disable_features`, `--log_level` |
| `adk conformance record [PATHS]... {none\|sse\|bidi}` | Generates `generated-recordings.yaml` and `generated-session.yaml` next to each `spec.yaml`. Marked "NOTE: this is work in progress." |
| `adk conformance test [PATHS]...` | `replay` mode compares against recorded interactions; `live` mode is "not yet implemented" |
| `adk eval_set`, `adk test`, `adk optimize` | Also listed by `adk --help` |

## Comparison with google-adk 2.14.1

A second virtual environment was created on the same Python 3.14.10 with `uv pip install google-adk==2.14.1 pytest==9.2.0 pytest-asyncio==1.5.0`. All scripts were run unchanged through `run_all.sh` on both versions, and the recorded outputs were compared after masking UUIDs, timestamps, process IDs, durations and directory names (`compare_versions.py`).

Result: no script failed on 2.14.1, and every exit status matched 2.15.0. Of 33 recorded output files, 27 are identical after masking. The 6 that differ are the three files that print the version number or install log, and the three that run the approval gate with resumability switched on.

| # | Question | Result on 2.14.1 |
|---|---|---|
| 1 | Installation | Same: installs and imports with zero warnings; `adk, version 2.14.1`. Same dependency versions except `watchdog` 6.0.0 instead of 7.1.0. Same `Requires-Python: >=3.11` and classifiers. |
| 2 | Function-only workflow | Identical output, including both error messages and the dynamic workflow. |
| 3 | Custom `BaseAgent` | Identical: `_run_async_impl` executed in all three placements. |
| 4 | Deprecated workflow agents | Identical: same warning text, same run results. |
| 5 | Approval gate | Same behavior. Without resumability the output is identical, including resume from a new process with SQLite. With `is_resumable=True`, 2.14.1 emits one more checkpoint event per node transition (see below). |
| 6 | LLM to Python swap | Identical, including the typed and untyped downstream results. |
| 7 | Structured output | Identical in all 13 cases, including the unvalidated root agent without `output_key`. |
| 8 | Callbacks and `output_key` | Identical. |
| 9 | Plugin hooks | Identical hook sequences. |
| 10 | Function tool declarations | Identical JSON. |
| 11 | Artifacts | Identical layout, versions and metadata fields. |
| 12 | pytest | 5 passed, also with `-W error`. |
| 13 | Metadata and CLI help | Identical, including `--num_runs` and `--parallelism` on `adk eval`. |

The one behavioral difference, with resumability on:

```text
2.15.0  [03] write_spec@1 output
        [04] agent_state={'nodes': {'write_spec': {'status': 3}, 'approve_spec': {'status': 2}}}
        [05] approve_spec@1 function_call=adk_request_input

2.14.1  [03] write_spec@1 output
        [04] agent_state={'nodes': {'write_spec': {'status': 3}}}
        [05] agent_state={'nodes': {'write_spec': {'status': 3}, 'approve_spec': {'status': 2}}}
        [06] approve_spec@1 function_call=adk_request_input
```

2.14.1 writes the "node finished" checkpoint and the "next node started" checkpoint as two events; 2.15.0 merges them into one. A full pause-and-resume run stored 18 events on 2.14.1 and 16 on 2.15.0. Nodes executed, state, outputs and the resume call are the same. Code that counts events or indexes into the event list would see the difference; code that reads `node_info.path`, `output` and state would not.

Nothing used in these experiments is missing from 2.14.1. Two differences were noticed in the installed files but not exercised by any script:

- `google/adk/cli/built_in_agents/` exists in 2.14.1 and is absent in 2.15.0, matching the 2.15.0 release note about its removal.
- The evaluation code for pass@k aggregation (`_multi_run_aggregation_methods.py` and related files) exists only in 2.15.0.

## Where observed behavior contradicts the documentation or the two notes files

Each item held on both 2.15.0 and 2.14.1.

1. **Custom agent overrides are not bypassed.** The 2.0 migration page says the Workflow Graph engine "completely bypasses" `_run_async_impl()` overrides and that such calls are "silently ignored". Observed: the override ran as root agent, as workflow node and as LLM sub-agent (question 3). This settles the conflict flagged in both notes files in favor of the custom-agents page and the source reading in `adk_llm_to_python_migration.md`.
2. **A `before_agent_callback` that skips the agent does not need to write `output_key` itself.** `adk_llm_to_python_migration.md` infers that such a callback "must write the contract state key itself". Observed: the returned content is stored under `output_key`, and a value the callback writes to that key is overwritten by it (question 8).
3. **`output_schema` is not always enforced.** The LLM agents page says the final response "must be a JSON string conforming to this schema" and that Python validates it. Observed: a root agent with `output_schema` and no `output_key` returned non-JSON text as a normal event with no error (question 7). Validation ran only with `output_key` set or when the agent was a workflow node.
4. **Invalid structured output: the open question is now answered.** Both notes list this as unknown. Observed: `pydantic.ValidationError` raised, an error event, no retry, no event with the bad text; a per-node `RetryConfig` on the agent does retry (question 7).
5. **`DatabaseSessionService` is not available in a plain install.** `adk_core_best_practices.md` presents `DatabaseSessionService(db_url="sqlite+aiosqlite:///...")` as the SQLite option. Observed: importing it raises `ImportError` asking for `pip install google-adk[db]`. The class that works with core dependencies is `google.adk.sessions.sqlite_session_service.SqliteSessionService`, which is not exported from `google.adk.sessions`.
6. **Resumability configuration is not needed for `RequestInput`.** Both notes pair human-in-the-loop with `ResumabilityConfig(is_resumable=True)` and list the requirement as unknown. Observed: pause and resume work without it, in one process and across two with SQLite (question 5).
7. **The documented resume call does not answer a `RequestInput`.** The Resume page shows `runner.run_async(user_id=..., session_id=..., invocation_id=...)`. Observed: for a paused workflow that call yields 0 events without resumability and stays paused with it. The answer has to be a function response named `adk_request_input` carrying the interrupt ID; the invocation ID is inferred (question 5).
8. **A plain-text reply to a paused workflow restarts it.** Not stated in the docs or notes. Observed: the text starts a new invocation from `START`, overwrites state and raises a second pause, with no error (question 5).
9. **Two outputs from one node: the Python statement is the right one.** The data-handling page has two conflicting passages. Observed: `ValueError: Output already set. A node can produce at most one output.`, raised after the first output event has already been emitted (question 2).
10. **A custom agent node passes nothing to the next node by default.** `adk_llm_to_python_migration.md` suggests keeping custom agents as thin wrappers that can be re-hosted as workflow nodes. Observed: as a node the agent does not receive `node_input`, and the next node gets `None` unless the agent's event sets `output` (question 3).
11. **`--num_runs` and `--parallelism` are not new in 2.15.0.** `adk_llm_to_python_migration.md` attributes them to the 2.15.0 CLI. Observed: `adk eval --help` on 2.14.1 lists both with the same text. Only the pass@k aggregation code is new in 2.15.0.
12. **Python version floor.** The quickstart page says Python 3.10 or later. Observed package metadata: `Requires-Python: >=3.11`, classifiers 3.11 to 3.15, as `adk_core_best_practices.md` already concluded.

Statements in the notes that were confirmed by a run:

- The three workflow agents emit a deprecation warning at construction and still run (question 4).
- `output_key` with a Pydantic `output_schema` stores a `dict` (question 7).
- Function-node parameters other than `ctx` and `node_input` are bound from state by name, and a missing key raises `WorkflowDataError` (question 2).
- No agent, model or tool hook fires around a plain function node; only run-level hooks and `on_event_callback` (question 9).
- `Runner(plugins=...)` is deprecated in favor of `App(plugins=...)` (question 9).
- `T | None` without a default stays required; the docstring is the only description; `ToolContext` is hidden from the schema (question 10).
- `save_artifact` returns versions from 0, `load_artifact` returns `None` for a missing version, `user:` filenames are visible across sessions, and a missing artifact service raises `ValueError` (question 11).
- The scripted-model test pattern and `InMemoryRunner(node=...)` with `run_debug(..., quiet=True)` work as composed in the notes (question 12).
- `{artifact.name}` accepts a filename containing a dot, which the notes listed as unconfirmed (question 11).

## What could not be tested here

| Area | Why not |
|---|---|
| Anything a real model decides | No provider was called. Not covered: whether a real model obeys `response_schema`, how often it returns invalid JSON, the `set_model_response` fallback for `output_schema` combined with tools, streaming partial events, real `usage_metadata` values, provider retries and context caching. |
| `output_schema` together with `tools` | The fake model reports no support for that combination, and the fallback path needs a model that chooses to call the tool. |
| Evaluation and conformance runs | `adk eval`, `AgentEvaluator` and `adk conformance` need a model or existing recordings. Only `--help` was read. |
| `adk web`, `adk api_server`, `adk run` | Not started. How a `RequestInput` pause and its answer travel over `/run` and `/run_sse` is untested. |
| Recovery after a crash | Only a clean pause was resumed. Killing a process in the middle of a node, and what `ResumabilityConfig` adds in that case, was not tried. |
| `DatabaseSessionService`, Vertex AI and GCS services | The `db` extra and Google Cloud credentials were not installed or used. |
| Windows and Linux | Only macOS on Apple silicon. File artifact paths, SQLite file locking and the `PYTHONUTF8` advice for Windows are unverified. |
| Other Python versions | Only 3.14.10. |
| OpenTelemetry spans and metrics | No exporter was configured, so span names and per-node metrics were not observed. |
| Workflow features outside the question list | `JoinNode` fan-in, parallel workers, `require_confirmation` on nodes, tool confirmation, `task`-mode agents in a workflow, a node used as an agent tool, nested workflows, `state_schema`, YAML-defined graphs. |
| Live and bidirectional streaming | `run_live` needs a live model connection. |
| Unbounded graph cycles | The loop tests carry their own counter. Whether the engine ever stops a cycle on its own was not tested. |
| Deprecation warning visibility in imported modules | The warning was observed only for agents constructed in the script being run. |
