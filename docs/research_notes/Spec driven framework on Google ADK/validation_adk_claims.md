# Validation of the ADK claims in the secondary documents

Validator output. The three documents were checked against primary sources only; none of them was used as evidence for itself. Nothing from `google-adk` was installed or executed: every verdict comes from reading source, package metadata and the repository at the release tag.

## 1. What this was validated against

| Item | Value |
| --- | --- |
| Package | `google-adk` **2.15.0**, the latest release on PyPI when checked (re-queried 2026-11-20, after the snapshot) |
| Release date | CHANGELOG heading: 2026-11-19. PyPI upload: 2026-11-20T00:30:35Z (wheel), 00:30:39Z (sdist) |
| Python support | `Requires-Python: >=3.11`; classifiers 3.11, 3.12, 3.13, 3.14, 3.15 |
| Does the claimed version match? | Yes. All three documents say 2.15.0 and that is the current release |
| Source read | Unpacked wheel at `<scratchpad>/adk_dl/whl/google/adk/` (`dist-info/METADATA` says `Version: 2.15.0`; wheel sha256 `0b50fcc5…` equals the digest in `adk_dl/pypi.json`). Paths below are relative to that `adk/` folder |
| Repository at tag | `google/adk-python` tree at `v2.15.0` (3,896 paths) plus 40 files fetched from `raw.githubusercontent.com/google/adk-python/v2.15.0/…` into `<scratchpad>/val2_fetch_gh/`: `constraints-3.14.txt`, `pyproject.toml`, `docs/guides/**/index.md`, `contributing/samples/workflows/*/agent.py`. Cited as `guide:` or `sample:` |
| Other packages | PyPI JSON for 34 packages in `<scratchpad>/val2_fetch_pypi/`; `ag-ui-adk` 0.13.0 and `litellm` 1.110.2 wheels read (not installed) for symbol names; uv settings reference for `exclude-newer` |
| Documents | Frozen snapshot of 2026-11-20 23:16 CET under `<scratchpad>/secondary-snapshot/` (all nine SHA-256 sums verified) |

`<scratchpad>` is `<scratch>`.

Not checked: runtime behaviour (nothing was run), the local `adk_review` project the documents cite, and the frontend (npm) versions.

## 2. Reliability verdict per file

| File | Verdict | Confirmed | Wrong | Partly right | Outdated | Unverifiable |
| --- | --- | --- | --- | --- | --- | --- |
| A. `research_notes/03-google-adk-v2-best-practices.md` (validated fully) | **Reliable for import paths and signatures; not reliable on four behaviour claims.** Every import path in its map resolves in 2.15.0. Four claims are false, and one of them (tool filtering) carries the security design | 91 | 4 | 9 | 0 | 5 |
| B. `reports/02-adk-spec-framework-architecture-and-roadmap.md` (ADK usage, code, versions) | **The code skeleton imports cleanly, but the plan is not safe to build on as written.** The read-only guarantee rests on a filter that does nothing, the `litellm` pin is outside ADK's declared range, and the reference `pyproject.toml` cannot resolve on the snapshot date | 35 | 7 | 7 | 0 | 1 |
| C. `research_notes/04-validation-audit-and-improvement-options.md` (ADK rows only) | **Mostly accurate, but it certifies two of the same errors as "verified".** Its audit log is where the tool-filter and GEPA claims are declared checked | 24 | 3 | 5 | 0 | 1 |

The counts are rows in the tables of section 5 (109, 50 and 33 rows), so a root error repeated in several places is counted each time. Distinct root errors behind the WRONG rows: four in A (tool filter, GEPA requirement, retry cascade, rule 6), four in B (tool filter in four places, `litellm` pin, GEPA, `exclude-newer`), two in C (tool filter twice, GEPA).

No claim was OUTDATED: the documents describe the current release, so the errors are misreadings rather than stale facts.

The documents call many features "verified" without their stability level. In 2.15.0 these are marked experimental in source: `FallbackModel`, `BufferedSessionService`, `ToolArgsMatcher`, `GEPARootAgentPromptOptimizer`, and `RunConfig.telemetry` / `TelemetryConfig`. None of the checked features is deprecated, except that `GOOGLE_GENAI_USE_VERTEXAI` is deprecated in favour of the `GOOGLE_GENAI_USE_ENTERPRISE` variable the documents already use.

## 3. The errors that matter most to an implementer

1. **`EnvironmentToolset(tool_filter=...)` does not filter anything.** `BaseToolset` only stores the filter; each toolset must apply it in its own `get_tools`. `EnvironmentToolset.get_tools` returns `Execute`, `ReadFile`, `EditFile` and `WriteFile` unconditionally (`tools/environment/_environment_toolset.py:107-118`), and the agent flow calls `get_tools_with_prefix`, which does not filter either (`tools/base_toolset.py:134-158`, `agents/llm_agent.py:205`). The official guide says so directly: "it does not apply the filter for you … a caller who passes `tool_filter` to your toolset still receives every tool" (guide: `docs/guides/tools/base_toolset/index.md:87-92`). So `make_readonly_env_toolset()` in report B hands the "read-only" auditor a shell. Fix: subclass and filter in `get_tools` with `self._is_tool_selected(tool, readonly_context)`, or give read-only agents a hand-written read tool.
2. **`GEPARootAgentPromptOptimizer` does not require or use `static_instruction`.** `require_static_instruction()` checks that `agent.instruction` is a plain `str` rather than a callable (`optimization/_gepa_utils.py:32-41`), and the optimizer writes its result back to `instruction` (`optimization/gepa_root_agent_prompt_optimizer.py:145`, `:340`). Under the proposed split (rules in `static_instruction`, a `{change_id}` template in `instruction`), GEPA would rewrite the template and never touch the rules.
3. **`litellm==1.110.2` is outside ADK's declared range.** ADK 2.15.0 declares `litellm>=1.84,<1.106.3` in the `all`, `extensions` and `test` extras (`pyproject.toml:121`, `:241`, `:390`), with the comment "1.107.0 was a compromised release; raise only after checking the new release is clean" (`:241`), and its own lock uses 1.95.0 (`constraints-3.14.txt:901`). The pin installs only because the reference `pyproject.toml` requests no ADK extra; adding `google-adk[extensions]` (what ADK's own error message recommends for LiteLLM) makes resolution impossible.
4. **The reference `pyproject.toml` cannot resolve on the snapshot date.** `exclude-newer = "P3D"` drops every file uploaded in the last three days, and it pins or floors `google-adk==2.15.0` (uploaded 2026-11-20T00:30Z), `litellm==1.110.2` (11-20), `ruff==0.17.6` (11-19), `pyrefly==1.5.0` (11-19), `hypothesis>=6.170.17` (11-20), `typer>=0.29.2` (11-18) and `import-linter>=2.17` (11-18). ADK's own `pyproject.toml` uses the same cooldown but exempts `google-adk` and `google-genai` through `exclude-newer-package` for exactly this reason (`pyproject.toml:446-451`).
5. **A `retry_config` on a `Workflow` does not cascade to its children.** It retries the whole sub-workflow, replaying children that produced an output or a state change; a child that produced neither runs again (`workflow/_base_node.py:101-104`; guide: `docs/guides/workflow/retry_config/index.md:83-108`). Side-effecting nodes (file writes, git) need an output or state marker, or they repeat.
6. **Rule 6 of the "10 rules" is misstated.** The sixth construction-time rule is "DEFAULT_ROUTE cannot be combined with other routes in a list". "Multiple terminal nodes produced output" is a run-time `WorkflowConfigurationError` raised in `Workflow._finalize` (`workflow/_workflow.py:1009-1016`), so a test that only constructs the `Workflow` will not catch a dangling fan-out.
7. **The per-run privacy setting does not reach ADK's own server routes.** `/run` and `/run_sse` (served by `adk web`, `adk api_server` and `get_fast_api_app`) build their own `RunConfig` from `streaming`, `custom_metadata`, `service_tier` and `max_llm_calls` only (`cli/api_server.py:2304-2311`, `:2398-2407`; request model at `:725-741`). `default_run_config()` in report B is never used there. Set `ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=false` in the environment instead.
8. **`ModelArmorPlugin` screens tool output only when `tool_output_template_name` is set.** The documented configuration sets only the prompt and response templates, which leaves the indirect-injection screening the documents emphasise switched off (`integrations/model_armor/_config.py:48-54`, `_plugin.py:231`).

## 4. Code that would fail as written

