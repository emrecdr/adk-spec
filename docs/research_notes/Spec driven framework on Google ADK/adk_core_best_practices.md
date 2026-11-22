# Google ADK for Python: core architecture and official best practices (as of 2026-11-20)

> **Version verified against: google-adk 2.15.0.** Where: PyPI JSON API (`https://pypi.org/pypi/google-adk/json`, `info.version` = 2.15.0, `requires_python` = `>=3.11`) and the GitHub releases page (`v2.15.0`, dated 19 Nov 2026, marked "Latest"). Both were read on 2026-11-20.
>
> **Documentation verified against:** the official docs at `https://adk.dev` (the old `google.github.io/adk-docs` address returns a 301 redirect to adk.dev). The content was read from the docs' own full-text export, `https://adk.dev/llms-full.txt`, downloaded on 2026-11-20; citations below point to the corresponding page. The docs are a single unversioned "latest" set. Pages carry "Supported in ADK Python vX" badges, but they do not say which 2.x point release each snippet was last tested with.
>
> **Limits of this verification:** nothing was installed or executed. Code snippets are copied or trimmed from the docs and the README, not run against 2.15.0. Where two official pages disagree, the conflict is flagged rather than resolved.

## What is the current stable version of the `google-adk` Python package, what changed in recent major releases, and what Python versions are supported?

### Takeaway
The current stable release is google-adk 2.15.0 (19 Nov 2026), which requires Python 3.11 or later. ADK 2.0 went GA for Python on 19 May 2026 and replaced the hierarchical agent executor with a graph-based Workflow Runtime; 2.x minors ship roughly every two weeks and several carry their own breaking changes.

