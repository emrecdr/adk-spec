# Google ADK 2.0 (`google-adk` v2.15.0) — Architecture & Best Practices Notes

- **Sources verified:** [`google/adk-python`](https://github.com/google/adk-python) (`v2.15.0`, released 2026-11-19; `src/google/adk/{__init__,runners,workflow/__init__,apps/__init__,apps/app,apps/_configs,agents/__init__,agents/llm_agent,agents/context,agents/readonly_context,agents/context_cache_config,events/__init__,models/__init__,planners/built_in_planner,sessions/__init__,sessions/sqlite_session_service,plugins/__init__,plugins/base_plugin,skills/__init__,telemetry/__init__,tools/base_toolset,tools/environment/*,tools/model_consult/__init__}.py`, `contributing/samples/workflows/{loop,request_input_rerun,node_as_tool,agent_in_workflow}/agent.py`, `docs/guides/{workflow,agents,apps,sessions,events,plugins,tools,environment,models,telemetry,artifacts,memory,cli,evaluation,integrations/model_armor,a2a}/*`).

---

## 1. Verified Public Imports Map (`google-adk 2.15.0`, Target Runtime: Python `3.14`)

ADK 2.0 (`google-adk` `2.15.0`, supporting Python 3.11–3.15 with companion `constraints-3.14.txt`) intentionally keeps the top-level package minimal and uses lazy submodule accessors. Using the wrong top-level import causes `ImportError` at module load time:

| Concept | Verified Import Path | Critical Caveat |
| --- | --- | --- |
| Top-level primitives | `from google.adk import Agent, Context, Event, Runner, Workflow` | `START` is **NOT** exported here |
| Graph & nodes | `from google.adk.workflow import BaseNode, DEFAULT_ROUTE, Edge, FunctionNode, JoinNode, Node, NodeTimeoutError, RetryConfig, START, Workflow, node` | Must import `START`, `node`, `JoinNode`, `RetryConfig` from `google.adk.workflow` |
| App & configs | `from google.adk.apps import App, ResumabilityConfig`<br>`from google.adk.apps.app import EventsCompactionConfig` | `EventsCompactionConfig` is in `google.adk.apps.app`, **not** `google.adk.apps` |
| Context caching | `from google.adk.agents.context_cache_config import ContextCacheConfig` | Submodule import |
| Agents & RunConfig | `from google.adk.agents import LlmAgent, BaseAgent, RunConfig`<br>`from google.adk.agents.run_config import RunConfig, StreamingMode, ToolThreadPoolConfig` | `Agent` is an alias for `LlmAgent` |
| Planners & thinking | `from google.adk.planners import BuiltInPlanner` | Configures per-agent `types.ThinkingConfig` budgets |
| Events & HITL | `from google.adk.events import Event, EventActions, RequestInput, get_active_events` | `RequestInput` is exported by both `google.adk.events` and `google.adk.events.request_input` |
| Models & Failover | `from google.adk.models import FallbackModel, Gemini, Claude, OpenAILlm, LiteLlm, ServiceTier, LLMRegistry` | Lazy provider imports; `gemma-4*` resolves to `Gemini` |
| Sessions & state | `from google.adk.sessions import BaseSessionService, BufferedSessionService, DatabaseSessionService, InMemorySessionService, Session, State, StateSchemaError`<br>`from google.adk.sessions.sqlite_session_service import SqliteSessionService` | `DatabaseSessionService` requires `[db]`/`sqlalchemy`; `SqliteSessionService` lives in submodule `sqlite_session_service` |
| Plugins | `from google.adk.plugins import BasePlugin, GlobalInstructionPlugin, ReflectAndRetryToolPlugin, ReflectAndRetryModelPlugin, ToolCallIntegrityPlugin, ContextFilterPlugin, AutoTracingPlugin, ForceEscalationPlugin, ModelConsultObservabilityPlugin` | Applied globally across the whole `App` tree |
| Model Armor security | `from google.adk.integrations.model_armor import ModelArmorConfig, ModelArmorPlugin` | Requires `pip install 'google-adk[gcp]'` and ADC credentials |
| Skills | `from google.adk.skills import Skill, SkillRegistry, load_skills_from_dir`<br>`from google.adk.tools.skill_toolset import SkillToolset` | `SkillToolset` is **not** exported by `google.adk.tools` |
| Environments | `from google.adk.environment import LocalEnvironment`<br>`from google.adk.tools.environment import EnvironmentToolset` | Swap `LocalEnvironment` for `E2B` / `Daytona` under `google.adk.integrations` |
| Model consult | `from google.adk.tools.model_consult import ModelConsultTool, ModelConsultContextConfig, ForceEscalationPlugin, ModelConsultObservabilityPlugin` | Gives fast executor models budgeted advisor escalation |
| Artifacts & Memory | `from google.adk.artifacts import InMemoryArtifactService`<br>`from google.adk.memory import InMemoryMemoryService`<br>`from google.adk.tools import load_memory` | Out-of-band large payloads (`ArtifactService`) and cross-session recall (`BaseMemoryService`) |
| Telemetry & Privacy | `from google.adk.telemetry import ContentCapturingMode, TelemetryConfig` | Controls prompt/response span capture |
| Web / FastAPI | `from google.adk.cli.fast_api import get_fast_api_app` | Keyword-only `agents_dir=...` (plural); `agent_dir` raises `TypeError` |
| Tools & Matchers | `from google.adk.tools import FunctionTool, LongRunningFunctionTool`<br>`from google.adk.tools.tool_args_matcher import ToolArgsMatcher` | `ToolArgsMatcher` supports per-arg eval matching |
| A2A federation | `from google.adk.a2a.utils.agent_to_a2a import to_a2a` | Nested module, not re-exported anywhere; returns `Starlette` app (counterpart `RemoteA2aAgent`) |
| MCP publishing | `from google.adk.tools.mcp_tool import to_mcp_server` | Exposes an agent/workflow as a `FastMCP`/`MCPServer` tool |
| Evaluation | `from google.adk.evaluation import AgentEvaluator` | Only symbol exported by `google.adk.evaluation` |

### 1.1 Python 3.14 & Latest Dependency Compatibility Notes (Verified 2026-11-20)

- **Target Runtime:** **Python 3.14** (`cpython-3.14.10`, `requires-python = ">=3.14,<3.15"`). `google-adk` `2.15.0` officially publishes the `Programming Language :: Python :: 3.14` classifier and a companion `constraints-3.14.txt` lock file.
- **`google-genai` Version Ceiling (`>=2.34,<3`):** Although `google-genai` `3.6.1` is published on PyPI, `google-adk` `2.15.0` explicitly bounds `google-genai>=2.34,<3` (`constraints-3.14.txt` pins `2.34.0`). Do **not** force `google-genai>=3` in `pyproject.toml`; let `google-adk` control `google-genai<3` until ADK releases v3 compatibility.
- **MCP SDK 2.x (`mcp` `2.3.0`):** Satisfies ADK's `mcp` extra (`>=1.24,<3`, excluding `aiohttp!=3.14.2`). Note that MCP SDK 2.x uses `mcp.server.mcpserver.MCPServer` rather than SDK 1.x `FastMCP` (handled internally by `to_mcp_server`).
- **AG-UI & A2UI Ecosystem (`ag-ui-adk` `0.13.0`):** Compatible with `google-adk>=1.28.1,<3.0.0`, pins `ag-ui-protocol>=1.0.0`, and automatically pulls `ag-ui-a2ui-toolkit>=0.0.6`.
- **Python 3.14 Synergy (PEP 649 / PEP 749 & PEP 750):**
  - **PEP 649 (Deferred Annotation Evaluation):** Forward references and complex Pydantic `2.14.4` / ADK `@node` `TypeAdapter` type hints work natively without `from __future__ import annotations` boilerplate; use stdlib `annotationlib` for custom introspection.
  - **PEP 750 (`t-strings` / `string.templatelib.Template`):** Separates static literal segments from interpolated runtime values—ideal for injection-safe prompt `<untrusted_data>` wrapping, Markdown rendering, and ANSI-safe TUI escaping.
- **`adk_review` Tooling & Proxy Conventions:**
  - **`pyrefly` (`1.5.0`) + ADK `LlmAgent`:** ADK declares `LlmAgent(BaseAgent, abc.ABC)` with no abstract method, so projects checking with `pyrefly` MUST set `[tool.pyrefly.errors] direct-abstract-base-instantiation = "ignore"`.
  - **`adk web --no_use_local_storage .`:** Keeps interactive dev sessions in memory so unredacted code diffs and credentials aren't persisted silently into `.adk/session.db`.
  - **`truststore` (`0.10.5`):** Inject OS certificate trust verification before constructing HTTP/LLM clients so corporate TLS proxies work seamlessly.

---

## 2. Graph-First `Workflow` Runtime & The 10 Validation Rules

ADK 2.0's `Workflow` is a directed execution graph (also itself a `BaseNode`, so workflows nest cleanly). A `NodeLike` can be a plain Python function (auto-wrapped in `FunctionNode`), `Agent`/`LlmAgent`, `BaseTool`, `JoinNode`, or another `Workflow`.

### Graph Syntax & Routing

- **Chain tuples:** `edges=[(START, step_a, (branch_b, branch_c), join_node, finalize)]` automatically runs independent branches concurrently when predecessors finish.
- **Conditional routing maps:**
  ```python
  from google.adk.workflow import DEFAULT_ROUTE, START
  edges = [(START, validator, {"ok": next_step, "fix": retry_step, DEFAULT_ROUTE: fallback})]
  ```
  Nodes emit routes via `Event(route="ok")` (or return/yield objects carrying a route).
- **Explicit `Edge` objects:** `Edge(from_node=START, to_node=step_a, route=...)` requires `BaseNode` instances (wrap functions with `@node()` or `FunctionNode`) and the `START` object (not `"START"`).

### The 10 Compile-Time Graph Validation Rules (Checked on `Workflow(...)` Instantiation)

1. **Unique node names:** Distinct objects cannot share a `name` (valid Python identifier `str.isidentifier()`, no hyphens). Reuse the *exact same object* to create a loop back to a step, or clone with `node(existing, name="new_name")`.
2. **`START` present with no incoming edges.**
3. **Edges leaving `START` carry no route** (put dynamic branching in a node right after `START`).
4. **Reachability:** Every node must be reachable from `START`.
5. **No duplicate edges** (cannot mix unconditional and duplicate routes between the same pair).
6. **Edge endpoint & terminal rules:** Multiple terminal nodes producing non-`None` output raise `WorkflowConfigurationError` — always converge parallel fan-outs into a `JoinNode`.
7. **No unconditional cycles:** Iteration loops (`A -> B -> A`) are valid **only** when the back-edge carries a conditional `route`.
8. **Static schema matching:** If a predecessor defines `output_schema` and its successor defines `input_schema`, **they must be equal** at construction time.
   - *Key migration superpower:* Swapping an `LlmAgent(input_schema=In, output_schema=Out)` for a Python `@node def fn(node_input: In) -> Out:` leaves all graph edges and compile-time checks 100% valid.
9. **Chat agent wiring:** An `LlmAgent(mode="chat")` may **only** follow `START`; mid-graph LLM steps must use `mode="single_turn"` or `mode="task"`.
10. **Node-specific outgoing edge checks:** Specialized nodes with fixed routes reject invalid/unhandled routes unless `DEFAULT_ROUTE` or an unconditional edge is present.

---

## 3. Critical `FunctionNode` / `@node` / `JoinNode` Mechanics

- **`@node(...)` kwargs vs. constructor kwargs:**
  - `@node(...)` accepts `name`, `rerun_on_resume`, `retry_config`, `timeout`, `auth_config`, `require_confirmation`, `parameter_binding`, `parallel_worker`, `max_parallel_workers`.
  - **Gotcha:** Passing `input_schema=`, `output_schema=`, or `state_schema=` to `@node(...)` raises `TypeError`! For function nodes, `input_schema` and `output_schema` are automatically inferred from `node_input` and return type hints via Pydantic `TypeAdapter` (including automatic `types.Content` -> `str` extraction when hinted `str`). Use `FunctionNode(func=..., state_schema=...)` or `BaseNode` subclass constructors if `state_schema` is needed.
- **Parameter resolution (`parameter_binding`):**
  - `'state'` (default): `ctx: Context` gets context, `node_input` gets predecessor output, and any other parameter name is looked up in `ctx.state` (raises `WorkflowDataError` if missing and no default exists).
  - `'node_input'`: unpacks `node_input` dict/Pydantic keys into parameters and exposes inferred schemas so the node can be passed directly as an agent tool (`NodeTool`).
- **Fan-out & `parallel_worker`:**
  - `@node(parallel_worker=True, max_parallel_workers=4)` or `Agent(..., parallel_worker=True, max_parallel_workers=4)` maps over a `list` concurrently, preserves input order, forces `rerun_on_resume=True`, and scopes `retry_config` **per item** (the lowest-index failure surfaces deterministically).
- **`JoinNode` validation semantics:**
  - `JoinNode` aggregates predecessors into `dict[node_name, output]` and merges parallel branch contexts back into the parent branch.
  - **Gotcha:** `JoinNode(input_schema=MyModel)` validates **each branch's output individually**, not the aggregated dict—and raw dict/JSON schemas are not enforced, so pass a Pydantic `BaseModel`.
- **`RetryConfig` defaults & inheritance:**
  - Defaults at runtime: `max_attempts=5`, `initial_delay=1.0`, `max_delay=60.0`, `backoff_factor=2.0`, `jitter=1.0` (skips `WorkflowConfigurationError` and `WorkflowInvariantError`). Setting `retry_config` on a `Workflow` cascades to child nodes without their own policy.
- **Sync I/O offloading:** Setting `tool_thread_pool_config` in `RunConfig` offloads synchronous functions and sync generators off the async event loop.

---

## 4. `LlmAgent` Modes, Instruction Splitting & Planners

### 4.1 Execution Modes (`chat`, `task`, `single_turn`)

| Mode | History Visibility | Termination & Output | Best Role in Spec Framework |
| --- | --- | --- | --- |
| **`chat`** | Full session history | Conversational replies + peer transfers | Top-level `SpecCoordinator` right after `START`; freeform `explore` partner |
| **`task`** | Isolated sub-branch; pauses & resumes multi-turn with user | Must call built-in `finish_task(output=...)`, auto-validated & retried against `output_schema` | `propose`, `clarify` (asks ≤ 5 questions across turns), interactive `apply` |
| **`single_turn`** | `include_contents="none"` (default inside `Workflow`) | Single structured/text output; exposed as a functional tool if nested as `sub_agent` | `specify`, `design`, `tasks`, `analyze`, `verify`/`converge` |

### 4.2 `static_instruction` vs. `instruction`, Joint `tools` + `output_schema`, & `BuiltInPlanner`

- **`static_instruction` vs. `instruction` (`docs/guides/agents/llm_agent/index.md`):**
  - `static_instruction`: Immutable system-level content containing **no `{placeholder}` variables** (e.g., constitution rules, EARS grammar, role contract). Placed at the very beginning of `system_instruction` so Gemini prefix caching hits consistently—and **explicitly required** by `GEPARootAgentPromptOptimizer` (`require_static_instruction`).
  - `instruction`: Dynamic per-turn template evaluated with `{change_id}` or optional `{feedback?}`, appended after `static_instruction`.
- **Joint `tools` + `output_schema`:** ADK 2.0 supports combining arbitrary `tools` and a Pydantic `output_schema` on the same `LlmAgent`—the agent loops through tool calls freely and ADK validates the final model response against `output_schema`.
- **`BuiltInPlanner(thinking_config=types.ThinkingConfig(...))`:** Assign stage-appropriate thinking budgets (`thinking_budget=0` or low on formatting steps, higher budgets on `Design`, `Clarify`, and `SemanticAudit`).

---

## 5. Human-in-the-Loop (HITL), Durable Resumability & State Scopes

### `RequestInput` & `ResumabilityConfig`

- Yielding `RequestInput(interrupt_id=..., message=..., response_schema=PydanticModel)` pauses the workflow and emits an `adk_request_input` function call containing JSON Schema for the UI/client.
- With `ResumabilityConfig(is_resumable=True)` on `App` (plus a persistent session service like `SqliteSessionService` or `DatabaseSessionService`), ADK records checkpoints and **replays completed upstream nodes from session history without re-running them**.
- **Loop & rerun gotchas:**
  - Nodes acting on the answer (or running inside a loop) must set `@node(rerun_on_resume=True)`, read `ctx.resume_inputs[interrupt_id]`, and use deterministic loop-scoped IDs: `f"review_{ctx.invocation_id}_{ctx.run_id}"`.
  - `Runner` raises `ValueError` if a resuming `new_message` mixes `FunctionResponse` and plain text—put comments inside the structured response payload.

### `ToolConfirmation`

- `FunctionTool(fn, require_confirmation=True)` or dynamic `ctx.request_confirmation()` emits `adk_request_confirmation` with `originalFunctionCall` and `toolConfirmation.hint`, pausing execution until approved (`confirmed: True`).

### Four Scopes of `State` (`ctx.state`)

Writes are persisted durably via `EventActions(state_delta=...)` (or `yield Event(state={...})` in workflow nodes):
- **Session scope (unprefixed, e.g., `change_id`):** Private to one session.
- **`app:` (`State.APP_PREFIX`):** Shared across all sessions of the app (e.g., cached `constitution`, `config`).
- **`user:` (`State.USER_PREFIX`):** Shared across all sessions of a user in the app (e.g., preferred profile/model).
- **`temp:` (`State.TEMP_PREFIX`):** Current invocation scratchpad; never persisted.

---

## 6. Runtime Plugins, Cost Control, Environments & Least-Privilege Tools

1. **Application-Wide `BasePlugin`:**
   - Hooks `on_user_message_callback`, `before_run_callback`, `before_agent_callback`, `before_model_callback`, `after_model_callback`, `before_tool_callback`, `after_tool_callback`, `on_event_callback`, `after_run_callback`, and error callbacks across the entire agent tree.
   - Registered plugins run in registration order and precede agent-level callbacks; returning a non-`None` value short-circuits remaining plugins and agent callbacks.
2. **Skill Progressive Disclosure (`SkillToolset`):**
   - Loads `SKILL.md` directories dynamically (`load_skills_from_dir`), keeping only name + description in system prompts until `load_skill` / `load_skill_resource` / `run_skill_script` are invoked. Supports skill-scoped `adk_additional_tools`.
3. **Executor + Budgeted Reasoning Advisor (`ModelConsultTool`):**
   - Allows fast/cheap executor models to call `model_consult` for a tool-less advisor turn (`gemini-3.1-pro-preview`, configurable `thinking_level`, `max_uses` per turn, `session_max_uses`, never raising exceptions back to the loop).
   - Pair with `ForceEscalationPlugin` and `ModelConsultObservabilityPlugin` for telemetry (`usage`, `latency_ms`, consult budget stats).
4. **Context Caching & Session Compaction (`App`):**
   - `ContextCacheConfig(cache_intervals=..., ttl_seconds=..., min_tokens=...)` caches shared prefixes starting at turn 2+ (requires `2048` min tokens on Gemini 2.5 or `4096` on Gemini 3; no-op on Gemini 4; single-turn needs `cached_content`).
   - `EventsCompactionConfig(compaction_interval=..., overlap_size=...)` summarizes old events into `EventCompaction` markers without deleting audit history.
5. **Pluggable Sandboxed Environments (`EnvironmentToolset` Exact Contracts & `tool_filter`):**
   - Wraps `BaseEnvironment` (`LocalEnvironment(working_dir=...)`, or cloud `E2B`/`Daytona` under `google.adk.integrations`), and backs `run_skill_script` in `SkillToolset`.
   - **Verified exact tool names & arguments (`src/google/adk/tools/environment/_*_tool.py`):**
     - `ReadFile(path, start_line?, end_line?)`
     - `WriteFile(path, content)`
     - `EditFile(path, old_string, new_string)`
     - `Execute(command)`
   - **Least-privilege via `BaseToolset.tool_filter`:** Filter tools at declaration time (`tool_filter=lambda tool, ctx: tool.name == "ReadFile"`) on read-only agents (`explore`, `analyze`) so `WriteFile`, `EditFile`, and `Execute` are never exposed to the LLM at all—providing defense-in-depth alongside runtime `WritePolicyPlugin` hooks.
6. **Evaluation & Automated Prompt Optimization:**
   - `AgentEvaluator` + `adk eval` scores `tool_trajectory_avg_score`, ROUGE-1 `response_match_score`, semantic `final_response_match_v2`, and rubric criteria inside `pytest`.
   - `google.adk.optimization` ships `GEPARootAgentPromptOptimizer` (`GEPARootAgentPromptOptimizerConfig`, requires `static_instruction`) and `SimplePromptOptimizer`.

---

## 7. Stability, Resilience & Performance Controls

### 7.1 Model Failover (`FallbackModel`)

`FallbackModel` wraps an ordered list of models (`str` IDs or `BaseLlm` instances like `Gemini(model=..., retry_options=types.HttpRetryOptions(attempts=3))`) and falls back on 429/503 outages. Before switching to the backup model, ADK rolls back in-place mutations on the `LlmRequest` so fallback calls remain clean and provider imports remain lazy until needed.

### 7.2 Self-Healing & Integrity Plugin Stack

- **`ReflectAndRetryToolPlugin(max_retries=3)`:** Uses a concurrency-safe per-tool consecutive failure counter; converts tool exceptions or error dicts (`extract_error_from_result`) into structured reflection prompts so the model self-corrects rather than crashing the workflow.
- **`ReflectAndRetryModelPlugin`:** Recovers from `FinishReason.MALFORMED_FUNCTION_CALL`, safety blocks, and recitation blocks via injected reflection turns.
- **`ToolCallIntegrityPlugin(secret_key=...)`:** Stamps every stored function call with HMAC-SHA256 and verifies the signature before resumed execution (guarding `adk_request_confirmation`, `adk_request_input`, and resumable tool checkpoints against session-store tampering).
  - **Verified limitation:** Protects agent-invoked tools; tools mounted *directly* as standalone workflow nodes are not checked by this plugin.

### 7.3 `RunConfig` Operational Controls

`RunConfig` scopes per-invocation execution controls cleanly without hardcoding them onto agents:
- **`max_llm_calls`:** Hard circuit breaker against infinite tool loops (shared across transferred sub-agents; counted independently per `AgentTool` nested run).
- **`streaming_mode=StreamingMode.SSE`:** Emits progressive `event.partial=True` text chunks and partial function-call arguments for responsive UIs, followed by one persisted `event.partial=False` aggregate event.
- **`tool_thread_pool_config=ToolThreadPoolConfig(max_workers=4)`:** Moves synchronous functions, synchronous generators, and synchronous `require_confirmation` callables off the asyncio event loop so blocking git/lint/parser calls don't stall parallel workflow branches.
- **`service_tier=ServiceTier.DEFERRED`:** Submits background batch work (CI spec-drift audits, nightly regression evals) to off-peak capacity. **Verified requirement:** Only applies when the agent's model sets `Gemini(use_interactions_api=True)`; otherwise ADK silently drops the tier with a warning log.

### 7.4 `BufferedSessionService`

Wraps `DatabaseSessionService` / `SqliteSessionService` with an ordered background writer so parallel `[P]` workers and high-frequency turns don't pay synchronous DB round trips on every `append_event`.
- **Mandatory lifecycle rule (`docs/guides/sessions/buffered_session_service/index.md`):** `Runner` does **not** flush the buffer automatically yet. Callers **MUST** invoke `await session_service.flush_session(app_name=..., user_id=..., session_id=...)` after each run and `close()` on shutdown.

---

## 8. Enterprise Privacy, Telemetry, Artifacts & Long-Term Memory

### 8.1 CRITICAL Privacy Default (`TelemetryConfig`)

From `docs/guides/telemetry/telemetry_config/index.md`:
- **Out of the box, `ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS` defaults to `True`** (`should_add_content_to_legacy_spans=True`). Every full prompt, source-code context snippet, tool argument, and tool response is written onto `call_llm` spans (`gcp.vertex.agent.llm_request`) and shipped to whatever OTLP/Cloud Trace exporter is configured.
- **Required production hardening:** Disable prompt capture globally via `ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=false` or per-run via:
  ```python
  from google.adk.agents.run_config import RunConfig
  from google.adk.telemetry import ContentCapturingMode, TelemetryConfig

  run_config = RunConfig(
      telemetry=TelemetryConfig(capture_message_content=ContentCapturingMode.NO_CONTENT)
  )
  ```

### 8.2 Out-of-Band Payloads (`ArtifactService`) & Cross-Session Recall (`BaseMemoryService`)

- **`ArtifactService` (`ctx.save_artifact` / `ctx.load_artifact`):** Stores bulky Markdown reports, diffs, and evidence bundles as versioned `types.Part` blobs (`types.Part.from_bytes(...)`), returning only `{filename, version}` handles into the model prompt so context windows stay fast and clean.
- **`BaseMemoryService` (`add_session_to_memory`, `search_memory`):** Ingests completed change sessions and lets future sessions search historical architectural decisions, past review rejections, and codebase quirks via `load_memory` / `preload_memory` tools.

---

## 9. Verified ADK 2.0 Coding Idioms & Web / AG-UI Serving

### 9.1 Idioms from `contributing/samples/workflows/`

- **State + Route shorthand in workflow nodes:** `yield Event(state={"feedback": resume_input}, route="revise")` mutates session state and emits the conditional edge route atomically.
- **Optional template placeholders in instructions:** `"{feedback?}"` injects state only when present without throwing missing-key errors on first pass.
- **Small-schema `NodeTool` typing rule (`node_as_tool/agent.py`):** When a `@node` generator yields intermediate `Event` / `RequestInput` control objects and will also be exposed as a `NodeTool`, annotate the yield type with **only the final data type** (e.g., `-> Generator[str, None, None]`), keeping the tool response schema small.
- **Verified `Context` / `ReadonlyContext` inspection attributes:** `agent_name`, `invocation_id`, `user_id`, `run_config`, `is_aborted`, `node`, `node_path`, `run_id`, `attempt_count`, `resume_inputs`, `tool_confirmation`, `state`, `actions`, `session`.

### 9.2 FastAPI, `adk web`, AG-UI 1.0 & A2UI Serving

- **Custom ASGI App (`google.adk.cli.fast_api.get_fast_api_app`):** Returns the full ADK `FastAPI` instance (`web=False` for hardened production routes without dev UI, `web=True` for `DevServer`), auto-providing `/health` and `/version`, A2A routes, and `services.py`/`services.yaml` loading—allowing custom auth middleware and `/api/spec/*` routes on the same process. Remember: parameter is `agents_dir=` (plural).
- **AG-UI 1.0 + A2UI Workbench Stack:** Wrap the ADK `root_agent` via `ag_ui_adk` (`ADKAgent` + `add_adk_fastapi_endpoint`) to stream standardized AG-UI bi-directional SSE events, thread state sync, and HITL interrupt/resume payloads to React/Next.js frontends (e.g., CopilotKit) rendering declarative **A2UI** JSON surfaces mapped onto a trusted host component catalog.
- **MCP Server (`to_mcp_server`):** Exposes the entire agent/workflow as a single MCP tool (`stdio` or `streamable-http`) forwarding non-final text as progress notifications with per-connection session continuity.

---

## 10. Security Screening (`ModelArmorPlugin`), Time-Travel Rewind, Efficiency Evals & A2A

### 10.1 Prompt-Injection Screening via `ModelArmorPlugin` (`docs/guides/integrations/model_armor/index.md`)

`ModelArmorPlugin(config=ModelArmorConfig(prompt_template_name=..., response_template_name=...))` screens user inputs (`before_model_callback`), model outputs (`after_model_callback`), and **tool outputs (`after_tool_callback`)** against Google Cloud Model Armor policies.
- **Why this matters for coding/spec agents:** Screening `after_tool_callback` catches **indirect prompt injection** hidden inside untrusted repository READMEs, issues, or PR diffs before the payload re-enters the model context.
- Screening failures fail closed by default; blocked inputs/outputs carry `custom_metadata['model_armor_blocked']`, while blocked tool outputs return `{'error': ...}` to the agent.

### 10.2 Time-Travel Rollback via `Runner.rewind_async`

`Runner.rewind_async(user_id=..., session_id=..., rewind_before_invocation_id=...)` replays state and artifact deltas from session start up to the target invocation boundary, enabling clean **undo / branch from earlier spec step** semantics directly in CLI and Web UIs without losing audit history.

### 10.3 Built-In Efficiency Evaluators & `ToolArgsMatcher`

- **Efficiency Metrics (`docs/guides/evaluation/efficiency_evaluators/index.md`):** Reported automatically on every `adk eval` run with zero extra configuration (informational, reference-free):
  - `tool_call_count_v1` (tool invocations per turn)
  - `inference_call_count_v1` (model calls per turn)
  - `token_usage_v1` (total + per-type token breakdown)
  - `invocation_duration_v1` (wall-clock seconds)
  These provide built-in telemetry to verify every Phase 2–4 Python migration reduces token/inference spend.
- **`ToolArgsMatcher` (`docs/guides/tools/tool_args_matcher/tool_args_matcher/index.md`):** Replaces brittle `==` tool-arg checks in evals with per-argument strategies (`casefold`, `numeric` tolerance, `ignore`, custom/model matchers), running deterministic matchers first with `short_circuit=True`.

### 10.4 A2A Multi-Team Spec Federation (`to_a2a` & `RemoteA2aAgent`)

`from google.adk.a2a.utils.agent_to_a2a import to_a2a` turns any ADK agent or `Workflow` into a Starlette HTTP JSON-RPC + Agent Card service (`to_a2a(root_agent, port=8001)`). Combined with `RemoteA2aAgent`, a platform team's Spec Store agent can publish shared contracts and capability specs for downstream service teams to query over A2A without merging repositories.

---

## 11. Dual-Arm Provider Support (GitHub Copilot + Gemini) & Windows/macOS Engineering

Verified directly from `google-adk` `2.15.0` (`lite_llm.py`, `built_in_planner.py`, `_local_environment.py`) and `adk_review/` (`judge/config.py`, `judge/settings.py`, `login.py`):

### 11.1 GitHub Copilot (`LiteLlm`) vs. Gemini Feature Compatibility

| ADK 2.0 Feature | Native Gemini Arm | GitHub Copilot (`LiteLlm`) Arm | Required Engineering Guard |
| --- | --- | --- | --- |
| `Workflow`, `JoinNode`, `RequestInput`, `ToolConfirmation`, `Runner.rewind_async` | Full support | Full support | Identical orchestration across both arms |
| `FallbackModel` + `ModelConsultTool` + `SkillToolset` + `AgentEvaluator` | Full support | Full support | Configure `ModelConsultTool` using a model available on the active arm |
| `BasePlugin`, `WritePolicyPlugin`, `ReflectAndRetry{Tool,Model}Plugin`, `ToolCallIntegrityPlugin` | Full support | Full support | Always attach `logging.getLogger("LiteLLM").addFilter(_HideBearer)` so `Bearer` tokens in `extra_headers` aren't printed by `adk web -v` |
| `BuiltInPlanner(thinking_config=...)` | Supported (`Gemini`) | **Errors on non-thinking models** | **MUST guard behind `provider == "gemini"`** (`built_in_planner.py` warns models without thinking fail) |
| `ContextCacheConfig` / `ServiceTier.DEFERRED` / `ModelArmorPlugin` | Supported (`Gemini`/Vertex) | Ignored or Gemini-only | Gate `ContextCacheConfig`/`ServiceTier.DEFERRED`/`ModelArmorPlugin` to Gemini/GCP configurations |

### 11.2 Verified GitHub Copilot (`LiteLlm`) Rules (from `adk_review`)

- **Lightweight `settings.py` vs. lazy `models.py`:** Keep `settings.py` free of ADK/LiteLLM imports so CLI help, rule-only runs, and `adk-spec-login` start instantly (`~0.05s` vs `~0.32s`).
- **OAuth Device Flow (`adk-spec-login`):** LiteLLM's built-in device-flow poll times out in ~60s; provide a dedicated login CLI polling GitHub's ~15-minute window, writing to `GITHUB_COPILOT_TOKEN_DIR` (`~/.config/litellm/github_copilot`) with `os.umask(0o077)` and `0o600`/`0o700` POSIX permissions, expanding `~` via `pin_copilot_dir()`, and supporting GitHub Enterprise Cloud (`*.ghe.com`) endpoints (`GITHUB_COPILOT_API_BASE`, `GITHUB_COPILOT_DEVICE_CODE_URL`, `GITHUB_COPILOT_ACCESS_TOKEN_URL`, `GITHUB_COPILOT_API_KEY_URL`).
- **Required LiteLLM Configuration:**
  - `LITELLM_LOCAL_MODEL_COST_MAP=True` (prevents network cost-map fetch on every import).
  - `litellm.suppress_debug_info = True`
  - `litellm.disable_copilot_system_to_assistant = True` (sends agent instructions as a true `system` turn rather than rewriting them as an `assistant` turn).
  - Pass `_skip_mcp_handler=True` on `LiteLlm(model="github_copilot/<name>", ...)` so tool-carrying calls don't crash importing LiteLLM proxy's `mcp` dependency.
  - Inject `truststore.inject_into_ssl()` before building HTTP/LLM clients so corporate Windows/macOS proxies re-signing HTTPS work cleanly.
  - Validate temperature/reasoning constraints offline (`require_ready`): Copilot reasoning-by-default models (e.g., o-series) cannot run at `temperature=0`, whereas Gemini 3 warns against looping below `temperature=1.0`.
  - Detect Vertex AI vs. AI Studio via `google.adk.utils.env_utils.is_enterprise_mode_enabled()` (`GOOGLE_GENAI_USE_ENTERPRISE`).

### 11.3 ADK `LocalEnvironment` Windows Caveats (`_local_environment.py`)

Inspected directly in `src/google/adk/environment/_local_environment.py`:
- `LocalEnvironment.execute()` uses `asyncio.create_subprocess_shell` (`cmd.exe` on Windows vs. `/bin/sh` on macOS/Linux) and notes explicitly: *"Ignored on Windows, as `os.killpg` is."* On Windows timeouts, descendant processes can outlive `proc.terminate()`.
- **Mitigation:** Prefer pure-Python domain tools and argv-list `subprocess.run(..., encoding="utf-8")` (no shell!) resolving `git`/`pytest`/`ruff`/`pyrefly` by **full path from absolute `PATH` entries only** (never CWD), and use `taskkill /F /T /PID` on Windows process-tree timeouts.