| # | Where | What happens | Reason |
| --- | --- | --- | --- |
| 1 | B §2.3 `make_readonly_env_toolset()`; A §6.5 `tool_filter=lambda tool, ctx: tool.name == "ReadFile"`; B §1.3 `tool_filter=['ReadFile']` | Constructs without error, then exposes all four tools. A silent failure of the function's purpose | `EnvironmentToolset.__init__` forwards `**kwargs` to `BaseToolset`, which stores `tool_filter`; nothing ever calls `_is_tool_selected` for this toolset. See error 1 |
| 2 | B §3.2 `pyproject.toml` and the `Makefile` `install` target (`--exclude-newer P3D`) | `uv lock` / `uv sync` / `uv tool install` cannot find `google-adk==2.15.0` (and six more) until about 2026-11-23 | uv: "Limit candidate packages to those that were uploaded prior to the given date"; `P3D` is a valid ISO 8601 duration. Upload times from PyPI. Fix: `exclude-newer-package = { google-adk = false, … }` or wait out the cooldown |
| 3 | B §3.2 `litellm==1.110.2` next to `google-adk==2.15.0` | Resolves today only because no ADK extra is requested; unsatisfiable with `google-adk[extensions]`, `[all]` or `[test]` | ADK bound `litellm>=1.84,<1.106.3`. Newest release inside the bound is 1.106.2 |
| 4 | A §10.1 `ModelArmorPlugin(config=ModelArmorConfig(prompt_template_name=..., response_template_name=...))` | Runs, but tool outputs are not screened | `tool_output_template_name` unset: "If unset, tool output screening is skipped" |
| 5 | A §1 `from google.adk.models import FallbackModel, Gemini, Claude, OpenAILlm, LiteLlm, ServiceTier, LLMRegistry` | `ImportError` on `Claude` in the reference environment | `models/anthropic_llm.py:39` imports `anthropic` at module load, and the reference `pyproject.toml` does not install it. Each provider class needs its own optional package (`models/__init__.py:132-150`) |
| 6 | B §3 / §4 / §6 use of `AgentEvaluator` and `adk eval` with the reference `pyproject.toml` | Fails at evaluation time for missing `pandas`, `tabulate`, `rouge-score` | These live in the `eval` extra (`evaluation/constants.py:19`, `evaluation/agent_evaluator.py:612-613`); the `pyproject.toml` declares only `mcp`, `a2a`, `db`. `ModelArmorPlugin` likewise needs `[gcp]`, GEPA needs `gepa` (also in `eval`) |
| 7 | A §2 `Edge(from_node=START, to_node=step_a, route=...)` | A real route value here raises `GraphValidationError` | Contradicts the document's own rule 3: edges leaving `START` carry no route (`workflow/utils/_graph_validation.py:155-162`) |

Everything else in report B §2.3 is valid against 2.15.0: all 20 import lines resolve (given `litellm` and `truststore` installed), and every constructor argument used exists (`BasePlugin(name=)`, `before_tool_callback(*, tool, tool_args, tool_context)`, `Gemini(model=, retry_options=)`, `FallbackModel(models=)`, `LiteLlm(model, **kwargs)`, `LocalEnvironment(working_dir=)`, `LlmAgent(mode=, static_instruction=, planner=, input_schema=, output_schema=, tools=)`, `node(x, name=)`, `JoinNode(name=)`, `Workflow(name=, input_schema=, output_schema=, edges=)`, `@node(rerun_on_resume=, retry_config=)`, `RequestInput(interrupt_id=, message=, response_schema=)`, `Event(state=, route=, output=)`, `RunConfig(streaming_mode=, max_llm_calls=, tool_thread_pool_config=, telemetry=)`).

Cautions on that skeleton that are not API errors:

- `instruction="Audit active change '{change_id}' …"` raises `KeyError` at run time unless an earlier node has written `change_id` to session state. Placeholders resolve from state, not from `node_input` (`flows/llm_flows/prompt/_instructions_utils.py:187-197`).
- `review_gate` yields `Event(output=ChangeContext(...))`. A returned model is dumped to a dict (`workflow/_function_node.py:637-638`), but a model placed inside a hand-built `Event` is passed through unchanged when the node has no `output_schema`. Use `.model_dump()` or annotate the return type. Not confirmed as a failure.
- `WritePolicyPlugin` decides by `tool_context.agent_name`, and unknown names pass. A node cloned by `node(x, name=f"{stage}_shadow_llm")` runs under the new name (`workflow/_node_runner_utils.py:117`), which is not in `READ_ONLY_AGENTS`. Combined with error 1, a shadow copy of a read-only stage can write and execute.
- Plain Python, outside ADK: `_escapes_via_link` calls `.resolve()` before `.is_symlink()`, so the symlink test can never be true (the containment test still works); and `build_stage_node(mode="hybrid", hybrid_node=None)` falls through to the shadow branch.

## 5. Claims checked

Verdicts: CONFIRMED, WRONG, PARTLY RIGHT, OUTDATED, UNVERIFIABLE. "EXPERIMENTAL" marks features the source flags as experimental.

### 5.1 File A: `research_notes/03-google-adk-v2-best-practices.md`