### Cited Findings
- PyPI reports `info.version` 2.15.0, `requires_python` `>=3.11`, classifiers for Python 3.11 through 3.15. — [PyPI JSON API](https://pypi.org/pypi/google-adk/json)
- GitHub marks v2.15.0 (19 Nov 2026) as "Latest". Preceding releases: v2.14.1 (12 Nov), v2.14.0 (7 Nov), v2.13.0 (23 Oct), v2.12.0 (13 Oct), v2.11.0 (2 Oct), v2.10.0 (25 Sep), v2.9.2 (18 Sep), v2.9.1 (15 Sep), v2.9.0 (10 Sep 2026). — [adk-python releases](https://github.com/google/adk-python/releases)
- The README says Python 3.11+ is required, constraints files exist for Python 3.11 through 3.15, and the release cadence is "roughly bi-weekly". Install with `pip install google-adk`; optional integrations with `pip install "google-adk[extensions]"`. — [adk-python README](https://github.com/google/adk-python/blob/main/README.md)
- Conflict: the Python quickstart still lists "Python 3.10 or later" and the MCP page says "Python 3.10+". PyPI metadata and the README say 3.11+, so 3.11 is the real floor for 2.x. — [Python Quickstart](https://adk.dev/get-started/python/); contradicted by [PyPI JSON API](https://pypi.org/pypi/google-adk/json)
- "ADK Python 2.0 is released for general availability as of May 19, 2026." Headline features: graph-based workflows, dynamic workflows, collaborative workflows. — [Welcome to ADK 2.0](https://adk.dev/2.0/)
- 1.x to 2.0 breaking change, event schema: "ADK 2.0 introduces new fields `node_info` and `output` to the core Event schema". Custom `BaseSessionService` implementations with rigid columns must update their schema (JSON-blob stores need no change); strict JSON validators with `additionalProperties: false` reject 2.0 events until updated. — [Welcome to ADK 2.0](https://adk.dev/2.0/)
- 1.x to 2.0 breaking change, execution: "the BaseAgent class now subclasses BaseNode ... Custom overrides of 1.x abstract methods, such as `_run_async_impl()` or `generate_content()`, are no longer the correct way to drive execution. The Workflow Graph engine completely bypasses these legacy overrides. If you inject custom telemetry or state management by overriding these methods, those calls are silently ignored." — [Welcome to ADK 2.0](https://adk.dev/2.0/)
- 1.x to 2.0 breaking change, events: "Do not append events directly to the session, and do not use `enqueue_event` directly. You must now explicitly yield the event from within your node or agent." — [Welcome to ADK 2.0](https://adk.dev/2.0/)
- 1.x to 2.0 breaking change, exceptions: a broad `except Exception:` inside a tool "masks the failure from the framework, permanently disabling the new 2.0 automatic retry mechanisms for that step"; catching `BaseException` "traps `NodeInterruptedError`, which breaks the framework's ability to pause the workflow for Human-in-the-Loop (HITL) input". — [Welcome to ADK 2.0](https://adk.dev/2.0/)
- To stay on 1.x: `pip install "google-adk~=1.0"`. The last 1.x release seen on PyPI in this check was 1.30.0 (13 Apr 2026). — [Welcome to ADK 2.0](https://adk.dev/2.0/); [PyPI JSON API](https://pypi.org/pypi/google-adk/json)
- Deprecation: "In Python and TypeScript, `SequentialAgent`, `ParallelAgent`, and `LoopAgent` are deprecated: constructing one emits a deprecation warning, and the classes are scheduled for removal in a future release. The examples below still run. For new code, express these patterns with a graph-based workflow; note that a `Workflow` cannot yet be used as an `LlmAgent` sub-agent." — [Multi-agent workflow patterns](https://adk.dev/workflows/patterns/)
- Deprecation: use `GlobalInstructionPlugin` "instead of the deprecated `global_instruction` parameter". — [Simple agents with LlmAgent](https://adk.dev/agents/llm-agents/)
- Unification: "In Python and TypeScript, `CallbackContext` and `ToolContext` are unified into a single `Context` type, and in Python both names remain usable as aliases of it." — [State](https://adk.dev/sessions/state/)
- Breaking changes listed for recent 2.x minors (quoted from the releases page):
  - v2.15.0: "The `/dev/apps/{app_name}/builder*` routes and `google.adk.cli.built_in_agents` are removed."; "`McpInstructionProvider` no longer auto-fills prompt arguments from `session.state`."
  - v2.14.0: "`FunctionTool` parameters annotated `Enum`, `Optional[Enum]`, or `list[Enum]` now receive enum members"; "`VertexAiSessionService.create_session` accepts only session config options"; "`RunSkillScriptTool` no longer takes `command` in environment mode".
  - v2.13.0: "Defaults to OpenTelemetry GenAI v2 (`otel_semconv_1_44`, removing `call_llm`)".
  - v2.9.0 (listed as behavior changes): failed workflow nodes rerun on resume; in-memory sessions raise an error on appends to unknown sessions.
  — [adk-python releases](https://github.com/google/adk-python/releases)
- Features by release: v2.15.0 buffered session service, unified artifact service for cloud stores, pass@k multi-run evaluation; v2.14.0 stabilized environment, A2A and evaluation modules; v2.13.0 twelve experimental features promoted to stable, `ClassifierNode`; v2.12.0 `after_tool_callback` for filtering tool output, `require_confirmation` for workflow nodes, Python 3.15 support; v2.11.0 `abort_signal` cancellation, tool confirmation in workflows, SQLite memory service; v2.9.0 `FallbackModel`, graphs loadable from YAML. — [adk-python releases](https://github.com/google/adk-python/releases)
- Renames: the managed runtime is now "Agent Runtime on Gemini Enterprise Agent Platform (formerly Vertex AI Agent Engine)". "`GOOGLE_GENAI_USE_ENTERPRISE` was previously `GOOGLE_GENAI_USE_VERTEXAI` ... These variable names are equivalent." — [adk-python README](https://github.com/google/adk-python/blob/main/README.md); [Connect to Google Cloud](https://adk.dev/get-started/google-cloud/)
- Security advisory: "Unauthorized code was identified in LiteLLM versions 1.82.7 and 1.82.8 on PyPI on March 24, 2026"; ADK now requires `litellm>=1.84`. — [LiteLLM connector](https://adk.dev/agents/models/litellm/)

### Inferences
- Pin an exact version (for example `google-adk==2.15.0` in a lock file, `>=2.15,<3` in project metadata). Minors have shipped breaking changes about once a month.
- Design for 2.x primitives (`Agent`, `Workflow`, function nodes) from the start. `SequentialAgent`, `ParallelAgent`, `LoopAgent` and `global_instruction` all still run but are on a removal path.

### Gaps
- The PyPI JSON read was truncated before the 2.x upload timestamps; 2.x dates above come from GitHub.
- Breaking-change lists for v2.1 through v2.8 were not read (the releases page shows the ten newest). Read `CHANGELOG.md` before relying on behavior introduced in that range.
- The release note "twelve experimental features promoted to stable" (v2.13.0) was not expanded, so which features are stable versus experimental in 2.15.0 is only known where a docs page says so.

## What is the recommended project layout and how are projects run?

### Takeaway
The minimum project is a package folder with `__init__.py`, `agent.py` exposing `root_agent` (an `Agent` or a `Workflow`), and `.env`; an optional `App` object named `app` adds plugins, caching, compaction and resumability. For projects meant to be tested and deployed, Google's Agents CLI scaffolds an `app/` plus `tests/{unit,integration,eval}` layout.

### Cited Findings
- `adk create my_agent` produces:
  ```text
  my_agent/
      agent.py      # main agent code
      .env          # API keys or project IDs
      __init__.py
  ```
  "The `agent.py` file contains a `root_agent` definition which is the only required element of an ADK agent." — [Python Quickstart](https://adk.dev/get-started/python/)
- "For ADK tools compatibility, the root agent must be named `root_agent`" (comment in the loop-agent sample). — [Loop template workflow](https://adk.dev/agents/workflow-agents/loop-agents/)
- `App` is optional and is "a top-level container for an entire ADK agent workflow". It configures context caching, context compression, agent resume and plugins. "Set your App object to the variable name `app` so it is compatible with the ADK command line interface runner tools."
  ```python
  from google.adk.agents.llm_agent import Agent
  from google.adk.apps import App

  root_agent = Agent(model="gemini-flash-latest", name="greeter_agent",
                     description="An agent that provides a friendly greeting.",
                     instruction="Reply with Hello, World!")

  app = App(
      name="agents",
      root_agent=root_agent,
      # plugins, context_cache_config, events_compaction_config, resumability_config
  )
  ```
  — [App class](https://adk.dev/apps/)
- Running programmatically: `runner = InMemoryRunner(app=app)` then `await runner.run_debug("Hello there!")` (`run_debug` needs ADK Python 1.18+). The classic form is `Runner(agent=..., app_name=..., session_service=..., artifact_service=...)` with `runner.run_async(user_id=..., session_id=..., new_message=types.Content(...))`. — [App class](https://adk.dev/apps/); [Artifacts](https://adk.dev/artifacts/)
- Agents CLI scaffold (recommended "when you plan to test, evaluate, and deploy an agent"; `adk create` is for a single-file learning agent):
  ```text
  my-agent/
      app/
          agent.py                # main agent code
          fast_api_app.py         # server, telemetry, and routes
          app_utils/              # session and artifact services
      tests/
          eval/                   # evaluation datasets and metrics
          integration/            # end-to-end agent tests
          unit/
      pyproject.toml
      agents-cli-manifest.yaml
      Dockerfile
      GEMINI.md                   # project guidance for coding agents
      .env
  ```
  Install with `uvx google-agents-cli setup`; requires Python 3.11+, `uv` and Node.js; run locally with `agents-cli playground`. — [Agents CLI Quickstart](https://adk.dev/get-started/agents-cli/)
- `adk run my_agent` starts an interactive terminal session; `adk run path/to/my_agent "hello"` sends one message and exits. Python-only session options: `--save_session`, `--session_id`, `--resume <file>.session.json`, `--replay <input.json>` (replay file holds `state` and `queries`). — [Command Line](https://adk.dev/runtime/command-line/)
- `adk web --port 8000` starts the dev UI; run it "from the parent directory that contains your `my_agent/` folder". "ADK Web is not meant for use in production deployments." — [Python Quickstart](https://adk.dev/get-started/python/)
- Local storage defaults for the Python CLI: `--session_service_uri` defaults to "Per-agent SQLite at `<agents_dir>/<agent>/.adk/session.db`", `--artifact_service_uri` to "Per-agent directory at `<agents_dir>/<agent>/.adk/artifacts`", `--memory_service_uri` to in-memory. Example: `adk web --port 3000 --session_service_uri "sqlite:///sessions.db"`. — [Command Line](https://adk.dev/runtime/command-line/); [Web Interface](https://adk.dev/runtime/web-interface/)
- `adk api_server` exposes agents over REST for programmatic testing; the confirmation and resume docs post to `/run` and `/run_sse` with `app_name`, `user_id`, `session_id`, and `new_message` or `invocation_id`. — [API Server](https://adk.dev/runtime/api-server/); [Resume](https://adk.dev/runtime/resume/)
- `adk eval <agent_folder> <file>.evalset.json --config_file_path <eval_config.json>` runs evaluations; test folders may hold a `test_config.json` with criteria. — [adk-python README](https://github.com/google/adk-python/blob/main/README.md); [Why evaluate agents](https://adk.dev/evaluate/)
- Skills, if used, live in directories that follow the Agent Skills specification (`SKILL.md` required; optional `references/`, `assets/`, `scripts/`) and are loaded with `load_skill_from_dir` and `SkillToolset`. — [Skills](https://adk.dev/skills/)

### Inferences
- The docs prescribe only `agent.py` + `root_agent` (+ optional `app`). Splitting into `sub_agents/`, `tools/`, `prompts.py` modules is a convention seen in samples, not a framework requirement; any importable layout works as long as `agent.py` exposes `root_agent`.
- For a spec-driven framework, the Agents CLI layout (`app/agent.py`, `tests/unit`, `tests/integration`, `tests/eval`) is the closest thing to an official "production" structure.

### Gaps
- No docs page read here prescribes where prompts, sub-agent modules or tool modules should live.
- `adk api_server` endpoint reference beyond `/run` and `/run_sse` was not read.

## What agent types exist and when does the documentation recommend each?

### Takeaway
In 2.x there are two primary classes: `Agent` (alias of `LlmAgent`) for model-driven reasoning, and `Workflow` for orchestration over nodes (agents, plain functions, tools, human-input steps, nested workflows). The docs steer new code to graph or dynamic workflows and mark the template agents and custom `BaseAgent` orchestration as superseded.

### Cited Findings
- "ADK applications are built using two main classes: `Agent` (defines instructions, tools, and behavior) and `Workflow` (orchestrates agents and tasks in a graph-based flow)." — [adk-python README](https://github.com/google/adk-python/blob/main/README.md)
- "In ADK, any agent application that has more than one agent or executable Node is considered a workflow." Stated reasons to move off a single agent: instruction-following degrades with long multi-step instructions; context-window limits; code modularity; mixing deterministic and non-deterministic tasks. — [Agents](https://adk.dev/agents/)
- Workflow styles: graph-based ("a declarative graph of nodes and edges with explicit routing, best for deterministic, structured processes"); dynamic ("programmatic orchestration in your own code (loops, conditionals, recursion), best when the control flow is too complex or iterative for a static graph"); prebuilt workflow agents (sequential, parallel, loop). The workflows overview adds collaborative workflows (a coordinator agent with sub-agents). — [Graph-based agent workflows](https://adk.dev/graphs/); [Workflows](https://adk.dev/workflows/)
- Minimal graph (imports are top-level: `from google.adk import Agent, Workflow, Event, Context`):
  ```python
  from google.adk import Agent, Workflow, Event
  from pydantic import BaseModel

  class CityTime(BaseModel):
      time_info: str
      city: str

  city_generator_agent = Agent(
      name="city_generator_agent", model="gemini-flash-latest",
      instruction="Return the name of a random city. Return only the name, nothing else.",
  )

  def lookup_time_function(node_input: str):
      return CityTime(time_info="10:10 AM", city=node_input)

  city_report_agent = Agent(
      name="city_report_agent", model="gemini-flash-latest", input_schema=CityTime,
      instruction="You receive a CityTime with time_info and city fields. Output one line stating the time in that city.",
  )

  def completed_message_function(node_input: str):
      return Event(message=f"{node_input}\n WORKFLOW COMPLETED.")

  root_agent = Workflow(
      name="root_agent",
      edges=[("START", city_generator_agent, lookup_time_function,
              city_report_agent, completed_message_function)],
  )
  ```
  — [Graph-based agent workflows](https://adk.dev/graphs/)
- Why graphs: "Define precise logic", "Run chains of functions without AI", "Enhance reliability: improve the predictability of your agents by relying on structured node definitions rather than prompts alone." As instructions get longer, "making sure that the agent is following each step and guideline becomes more complicated and less reliable." — [Graph-based agent workflows](https://adk.dev/graphs/)
- Nodes "can be Agents, ADK Tools, human input tasks, or code functions you write". Explicit wrappers: `@node(name=..., rerun_on_resume=..., retry_config=..., timeout=...)` and `FunctionNode(func=..., name=...)` from `google.adk.workflow`. — [Graph routes](https://adk.dev/graphs/routes/); [Dynamic workflows](https://adk.dev/graphs/dynamic/)
- Conditional routing: a function node returns `Event(route="KEY")` (a list dispatches to several branches) and an edge row maps keys to nodes:
  ```python
  def router(node_input: str):
      return Event(route="RETRY" if needs_work(node_input) else "DONE")

  root_agent = Workflow(name="looping_workflow", edges=[
      ("START", task_A_node, router),
      (router, {"RETRY": task_A_node, "DONE": final_task_node}),
  ])
  ```
  "A cycle must contain at least one routed, or conditional, edge." "A graph cycle is not bounded automatically"; the docs suggest a dynamic workflow when the bound should live in code. — [Graph routes](https://adk.dev/graphs/routes/)
- Fan-out and join: put `"START"` (or a shared source) in several edge rows and merge with `JoinNode(name=...)` from `google.adk.workflow`; the join passes a record keyed by predecessor node name. "Make sure that every node that feeds a join has an output of its own." — [Graph routes](https://adk.dev/graphs/routes/)
- Nested workflows: "A `Workflow` is itself a node." "A workflow must have at most one terminal node that produces output", otherwise it fails with `ValueError`. — [Graph routes](https://adk.dev/graphs/routes/)
- Dynamic workflow (ordinary Python control flow, with checkpointing: "Successful sub-nodes are automatically skipped when resuming the workflow"):
  ```python
  from google.adk import Context, Event, Workflow
  from google.adk.workflow import node

  @node(rerun_on_resume=True)
  async def code_workflow(ctx: Context, node_input: str):
      code = await ctx.run_node(coder_agent, node_input)
      check = await ctx.run_node(compile_lint_check, code)
      while check.findings:
          yield Event(state={"code": code, "findings": check.findings})
          code = await ctx.run_node(fixer_agent, {"code": code, "findings": check.findings})
          check = await ctx.run_node(compile_lint_check, code)
      yield Event(output=code)

  root_agent = Workflow(name="root_agent", edges=[("START", code_workflow)])
  ```
  "Parent nodes in dynamic workflows that call `ctx.run_node` must set `rerun_on_resume=True`." Parallelism: `asyncio.gather` over `ctx.run_node(worker, item, use_sub_branch=True)`. — [Dynamic workflows](https://adk.dev/graphs/dynamic/)
- Retries and timeouts per node: `@node(retry_config=RetryConfig(max_attempts=3, initial_delay=1.0, exceptions=[MyError, NodeTimeoutError]), timeout=10.0)`, importing `RetryConfig` and `NodeTimeoutError` from `google.adk.workflow`. Defaults: 5 attempts, 1 s initial delay, 60 s max delay, backoff 2.0, jitter 1.0, all errors retried. Guidance: "Retry only transient errors", "Make retried work safe to repeat". The attempt count is not saved across a pause or restart. — [Retries and timeouts](https://adk.dev/graphs/retry/)
- Agents inside a graph: "An agent used as a graph node defaults to `single_turn` mode; a `chat` mode agent is only allowed directly after `START`, because it consumes conversational history rather than a node input." — [Graph routes](https://adk.dev/graphs/routes/)
- Template agents: "In ADK Python, TypeScript, Go, and Kotlin, template workflows have been superseded by more flexible workflow structures, including graph-based workflows and dynamic workflows." — [Template agent workflows](https://adk.dev/agents/workflow-agents/)
- Custom agents: "Starting in ADK 2.0, agent-based workflows using `BaseAgent` have been superseded by more flexible workflow structures ... You should evaluate the capabilities of these workflow mechanisms before building a custom agent." The same page still documents subclassing `BaseAgent` and implementing `async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]`. — [Custom agent template workflows](https://adk.dev/agents/custom-agents/)
- Conflict: the 2.0 migration page says `_run_async_impl()` overrides are bypassed and "silently ignored" by the Workflow Graph engine, while the custom-agents and patterns pages still present `_run_async_impl` subclasses as working code. — [Welcome to ADK 2.0](https://adk.dev/2.0/); contradicted by [Custom agent template workflows](https://adk.dev/agents/custom-agents/)
- Other agent kinds listed: managed agents (Google first-party agents via the Managed Agents API), Agent Config ("build agents without code"; page not read), and experimental Agent Routing (router functions choosing between agents for fallback or A/B testing). — [Agents](https://adk.dev/agents/); [adk-python README](https://github.com/google/adk-python/blob/main/README.md); [Workflows](https://adk.dev/workflows/)
- Known limitation: "Some third-party integrations may not be compatible with graph-based workflows." — [Graph-based agent workflows](https://adk.dev/graphs/)

### Inferences
- For a staged spec pipeline (interview, requirements, plan, tasks, validate, implement), the 2.x docs point to a `Workflow` root with `Agent` nodes for writing and plain function nodes for deterministic steps (validation, file writes, routing).
- Bounded review-and-fix loops fit dynamic workflows (`while` with a counter) better than graph back-edges, which the docs warn are unbounded.
- Avoid new `BaseAgent` subclasses for deterministic logic until the `_run_async_impl` conflict is tested on the installed version; function nodes are the unambiguous 2.x route.

### Gaps
- Whether a `BaseAgent` subclass with `_run_async_impl` still executes under 2.15.0 when placed in a `Workflow` or run as root was not tested; the official pages disagree.
- `ClassifierNode` (added v2.13.0) and YAML-defined graphs (v2.9.0) were seen only in release notes; their docs were not read.

## How should multi-agent systems be composed?

### Takeaway
Use `sub_agents` with an explicit `mode` (`chat`, `task`, `single_turn`) for LLM-driven delegation, and a `Workflow` when order must be deterministic. For Python the docs now prefer a `single_turn` sub-agent over wrapping an agent in `AgentTool`. Clear `description` fields drive routing.

### Cited Findings
- Sub-agent modes: `chat` (default; full user interaction, manual return via transfer), `task` (asks the user for clarification only; automatic return via `finish_task`), `single_turn` (no user interaction; returns immediately with a result; can run in parallel). — [Collaborative agent teams](https://adk.dev/workflows/collaboration/)
- Coordinator with typed sub-agents; ADK "auto-injects delegation tools named after each subagent":
  ```python
  from google.adk import Agent

  weather_agent = Agent(name="weather_checker", mode="single_turn", tools=[get_weather])
  flight_agent = Agent(name="flight_booker", mode="task",
                       input_schema=FlightInput, output_schema=FlightResult,
                       tools=[search_flights, book_flight])
  root = Agent(name="travel_planner", sub_agents=[weather_agent, flight_agent])
  ```
  — [Collaborative agent teams](https://adk.dev/workflows/collaboration/)
- "The mode setting is intended specifically for use with subagents invoked by a coordinator parent agent. Do not configure a root agent with the mode setting." "Task mode agents must be leaf agents and cannot have subagents." — [Collaborative agent teams](https://adk.dev/workflows/collaboration/)
- "The collaborative mode `task` behavior is disabled for use in graph-based workflows in ADK Python v2.0.0. This feature is expected to be re-enabled in a future release." — [Collaborative agent teams](https://adk.dev/workflows/collaboration/)
- Context isolation: "Each task or single-turn mode agent operates in its own isolated session branch", sees only its own branch's events, and the parent receives collected results once parallel branches complete. — [Collaborative agent teams](https://adk.dev/workflows/collaboration/)
- Reuse: the same task or single-turn agent works as a workflow node (control advances to the next node) or as a transferee of an `LlmAgent` (control returns to the originating agent). — [Collaborative agent teams](https://adk.dev/workflows/collaboration/)
- `description` is "primarily used by other LLM agents to determine if they should route a task to this agent. Make it specific enough to differentiate it from peers (e.g., 'Handles inquiries about current billing statements,' not just 'Billing agent')." Names must be valid Python identifiers; `user` is reserved. — [Simple agents with LlmAgent](https://adk.dev/agents/llm-agents/)
- Sub-agent versus agent-as-tool: with a tool call, "Agent B's answer is passed back to Agent A ... Agent A retains control"; with a (chat) sub-agent, "the responsibility of answering the user is completely transferred to Agent B". — [Function tools](https://adk.dev/tools-custom/function-tools/)
- "For standard inline delegation in ADK Python, prefer setting `mode="single_turn"` on a sub-agent and attaching it with `sub_agents=[...]` rather than wrapping it in `AgentTool`. ADK exposes the sub-agent as a tool and runs it inline in the parent's session." `AgentTool(agent=...)` (from `google.adk.tools.agent_tool`) still exists, with `skip_summarization` and `propagate_grounding_metadata` options. — [Function tools](https://adk.dev/tools-custom/function-tools/)
- Coordinator/dispatcher: a central `LlmAgent` with specialists in `sub_agents`; LLM-driven delegation "requires clear `description`s on sub-agents and appropriate `instruction` on Coordinator". — [Multi-agent workflow patterns](https://adk.dev/workflows/patterns/)
- Sequential pipeline, parallel fan-out/gather and generate-and-review are documented with `output_key` writing to shared state and later agents reading `{key}` in instructions, e.g. `LlmAgent(name="DraftWriter", ..., output_key="draft_text")` followed by a reviewer whose instruction contains `{draft_text}`. These examples use the deprecated template agents. — [Multi-agent workflow patterns](https://adk.dev/workflows/patterns/)
- Iterative refinement is documented with `LoopAgent(max_iterations=5, ...)` ending when a checker yields `Event(author=self.name, actions=EventActions(escalate=True))`; the 2.x equivalents are a routed back-edge or a dynamic-workflow loop. — [Multi-agent workflow patterns](https://adk.dev/workflows/patterns/); [Graph routes](https://adk.dev/graphs/routes/)
- Human-in-the-loop: "ADK has no Human Agent agent type, but you do not have to build the pause yourself: yield a `RequestInput` event from a graph workflow node, or enable tool confirmation on a `FunctionTool` for a yes/no approval." — [Multi-agent workflow patterns](https://adk.dev/workflows/patterns/)
- Graph human-input node:
  ```python
  from google.adk.events import RequestInput
  from google.adk import Workflow

  def ask_user():
      yield RequestInput(message="Enter a number:")

  def double(node_input):
      return node_input * 2

  root_agent = Workflow(name="root_agent", edges=[("START", ask_user, double)])
  ```
  `RequestInput` takes `message`, `payload` (structured data for the client to render) and `response_schema`. "A response schema does not reformat a human reply ... collect structured data in your client interface, or place an agent node after the pause to convert the reply into the required format." These nodes "do not require artificial intelligence (AI) models to run". — [Human input](https://adk.dev/graphs/human-input/)
- In dynamic workflows the leaf that yields `RequestInput` uses `@node(rerun_on_resume=False)` and the orchestrator that calls it uses `rerun_on_resume=True`; `await ctx.run_node(get_user_approval)` returns the reply. — [Dynamic workflows](https://adk.dev/graphs/dynamic/)
- Cross-cutting rules: "Apply consistent rules across your workflow using the `GlobalInstructionPlugin` on your `App`." — [Collaborative agent teams](https://adk.dev/workflows/collaboration/)
- Model inheritance: an agent without `model` "inherits the model of its nearest `LlmAgent` ancestor"; `LlmAgent.set_default_model("...")` sets a process-wide default. — [Simple agents with LlmAgent](https://adk.dev/agents/llm-agents/)

### Inferences
- An interview stage maps to either a `task`-mode sub-agent (may ask clarifying questions, returns automatically) or `RequestInput` nodes in a graph. Approval gates on generated specs map naturally to `RequestInput` with the draft as `payload`.
- Because "a `Workflow` cannot yet be used as an `LlmAgent` sub-agent", a chat-style coordinator cannot simply delegate to a deterministic pipeline as a sub-agent. The pipeline has to be the root (`Workflow`), or exposed another way; `contributing/samples/workflows/node_as_tool` in adk-python suggests a node-as-tool route, which was not read.
- Generator-critic for spec validation: writer `Agent` node, then a validator (function node for structural checks and/or a critic `Agent` with `output_schema`), then a router with a bounded retry.

### Gaps
- Whether `task` mode in graph workflows was re-enabled between 2.0.0 and 2.15.0 is unconfirmed; the docs sentence still names v2.0.0, and a nearby sentence in the data-handling page (in a passage that mixes languages) says graph agents may run in `single_turn` or `task` mode.
- The `node_as_tool` sample and the "Sub-agent delegation" MCP page were not read.

## How do session, state and memory work, and what are the rules for safe state mutation?

### Takeaway
State is a serializable key-value scratchpad scoped by key prefix and changed only through events: via `output_key`, via `context.state[...]` inside tools, callbacks and nodes, or via `Event(state=...)` / `EventActions(state_delta=...)`. Never mutate a `Session` object fetched from the service. In graph workflows, node `output` is the preferred step-to-step channel and state is for values that must persist or feed `{key}` templates.

### Cited Findings
- Prefixes: no prefix is session-scoped; `user:` is shared across a user's sessions in the app; `app:` is shared across all users and sessions; `temp:` lasts for the current invocation only and is not persisted. A parent and its sub-agents share the same invocation and therefore the same `temp:` state. — [State](https://adk.dev/sessions/state/)
- Values "must be serializable ... Do not store non-serializable objects (custom class instances, functions, connections, etc.) directly in the state." Recap: minimalism, basic serializable types, descriptive keys and prefixes, shallow structures. — [State](https://adk.dev/sessions/state/)
- Instruction templating: `{key}` inserts `session.state[key]`; `{artifact.name}` inserts the text content of an artifact; a missing key raises an error unless written `{key?}`. — [Simple agents with LlmAgent](https://adk.dev/agents/llm-agents/); [State](https://adk.dev/sessions/state/)
- Literal braces: "The `{key}` syntax matches any valid Python identifier inside single curly braces." For JSON examples in prompts, pass a function (an `InstructionProvider` taking `ReadonlyContext`) as `instruction`; then no injection occurs. To combine both, call `await instructions_utils.inject_session_state(template, context)` from `google.adk.utils`. — [State](https://adk.dev/sessions/state/)
- `output_key`: "the agent's final response will be automatically saved to the session's state dictionary under this key". With `output_schema` also set, "ADK parses the response against the schema first and stores the parsed value ... A `BaseModel` schema is stored as a `dict`". — [Simple agents with LlmAgent](https://adk.dev/agents/llm-agents/)
- Recommended update paths: (1) `output_key`; (2) `EventActions(state_delta={...})` on an event passed to `session_service.append_event`; (3) `context.state["k"] = v` inside callbacks and tools, where changes "are automatically captured and correctly routed into the `EventActions.state_delta`".
  ```python
  from google.adk.tools import ToolContext

  def record_choice(choice: str, tool_context: ToolContext) -> dict:
      """Stores the user's choice."""
      tool_context.state["user:last_choice"] = choice
      tool_context.state["temp:last_operation_status"] = "success"
      return {"status": "success"}
  ```
  — [State](https://adk.dev/sessions/state/); [Function tools](https://adk.dev/tools-custom/function-tools/)
- Warning: do not modify `session.state` on a `Session` obtained from `get_session()` or `create_session()`. It "bypasses event history", "changes made this way will likely NOT be saved by `DatabaseSessionService` or `VertexAiSessionService`", and is "not thread-safe". Use such sessions only for reading. — [State](https://adk.dev/sessions/state/)
- In graph nodes: write with `yield Event(state={...})`, read with `ctx.state[...]`. "The state parameter should not be used to persist large amounts of data between nodes. Use artifacts or other data persistence mechanisms." — [Data handling](https://adk.dev/graphs/data-handling/)
- Node event fields: `output` (data for the next node), `message` (user-facing), `state` (persisted), `route` (branch choice). In dynamic workflows, `ctx.run_node(...)` returns the child's output directly, "eliminating the need to manually read and write session state keys for data transfer". — [Data handling](https://adk.dev/graphs/data-handling/); [Dynamic workflows](https://adk.dev/graphs/dynamic/)
- Conflict on multiple outputs: one Python passage says only one yielded event may carry `output` and that two "results in a runtime error"; another passage (written for TypeScript) says later outputs overwrite earlier ones. Treat one `output` per node execution as the rule. — [Data handling](https://adk.dev/graphs/data-handling/)
- Passing data between tools in one turn: "The recommended way to do this is by using the `temp:` prefix in the session state." — [Function tools](https://adk.dev/tools-custom/function-tools/)
- Session services: `InMemorySessionService` (lost on restart); `DatabaseSessionService(db_url="sqlite+aiosqlite:///./my_agent_data.db")`, which "requires an async database driver" (`asyncpg` for PostgreSQL, `aiomysql` for MySQL); `VertexAiSessionService(project=..., location=...)`. The session database schema changed in ADK Python v1.22.0 and needs migration from older versions. — [Session](https://adk.dev/sessions/session/)
- Reading user state without a session: `await session_service.get_user_state(app_name=..., user_id=...)`; `VertexAiSessionService` raises `NotImplementedError` for it. — [State](https://adk.dev/sessions/state/)
- Memory: `BaseMemoryService` offers `add_session_to_memory(session)` and `search_memory(...)`. Python ships `InMemoryMemoryService` (keyword match, prototyping), `VertexAiMemoryBankService` (managed Memory Bank) and `VertexAiRagMemoryService` (needs `pip install google-adk[gcp]`). Agents query memory with the `load_memory` tool or `await tool_context.search_memory(query)`. — [Memory](https://adk.dev/sessions/memory/)
- Context objects: "prefer `Context` in new code; `ReadonlyContext` is the restricted view you get where mutation is disallowed. Use the full `InvocationContext` directly ... only when necessary." — [Agent context](https://adk.dev/context/)
- Resumability: `App(..., resumability_config=ResumabilityConfig(is_resumable=True))`; resume with `runner.run_async(user_id=..., session_id=..., invocation_id=...)` or a POST to `/run_sse` with `invocation_id`. "Resuming a workflow from the ADK Web user interface or using the ADK command line (CLI) tool is not currently supported." — [Resume](https://adk.dev/runtime/resume/)

### Inferences
- For a spec pipeline: keep small routing facts in state (current phase, approval flags, artifact filenames and versions, validation verdicts), pass step results between nodes as typed `output`, and keep document bodies in artifacts.
- Prompt templates containing JSON or other brace-heavy examples should be `InstructionProvider` functions, otherwise ADK tries to resolve the braces as state keys.
- Local runs through `adk web` / `adk run` already persist sessions to a per-agent SQLite file, so multi-session spec work survives restarts without extra setup.

### Gaps
- The docs example shows function nodes declaring a state key as a parameter (`async def task_attempt_node(node_input, attempts: int)`), but the injection rule is not spelled out in the text read here.
- The CLI example uses `sqlite:///my_sessions.db` while `DatabaseSessionService` requires `sqlite+aiosqlite:///`; whether the CLI rewrites the scheme was not confirmed.
- The v2.11.0 SQLite memory service and v2.15.0 buffered session service are in release notes only; their class names were not confirmed in docs.

## How do Artifacts work, and when should they be used versus state versus the real filesystem?

### Takeaway
Artifacts are named, automatically versioned blobs (`google.genai.types.Part`) scoped to a session or, with a `user:` filename prefix, to a user. They are saved and loaded through the context (`await context.save_artifact(...)`), stored by an `ArtifactService` configured on the `Runner`, and are the documented home for large or file-like outputs; state is for small values.

### Cited Findings
- "An Artifact is essentially a piece of binary data ... identified by a unique `filename` string within a specific scope (session or user). Each time you save an artifact with the same filename, a new version is created." Content is a `types.Part` with `inline_data` (`data` bytes plus `mime_type`). — [Artifacts](https://adk.dev/artifacts/)
- Saving and loading from a tool, callback or node (both are async and must be awaited):
  ```python
  import google.genai.types as types
  from google.adk.tools import ToolContext

  async def save_spec(markdown: str, tool_context: ToolContext) -> dict:
      """Saves the spec as a versioned markdown artifact."""
      part = types.Part.from_bytes(data=markdown.encode("utf-8"), mime_type="text/markdown")
      version = await tool_context.save_artifact(filename="spec.md", artifact=part)
      return {"status": "success", "filename": "spec.md", "version": version}

  async def read_spec(tool_context: ToolContext) -> dict:
      """Loads the latest spec."""
      part = await tool_context.load_artifact(filename="spec.md")   # version=N for a specific one
      if not part or not part.inline_data:
          return {"status": "error", "error_message": "spec.md not found"}
      return {"status": "success", "content": part.inline_data.data.decode("utf-8")}
  ```
  (Adapted from the docs' PDF example; the `text/markdown` MIME type and filenames are illustrative.) — [Artifacts](https://adk.dev/artifacts/)
- Versioning: `save_artifact` "returns the integer version number", "typically starting from 0 and incrementing"; `load_artifact(..., version=None)` returns the latest; it returns `None` if the artifact or version does not exist. The saving event records `event.actions.artifact_delta == {"<filename>": version}`. — [Artifacts](https://adk.dev/artifacts/)
- Scoping: a plain filename is tied to `app_name`, `user_id` and `session_id`; a `"user:"` prefix ties it to `app_name` and `user_id` across sessions. In Python, `list_artifacts()` returns session-scoped names plus the user's `user:`-prefixed names. — [Artifacts](https://adk.dev/artifacts/)
- Service must be configured: `Runner(..., artifact_service=InMemoryArtifactService())`; without one, `save_artifact`, `load_artifact` and `list_artifacts` raise `ValueError`. — [Artifacts](https://adk.dev/artifacts/)
- Implementations exported by `google.adk.artifacts` on main: `BaseArtifactService`, `FileArtifactService`, `GcsArtifactService`, `InMemoryArtifactService`. — [adk-python source](https://github.com/google/adk-python/blob/main/src/google/adk/artifacts/__init__.py)
- CLI wiring: `--artifact_service_uri` accepts `gs://<bucket_name>`, `file://<path>` or `memory://`; the Python CLI default is a per-agent directory at `<agents_dir>/<agent>/.adk/artifacts`. — [Deploy to Cloud Run](https://adk.dev/deploy/cloud-run/); [Command Line](https://adk.dev/runtime/command-line/)
- Service interface also offers list-versions, delete, and (Python) `ArtifactVersion` metadata: version number, canonical URI, MIME type, creation time, custom metadata. "Delete is not exposed via context objects for safety." — [Artifacts](https://adk.dev/artifacts/)
- Artifacts in prompts: `{artifact.var}` "is used to insert the text content of the artifact named var" into an instruction. — [Simple agents with LlmAgent](https://adk.dev/agents/llm-agents/)
- `LoadArtifactsTool` (from `google.adk.tools.load_artifacts_tool`) lists available artifacts to the model and, when called, "temporarily appends the selected artifact contents to that request ... The loaded artifact content is not permanently saved back into the session history". — [Artifacts](https://adk.dev/artifacts/)
- State versus artifacts: state suits "small pieces of configuration or conversational context"; "Session state is generally not optimized for storing large amounts of data. Artifacts provide a dedicated mechanism for persisting larger blobs." Context guidance: "Store references, load content on demand." — [Artifacts](https://adk.dev/artifacts/); [Agent context](https://adk.dev/context/)
- Best practices: choose the service by environment (in-memory for tests, GCS or a custom `BaseArtifactService` for production); meaningful filenames with extensions; accurate MIME types; pass an explicit version when logic depends on history; use `user:` only for data that belongs across sessions; plan cleanup, since persistent artifacts "remain until explicitly deleted". — [Artifacts](https://adk.dev/artifacts/)

### Inferences
- Markdown specs fit artifacts well: each save gives a version number (useful for review loops and audit), `{artifact.spec.md}`-style templating or `LoadArtifactsTool` brings the text into a prompt only when needed, and the dev UI and local CLI persist them under `.adk/artifacts` by default.
- Use `user:`-prefixed filenames for specs that must be visible in later sessions (for example plan and task stages run on different days); plain names are invisible outside the creating session.
- If the framework's deliverable must be real files in a repository (for example `specs/001-feature/spec.md`), a deterministic function node or tool that writes to disk is still needed; artifacts are an ADK-managed store, not the project working tree. Keeping the artifact as the source of truth and exporting to disk at approval points keeps versioning and file output aligned.

### Gaps
- No official guidance was found on writing directly to the project filesystem versus artifacts. The docs cover state versus artifacts only.
- The on-disk layout of `FileArtifactService` (whether files are human-browsable `.md` files or an internal structure) and its constructor arguments were not read; the Artifacts page describes only the in-memory and GCS services for Python.
- Whether `{artifact.name}` accepts filenames containing dots or a `user:` prefix was not confirmed.
- The v2.15.0 "unified artifact service for cloud stores" appears only in release notes.

## How are tools defined and designed?

### Takeaway
A tool is usually a plain Python function: ADK builds the schema from the name, type hints, defaults and docstring, and the whole docstring is the tool description. Return a dict with a `status` key, keep parameters few and simple, take a `ToolContext` parameter for state and artifacts, and use `FunctionTool(..., require_confirmation=...)` or `tool_context.request_confirmation(...)` for approval. Some Gemini built-in tools cannot share an agent with other tools.

### Cited Findings
- "When you assign a function to an agent's `tools` list, the framework automatically wraps it as a `FunctionTool`." The schema comes from "its name, docstring, parameters, type hints, and default values". — [Function tools](https://adk.dev/tools-custom/function-tools/)
- "ADK does not emit a per-parameter description: the whole docstring becomes the tool's single top-level `description`, so describe each parameter there." — [Function tools](https://adk.dev/tools-custom/function-tools/)
- Required versus optional: a parameter is optional "only if you provide a default value"; `Optional[T]` or `T | None` alone "does not make it optional". "Do not add defaults for information the model should derive from the user request or ask the user to provide." — [Function tools](https://adk.dev/tools-custom/function-tools/)
- Pydantic parameters are supported (`BaseModel`, `list[Model]`, `Optional[Model]`, unions); the function receives a model instance. `*args` and `**kwargs` are ignored in the schema. Since v2.14.0, `Enum`-annotated parameters receive enum members. — [Function tools](https://adk.dev/tools-custom/function-tools/); [adk-python releases](https://github.com/google/adk-python/releases)
- Return type: "The preferred return type for a Function Tool is a dictionary"; other types are wrapped as `{"result": ...}`. "Include a 'status' key in your return dictionary to indicate the overall outcome (e.g., 'success', 'error', 'pending')"; return a human-readable `error_message` rather than an error code.
  ```python
  def get_weather(city: str) -> dict:
      """Retrieves the current weather report for a specified city.

      Args:
          city (str): The name of the city.
      Returns:
          dict: status and result or error msg.
      """
      if city.lower() == "new york":
          return {"status": "success", "report": "Sunny, 25 C."}
      return {"status": "error", "error_message": f"No weather data for '{city}'."}
  ```
  — [Function tools](https://adk.dev/tools-custom/function-tools/); [Simple agents with LlmAgent](https://adk.dev/agents/llm-agents/)
- Context injection: add a parameter typed `ToolContext`; ADK "detects it by its `ToolContext` type annotation rather than by name" and hides it from the model. It exposes `state`, `actions` (for example `transfer_to_agent`), and artifact and memory methods. — [Function tools](https://adk.dev/tools-custom/function-tools/)
- Best practices: "Fewer Parameters are Better", "Simple Data Types", "Meaningful Names" (avoid `do_stuff()`), "Build for Parallel Execution" (async tools). — [Function tools](https://adk.dev/tools-custom/function-tools/)
- Exceptions: let standard exceptions propagate so `RetryConfig` can act; never swallow `BaseException`. — [Welcome to ADK 2.0](https://adk.dev/2.0/)
- Long-running tools: `LongRunningFunctionTool(func=ask_for_approval)` returns an initial result (for example `{'status': 'pending', 'ticket-id': ...}`), the run pauses, and the client later sends an intermediate or final `FunctionResponse`. They are "designed to help you start and manage long running tasks ... but not perform the actual, long task". — [Function tools](https://adk.dev/tools-custom/function-tools/)
- Boolean confirmation: `FunctionTool(reimburse, require_confirmation=True)`, or pass a function such as `async def confirmation_threshold(amount: int, tool_context: ToolContext) -> bool` to require it conditionally. — [Action confirmations](https://adk.dev/tools-custom/confirmation/)
- Advanced confirmation inside the tool:
  ```python
  def request_time_off(days: int, tool_context: ToolContext):
      """Request day off for the employee."""
      tool_confirmation = tool_context.tool_confirmation
      if not tool_confirmation:
          tool_context.request_confirmation(
              hint="Please approve or reject the tool call request_time_off().",
              payload={"approved_days": 0},
          )
          return {"status": "Manager approval is required."}
      approved_days = min(tool_confirmation.payload["approved_days"], days)
      if approved_days == 0:
          return {"status": "The time off request is rejected.", "approved_days": 0}
      return {"status": "ok", "approved_days": approved_days}
  ```
  "ADK only rejects the call for you on the `require_confirmation=True` path", so a self-confirming tool must also check `tool_context.tool_confirmation.confirmed`. Remote replies are a `function_response` named `adk_request_confirmation` with `{"confirmed": true, "payload": {...}}` posted to `/run` or `/run_sse`. — [Action confirmations](https://adk.dev/tools-custom/confirmation/); [Human input](https://adk.dev/graphs/human-input/)
- Built-in tool restriction: Code Execution, Google Search and Agent Search (Gemini API) "can only be used by themselves, without any other tools, in a single agent object", and "Built-in tools cannot be used within a sub-agent". Workarounds: wrap the built-in-tool agent in `AgentTool`, or construct `GoogleSearchTool(bypass_multi_tools_limit=True)` (from `google.adk.tools.google_search_tool`); the shared `google_search` instance leaves the flag off. — [Tool limitations](https://adk.dev/tools/limitations/)
- MCP: `pip install "google-adk[mcp]"`, then
  ```python
  from google.adk.agents import LlmAgent
  from google.adk.tools.mcp_tool import McpToolset
  from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
  from mcp import StdioServerParameters

  root_agent = LlmAgent(
      model="gemini-flash-latest", name="filesystem_assistant",
      instruction="Help users manage local files.",
      tools=[McpToolset(
          connection_params=StdioConnectionParams(server_params=StdioServerParameters(
              command="npx", args=["-y", "@modelcontextprotocol/server-filesystem", TARGET_FOLDER])),
          tool_filter=["list_directory", "read_file"],
      )],
  )
  ```
  "Agents deployed to production must define `McpToolset` synchronously in `agent.py`." Direct MCP integration has "High Context Bloat: every tool definition and raw output ... enters the primary agent's history"; delegation to a sub-agent is advised for "scenarios with >20 tools where schema overload harms accuracy". — [MCP tools](https://adk.dev/tools-custom/mcp-tools/)
- OpenAPI: `OpenAPIToolset` (from `google.adk.tools.openapi_tool.openapi_spec_parser.openapi_toolset`) takes `spec_str` / `spec_dict` and `spec_str_type`, creates one `RestApiTool` per operation, and accepts `auth_scheme` and `auth_credential`. — [OpenAPI tools](https://adk.dev/tools-custom/openapi-tools/)
- Skills: `SkillToolset(skills=[load_skill_from_dir(...)])` gives the agent `load_skill`, `load_skill_resource` and `run_skill_script` tools, loading instructions only when needed (ADK Python 1.25.0+). — [Skills](https://adk.dev/skills/)

### Inferences
- Spec-framework tools (save spec, load spec, list tasks, mark task done) should be small, dict-returning functions with full docstrings, taking `ToolContext` for artifact and state access.
- Where a step is always required (for example "write the spec file after the writer agent finishes"), make it a function node rather than a tool the model may or may not call.
- If web search grounding is needed during research stages, isolate it in its own agent or use the `bypass_multi_tools_limit` construction, because it cannot sit beside custom function tools by default.

### Gaps
- Tool authentication, parallel tool execution settings and the "advanced MCP" page were not read.
- How `require_confirmation` on workflow nodes (v2.12.0) is expressed in code was not confirmed in docs.

## How are structured inputs and outputs handled?

### Takeaway
`input_schema` and `output_schema` take Pydantic models (also `list[...]` of primitives, `dict`, or `genai.types.Schema`). In Python, `output_schema` and `tools` can be combined, with a reliability caveat on models that need the `set_model_response` fallback. Sampling settings go in `generate_content_config`; thinking is configured through a planner.

### Cited Findings
- `output_schema`: "If set, the agent's final response must be a JSON string conforming to this schema." Python "validates against a Pydantic model, which does enforce the constraints declared on it". Supported types: a Pydantic model class, lists of primitives (`list[str]` etc.), `dict`, `google.genai.types.Schema`. — [Simple agents with LlmAgent](https://adk.dev/agents/llm-agents/)
- `output_schema` with `tools`: "In Python, ADK supports `output_schema` and `tools` on the same agent: the tools stay available while the agent works, and the schema applies only to the final response. Some models accept both in one request, such as Gemini models on Google Cloud and `LiteLlm` models whose provider supports response schemas ... For other models, ADK adds a `set_model_response` function tool and instructs the model to return its final answer through that tool, which may not work reliably. In such cases, consider using sub-agents that handle output formatting separately." — [Simple agents with LlmAgent](https://adk.dev/agents/llm-agents/)
- Stale material: an older full example on the same page still carries the comment "Agent 2: Uses output_schema (NO tools possible)". The prose above supersedes it for Python. — [Simple agents with LlmAgent](https://adk.dev/agents/llm-agents/)
- `input_schema`: "Define a schema representing the expected input structure when this agent is invoked as a tool ... The schema does not apply to user messages sent directly to the agent." In graphs, "use `input_schema` on an agent to validate the structured output of the preceding node and deliver it as the agent's input". — [Simple agents with LlmAgent](https://adk.dev/agents/llm-agents/); [Data handling](https://adk.dev/graphs/data-handling/)
- Example combining schemas, tools and mode:
  ```python
  class CapitalOutput(BaseModel):
      capital: str = Field(description="The capital of the country.")

  structured_capital_agent = LlmAgent(
      name="capital_agent", model="gemini-flash-latest",
      instruction='Given a country, respond ONLY with JSON: {"capital": "capital_name"}',
      output_schema=CapitalOutput,
      output_key="found_capital",   # stored in state as a dict
  )
  ```
  — [Simple agents with LlmAgent](https://adk.dev/agents/llm-agents/)
- Function nodes may return Pydantic objects directly (`return CityTime(...)`), and the next agent node receives them through its `input_schema`. — [Graph-based agent workflows](https://adk.dev/graphs/)
- Templating caveat: `{key}` placeholders "are substituted from session state, not from the node input, so a placeholder such as `{CityTime.time_info}` is left in the prompt verbatim". To template a value, write it to state first. — [Data handling](https://adk.dev/graphs/data-handling/)
- `generate_content_config` takes `google.genai.types.GenerateContentConfig` (temperature, `max_output_tokens`, `top_p`, `top_k`, safety settings). "ADK raises a `ValueError` if `generate_content_config` sets `tools`, `system_instruction`, `response_schema`, or `http_options.base_url`"; use the agent's `tools`, `instruction` and `output_schema` instead. — [Simple agents with LlmAgent](https://adk.dev/agents/llm-agents/)
- Planners: `BuiltInPlanner(thinking_config=types.ThinkingConfig(include_thoughts=True, thinking_budget=1024))` uses the model's native thinking; `PlanReActPlanner()` forces a plan/action/reasoning/final-answer output structure and is "particularly useful for models that don't have a built-in 'thinking' feature". Both import from `google.adk.planners`. — [Simple agents with LlmAgent](https://adk.dev/agents/llm-agents/)
- `RequestInput(response_schema=...)` declares the expected shape of a human reply but does not coerce free text into it. — [Human input](https://adk.dev/graphs/human-input/)

### Inferences
- Use `output_schema` for machine-consumed stage outputs (requirement lists, task breakdowns, validation verdicts) and render markdown from them in a function node; this gives deterministic file formatting and lets Pydantic enforce constraints.
- For agents that both call tools and must return structured output on non-Gemini models, split the work: a tool-using agent followed by a formatting agent, as the docs suggest.

### Gaps
- What happens in Python when the model's final response fails `output_schema` validation (exception, retry, or raw string stored) is described on the page only for Java and Kotlin.
- The data-handling page mentions `{Class.field}` and `<Class.field from source_node>` instruction forms in a passage that reads as TypeScript-specific; whether they work in Python is unclear, and the Python text says such placeholders are left verbatim.

## How are models configured?

### Takeaway
Gemini models are selected by string (`"gemini-flash-latest"` and `"gemini-pro-latest"` in the docs; the README uses `"gemini-3.5-flash"`), with auth through `GOOGLE_API_KEY` or Google Cloud project variables. Claude is supported natively via `AnthropicLlm` (Anthropic API) or `claude-*` strings (Google Cloud); other providers go through `LiteLlm`.

### Cited Findings
- Three integration mechanisms: direct string / registry (Gemini, Claude, Agent Platform endpoints); model connector classes passed as `model` (`LiteLlm`, `ApigeeLlm`, Ollama, vLLM, LiteRT-LM); and model routing "with automatic failover on error". — [AI Models for ADK agents](https://adk.dev/agents/models/)
- "Most code examples in ADK documentation use `gemini-flash-latest` to select the latest available Gemini Flash version. However, if you access Gemini from a regional endpoint, such as `us-central1`, this selection string may not work. In that case, use a specific model version string." — [Gemini models](https://adk.dev/agents/models/google-gemini/)
- The README quick start uses `model="gemini-3.5-flash"`; the LlmAgent page uses `"gemini-pro-latest"` as the stronger-model example. Older snippets in the docs still show `gemini-2.0-flash` and `gemini-2.5-pro`. — [adk-python README](https://github.com/google/adk-python/blob/main/README.md); [Simple agents with LlmAgent](https://adk.dev/agents/llm-agents/)
- AI Studio auth: `.env` with `GOOGLE_API_KEY="..."` (the Agents CLI scaffold uses `GEMINI_API_KEY`). Google Cloud auth: `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, `GOOGLE_GENAI_USE_ENTERPRISE=True`, plus `gcloud auth application-default login`. — [Gemini models](https://adk.dev/agents/models/google-gemini/); [Agents CLI Quickstart](https://adk.dev/get-started/agents-cli/)
- 429 `RESOURCE_EXHAUSTED` handling: request more quota or enable client-side retries. The docs give two ways to set retry options; option 1, for a model passed as a string, is through `generate_content_config`, using `retry_options=types.HttpRetryOptions(initial_delay=1, attempts=2)` (option 2 was not read). v2.9.0 added `FallbackModel` for automatic failover. — [Gemini models](https://adk.dev/agents/models/google-gemini/); [adk-python releases](https://github.com/google/adk-python/releases)
- Gemini Interactions API: `Gemini(model="gemini-flash-latest", use_interactions_api=True)` from `google.adk.models.google_llm` chains turns by `previous_interaction_id` rather than resending history; it cannot mix custom function tools with built-in tools unless the built-in is converted with `bypass_multi_tools_limit`. — [Gemini models](https://adk.dev/agents/models/google-gemini/)
- Claude via Anthropic API (`pip install "google-adk[extensions]"`, `ANTHROPIC_API_KEY`):
  ```python
  from google.adk.agents import LlmAgent
  from google.adk.models.anthropic_llm import AnthropicLlm

  root_agent = LlmAgent(
      name="claude_agent",
      model=AnthropicLlm(model="claude-sonnet-4-6"),
      instruction="You are a helpful assistant.",
  )
  ```
  "The `AnthropicLlm` class is available in ADK Python v1.20.0 and later." — [Claude models](https://adk.dev/agents/models/anthropic/)
- "In Python, a bare `claude-*` model string, such as `model="claude-sonnet-4-6"`, routes to the Agent Platform backend and requires Google Cloud project settings. To use the Anthropic API from Python, pass an `AnthropicLlm` instance instead of a string." — [Claude models](https://adk.dev/agents/models/anthropic/)
- LiteLLM: `pip install "litellm>=1.84"`, then `LlmAgent(model=LiteLlm(model="openai/gpt-4o"), ...)` with `from google.adk.models.lite_llm import LiteLlm`; provider keys via env vars such as `OPENAI_API_KEY`. On Windows set `PYTHONUTF8=1`. — [LiteLLM connector](https://adk.dev/agents/models/litellm/)
- Mixed systems are supported: "Combine Claude and Gemini agents in one multi-agent system, and choose the model for each agent based on its task." The MCP page describes "model tiering" (a stronger orchestrator model with a cheaper model for sub-agent tool execution). — [Claude models](https://adk.dev/agents/models/anthropic/); [MCP tools](https://adk.dev/tools-custom/mcp-tools/)

### Inferences
- Keep model names in one config module and set per-agent models explicitly (or use `LlmAgent.set_default_model`), since `-latest` aliases move and can fail on regional endpoints.
- Several ADK features are Gemini-specific (context caching, built-in search and code execution, Interactions API). A design that must run on Claude or OpenAI models should not depend on them.

### Gaps
- No page read here states which specific Gemini model Google currently recommends for which task; the docs deliberately use `-latest` aliases, and the README's `gemini-3.5-flash` is the only concrete current-generation string seen.
- The OpenAI page (a native connector appears to exist alongside LiteLLM) and the model-routing page were not read.

## What do the docs say about instruction writing, context management and keeping agents focused?

### Takeaway
Instructions should be specific, structured with Markdown, include few-shot examples and say when and why to use each tool. Context is controlled with `include_contents`, isolated sub-agent branches, `App`-level context caching and events compaction, and by keeping large content out of state and history. The docs' main lever for focus is decomposition into smaller agents and deterministic nodes.

### Cited Findings
- The `instruction` should state the core task, persona, constraints, "how and when to use its `tools`", and the output format. Tips: "Be Clear and Specific", "Use Markdown", "Provide Examples (Few-Shot)", "Guide Tool Use: Don't just list tools; explain when and why the agent should use them." — [Simple agents with LlmAgent](https://adk.dev/agents/llm-agents/)
- Direct state injection is preferred over telling the model to look things up: it "avoids relying on the LLM to correctly interpret natural language instructions to access state". — [State](https://adk.dev/sessions/state/)
- Shared rules: `GlobalInstructionPlugin` on the `App` for rules or persona across all agents. — [Simple agents with LlmAgent](https://adk.dev/agents/llm-agents/)
- `include_contents`: `'default'` sends relevant conversation history; `'none'` means the agent "operates based solely on its current instruction and any input provided in the current turn (useful for stateless tasks or enforcing specific contexts)". — [Simple agents with LlmAgent](https://adk.dev/agents/llm-agents/)
- Decomposition rationale: single agents hit limits on instruction-following, context windows and modularity; graphs let you "explicitly break out the tasks of a procedure" and switch "between non-deterministic AI-powered agents and deterministic code as needed". — [Agents](https://adk.dev/agents/); [Graph-based agent workflows](https://adk.dev/graphs/)
- Context isolation in teams: task and single-turn agents run in isolated branches; sub-agent delegation gives "Zero Context Bloat: intermediate exploratory reasoning, failed tool calls, and large raw outputs remain isolated in the sub-agent loop". — [Collaborative agent teams](https://adk.dev/workflows/collaboration/); [MCP tools](https://adk.dev/tools-custom/mcp-tools/)
- Context caching (experimental; Gemini 2.0+; configured on `App`):
  ```python
  from google.adk.apps.app import App
  from google.adk.agents.context_cache_config import ContextCacheConfig

  app = App(name="my-caching-agent-app", root_agent=root_agent,
            context_cache_config=ContextCacheConfig(min_tokens=2048, ttl_seconds=600, cache_intervals=5))
  ```
  Defaults: `min_tokens` 0, `ttl_seconds` 1800, `cache_intervals` 10. "The first request in a session is never cached." For long instructions reused through a session, the docs point to the agent's `static_instruction` parameter. — [Context caching](https://adk.dev/context/caching/)
- Context compaction (configured on `App`): token-based `EventsCompactionConfig(token_threshold=4000, event_retention_size=5)` and/or sliding-window `EventsCompactionConfig(compaction_interval=3, overlap_size=1)`, with an optional `summarizer` (`LlmEventSummarizer`) to choose the summarizing model. If both are set, token-based takes priority. — [Context compression](https://adk.dev/context/compaction/)
- Large content: keep it in artifacts, "store references, load content on demand"; `LoadArtifactsTool` content is appended only to the current request. — [Agent context](https://adk.dev/context/); [Artifacts](https://adk.dev/artifacts/)
- Skills provide progressive disclosure: metadata first, full instructions on trigger, resources on demand, "optimiz[ing] the context window by only loading instructions when they are needed". — [Skills](https://adk.dev/skills/)

### Inferences
- For document stages, give each writer agent only what it needs: prior-stage output as node input or `{artifact...}` / `{key}` injection, with `single_turn` mode (graph default) rather than the whole chat history.
- Compaction matters mostly for the interactive interview stage; pipeline stages that run as single-turn nodes already see a narrow context.
- Stage-specific writing guidance (spec template, quality checklist) could be packaged as skills or as `static_instruction` text to benefit from caching.

### Gaps
- Google Cloud / Google Developers blog posts and codelabs on prompt-writing and multi-agent best practices (2025-2026) were not read in this pass; the findings above are from the product docs only.
- `static_instruction` semantics were not read beyond the pointer on the caching page.
- Whether single-turn graph nodes in Python ignore `include_contents='default'` (the docs state this for Go) was not confirmed.

## What are the official deployment and observability options?

### Takeaway
Deployment targets are Agent Runtime (managed, formerly Vertex AI Agent Engine), Cloud Run, GKE, or any container host; `adk deploy` and the Agents CLI automate them. Observability is OpenTelemetry-based (structured GenAI logs, metrics, traces) plus standard Python logging, with many third-party integrations.

### Cited Findings
- Options: "Agent Runtime on Agent Platform" ("a fully managed auto-scaling service"), Cloud Run, GKE ("a good option if you need more control ... as well as for running Open Models"), and "other container-friendly infrastructure" such as local Docker or Podman. — [Deploying Your Agent](https://adk.dev/deploy/)
- Commands: `adk deploy docker --with_ui <agent-folder>`, `adk deploy cloud_run --with_ui <agent-folder>`, with `--env KEY=VALUE` or a `.env` file. — [adk-python README](https://github.com/google/adk-python/blob/main/README.md)
- Cloud Run deploy flags include `--session_service_uri` (`agentengine://<agent_engine>` for managed sessions, among others) and `--artifact_service_uri` (`gs://<bucket_name>`, `file://<path>`, `memory://`). — [Deploy to Cloud Run](https://adk.dev/deploy/cloud-run/)
- Agent Runtime: two paths, a standard deployment (console plus ADK CLI) and an Agents CLI path that sets up "CI/CD, infrastructure-as-code, and deployment pipelines". The Python payload "does not include the ADK API server or the ADK web user interface libraries". It is a paid service. — [Deploy to Agent Runtime](https://adk.dev/deploy/agent-runtime/)
- Logging: ADK uses Python's `logging` module and OpenTelemetry structured GenAI events. `DEBUG` logs include "the complete request sent to the language model"; "It is recommended to use `INFO` or `WARNING` in production." Prompt content is elided from structured logs by default. — [Logging](https://adk.dev/observability/logging/)
- Tracing: OTel GenAI semantic conventions with spans `invoke_agent {agent.name}`, `invoke_workflow {workflow.name}`, `execute_tool {tool.name}`, `generate_content {model.name}`; export by setting `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` before `adk web` or `adk api_server`. v2.13.0 "defaults to OpenTelemetry GenAI v2 (`otel_semconv_1_44`, removing `call_llm`)", so dashboards built on older span names need checking. — [Traces](https://adk.dev/observability/traces/); [adk-python releases](https://github.com/google/adk-python/releases)
- Integrations listed in the docs catalog include Cloud Trace, BigQuery Agent Analytics plugin, AgentOps, Arize AX, Phoenix, Langfuse, LangWatch, MLflow, Datadog, W&B Weave. — [Observability](https://adk.dev/observability/)
- Plugins are registered on the `App` (`plugins=[...]`) and apply across the whole workflow; catalog entries include a Reflect and Retry plugin, Model Armor and other guardrail plugins. (Callbacks, plugins as guardrails, and evaluation are covered by a separate researcher.) — [App class](https://adk.dev/apps/); [Observability](https://adk.dev/observability/)

### Inferences
- A local-first spec tool can run entirely on `adk web` / `adk run` with SQLite sessions and file artifacts, then move to Cloud Run with `gs://` artifacts and a database or managed session service without code changes, because storage is selected by URI.
- Human-in-the-loop pauses over a deployed API need a client that handles `RequestInput` and confirmation function calls and posts the replies back.

### Gaps
- GKE specifics, Agent Runtime limits, and the metrics page were not read.
- How `RequestInput` interrupts surface over `adk api_server` and Agent Runtime (payload shape for the reply) was not read.

## Which official sample agents are closest to a document-producing, multi-stage pipeline, and what structure do they use?

### Takeaway
`google/adk-samples` has been restructured into `google/adk-recipes` (the old URL resolves to it). The closest match is `core/python/deep-search`: plan, human approval of the plan, outline, per-section research with a critic loop, then a composed report with citations. For 2.x building blocks, the workflow samples inside `google/adk-python` (`contributing/samples/workflows`) are the most direct reference.

### Cited Findings
- `google/adk-recipes` is "the restructured successor to `google/adk-samples`" and the source for Agents CLI, Agent Garden and the Gemini Enterprise app. Layers: `core/` (reference patterns), `plugins/` (installable vertical skills), `contrib/` (end-to-end deployable services, twelve Python agents). Published 15 Oct 2026. — [Google Developers Blog: a tour of google/adk-recipes](https://developers.googleblog.com/en/three-layers-one-repo-a-tour-of-googleadk-recipes/)
- Every recipe has a validated `manifest.yaml`, an `AGENTS.md` for coding assistants and a `README.md` for people; `contrib/` and `plugins/` recipes add a `Dockerfile` and a runnability test. Recipes are "for demonstration and as starting points, not production use". — [Google Developers Blog: a tour of google/adk-recipes](https://developers.googleblog.com/en/three-layers-one-repo-a-tour-of-googleadk-recipes/)
- `core/python` directories seen: `adk-voice-agent`, `ambient-expense-agent`, `ambient-quality-agent`, `cross-session-memory`, `deep-search`, `genmedia-for-commerce`, `long-horizon-harness`, `oauth-user-consent-flow`, `rag-agent-search`, `rag-vector-search`, `safety-plugins` (the listing may be truncated). — [adk-recipes core/python](https://github.com/google/adk-recipes/tree/main/core/python)
- `deep-search` pipeline: (1) planner turns a topic into a research plan; (2) the user approves or edits the plan, and "research doesn't begin without explicit approval"; (3) the plan becomes a report outline; (4) per section, search then critic then follow-up searches until a quality bar is met; (5) a composer writes the final report with inline citations. Layout: `app/agent.py`, `app/config.py` (a `ResearchConfiguration` dataclass holding models and loop iterations), `tests/`, `frontend/`, `pyproject.toml`, `uv.lock`, `Makefile`, `manifest.yaml`, `AGENTS.md`, `.env.example`. Agent names include `interactive_planner_agent`, `plan_generator`, `section_planner`, `section_researcher`, `enhanced_search_executor`, `report_composer_with_citations`. — [adk-recipes deep-search](https://github.com/google/adk-recipes/tree/main/core/python/deep-search)
- `core/python/long-horizon-harness` ("Horizon") is the reference for long-running agents: cross-session memory, per-user sandboxing, secrets, guardrails, "resumable multi-step orchestration"; evals live in `tests/eval/evalsets/` (18 behavioral rubrics) and run with `uv run pytest tests/eval`; it defaults to local backends and in-memory sessions. — [Google Developers Blog: a tour of google/adk-recipes](https://developers.googleblog.com/en/three-layers-one-repo-a-tour-of-googleadk-recipes/)
- `contrib/python` agents named by category include an LLM auditor, a high-volume document analyzer, brand-aligned presentations, a small-business loan processor and a financial advisor. — [Google Developers Blog: a tour of google/adk-recipes](https://developers.googleblog.com/en/three-layers-one-repo-a-tour-of-googleadk-recipes/)
- Design stance in the blog: prefer single-agent designs when possible (coordinator layers "would obscure the pattern rather than clarify it"), and put complexity in the pipeline and the evaluation. — [Google Developers Blog: a tour of google/adk-recipes](https://developers.googleblog.com/en/three-layers-one-repo-a-tour-of-googleadk-recipes/)
- 2.x workflow samples in adk-python (`contributing/samples/workflows`): `agent_in_workflow`, `classifier_node`, `dynamic_fan_out_fan_in`, `dynamic_nodes`, `fan_out_fan_in`, `loop`, `loop_config`, `loop_self`, `message`, `multi_triggers`, `nested_workflow`, `node_as_tool`, `node_output`, `parallel_worker`, `request_input`, `request_input_advanced`, `request_input_rerun`, `retry`, `route`, `sequence`, `state`, `use_as_output`, plus auth samples. The 2.0 page also points to `contributing/samples/multi_agent` for collaborative samples. — [adk-python workflow samples](https://github.com/google/adk-python/tree/main/contributing/samples/workflows); [Welcome to ADK 2.0](https://adk.dev/2.0/)
- Docs-embedded examples of document pipelines, both written with the deprecated template agents: the sequential code pipeline (writer with `output_key="generated_code"`, reviewer reading `{generated_code}` and writing `review_comments`, refactorer reading both), and the iterative document loop (initial writer, then a `LoopAgent(max_iterations=5)` of critic and refiner, where the refiner has an `exit_loop(tool_context: ToolContext)` tool that sets `tool_context.actions.escalate = True` and otherwise overwrites the document in state through `output_key`). — [Sequential template workflow](https://adk.dev/agents/workflow-agents/sequential-agents/); [Loop template workflow](https://adk.dev/agents/workflow-agents/loop-agents/)
- A Google codelab, "Building AI Agents with ADK: Orchestrating Graph Workflows", covers graph workflows including maker-checker cycles routed with `Event(route=...)` (seen in search results, not read). — [Codelab](https://codelabs.developers.google.com/devsite/codelabs/build-agents-with-adk-graph-workflows)

### Inferences
- `deep-search` is the best structural analogue for a spec pipeline: an interactive planning agent with an explicit human approval gate, followed by an autonomous multi-stage pipeline with a critic loop and a final composer, and config centralized in `app/config.py`.
- Its agent names come from the 1.x-era sample (formerly the "gemini-fullstack" pattern), so it may still use `SequentialAgent` / `LoopAgent` and custom `BaseAgent` classes. Treat it as a reference for stage design, and take the 2.x mechanics (`Workflow`, `RequestInput`, `@node`, retries) from `contributing/samples/workflows`.

### Gaps
- `deep-search`'s `app/agent.py` and `pyproject.toml` were not read, so the ADK classes it uses and the google-adk version it pins are unknown.
- No official recipe that writes versioned markdown documents to artifacts or to disk was identified; the `contrib/python` document-oriented agents (LLM auditor, document analyzer, brand-aligned presentations) were not opened.
- The individual `contributing/samples/workflows` directories were listed but not read.