| ID | Claim (section) | Verdict | Evidence | Correct API where not confirmed |
| --- | --- | --- | --- | --- |
| A01 | v2.15.0, released 2026-11-19 (header) | CONFIRMED | CHANGELOG heading `## [2.15.0] … (2026-11-19)`; PyPI upload 2026-11-20T00:30:35Z UTC | |
| A02 | Cited source files, `docs/guides/**` and `contributing/samples/workflows/*` exist (header) | CONFIRMED | Tree at `v2.15.0`: all cited paths present | |
| A03 | Python 3.11–3.15 supported; `constraints-3.14.txt` exists (§1) | CONFIRMED | `METADATA` classifiers; repo root has `constraints-3.11…3.15.txt` | |
| A04 | `from google.adk import Agent, Context, Event, Runner, Workflow`; `START` not exported (§1) | CONFIRMED | `__init__.py:30-37` | |
| A05 | `google.adk.workflow` exports `BaseNode, DEFAULT_ROUTE, Edge, FunctionNode, JoinNode, Node, NodeTimeoutError, RetryConfig, START, Workflow, node` (§1) | CONFIRMED | `workflow/__init__.py:34-59` | |
| A06 | `from google.adk.apps import App, ResumabilityConfig`; `EventsCompactionConfig` only from `google.adk.apps.app` (§1) | CONFIRMED | `apps/__init__.py:24-39`; `apps/app.py:28-36` | |
| A07 | `from google.adk.agents.context_cache_config import ContextCacheConfig` (§1) | CONFIRMED | `agents/context_cache_config.py:23` | |
| A08 | `from google.adk.agents import LlmAgent, BaseAgent, RunConfig`; `run_config` exports `RunConfig, StreamingMode, ToolThreadPoolConfig`; `Agent` aliases `LlmAgent` (§1) | CONFIRMED | `agents/__init__.py:43-64`; `agents/run_config.py:33`, `:54`, `:83`; `agents/llm_agent.py:1462` | |
| A09 | `from google.adk.planners import BuiltInPlanner` (§1) | CONFIRMED | `planners/__init__.py`; `planners/built_in_planner.py:32` | |
| A10 | `from google.adk.events import Event, EventActions, RequestInput, get_active_events`; `RequestInput` also in `events.request_input` (§1) | CONFIRMED | `events/__init__.py:15-25`; `events/request_input.py:27` | |
| A11 | `from google.adk.models import FallbackModel, Gemini, Claude, OpenAILlm, LiteLlm, ServiceTier, LLMRegistry`; lazy; `gemma-4*` → `Gemini` (§1) | CONFIRMED | `models/__init__.py:43-150` (`OpenAILlm` resolves through `__getattr__` although absent from `__all__`); `:61-64`. Each provider needs its optional package (section 4 #5). `FallbackModel` is EXPERIMENTAL | |
| A12 | Sessions import list; `DatabaseSessionService` needs `[db]`; `SqliteSessionService` in `sessions.sqlite_session_service` (§1) | CONFIRMED | `sessions/__init__.py:33-61`; `sessions/sqlite_session_service.py:203-210` (`SqliteSessionService(db_path: str)`). `BufferedSessionService` is EXPERIMENTAL | |
| A13 | Plugins import list (nine names); plugins apply to the whole `App` (§1) | CONFIRMED | `plugins/__init__.py:42-84`; `plugins/base_plugin.py:41-49` | |
| A14 | `from google.adk.integrations.model_armor import ModelArmorConfig, ModelArmorPlugin`; needs `google-adk[gcp]` and ADC (§1) | CONFIRMED | `integrations/model_armor/__init__.py:35-38`; `METADATA`: `google-cloud-modelarmor … extra == "gcp"`; `_plugin.py:76-93` | |
| A15 | `from google.adk.skills import Skill, SkillRegistry, load_skills_from_dir`; `SkillToolset` only from `google.adk.tools.skill_toolset` (§1) | CONFIRMED | `skills/__init__.py:36-53`; `tools/skill_toolset.py:2189`; `tools/__init__.py:55-115` has no `SkillToolset` | |
| A16 | `from google.adk.environment import LocalEnvironment`; `from google.adk.tools.environment import EnvironmentToolset`; E2B / Daytona under `google.adk.integrations` (§1) | CONFIRMED | `environment/__init__.py:24-29`; `tools/environment/__init__.py:21-23`; `integrations/e2b/__init__.py:36` (`E2BEnvironment`, extra `e2b`); `integrations/daytona/__init__.py:36` (`DaytonaEnvironment`, extra `daytona`) | |
| A17 | `from google.adk.tools.model_consult import ModelConsultTool, ModelConsultContextConfig, ForceEscalationPlugin, ModelConsultObservabilityPlugin` (§1) | CONFIRMED | `tools/model_consult/__init__.py:25-33` | |
| A18 | `InMemoryArtifactService`, `InMemoryMemoryService`, `from google.adk.tools import load_memory` (§1) | CONFIRMED | `artifacts/__init__.py:27-32`; `memory/__init__.py:28-34`; `tools/__init__.py:82` | |
| A19 | `from google.adk.telemetry import ContentCapturingMode, TelemetryConfig` (§1) | CONFIRMED | `telemetry/__init__.py:39-47`. EXPERIMENTAL: `agents/run_config.py:299-300` | |
| A20 | `get_fast_api_app` takes keyword-only `agents_dir=`; `agent_dir=` raises `TypeError` (§1, §9.2) | CONFIRMED | `cli/fast_api.py:107-146` (`*, agents_dir: str, …, web: bool`; `web` has no default) | |
| A21 | `from google.adk.tools import FunctionTool, LongRunningFunctionTool`; `from google.adk.tools.tool_args_matcher import ToolArgsMatcher` (§1) | CONFIRMED | `tools/__init__.py:74`, `:83`; `tools/tool_args_matcher/__init__.py:24-31`. `ToolArgsMatcher` is EXPERIMENTAL (`_tool_args_matcher.py:362`) | |
| A22 | `from google.adk.a2a.utils.agent_to_a2a import to_a2a`; not re-exported; returns `Starlette` (§1) | CONFIRMED | `a2a/utils/agent_to_a2a.py:78-95`; `a2a/__init__.py` and `a2a/utils/__init__.py` export nothing. Needs extra `a2a` | |
| A23 | `from google.adk.tools.mcp_tool import to_mcp_server` exposes "an agent/workflow" (§1, §9.2) | PARTLY RIGHT | Import path right (`tools/mcp_tool/__init__.py:18`). Signature is `to_mcp_server(agent: BaseAgent, *, name, instructions, runner)` (`_agent_to_mcp.py:278-284`); the guide lists only `BaseAgent`. Unlike `to_a2a`, `Workflow` is not in the signature | Pass a `BaseAgent`; treat a `Workflow` root as unsupported until tested |
| A24 | `AgentEvaluator` is the only symbol exported by `google.adk.evaluation` (§1) | PARTLY RIGHT | `evaluation/__init__.py:21-26`: `RunResult` is always exported; `AgentEvaluator` is added only when its import succeeds | Install `google-adk[eval]` |
| A25 | ADK bounds `google-genai>=2.34,<3`; lock pins 2.34.0; 3.6.1 is on PyPI (§1.1) | CONFIRMED | `METADATA`; `constraints-3.14.txt:593`; PyPI | |
| A26 | `mcp` 2.3.0 satisfies `mcp>=1.24,<3`; SDK 2.x renames `FastMCP` to `MCPServer`, handled inside ADK (§1.1) | CONFIRMED | `METADATA`; `dependencies/_mcp.py:21-30`, `:67-70`. ADK's lock pins `mcp==1.28.1` (`constraints-3.14.txt:968`) | |
| A27 | `ag-ui-adk` 0.13.0 needs `google-adk>=1.28.1,<3.0.0`, `ag-ui-protocol>=1.0.0`, `ag-ui-a2ui-toolkit>=0.0.6` (§1.1) | CONFIRMED | PyPI `requires_dist` for `ag-ui-adk` 0.13.0 | |
| A28 | PEP 649 / PEP 750 make `@node` type hints work without `from __future__ import annotations` (§1.1) | UNVERIFIABLE | Would need execution on 3.14; not established from source | |
| A29 | ADK declares `LlmAgent(BaseAgent, abc.ABC)` with no abstract method (§1.1) | CONFIRMED | `agents/llm_agent.py:262-265`. The pyrefly setting itself was not checked | |
| A30 | `adk web --no_use_local_storage .` keeps sessions in memory instead of `.adk/session.db` (§1.1) | CONFIRMED | `cli/cli_tools_click.py:966-977`; `cli/utils/dot_adk_folder.py:55`; `cli/utils/service_factory.py:255` | |
| A31 | `truststore` injection for corporate proxies (§1.1) | UNVERIFIABLE | Not an ADK claim; not checked | |
| A32 | `Workflow` is a `BaseNode`; a node may be a function, `LlmAgent`, `BaseTool`, `JoinNode` or `Workflow` (§2) | CONFIRMED | `workflow/_workflow.py:154`; `workflow/_graph.py:41-43` | |
| A33 | Chain tuples with a nested tuple fan out and run branches concurrently (§2) | CONFIRMED | `workflow/utils/_graph_parser.py` (`_process_chain`); guide: `docs/guides/workflow/graph/index.md:106-113` | |
| A34 | Routing maps with `DEFAULT_ROUTE`; nodes emit `Event(route=…)` (§2) | CONFIRMED | `workflow/_graph.py:46-56`, `:91`; `events/event.py:34` | |
| A35 | Explicit `Edge(...)` needs `BaseNode` objects and the `START` object, not `"START"` (§2) | CONFIRMED | `workflow/_graph.py:59-66`; guide: `graph/index.md:65` | |
| A36 | Ten rules, checked when `Workflow(...)` is constructed (§2) | CONFIRMED | `workflow/_workflow.py:192-202`; `workflow/utils/_graph_validation.py:234-246`. Errors are `GraphValidationError(ValueError)`, wrapped in a Pydantic `ValidationError` per guide `:233` | |
| A37 | Rule 1: unique names, `str.isidentifier()`, reuse the same object, or clone with `node(existing, name=…)` | CONFIRMED | `_graph_validation.py:66-81`; `workflow/_base_node.py:55-64`; `workflow/utils/_workflow_graph_utils.py:102-188` | |
| A38 | Rules 2–5: `START` present with no incoming edges; no route on edges from `START`; reachability; no duplicate edges | CONFIRMED | `_graph_validation.py:84-162` | |
| A39 | Rule 6: "multiple terminal nodes producing output raise `WorkflowConfigurationError`", checked at instantiation | WRONG | The sixth construction-time rule is DEFAULT_ROUTE constraints (`_graph_validation.py:165-174`; guide `:210`). The terminal-output error exists but is raised at run time in `Workflow._finalize` (`workflow/_workflow.py:1009-1016`) | Rule 6: `DEFAULT_ROUTE` may not appear in a route list with other routes. Test dangling fan-out by running the workflow |
| A40 | Rule 7: loops need a routed back-edge | CONFIRMED | `_graph_validation.py:30-63` | |
| A41 | Rule 8: predecessor `output_schema` must equal successor `input_schema`; swapping an `LlmAgent` for a typed `@node` keeps the check valid | CONFIRMED | `_graph_validation.py:177-189` (compared only when both are set); `workflow/_function_node.py:408-443` | |
| A42 | Rule 9: a `mode="chat"` agent may only follow `START`; mid-graph agents use `single_turn` or `task` | CONFIRMED | `_graph_validation.py:192-210`; `adk_docs_py/graphs_data-handling.md:259` | |
| A43 | Rule 10: node-specific outgoing-edge checks | CONFIRMED | `_graph_validation.py:213-221`; `workflow/_base_node.py:271-279` | |
| A44 | `@node(...)` accepts `name, rerun_on_resume, retry_config, timeout, auth_config, require_confirmation, parameter_binding, parallel_worker, max_parallel_workers` (§3) | CONFIRMED | `workflow/_node.py:52-98` | |
| A45 | `@node(input_schema=…)` raises `TypeError`; schemas come from type hints; `FunctionNode(func=…, state_schema=…)` is accepted (§3) | CONFIRMED | `_node.py:86-98`; `workflow/_function_node.py:297-309`, `:408-443`. In the default binding only `BaseModel` classes become schemas | |
| A46 | `parameter_binding='state'`: `ctx` gets the context, `node_input` the predecessor output, other names come from `ctx.state`, else `WorkflowDataError` (§3) | CONFIRMED | `workflow/_function_node.py:486-575` | |
| A47 | `parameter_binding='node_input'` unpacks the input and infers schemas so the node can serve as a tool (§3) | CONFIRMED | `workflow/_function_node.py:445-477` | |
| A48 | `parallel_worker=True` (on `@node` or `Agent`) maps over a list, keeps order, forces `rerun_on_resume=True`, retries per item, lowest-index failure surfaces (§3) | CONFIRMED | `workflow/_parallel_worker.py:69-127`, `:227-240`; `agents/llm_agent.py:426-433`; guide: `parallel_worker/index.md:78-94` | |
| A49 | `JoinNode` emits `dict[node_name, output]` and merges branches; `input_schema` is applied per branch value; raw dict schemas are not enforced (§3) | CONFIRMED | `workflow/_join_node.py:32-59`; `workflow/_base_node.py:130-131`; guide: `join_node/index.md:10-11`, `:84` | |
| A50 | `RetryConfig` run-time defaults 5 / 1.0 / 60.0 / 2.0 / 1.0; configuration and invariant errors are never retried (§3) | CONFIRMED | `workflow/utils/_retry_utils.py:41-49`, `:170-183` | |
| A51 | "Setting `retry_config` on a `Workflow` cascades to child nodes without their own policy" (§3) | WRONG | `workflow/_base_node.py:101-104`; guide: `retry_config/index.md:83-108`. No inheritance code path; the helper `_has_own_retry_config` (`_retry_utils.py:117`) is never called | The whole sub-workflow is retried, with completed children replayed. Put `RetryConfig` on each node that should retry alone |
| A52 | `tool_thread_pool_config` moves synchronous functions and generators off the event loop (§3, §7.3) | CONFIRMED | `agents/run_config.py:196-257` | |
| A53 | `chat` mode: full history, conversational, transfers (§4.1) | CONFIRMED | `utils/_agent_mode.py:24-38`; `adk_docs_py/workflows_collaboration.md:60-66` | |
| A54 | `task` mode: "must call built-in `finish_task(output=…)`", validated against `output_schema` (§4.1) | PARTLY RIGHT | The tool exists and validates (`agents/llm/task/_finish_task_tool.py:39`, `:69`). It has no `output` parameter: arguments are the fields of `output_schema`, or a single `result` key for non-object schemas (`:48`) | The model calls `finish_task(<output_schema fields>)` or `finish_task(result=…)` |
| A55 | `single_turn` mode: `include_contents="none"` by default inside a workflow; a `single_turn` sub-agent is exposed as a tool (§4.1) | CONFIRMED | `workflow/utils/_workflow_graph_utils.py:163-168`; `adk_docs_py/workflows_collaboration.md:22-40` | |
| A56 | `static_instruction` holds no placeholders and is sent first, for prefix caching (§4.2) | CONFIRMED | `agents/llm_agent.py:344-393` | |
| A57 | `static_instruction` is "explicitly required by `GEPARootAgentPromptOptimizer` (`require_static_instruction`)" (§4.2, §6) | WRONG | `optimization/_gepa_utils.py:32-41`; `optimization/gepa_root_agent_prompt_optimizer.py:145`, `:311`, `:340` | GEPA needs `agent.instruction` to be a plain `str` and rewrites `instruction`. It never reads `static_instruction` |
| A58 | `instruction` is a dynamic template, "appended after `static_instruction`" (§4.2) | PARTLY RIGHT | Templates and `{name?}` confirmed. But when `static_instruction` is set, `instruction` leaves the system instruction and is sent as user content (`agents/llm_agent.py:323-328`) | Expect `instruction` in the user turn once `static_instruction` is used |
| A59 | `tools` and `output_schema` can be combined on one `LlmAgent` (§4.2) | CONFIRMED | `agents/llm_agent.py:470-473` | |
| A60 | `BuiltInPlanner(thinking_config=types.ThinkingConfig(...))` (§4.2) | CONFIRMED | `planners/built_in_planner.py:47` | |
| A61 | `RequestInput(interrupt_id=, message=, response_schema=)` pauses and emits an `adk_request_input` call carrying JSON Schema (§5) | CONFIRMED | `events/request_input.py:27-69`; `workflow/utils/_workflow_hitl_utils.py:105-127` | |
| A62 | `ResumabilityConfig(is_resumable=True)` plus a persistent session service records checkpoints and replays completed nodes (§5) | CONFIRMED | `apps/_configs.py:25-42`; guide: `docs/guides/apps/resumability/index.md:22-41`. Best effort, at-least-once (`_configs.py:33-36`) | |
| A63 | Nodes that act on the answer set `rerun_on_resume=True`, read `ctx.resume_inputs[...]` and scope the id as `f"review_{ctx.invocation_id}_{ctx.run_id}"` (§5) | CONFIRMED | guide: `docs/guides/events/request_input/index.md:49`, `:55`; sample: `request_input_rerun/agent.py`. A recommendation: reuse of an id is supported (`events/request_input.py:45-48`) | |
| A64 | `Runner` raises `ValueError` when a resume message mixes a function response with text (§5) | CONFIRMED | guide: `request_input/index.md:54`; `resumability/index.md:260-261` | |
| A65 | `FunctionTool(fn, require_confirmation=True)` or `ctx.request_confirmation()` emits `adk_request_confirmation` with `originalFunctionCall` and a hint (§5) | CONFIRMED | `tools/function_tool.py:184-189`; `agents/context.py:703-733`; `flows/llm_flows/tools/_confirmation.py:51-67`; `tools/tool_confirmation.py:25-41` | |
| A66 | Four state scopes: unprefixed, `app:`, `user:`, `temp:` (§5) | CONFIRMED | `sessions/state.py:96-98` | |
| A67 | `BasePlugin` hook names; registration order; plugins run before agent callbacks; a non-`None` return short-circuits (§6.1) | CONFIRMED | `plugins/base_plugin.py:55-62`, `:114-417` | |
| A68 | `SkillToolset`: `load_skills_from_dir`, tools `load_skill`, `load_skill_resource`, `run_skill_script`, skill-scoped `adk_additional_tools` (§6.2) | CONFIRMED | `tools/skill_toolset.py:92-97`, `:2189-2206`, `:2389`; guide: `docs/guides/tools/skill_toolset/index.md:5-23` | |
| A69 | `ModelConsultTool`: tool `model_consult`, default advisor `gemini-3.1-pro-preview`, `thinking_level`, `max_uses` per turn, `session_max_uses`, never raises into the loop (§6.3) | CONFIRMED | `tools/model_consult/_model_consult_tool.py:55-56`, `:157-184`; guide: `model_consult_tool/index.md:50-52` | |
| A70 | `ContextCacheConfig(cache_intervals, ttl_seconds, min_tokens)`; from turn 2; 2048 / 4096 token minimums; no effect on Gemini 4; single turn needs `cached_content` (§6.4) | CONFIRMED | `agents/context_cache_config.py:23-87` | |
| A71 | `EventsCompactionConfig(compaction_interval=, overlap_size=)` summarises old events (§6.4) | CONFIRMED | `apps/_configs.py:45-101`; `events/event_actions.py:90`. The two fields must be set together | |
| A72 | `EnvironmentToolset` wraps a `BaseEnvironment` (`LocalEnvironment(working_dir=…)`) and backs `run_skill_script` (§6.5) | CONFIRMED | `tools/environment/_environment_toolset.py:63-82`; `environment/_local_environment.py:80-98`; `tools/skill_toolset.py:2198` | |
| A73 | Tool names and arguments: `ReadFile(path, start_line?, end_line?)`, `WriteFile(path, content)`, `EditFile(path, old_string, new_string)`, `Execute(command)` (§6.5) | CONFIRMED | `_read_file_tool.py:109-149`; `_write_file_tool.py:43-69`; `_edit_file_tool.py:44-78`; `_execute_tool.py:61-85` | |
| A74 | "Least-privilege via `BaseToolset.tool_filter`" so `WriteFile`, `EditFile`, `Execute` "are never exposed to the LLM at all" (§6.5) | WRONG | `tools/environment/_environment_toolset.py:107-118`; `tools/base_toolset.py:134-158`, `:229-238`; `agents/llm_agent.py:205`; guide: `docs/guides/tools/base_toolset/index.md:87-92` | Subclass `EnvironmentToolset` and filter in `get_tools` with `self._is_tool_selected(...)`, or build read-only tools yourself |
| A75 | `AgentEvaluator` and `adk eval`; metrics `tool_trajectory_avg_score`, `response_match_score`, `final_response_match_v2`, rubric criteria (§6.6) | CONFIRMED | `evaluation/agent_evaluator.py:119`; `evaluation/eval_metrics.py:60-78`. Needs `google-adk[eval]` | |
| A76 | `google.adk.optimization` ships `GEPARootAgentPromptOptimizer` (with config, "requires `static_instruction`") and `SimplePromptOptimizer` (§6.6) | PARTLY RIGHT | Classes exist (`optimization/gepa_root_agent_prompt_optimizer.py:60`, `:226-227`; `optimization/simple_prompt_optimizer.py`). The package `__init__` exports nothing; GEPA is EXPERIMENTAL; the requirement is false (A57) | `from google.adk.optimization.gepa_root_agent_prompt_optimizer import GEPARootAgentPromptOptimizer, GEPARootAgentPromptOptimizerConfig` |
| A77 | `FallbackModel` takes ordered model ids or `BaseLlm` instances, falls back on 429 / 503, rolls back request mutations, resolves lazily (§7.1) | CONFIRMED | `models/_fallback_model.py:206-292`, `:329-331`. EXPERIMENTAL. Default codes are 429, 500, 502, 503, 504 | |
| A78 | `ReflectAndRetryToolPlugin(max_retries=3)`: lock-protected per-tool counter, `extract_error_from_result` (§7.2) | CONFIRMED | `plugins/reflect_retry_tool_plugin.py:85-146`, `:252` | |
| A79 | `ReflectAndRetryModelPlugin` recovers from `MALFORMED_FUNCTION_CALL`, safety and recitation blocks (§7.2) | PARTLY RIGHT | Default handles only `MALFORMED_FUNCTION_CALL` (`plugins/_reflect_retry_model_plugin.py:55`, `:77`; guide `:75`, `:86`) | `ReflectAndRetryModelPlugin(on_model_errors=[FinishReason.MALFORMED_FUNCTION_CALL, FinishReason.SAFETY, FinishReason.RECITATION])` |
| A80 | `ToolCallIntegrityPlugin(secret_key=…)` stamps stored function calls with HMAC-SHA256 and verifies them; tools mounted as workflow nodes are not checked (§7.2) | CONFIRMED | `plugins/_tool_call_integrity_plugin.py:147-185`, `:230`. `secret_key` must be `bytes`. See omissions for what it does not cover | |
| A81 | `max_llm_calls` is shared across transferred sub-agents and counted separately per `AgentTool` run (§7.3) | CONFIRMED | `agents/run_config.py:268-285` (default 500); guide: `docs/guides/agents/run_config/index.md:71` | |
| A82 | `StreamingMode.SSE` yields partial events, then one aggregated non-partial event (§7.3) | CONFIRMED | `agents/_streaming_mode.py` (`SSE` docstring) | |
| A83 | `ToolThreadPoolConfig(max_workers=4)` also covers synchronous `require_confirmation` callables (§7.3) | CONFIRMED | `agents/run_config.py:54-80`, `:213-221` | |
| A84 | `ServiceTier.DEFERRED` only applies with `Gemini(use_interactions_api=True)`; otherwise dropped with a warning (§7.3) | CONFIRMED | `agents/run_config.py:103-122`; `models/google_llm.py:173`; guide: `docs/guides/models/service_tier/index.md:84`, `:227`. Omits the SSE restriction (see omissions) | |
| A85 | `BufferedSessionService` wraps another service; the runner does not flush; call `flush_session(app_name=, user_id=, session_id=)` and `close()` (§7.4) | CONFIRMED | `sessions/_buffered_session_service.py:100-118`, `:255-292`; guide `:20-23`. EXPERIMENTAL | |
| A86 | `ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS` defaults on; content goes to `gcp.vertex.agent.llm_request`; `TelemetryConfig(capture_message_content=ContentCapturingMode.NO_CONTENT)` turns it off per run (§8.1) | CONFIRMED | `telemetry/context.py:136-141`, `:232`, `:345-357`; `telemetry/tracing.py:355` | |
| A87 | `ctx.save_artifact` / `ctx.load_artifact` store versioned `types.Part` values (§8.2) | CONFIRMED | `agents/context.py:547-593` (`save_artifact` returns the `int` version; the base class is `BaseArtifactService`) | |
| A88 | `BaseMemoryService` (`add_session_to_memory`, `search_memory`) with `load_memory` / `preload_memory` (§8.2) | CONFIRMED | `memory/base_memory_service.py:52`, `:124`; `tools/__init__.py:82`, `:95` | |
| A89 | `yield Event(state={…}, route="revise")` sets state and route together (§9.1) | CONFIRMED | `events/event.py:34`, `:184-238`; sample: `request_input_rerun/agent.py` | |
| A90 | `"{feedback?}"` is an optional placeholder (§9.1) | CONFIRMED | `flows/llm_flows/prompt/_instructions_utils.py:153-197`; sample: `loop/agent.py` | |
| A91 | A generator node used as a tool annotates only its data type, e.g. `-> Generator[str, None, None]` (§9.1) | CONFIRMED | sample: `node_as_tool/agent.py` | |
| A92 | Context attributes `agent_name, invocation_id, user_id, run_config, is_aborted, node, node_path, run_id, attempt_count, resume_inputs, tool_confirmation, state, actions, session` (§9.1) | CONFIRMED | `agents/readonly_context.py:45-83`; `agents/context.py:279-340` | |
| A93 | `get_fast_api_app` returns a `FastAPI` app; `web=False` gives production routes, `web=True` the dev server; `/health`, `/version`, A2A routes, `services.py` loading (§9.2) | CONFIRMED | `cli/fast_api.py:119`, `:312-332`; `cli/api_server.py:1713-1717` | |
| A94 | `ag_ui_adk` provides `ADKAgent` and `add_adk_fastapi_endpoint` (§9.2) | CONFIRMED | `ag_ui_adk/__init__.py:14`, `:19` in the 0.13.0 wheel. Behaviour not examined | |
| A95 | `to_mcp_server` exposes one MCP tool over `stdio` or `streamable-http`, forwards non-final text as progress, keeps one session per connection (§9.2) | CONFIRMED | `tools/mcp_tool/_agent_to_mcp.py:285-305`; guide: `agent_to_mcp/index.md:69` | |
| A96 | `ModelArmorPlugin(config=ModelArmorConfig(prompt_template_name=…, response_template_name=…))` screens inputs, outputs and tool outputs (§10.1) | PARTLY RIGHT | Inputs and outputs: yes. Tool outputs only with a third field (`integrations/model_armor/_config.py:48-54`; `_plugin.py:222-232`) | Add `tool_output_template_name="projects/…/templates/…"` |
| A97 | Model Armor fails closed by default; blocked events carry `custom_metadata['model_armor_blocked']`; blocked tool output returns `{'error': …}` (§10.1) | CONFIRMED | `_config.py:65`; `_plugin.py:248-251`, `:360` | |
| A98 | `Runner.rewind_async(user_id=, session_id=, rewind_before_invocation_id=)` (§10.2) | CONFIRMED | `runners.py:1395-1433` | |
| A99 | Efficiency metrics `tool_call_count_v1`, `inference_call_count_v1`, `token_usage_v1`, `invocation_duration_v1` are reported on every `adk eval` run with no configuration (§10.3) | CONFIRMED | guide: `docs/guides/evaluation/efficiency_evaluators/index.md:6-21` | |
| A100 | `ToolArgsMatcher` strategies `casefold`, `numeric`, `ignore`, custom and model matchers, deterministic first, `short_circuit` (§10.3) | CONFIRMED | guide: `docs/guides/tools/tool_args_matcher/tool_args_matcher/index.md:25-107`, `:184-187`. EXPERIMENTAL | |
| A101 | `to_a2a(root_agent, port=8001)` serves an agent or `Workflow`; pairs with `RemoteA2aAgent` (§10.4) | CONFIRMED | `a2a/utils/agent_to_a2a.py:78-96` (`agent: BaseAgent \| Workflow`); `agents/remote_a2a_agent.py:23` | |
| A102 | `Workflow`, `JoinNode`, `RequestInput`, `ToolConfirmation`, `rewind_async`, `FallbackModel`, `ModelConsultTool`, `SkillToolset`, `AgentEvaluator` have "full support" on the Copilot (`LiteLlm`) arm (§11.1) | UNVERIFIABLE | No source or guide statement; would need a run against Copilot | |
| A103 | `BuiltInPlanner(thinking_config=…)` "errors on non-thinking models" on the `LiteLlm` arm and "MUST" be guarded (§11.1) | PARTLY RIGHT | The docstring warns of an error (`planners/built_in_planner.py:36-38`). But `LiteLlm` applies `thinking_config` only when `litellm.supports_reasoning(...)` is true and otherwise skips it (`models/lite_llm.py:4092-4103`) | Guarding is harmless; on `LiteLlm` an unsupported model gets no thinking parameters rather than an error |
| A104 | `ContextCacheConfig`, `ServiceTier.DEFERRED` and `ModelArmorPlugin` are Gemini- or GCP-only (§11.1) | CONFIRMED | `agents/context_cache_config.py:39-41`; `agents/run_config.py:106-110`. Model Armor depends on GCP credentials, not on the model | |
| A105 | LiteLLM / Copilot rules: `suppress_debug_info`, `disable_copilot_system_to_assistant`, `_skip_mcp_handler`, `LITELLM_LOCAL_MODEL_COST_MAP`, token directory and GHE variables (§11.2) | UNVERIFIABLE | Attributed to the local `adk_review` project. For reference, the symbols exist in the `litellm` 1.110.2 wheel (`litellm/__init__.py:425`, `:492`; `litellm/main.py:5635`), except `GITHUB_COPILOT_API_KEY_URL`, which does not occur in that wheel at all | |
| A106 | `google.adk.utils.env_utils.is_enterprise_mode_enabled()` reads `GOOGLE_GENAI_USE_ENTERPRISE` (§11.2) | CONFIRMED | `utils/env_utils.py:82-97` | |
| A107 | `LocalEnvironment.execute()` uses `asyncio.create_subprocess_shell`; "Ignored on Windows, as `os.killpg` is"; descendants can survive a timeout on Windows (§11.3) | CONFIRMED | `environment/_local_environment.py:47-52`, `:138-147`, `:179-181` | |
| A108 | "Gemini 3 warns against looping below `temperature=1.0`"; Copilot reasoning models cannot run at `temperature=0` (§11.2) | UNVERIFIABLE | Not in ADK source | |
| A109 | `Edge(from_node=START, to_node=step_a, route=...)` as the explicit-edge example (§2) | PARTLY RIGHT | The field names are right (`workflow/_graph.py:59-77`), but an edge from `START` that carries a route fails rule 3 (`_graph_validation.py:155-162`) | `Edge(from_node=START, to_node=step_a)`; put `route=` on edges from later nodes |

### 5.2 File B: `reports/02-adk-spec-framework-architecture-and-roadmap.md`

| ID | Claim (section) | Verdict | Evidence | Correct API where not confirmed |
| --- | --- | --- | --- | --- |
| B01 | ADK 2.0 runtime is `v2.15.0` (§1, §2) | CONFIRMED | PyPI; CHANGELOG | |
| B02 | `explore` is read-only through `mode="chat"`, `tool_filter=['ReadFile']` (§1.3) | WRONG | See A74. A name list is ignored the same way | Filter inside a subclass, or a custom read tool |
| B03 | Shadow mode clones with `node(llm_node, name=…)`, forwards `input_schema` / `output_schema` to a nested `Workflow`, joins with `JoinNode` (§2.1) | CONFIRMED | `workflow/_node.py:73-173`; `workflow/_base_node.py:127-138`; `workflow/_join_node.py:32` | |
| B04 | Identical adapter contracts are "enforced at startup by ADK Rule #8" (§2.1) | PARTLY RIGHT | Rule 8 compares one edge's two schemas, and only when both are set (`_graph_validation.py:177-189`). It does not compare two alternative adapters | Assert schema equality in the registry itself |
| B05 | Copilot arm "pinned `litellm==1.110.2`" as part of a verified baseline (§2.2, §3.1, §3.2) | WRONG | ADK bound `litellm>=1.84,<1.106.3` (`pyproject.toml:121`, `:241`, `:390`, with the compromised-release comment at `:241`); lock `litellm==1.95.0` (`constraints-3.14.txt:901`). The report says its versions were verified against that lock file | Pin within the bound (newest is 1.106.2), or accept running `LiteLlm` outside ADK's declared range |
| B06 | LiteLLM flags `LITELLM_LOCAL_MODEL_COST_MAP`, `suppress_debug_info`, `disable_copilot_system_to_assistant`, `_skip_mcp_handler` (§2.2, §2.3) | CONFIRMED | Present in the `litellm` 1.110.2 wheel (`litellm/__init__.py:425`, `:492`; `litellm/main.py:5635`). `LiteLlm` forwards extra keyword arguments to `acompletion` (`models/lite_llm.py:4580-4600`). What the flags do was not verified | |
| B07 | GHE overrides `GITHUB_COPILOT_API_BASE`, `…_DEVICE_CODE_URL`, `…_ACCESS_TOKEN_URL`, `…_API_KEY_URL` (§2.2) | PARTLY RIGHT | The first three are read by `litellm` 1.110.2. `GITHUB_COPILOT_API_KEY_URL` does not occur in the wheel | Only valid if the project's own login CLI reads that variable |
| B08 | Gemini arm: `GOOGLE_API_KEY`, or Vertex via `GOOGLE_GENAI_USE_ENTERPRISE` and `is_enterprise_mode_enabled()` (§2.2) | CONFIRMED | `utils/env_utils.py:82-97` | |
| B09 | Capability table: graph, HITL, plugins, `FallbackModel`, `ModelConsultTool`, `SkillToolset` have "full support" on both arms (§2.2) | UNVERIFIABLE | As A102 | |
| B10 | `BuiltInPlanner` is "unsupported on non-thinking models" and must be guarded (§2.2, §2.3 comment, §2.4) | PARTLY RIGHT | As A103 | |
| B11 | `ContextCacheConfig`, `ServiceTier.DEFERRED`, `ModelArmorPlugin` only on Gemini / GCP (§2.2) | CONFIRMED | As A104 | |
| B12 | `static_instruction` has zero placeholders and is "required for Gemini prefix caching and `GEPARootAgentPromptOptimizer`" (§2.2) | PARTLY RIGHT | Caching: confirmed (A56). GEPA: false (A57) | |
| B13 | `FallbackModel` gives "429/5xx/timeout failover" (§2.2) | PARTLY RIGHT | 429 and 5xx: yes. 408 is deliberately excluded and status-less failures propagate (`models/_fallback_model.py:237-274`). EXPERIMENTAL | Add 408 with `retriable_status_codes=` if wanted |
| B14 | `ReflectAndRetryToolPlugin(max_retries=3)`, `ReflectAndRetryModelPlugin`, `ModelConsultTool(max_uses=2, session_max_uses=5)`, `ForceEscalationPlugin`, `ModelConsultObservabilityPlugin` (§2.2) | CONFIRMED | `plugins/reflect_retry_tool_plugin.py:141-146`; `tools/model_consult/_model_consult_tool.py:161-162`; `tools/model_consult/_force_escalation_plugin.py:105-129` | |
| B15 | "Least-privilege `EnvironmentToolset(environment=…, tool_filter=…)`" (§2.2) | WRONG | As A74 | |
| B16 | `ModelArmorPlugin` on `after_tool_callback`; `ToolCallIntegrityPlugin(secret_key=…)` protects agent-invoked tools only; `ToolConfirmation` (§2.2) | CONFIRMED | `integrations/model_armor/_plugin.py:222`; `plugins/_tool_call_integrity_plugin.py:162-164`. Needs `tool_output_template_name` (A96) and a `bytes` key | |
| B17 | `os.killpg` is ignored on Windows in `LocalEnvironment` (§2.2, §2.4) | CONFIRMED | `environment/_local_environment.py:47-52`, `:145` | |
| B18 | Span capture defaults on; `RunConfig(telemetry=TelemetryConfig(capture_message_content=ContentCapturingMode.NO_CONTENT))` (§2.2, §2.3, §2.4) | CONFIRMED | As A86. Does not reach ADK's server routes (section 3, error 7) | |
| B19 | `RunConfig(streaming_mode=StreamingMode.SSE, max_llm_calls=40, tool_thread_pool_config=ToolThreadPoolConfig(max_workers=4))`; `BufferedSessionService` needs `flush_session(...)` and `close()` (§2.2) | CONFIRMED | `agents/run_config.py:54-80`, `:152`, `:196`, `:268`; `sessions/_buffered_session_service.py:255-292` | |
| B20 | §2.3: every import in the skeleton is valid for 2.15.0 | CONFIRMED | All 20 `google.adk` / `google.genai` import lines resolve against the exports cited in A04–A22 and `models/base_llm.py`, `models/google_llm.py:100`, `utils/env_utils.py:82` | |
| B21 | §2.3 `WritePolicyPlugin`: `super().__init__(name=…)`, `before_tool_callback(self, *, tool, tool_args, tool_context)`, tool names, `tool_args["path"]`, `tool_context.agent_name`, returning a dict blocks the call | CONFIRMED | `plugins/base_plugin.py:105`, `:306-312`; A73; `agents/readonly_context.py:50-54`; `workflow/_node_runner_utils.py:117` | |
| B22 | §2.3 `build_model`: `Gemini(model=, retry_options=types.HttpRetryOptions(attempts=3))`, `FallbackModel(models=…)`, `LiteLlm(model="github_copilot/…", max_retries=2, _skip_mcp_handler=True)` | CONFIRMED | `models/google_llm.py:191`; `models/_fallback_model.py:276`; `models/lite_llm.py:4580-4600` | |
| B23 | §2.3 `make_readonly_env_toolset` returns a read-only toolset | WRONG | As A74. `LocalEnvironment(working_dir=Path(...))` itself is valid | |
| B24 | §2.3 `make_semantic_audit_agent`: `LlmAgent(name, mode="single_turn", model, static_instruction, instruction, planner, input_schema, output_schema, tools)` | CONFIRMED | `agents/llm_agent.py:296-485` | |
| B25 | §2.3 `build_stage_node`: `node(x, name=)`, `JoinNode(name=)`, `Workflow(name=, input_schema=, output_schema=, edges=[(START, (a, b), join, fn)])`, join output keyed by node name | CONFIRMED | `workflow/_node.py:73`; `workflow/_join_node.py:32-45`; `workflow/_workflow.py:154-202` | |
| B26 | §2.3 `review_gate`: `@node(rerun_on_resume=True, retry_config=RetryConfig(max_attempts=3))`, `ctx.invocation_id`, `ctx.run_id`, `ctx.resume_inputs`, `RequestInput(...)`, `Event(state=, route=, output=)` | CONFIRMED | `workflow/_node.py:52-64`; `agents/context.py:330-342`; `events/request_input.py:36-69`; `events/event.py:34`, `:128` | |
| B27 | §2.3 `default_run_config` | CONFIRMED | `agents/run_config.py:152`, `:196`, `:268`, `:290`; `telemetry/context.py:100`, `:232` | |
| B28 | §2.4: ADK requires `google-genai>=2.34,<3`, lock at 2.34.0, while 3.6.1 is on PyPI | CONFIRMED | `METADATA`; `constraints-3.14.txt:593`; PyPI | |
| B29 | §2.4: `LlmAgent(BaseAgent, abc.ABC)` has no abstract methods (pyrefly row) | CONFIRMED | `agents/llm_agent.py:262-265` | |
| B30 | §2.4: `adk web .` writes `.adk/session.db`; `--no_use_local_storage` avoids it | CONFIRMED | As A30 | |
| B31 | §2.4: `from google.adk import START`, `from google.adk.apps import EventsCompactionConfig`, `from google.adk.tools import SkillToolset`, `from google.adk.a2a import to_a2a` all raise `ImportError` | CONFIRMED | `__init__.py:30-37`; `apps/__init__.py:29-39`; `tools/__init__.py:55-125`; `a2a/__init__.py` is empty | |
| B32 | §2.4: `@node(input_schema=…)` raises `TypeError` | CONFIRMED | `workflow/_node.py:73-98` | |
| B33 | §2.4: `get_fast_api_app(agent_dir=…)` raises `TypeError` | CONFIRMED | `cli/fast_api.py:107-146` | |
| B34 | §2.4: shadow mode — shared names break rule 1; "missing `Workflow` schemas breaks Rule #8" | PARTLY RIGHT | Rule 1: yes. A missing schema makes rule 8 skip the edge rather than fail (`_graph_validation.py:182`) | Forward the schemas to keep the check, not to pass it |
| B35 | §2.4 and §4 Phase 1: static rules in `instruction` "fail `GEPARootAgentPromptOptimizer`"; "tune `static_instruction` with `GEPARootAgentPromptOptimizer`" | WRONG | As A57 | GEPA tunes `instruction` |
| B36 | §2.4: `ToolCallIntegrityPlugin` does not check tools mounted as workflow nodes | CONFIRMED | `plugins/_tool_call_integrity_plugin.py:162-164` | |
| B37 | §2.4: `ServiceTier.DEFERRED` is dropped unless the model sets `use_interactions_api=True` | CONFIRMED | As A84 | |
| B38 | §2.4: generator typing for nodes used as tools | CONFIRMED | As A91 | |
| B39 | §2.4: chat agents only after `START`; fan-out must converge in a `JoinNode` | CONFIRMED | `_graph_validation.py:192-210`; guide: `graph/index.md:115-121` (a run-time error, see A39) | |
| B40 | §2.4: a static `interrupt_id` in a loop "collides across iterations" | PARTLY RIGHT | Scoping is the guide's recommendation (`request_input/index.md:55`), but reuse "is supported — the framework matches function calls and responses by count" (`events/request_input.py:45-48`) | Scope the id for clarity and stable client ids, not because reuse breaks |
| B41 | §3 layout: `agent.py` exports `app` / `root_agent`; `get_fast_api_app(agents_dir=…, web=False)`; `to_mcp_server()`; `to_a2a` + `RemoteA2aAgent`; `*.test.json` suites | CONFIRMED | `cli/utils/agent_loader.py:131-133`; `cli/fast_api.py:107-118`; `evaluation/agent_evaluator.py:394-401` | |
| B42 | §3.1: the 31 Python package versions listed are the latest on PyPI | CONFIRMED | PyPI JSON on 2026-11-20: every listed version exists, is not yanked and is the newest | |
| B43 | §3.1: `pydantic`, `fastapi`, `uvicorn`, `pyyaml`, `sqlalchemy`, `mcp`, `a2a-sdk` latest versions fall inside ADK's ranges | CONFIRMED | `METADATA` `Requires-Dist`. ADK's own lock sits lower: `pydantic==2.13.4`, `fastapi==0.139.2`, `sqlalchemy==2.0.51`, `mcp==1.28.1`, `a2a-sdk==1.1.1` | |
| B44 | §3.2: `[tool.uv] exclude-newer = "P3D"` together with the pinned versions | WRONG | Seven pinned or floored packages were uploaded inside the three-day window (times in section 3, error 4); uv settings reference for `exclude-newer` | Add `exclude-newer-package` exemptions as ADK does (`pyproject.toml:446-451`) |
| B45 | §3.2: extras `google-adk[mcp]`, `[a2a]`, `[db]` exist | CONFIRMED | `METADATA` `Provides-Extra` entries | |
| B46 | §3.2: `uv run adk web --no_use_local_storage .` | CONFIRMED | `cli/cli_tools_click.py:966` | |
| B47 | §4 Phase 3 / 4: `@node(parallel_worker=True)`; `ServiceTier.DEFERRED` with `use_interactions_api=True`; `E2B` / `Daytona` environments; `to_mcp_server()` | CONFIRMED | `workflow/_node.py:58`; `models/google_llm.py:173`; `integrations/e2b/__init__.py:36`; `integrations/daytona/__init__.py:36` | |
| B48 | §5 matrix: `LlmAgent(mode="task")` and `single_turn` agents as graph nodes; `(FunctionNode, LlmAgent) → JoinNode`; read-only `FunctionTool` | CONFIRMED | `workflow/utils/_workflow_graph_utils.py:146-171`; `adk_docs_py/graphs_data-handling.md:259`; changelog: "Support state-based resumption for task-mode agent workflow nodes" | |
| B49 | §6: gates on `token_usage_v1`, `inference_call_count_v1`, `invocation_duration_v1` through `adk eval` | CONFIRMED | As A99. These metrics are informational only: setting a threshold raises `ValueError` (guide `:180-181`), so a gate must compare the numbers itself | |
| B50 | §5 / §6: security rows list `tool_filter` as a day-one control | WRONG | As A74 | |

### 5.3 File C: `research_notes/04-validation-audit-and-improvement-options.md` (ADK rows)

| ID | Claim (section) | Verdict | Evidence | Correct API where not confirmed |
| --- | --- | --- | --- | --- |
| C01 | First pass, "exact imports": `START`, `EventsCompactionConfig`, `SkillToolset`, `SqliteSessionService` locations | CONFIRMED | As A04, A06, A15, A12 | |
| C02 | First pass, `@node` and `JoinNode` gotchas | CONFIRMED | As A45, A49, A35 | |
| C03 | First pass, HITL / caching / built-ins | CONFIRMED | As A63, A70, A69, A72. The loop-scoped id is a recommendation | |
| C04 | Second pass, telemetry default | CONFIRMED | As A86 | |
| C05 | Second pass, `ToolCallIntegrityPlugin` scope | CONFIRMED | As A80 | |
| C06 | Second pass, `BufferedSessionService` flushing | CONFIRMED | As A85 | |
| C07 | Second pass, `ServiceTier.DEFERRED` "silently has no effect" without the interactions API | CONFIRMED | As A84. A warning is logged once per run | |
| C08 | Second pass, node-as-tool typing and idioms | CONFIRMED | As A91, A92, A89 | |
| C09 | Second pass, `get_fast_api_app(agents_dir=…)` | CONFIRMED | As A20 | |
| C10 | Third pass and improvement 2: the fix is to "pair `EnvironmentToolset(…, tool_filter=…)` least-privilege exclusion" (cites `base_toolset.py`) | WRONG | As A74. `base_toolset.py` defines the filter; `_environment_toolset.py` never applies it | |
| C11 | Third pass, `build_stage_node`: (1) shared names violate rule 1; (2) missing schema forwarding "breaks Rule #8" | PARTLY RIGHT | (1) confirmed; (2) as B34 | |
| C12 | Third pass: `static_instruction` is placed first for caching and "is required by `GEPARootAgentPromptOptimizer`" | PARTLY RIGHT | Caching confirmed; requirement false (A57) | |
| C13 | Third pass: ADK ships `Runner.rewind_async`, `BuiltInPlanner`, `ModelArmorPlugin`, `ToolArgsMatcher`, efficiency evaluators, joint `tools` + `output_schema`, `to_a2a` | CONFIRMED | As A98, A60, A14, A21, A99, A59, A22 | |
| C14 | Fourth pass: `google-adk` 2.15.0 has the 3.14 classifier, a wheel and `constraints-3.14.txt` | CONFIRMED | `METADATA`; PyPI (`py3-none-any` wheel); repo root | |
| C15 | Fourth pass: `google-genai` 3.6.1 exists but ADK bounds `<3` | CONFIRMED | As A25 | |
| C16 | Fourth pass: ranges `pydantic>=2.12,<3`, `fastapi>=0.133,<1`, `sqlalchemy>=2,<3` | CONFIRMED | `METADATA` | |
| C17 | Fourth pass: `mcp` 2.3.0 uses `MCPServer`; `ag-ui-adk` 0.13.0 pairs with `google-adk<3` | CONFIRMED | As A26, A27 | |
| C18 | Fourth pass: `litellm` 1.110.2 listed among verified, compatible conventions | PARTLY RIGHT | The version exists; the ADK bound was not noticed (B05) | |
| C19 | Fifth pass: `LocalEnvironment` on Windows | CONFIRMED | As A107 | |
| C20 | Fifth pass: `BuiltInPlanner` on Copilot models "crash" unless guarded | PARTLY RIGHT | As A103 | |
| C21 | Fifth pass: LiteLLM and Copilot quirks | UNVERIFIABLE | As A105 | |
| C22 | Improvement 3: `ModelConsultTool` with `max_uses` / `session_max_uses`, `ForceEscalationPlugin`, `ModelConsultObservabilityPlugin` | CONFIRMED | As A69 | |
| C23 | Improvement 4: `ContextCacheConfig` and `EventsCompactionConfig` on `App` | CONFIRMED | `apps/app.py:83-87` | |
| C24 | Improvement 5: swap `LocalEnvironment` for `E2BEnvironment` / `DaytonaEnvironment` | CONFIRMED | As A16 | |
| C25 | Improvement 8: use `GEPARootAgentPromptOptimizer` to "tune `static_instruction` systematically" | WRONG | As A57 | |
| C26 | Improvement 9: `ToolCallIntegrityPlugin` stamps and `ToolConfirmation` | CONFIRMED | As A80, A65 | |
| C27 | Improvement 10: drift check on `ServiceTier.DEFERRED` | CONFIRMED | As A84 | |
| C28 | Improvement 15: `FallbackModel` (429/503), retry plugins, `RunConfig(...)`, `BufferedSessionService` with `flush_session()`, `ServiceTier.DEFERRED` | CONFIRMED | As A77, A78, A81–A85 | |
| C29 | Improvement 16: `BaseMemoryService`, `ArtifactService`, AG-UI workbench | CONFIRMED | As A87, A88, A94 | |
| C30 | Improvement 17: "`BaseToolset(tool_filter=…)` least-privilege" | WRONG | As A74 | |
| C31 | Improvement 19: `static_instruction` for caching "& GEPA optimization", thinking budgets, efficiency evals, `ToolArgsMatcher` | PARTLY RIGHT | All correct except the GEPA link (A57) | |
| C32 | Improvement 20: `Runner.rewind_async`, `to_a2a` / `RemoteA2aAgent` | CONFIRMED | As A98, A101 | |
| C33 | Improvement 14: `(LlmNode, PythonNode) → JoinNode` with cloned names and forwarded schemas | CONFIRMED | As B03 | |

## 6. Material omissions

Constraints the documents never mention and that change how the plan has to be built.

1. **`LocalEnvironment` is not a sandbox.** It runs shell commands on the host, and "the subprocess inherits everything the host process has", including API keys and tokens in the environment (guide: `docs/guides/environment/base_environment/index.md:180`). Together with error 1 this is the largest gap in the security design.
2. **Experimental status.** `FallbackModel`, `BufferedSessionService`, `ToolArgsMatcher`, `GEPARootAgentPromptOptimizer` and `TelemetryConfig` may change between releases, and the plan pins exactly one release.
3. **`ServiceTier.DEFERRED` cannot be combined with `StreamingMode.SSE`.** `RunConfig` raises a validation error and `/run_sse` returns 422 (`agents/run_config.py:373-393`; guide: `service_tier/index.md:172`, `:228`). `default_run_config()` defaults to SSE.
4. **`get_fast_api_app` defaults to `use_local_storage=True`** (`cli/fast_api.py:115`), so `get_fast_api_app(agents_dir=…, web=False)` writes `.adk/session.db` just as `adk web` does. Pass `use_local_storage=False` or a `session_service_uri`.
5. **Telemetry settings have an admin lock and a blind spot.** `ADK_TELEMETRY_IGNORE_RUN_CONFIG` overrides per-run settings, and when `opentelemetry-instrumentation-google-genai` is installed the inference span follows that library's own variables (`telemetry/context.py:51`, `:204-209`).
6. **`FallbackModel` does not fall back after the first streamed chunk**, and tries each model once (`models/_fallback_model.py:210-250`). With SSE on, a mid-stream failure propagates.
7. **`ToolCallIntegrityPlugin` covers function calls only.** Function responses (the human's answer to `adk_request_input`), session state and completed node outputs are not stamped; it must be registered before other plugins; its errors surface as `RuntimeError` (guide: `tool_call_integrity_plugin/index.md:180-185`; `plugins/_tool_call_integrity_plugin.py:173-178`).
8. **`BufferedSessionService` loses unflushed writes on a crash**, is tied to one event loop, is not thread-safe, and `Runner.run` cancels in-flight writes (guide: `buffered_session_service/index.md:205-217`). That works against durable HITL checkpoints.
9. **Resumption is best effort and at-least-once.** Tools must be idempotent and `temp:` state is lost (`apps/_configs.py:33-36`).
10. **Graph validation is structural only.** A route that matches no edge ends the branch with a log warning, not an error (`workflow/_graph.py:179-185`; guide: `graph/index.md:232`).
11. **`max_llm_calls` is one budget per invocation**, shared by every node in the workflow run (guide: `run_config/index.md:106`). Forty calls for a whole pipeline run may be tight.
12. **Model strings.** A bare `gpt-4.1` resolves to `OpenAILlm`, and `github_copilot/…` matches no registry pattern (`models/__init__.py:80-104`). The Copilot arm must always pass `LiteLlm(...)` instances, including to `ModelConsultTool(model=…)`, whose default advisor is a Gemini model.
13. **`BaseMemoryService` is keyed by `(app_name, user_id)` only** (`memory/base_memory_service.py:124-129`). The planned `(app_name, project_id)` partition has to be encoded into one of those two values.
14. **Efficiency metrics are not produced by the `adk web` evaluation path**, only by `adk eval` and `AgentEvaluator` (guide: `efficiency_evaluators/index.md:185-188`).
15. **`ag_ui_adk.ADKAgent` defaults**, read from the 0.13.0 wheel and not otherwise verified: `use_in_memory_services=True`, `session_timeout_seconds=1200`, `delete_session_on_cleanup=True`, `save_session_to_memory_on_cleanup=True`. The last one conflicts with human-approved-only memory ingestion.
16. **`Runner.rewind_async` rewinds session state and artifacts.** Nothing in `runners.py:1395-1433` touches the working tree, so files and git changes made by tools are not undone.
17. **Python 3.15 is the current stable line** (3.15.2) and ADK declares support for it. Targeting `>=3.14,<3.15` is a choice, not something ADK requires.
