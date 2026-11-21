# Combining LLM agents with deterministic Python in Google ADK (Python), and migrating steps from LLM to Python

**Version verified against: `google-adk` 2.15.0** (PyPI upload 2026-11-20 00:30 UTC; changelog dates it 2026-11-19; requires Python >=3.11). How it was verified:

- **Source**: the published 2.15.0 wheel was downloaded from PyPI and read (not installed, not executed). Links of the form `github.com/google/adk-python/blob/v2.15.0/src/google/adk/...` point to the same files at the release tag; the tag was confirmed to exist for `agents/base_agent.py`, the other links follow the same layout and were not opened one by one.
- **Docs**: the official docs at `adk.dev` (the old `google.github.io/adk-docs` URL now 301-redirects there), fetched 2026-11-20 as the `index.md` variants listed in `https://adk.dev/llms.txt`.
- **Not done**: no code was run. Snippets marked "from docs" are copied from the cited page; snippets marked "composed, not executed" were assembled by me from verified signatures and doc patterns and have not been run against 2.15.0.
- Quotes from blog posts (Google Developers Blog, Anthropic) were extracted through an automated page reader; wording should be close but was not re-checked character by character.

Release context: ADK Python 2.0 went GA on 2026-05-19; a 1.x maintenance line still ships (latest seen: 1.39.1, 2026-08-27) — [Welcome to ADK 2.0](https://adk.dev/2.0/), [PyPI](https://pypi.org/project/google-adk/#history). **The biggest finding for planning: in 2.x the documented, non-deprecated way to mix LLM steps and Python steps is the `Workflow` graph / dynamic-workflow runtime, in which a plain Python function is a first-class node. `SequentialAgent`, `ParallelAgent` and `LoopAgent` are deprecated, and custom `BaseAgent` subclasses are described as "superseded".**

## How do you write a custom deterministic agent by subclassing BaseAgent and implementing _run_async_impl?

### Takeaway
It still works in 2.15.0 (subclass `BaseAgent`, implement the async generator `_run_async_impl(self, ctx)`, yield `Event`s, signal state changes through `EventActions.state_delta`, signal loop exit through `escalate`), but the docs now call this approach "superseded" by graph and dynamic workflows, and one official page claims the override is bypassed. For new code, a Python function node (next section) is the cheaper deterministic unit; keep `BaseAgent` subclasses for cases that must sit inside an `LlmAgent` sub-agent tree.

### Cited Findings
- Signature and contract: `async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]`; it "must be an `async def` function and return an `AsyncGenerator`"; sub-agents are run with `async for event in self.some_sub_agent.run_async(ctx): yield event`; `ctx.session.state` is "the primary way to share data between steps". — [Custom agents](https://adk.dev/agents/custom-agents/)
- `BaseAgent` is a Pydantic model with `extra='forbid'`: each sub-agent kept on the instance must be a declared annotated field and passed to `super().__init__(...)`; "Assigning an undeclared attribute in `__init__` raises a `ValueError`". Sub-agents should also be passed in `sub_agents` so the framework knows the hierarchy. — [Custom agents](https://adk.dev/agents/custom-agents/)
- Agent names must be Python identifiers, unique in the tree, and not `"user"`; an agent instance can be added as a sub-agent only once. — [base_agent.py @ v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/agents/base_agent.py)
- In 2.15.0 `BaseAgent` subclasses `BaseNode`. `run_async()` wraps `_run_async_impl` in a lifecycle: plugin and agent before-callbacks, then the implementation, then after-callbacks, plus an OpenTelemetry agent span. When the agent runs as a graph node, `BaseAgent._run_impl` calls `self.run_async(...)`, so `_run_async_impl` is still executed. — [base_agent.py @ v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/agents/base_agent.py)
- Conflicting official statement: the 2.0 migration page says custom overrides of `_run_async_impl()` "are no longer the correct way to drive execution. The Workflow Graph engine completely bypasses these legacy overrides" and recommends `BeforeAgentCallback`/`AfterAgentCallback` instead. — [Welcome to ADK 2.0](https://adk.dev/2.0/); contradicted by [base_agent.py @ v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/agents/base_agent.py) and by the [Custom agents](https://adk.dev/agents/custom-agents/) page, which still documents the override for Python.
- "Starting in ADK 2.0, agent-based workflows using `BaseAgent` have been superseded by more flexible workflow structures, including graph-based workflows and dynamic workflows. You should evaluate the capabilities of these workflow mechanisms before building a custom agent". — [Custom agents](https://adk.dev/agents/custom-agents/)
- `EventActions` fields in 2.15.0: `skip_summarization`, `state_delta: dict`, `artifact_delta: dict[str, int]`, `transfer_to_agent`, `transfer_reason`, `escalate`, `requested_auth_configs`, `requested_tool_confirmations`, `compaction`, `end_of_agent`, `agent_state`, `rewind_before_invocation_id`, `route`, `render_ui_widgets`, `set_model_response`. — [event_actions.py @ v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/events/event_actions.py)
- `Event` (a subclass of `LlmResponse`) has `invocation_id`, `author`, `actions`, `output`, `node_info`, `branch`, plus convenience constructor kwargs: `message` -> `content`, `state` -> `actions.state_delta`, `route` -> `actions.route`. — [event.py @ v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/events/event.py)
- State commit rule: a state change "is only guaranteed to be persisted ... after the `Event` carrying the corresponding `state_delta` in its `actions` has been `yield`-ed"; code that resumes after a `yield` "can reliably assume that the state changes signaled in the yielded event have been committed". — [Event loop](https://adk.dev/runtime/event-loop/)
- Do not append to `session.events` directly and do not use `enqueue_event`; "explicitly yield the event from within your node or agent". — [Welcome to ADK 2.0](https://adk.dev/2.0/)
- Docs example of a deterministic checker used to end a loop (from docs):
  ```python
  class CheckCondition(BaseAgent): # Custom agent to check state
      async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
          status = ctx.session.state.get("status", "pending")
          is_done = (status == "completed")
          yield Event(author=self.name, actions=EventActions(escalate=is_done)) # Escalate if done
  ```
  — [Custom agents](https://adk.dev/agents/custom-agents/)
- Resumability is not automatic for custom agents: you must define a `BaseAgentState` subclass, call `self._load_agent_state(ctx, StateType)`, checkpoint with `ctx.set_agent_state(self.name, agent_state=...)` + `yield self._create_agent_state_event(ctx)`, and finish with `ctx.set_agent_state(self.name, end_of_agent=True)`. — [Resume agents](https://adk.dev/runtime/resume/)
- `_run_async_impl` covers only non-live runs; live runs need `_run_live_impl` or they raise `NotImplementedError`. — [Custom agents](https://adk.dev/agents/custom-agents/)

### Inferences
- Composed, not executed — a deterministic validator agent that writes its verdict to state and ends an enclosing loop:
  ```python
  from typing import AsyncGenerator
  from google.adk.agents import BaseAgent
  from google.adk.agents.invocation_context import InvocationContext
  from google.adk.events import Event, EventActions

  REQUIRED = ("## Requirements", "## Acceptance Criteria")

  class SpecStructureGate(BaseAgent):
      async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
          spec = ctx.session.state.get("spec_md", "")
          missing = [h for h in REQUIRED if h not in spec]
          yield Event(
              invocation_id=ctx.invocation_id, author=self.name, branch=ctx.branch,
              actions=EventActions(
                  state_delta={"spec_check": {"ok": not missing, "missing": missing}},
                  escalate=not missing,  # ends an enclosing LoopAgent once the spec passes
              ),
          )
  ```
- Pitfalls implied by the findings: (1) prefer `state_delta` on a yielded event over mutating `ctx.session.state` in place, because only yielded deltas are guaranteed to persist; (2) read state only after the sub-agent's events have been yielded onward; (3) `escalate` is interpreted by the parent (see next section), so a gate agent behaves differently under `LoopAgent`, `ParallelAgent` and `SequentialAgent`; (4) undeclared attributes fail Pydantic validation.
- Given the docs conflict, treat `_run_async_impl` as working but on a deprecation path: keep each custom agent a thin wrapper around a plain function so the logic can be re-hosted as a workflow node without rewriting it.

### Gaps
- No statement was found of when (or whether) `_run_async_impl` overrides will be removed. The 2.0 page and the source disagree; I did not run a test to observe the behaviour.
- Not verified: how a `BaseAgent` subclass with a custom `_run_async_impl` behaves on resume inside a `Workflow` without the agent-state checkpoints.

## How do workflow agents provide deterministic orchestration, how do you terminate a LoopAgent, and are there newer graph or workflow constructs?

### Takeaway
`SequentialAgent`, `ParallelAgent` and `LoopAgent` still run but are deprecated in Python 2.x. Their replacement is `google.adk.Workflow`: a graph whose nodes can be LLM agents, plain Python functions, tools, human-input steps or nested workflows, plus "dynamic workflows" where a Python function orchestrates nodes with ordinary `await`, `if` and `while`. This is the mechanism that makes "swap one LLM step for Python" a one-node change.

### Cited Findings
**Legacy workflow ("template") agents**
- All three classes carry `@deprecated('... is deprecated in favor of Workflow and will be removed in a future version. Workflow cannot yet be used as an LlmAgent sub-agent.')`. — [loop_agent.py](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/agents/loop_agent.py), [sequential_agent.py](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/agents/sequential_agent.py), [parallel_agent.py](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/agents/parallel_agent.py) @ v2.15.0
- Docs: "constructing one emits a deprecation warning, and the classes will be removed in a future release. A `Workflow` cannot be used as an `LlmAgent` sub-agent." — [Custom agents](https://adk.dev/agents/custom-agents/); "template workflows have been superseded by more flexible workflow structures" — [Template agent workflows](https://adk.dev/agents/workflow-agents/)
- They orchestrate "without consulting an AI model", which "results in deterministic and predictable execution patterns". — [Template agent workflows](https://adk.dev/agents/workflow-agents/)
- `LoopAgent` termination, from source: the loop ends when any yielded sub-agent event has `actions.escalate` truthy, or when `times_looped` reaches `max_iterations`. `max_iterations=None` means "run indefinitely until a sub-agent escalates"; "A value of zero or less runs the sub-agents no times at all." After an escalating event the remaining sub-agents of that iteration are skipped. — [loop_agent.py @ v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/agents/loop_agent.py)
- The built-in `exit_loop` tool is two lines: `tool_context.actions.escalate = True` and `tool_context.actions.skip_summarization = True`. — [exit_loop_tool.py @ v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/tools/exit_loop_tool.py)
- `SequentialAgent._run_async_impl` does not inspect `escalate`; it only stops early when the invocation pauses. — [sequential_agent.py @ v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/agents/sequential_agent.py)
- `ParallelAgent`: an escalating event authored by a direct sub-agent stops the remaining branches; only conversation history is isolated per branch, session state is shared. — [parallel_agent.py @ v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/agents/parallel_agent.py)

**Graph-based workflows (ADK 2.0+)**
- "Graph-based workflows allow you to define your agent logic as a graph of execution nodes and edges, combining AI-powered agent reasoning with deterministic tools and code." Advantages listed include "Run chains of functions without AI: Call agent tools and your own code without invoking a generative AI model." — [Graph-based agent workflows](https://adk.dev/graphs/)
- Minimal sequence mixing agents and functions (from docs):
  ```python
  from google.adk import Agent, Workflow, Event
  root_agent = Workflow(
      name="root_agent",
      edges=[("START", city_generator_agent, lookup_time_function,
              city_report_agent, completed_message_function)],
  )
  ```
  where `lookup_time_function(node_input: str)` is a plain function returning a Pydantic object. — [Graph-based agent workflows](https://adk.dev/graphs/)
- Conditional routing: a function node returns `Event(route="KEY")` (or a list of keys) and a dict edge maps keys to nodes: `(router, {"BUG": fn1, "CUSTOMER_SUPPORT": fn2})`. Loops are a back-edge: `(router, {"RETRY": task_A_node, "DONE": final_task_node})`. Fan-in uses `JoinNode`. Workflows nest as nodes. — [Graph routes](https://adk.dev/graphs/routes/)
- Public exports of `google.adk.workflow`: `BaseNode, DEFAULT_ROUTE, Edge, FunctionNode, JoinNode, Node, NodeTimeoutError, RetryConfig, START, Workflow, node`. Top-level `google.adk` exports `Agent, Context, Event, Runner, Workflow`. — [workflow/__init__.py](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/workflow/__init__.py), [__init__.py](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/__init__.py) @ v2.15.0
- Data between nodes: `Event(output=...)` (or simply returning a value) is the next node's `node_input`; `Event(message=...)` is user-facing; `Event(state={...})` persists into session state. In Python, "having two or more `yield` commands with an `Event.output` results in a runtime error". State "should not be used to persist large amounts of data"; use artifacts. — [Data handling](https://adk.dev/graphs/data-handling/)
- Function-node parameter binding: parameters named `ctx` and `node_input` are special; by default (`parameter_binding='state'`) every other parameter is bound from `ctx.state` by name, coerced through Pydantic `TypeAdapter`; a missing key with no default raises `WorkflowDataError`. If the `Workflow` declares a `state_schema`, function-node parameters not declared in it raise `StateSchemaError` at construction. — [_function_node.py](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/workflow/_function_node.py), [_workflow.py](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/workflow/_workflow.py) @ v2.15.0
- Every node (`BaseNode`) has `rerun_on_resume`, `wait_for_output`, `retry_config`, `timeout`, `input_schema`, `output_schema`, `state_schema`. — [_base_node.py @ v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/workflow/_base_node.py)
- `{key}` placeholders in an agent instruction are filled from session state, not from node input; to template a value, write it to state first (`output_key` or `Event(state=...)`). — [Data handling](https://adk.dev/graphs/data-handling/)
- An `LlmAgent`'s `mode` defaults to `chat` as a sub-agent and `single_turn` as a node in a workflow. — [llm_agent.py @ v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/agents/llm_agent.py). The docs say `task` mode "is disabled for use in graph-based workflows in ADK Python v2.0.0". — [Collaborative workflows](https://adk.dev/workflows/collaboration/)
- Retries and timeouts per node: `@node(retry_config=RetryConfig(max_attempts=3, initial_delay=1.0, exceptions=[...]), timeout=10.0)`; `max_attempts` counts the first attempt; `ctx.attempt_count` starts at 1; the attempt count is not persisted across a pause or restart. "Make retried work safe to repeat." — [Retries and timeouts](https://adk.dev/graphs/retry/)
- Exceptions should propagate: a broad `except Exception:` inside a tool "masks the failure from the framework, permanently disabling the new 2.0 automatic retry mechanisms for that step", and catching `BaseException` traps `NodeInterruptedError`, breaking human-in-the-loop pauses. — [Welcome to ADK 2.0](https://adk.dev/2.0/)

**Dynamic workflows (ADK 2.0+)**
- "Dynamic workflows in ADK allow you to put aside graph-based path structures and use the full power of your chosen programming language"; benefits listed include "Automatic Checkpointing: ... Successful sub-nodes are automatically skipped when resuming the workflow". — [Dynamic workflows](https://adk.dev/graphs/dynamic/)
- Generate / Python-check / fix loop (from docs):
  ```python
  @node(rerun_on_resume=True) # workflow node
  async def code_workflow(ctx: Context, node_input: str):
    code = await ctx.run_node(coder_agent, node_input)
    check_resp = await ctx.run_node(compile_lint_check, code)
    while check_resp.findings:
      yield Event(state={"code": code, "findings": check_resp.findings})
      code = await ctx.run_node(fixer_agent, {"code": code, "findings": check_resp.findings})
      check_resp = await ctx.run_node(compile_lint_check, code)
    yield Event(output=code)
  ```
  — [Dynamic workflows](https://adk.dev/graphs/dynamic/)
- "Parent nodes in dynamic workflows that call `ctx.run_node` must set `rerun_on_resume=True`". Parallelism: collect `ctx.run_node(worker, item, use_sub_branch=True)` coroutines and `await asyncio.gather(*tasks)`. — [Dynamic workflows](https://adk.dev/graphs/dynamic/)
- `ctx.run_node(node, node_input=None, *, use_as_output=False, run_id=None, use_sub_branch=False, ...)`; "Always `await` this method directly. Wrapping it in `asyncio.create_task()` means the task runs unsupervised". — [context.py @ v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/agents/context.py)
- `node(...)` decorator/function options: `name, rerun_on_resume, retry_config, timeout, parallel_worker, max_parallel_workers, auth_config, require_confirmation, parameter_binding`. — [_node.py @ v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/workflow/_node.py)

**Other**
- "Collaborative workflows": a coordinator `Agent` with `sub_agents` whose `mode` is `chat`, `task` or `single_turn`; ADK "auto-injects delegation tools named after each subagent". — [Collaborative workflows](https://adk.dev/workflows/collaboration/)
- Agent Routing (router functions for fallback, A/B testing, auto-routing) is flagged experimental. — [Workflows overview](https://adk.dev/workflows/)
- The `AgentConfig` YAML loader and `config_type` are marked deprecated in source. — [base_agent.py @ v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/agents/base_agent.py)
- Known limitation: "Some third-party integrations may not be compatible with graph-based workflows." — [Graph-based agent workflows](https://adk.dev/graphs/)

### Inferences
- For a spec pipeline (clarify -> spec -> plan -> tasks -> cross-check -> implement -> verify -> archive), one dynamic-workflow orchestrator node with one child node per stage gives a fixed seam per stage: each child can start as an `Agent` and later become a `@node` Python function with the same input and output, without touching the orchestrator.
- Composed, not executed — pipeline skeleton with a bounded Python-critic loop:
  ```python
  from google.adk import Agent, Context, Workflow
  from google.adk.workflow import node

  @node
  def validate_spec(node_input: str) -> list[str]:      # deterministic critic
      return [h for h in ("## Requirements", "## Acceptance Criteria") if h not in node_input]

  @node(rerun_on_resume=True)
  async def sdd_pipeline(ctx: Context, node_input: str):
      spec = await ctx.run_node(spec_writer, node_input)          # LLM today
      for _ in range(3):                                           # explicit bound
          issues = await ctx.run_node(validate_spec, spec)         # Python today
          if not issues:
              break
          spec = await ctx.run_node(spec_fixer, {"spec": spec, "issues": issues})
      plan = await ctx.run_node(planner, spec)
      return plan

  root_agent = Workflow(name="sdd", edges=[("START", sdd_pipeline)])
  ```
- A graph back-edge has no built-in iteration cap that I found (the dynamic-workflow page contrasts "Unlike a graph cycle, the loop is bounded by its loop condition"), so a graph loop should carry its own counter in state or use a dynamic node.
- `escalate`-based loop exit is specific to the deprecated `LoopAgent`; in a `Workflow`, loop exit is a route value or a Python loop condition.
- The source has a code path that wraps a `BaseNode` passed in an `LlmAgent`'s `tools` as a `NodeTool` (and rejects `BaseAgent` instances there), which suggests a `Workflow` or function node can be exposed to a chat agent as a tool even though it cannot be a sub-agent. I did not exercise this.

### Gaps
- No removal date for the deprecated workflow agents was found.
- Whether `task` mode is still disabled inside graph workflows in 2.15.0 was not checked beyond the doc sentence, which names v2.0.0.
- The data-handling page contains two contradictory cautions about several `output` events from one node (Python text: runtime error; another paragraph, apparently for TypeScript: last value wins). Python behaviour was not tested.

## How do callbacks work, how can each skip, replace, validate or enforce, and how do Plugins differ?

### Takeaway
Six agent-level callbacks plus two error callbacks give per-agent interception points; returning a value from a `before_*` callback skips the real step and substitutes your Python result. Plugins expose the same hooks app-wide (plus run-level hooks), run before agent callbacks, and are the recommended home for cross-cutting policy, logging and caching. Plugins are now registered on `App`, not on `Runner`.

### Cited Findings
- Exact signatures and return semantics in 2.15.0 — [llm_agent.py](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/agents/llm_agent.py), [base_agent.py](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/agents/base_agent.py) @ v2.15.0:

  | Callback | Arguments | Return | Effect of a non-empty return |
  |---|---|---|---|
  | `before_agent_callback` | `callback_context` | `types.Content \| None` | Agent run is skipped; content is returned as the agent's event |
  | `after_agent_callback` | `callback_context` | `types.Content \| None` | An additional event with this content is appended (it does not replace earlier events) |
  | `before_model_callback` | `callback_context, llm_request` | `LlmResponse \| None` | "A truthy response skips the model call"; the request may also be mutated in place |
  | `after_model_callback` | `callback_context, llm_response` | `LlmResponse \| None` | "A truthy response replaces the model response" |
  | `on_model_error_callback` | `callback_context, llm_request, error` | `LlmResponse \| None` | Recovery response instead of raising |
  | `before_tool_callback` | `tool, args, tool_context` | `dict \| None` | "Any non-None response, including an empty dict, ... skips the tool call" |
  | `after_tool_callback` | `tool, args, tool_context, tool_response` | `dict \| None` | Replaces the tool result |
  | `on_tool_error_callback` | `tool, args, tool_context, error` | `dict \| None` | Recovery result instead of raising |

- Each field accepts one callable or a list; lists run in order until one returns a value (a truthy value for agent and model callbacks, any non-`None` value for tool callbacks). Callbacks may be sync or `async def`. For the agent callbacks the docstring adds that arguments "are passed by keyword first. If keyword binding fails, ADK tries positional binding", so keyword-only parameters must use the documented names. — [base_agent.py](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/agents/base_agent.py), [llm_agent.py](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/agents/llm_agent.py) @ v2.15.0
- `CallbackContext` and `ToolContext` are now aliases of one `Context` class ("CallbackContext is unified into Context"; `ToolContext = Context`). Docs: "prefer `Context` for new code; the older names remain for backward compatibility". — [callback_context.py](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/agents/callback_context.py), [tool_context.py](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/tools/tool_context.py) @ v2.15.0; [Callback patterns](https://adk.dev/callbacks/design-patterns-and-best-practices/)
- Documented patterns: guardrails and policy enforcement, dynamic state management, logging, caching, request/response modification, conditional skipping, tool-specific actions (`skip_summarization`, auth), artifact handling. State writes in callbacks are "automatically tracked in the subsequent `Event.actions.state_delta`". — [Callback patterns](https://adk.dev/callbacks/design-patterns-and-best-practices/)
- Best practices: keep each callback single-purpose; "avoid long-running or blocking operations"; design for idempotency; "Unit test your callback functions using mock context objects". — [Callback patterns](https://adk.dev/callbacks/design-patterns-and-best-practices/)
- `output_key` is written by the `LlmAgent`'s own run loop when it sees its final text event (parsed through `output_schema` first if one is set). — [llm_agent.py @ v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/agents/llm_agent.py)
- Plugins: a plugin "is registered once, on the `Runner` or in Python on the `App`, and its callbacks apply globally to every agent, tool, and LLM call managed by that runner". "Plugin callback functions have precedence over callbacks implemented at the object level"; if a plugin callback returns a value, the corresponding agent/model/tool callback "is not executed (skipped)". Plugins run in list order and stop at the first non-`None` return. — [Plugins](https://adk.dev/plugins/)
- `BasePlugin` hooks (all `async`, keyword-only): `on_user_message_callback(invocation_context, user_message)`, `before_run_callback(invocation_context)`, `on_event_callback(invocation_context, event)`, `after_run_callback(invocation_context)`, `before_agent_callback(agent, callback_context)`, `after_agent_callback(agent, callback_context)`, `before_model_callback(callback_context, llm_request)`, `after_model_callback(callback_context, llm_response)`, `on_model_error_callback(...)`, `before_tool_callback(tool, tool_args, tool_context)`, `after_tool_callback(tool, tool_args, tool_context, result)`, `on_tool_error_callback(...)`, `on_agent_error_callback(agent, callback_context, error)`, `on_run_error_callback(invocation_context, error)`. Note the plugin argument names `tool_args` / `result` differ from the agent callback names `args` / `tool_response`. — [base_plugin.py @ v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/plugins/base_plugin.py)
- `Runner(plugins=...)` is documented in source as "Deprecated ... Please use the `app` argument to provide plugins instead"; `App` has `name, root_agent, plugins, events_compaction_config, context_cache_config, resumability_config`. — [runners.py](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/runners.py), [apps/app.py](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/apps/app.py) @ v2.15.0
- "When implementing security guardrails and policies, use ADK Plugins for better modularity and flexibility than Callbacks." — [Plugins](https://adk.dev/plugins/)
- Prebuilt plugins exported from `google.adk.plugins` include `LoggingPlugin`, `DebugLoggingPlugin`, `ReflectAndRetryToolPlugin`, `ReflectAndRetryModelPlugin`, `ContextFilterPlugin`, `GlobalInstructionPlugin`, `SaveFilesAsArtifactsPlugin`, `AutoTracingPlugin`, `BigQueryAgentAnalyticsPlugin`, `ToolCallIntegrityPlugin`. — [plugins/__init__.py @ v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/plugins/__init__.py); descriptions at [Plugins](https://adk.dev/plugins/)
- `ReflectAndRetryToolPlugin(max_retries=3)` feeds tool failures back to the model and retries; override `extract_error_from_result` to treat `{"status": "error"}` results as failures. — [Reflect and Retry plugin](https://adk.dev/integrations/reflect-and-retry/)

### Inferences
- Composed, not executed — the four interception shapes:
  ```python
  from google.genai import types
  from google.adk.models.llm_response import LlmResponse

  def text(s): return types.Content(role="model", parts=[types.Part(text=s)])

  # 1. Replace a whole LLM agent with Python behind a flag
  def ids_in_python(callback_context):
      if not callback_context.state.get("use_python_task_ids"):
          return None                                   # fall through to the LLM
      callback_context.state["task_ids"] = allocate_ids(callback_context.state["tasks"])
      return text("Task IDs allocated.")                # agent run is skipped

  # 2. Skip one model call
  def cached_plan(callback_context, llm_request):
      hit = callback_context.state.get("temp:plan_cache")
      return LlmResponse(content=text(hit)) if hit else None

  # 3. Validate or repair model output
  def repair_markdown(callback_context, llm_response):
      fixed = normalise_headings(llm_response)          # your Python
      return fixed if fixed is not llm_response else None

  # 4. Enforce policy on a tool
  def guard_writes(tool, args, tool_context):
      if tool.name == "write_file" and not args["path"].startswith("specs/"):
          return {"status": "error", "error_message": "Writes are limited to specs/."}
      return None
  ```
- Because `output_key` is written inside the agent's run loop, a `before_agent_callback` that short-circuits the agent must write the contract state key itself (as in shape 1). A `before_model_callback` short-circuit still flows through the agent loop, so `output_key` and `output_schema` handling should still apply; I did not test either path.
- Callbacks are a low-commitment first migration step (flag-guarded Python in front of an unchanged agent); replacing the node is the durable step once the Python path is trusted.
- Inside `google/adk/workflow/` the plugin manager is invoked for tool nodes (tool callbacks) and for run-level hooks; I found no agent/model/tool callback invocation around plain function nodes. So policy that must cover Python nodes should live in the node code or in `on_event_callback`, not in tool callbacks.

### Gaps
- Not verified by execution: which plugin hooks fire for plain `FunctionNode` runs.
- The full `types-of-callbacks` page (45 KB of Python-relevant text) was only sampled; per-callback examples there were not re-checked against 2.15.0.

## How should function tools be used to push deterministic work out of prompts, and what makes the LLM use them reliably?

### Takeaway
Any Python callable placed in `tools=[...]` becomes a `FunctionTool` whose schema is derived from its name, type hints, defaults and docstring. Put side effects and exactness (file writes, ID allocation, template rendering, structure checks, git) in tools so the model only chooses and parameterises; in a `Workflow`, a step that needs no model judgement at all should be a function node instead of a tool.

### Cited Findings
- "The ADK framework automatically inspects your Python function's signature—including its name, docstring, parameters, type hints, and default values—to generate a schema." A parameter is required if it has no default; `Optional[...]` alone does not make it optional. "ADK does not emit a per-parameter description: the whole docstring becomes the tool's single top-level `description`, so describe each parameter there." `*args`/`**kwargs` are ignored. — [Function tools](https://adk.dev/tools-custom/function-tools/)
- Return a `dict`; non-dict returns are wrapped. "As a best practice, include a "status" key"; prefer a human-readable `error_message` over error codes because "the LLM, not a piece of code, needs to understand the result". — [Function tools](https://adk.dev/tools-custom/function-tools/)
- Best practices: "Fewer Parameters are Better", "Simple Data Types", "Meaningful Names", "Build for Parallel Execution". — [Function tools](https://adk.dev/tools-custom/function-tools/)
- Use verb-noun names (`get_weather`, `schedule_meeting`), descriptive parameter names, and "Decompose Complex Tasks" into smaller focused tools. — [Custom tools](https://adk.dev/tools-custom/)
- Context injection: a parameter annotated `ToolContext` is detected "by its `ToolContext` type annotation rather than by name" and excluded from the schema; it exposes `state`, `actions`, artifacts, `request_confirmation`. State written through it lands in the tool-response event's `actions.state_delta`. — [Function tools](https://adk.dev/tools-custom/function-tools/), [Custom tools](https://adk.dev/tools-custom/)
- `FunctionTool(func, *, require_confirmation: bool | Callable[..., bool] = False)`. — [function_tool.py @ v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/tools/function_tool.py)
- `tool_context.actions.skip_summarization = True` passes the raw tool result through without an extra LLM summarisation step. — [Callback patterns](https://adk.dev/callbacks/design-patterns-and-best-practices/)
- With resumability on, tools "are run at least once, and may run more than once when resuming"; tools with side effects should "check for and prevent duplicate runs". — [Resume agents](https://adk.dev/runtime/resume/)
- A `BashTool` and "Environment Toolsets" exist as integrations. — [llms.txt index](https://adk.dev/llms.txt) (pages not read)

### Inferences
- Composed, not executed — an ID allocator that takes the counter out of the prompt:
  ```python
  from google.adk.tools import ToolContext

  def allocate_task_id(prefix: str, tool_context: ToolContext) -> dict:
      """Allocate the next sequential task ID.

      Args:
        prefix: Short uppercase prefix for the ID, for example "T".
      Returns:
        dict with "status" and "task_id" (for example "T-007").
      """
      n = tool_context.state.get("next_task_seq", 1)
      tool_context.state["next_task_seq"] = n + 1
      return {"status": "success", "task_id": f"{prefix}-{n:03d}"}
  ```
- Migration ladder for one responsibility: (a) prompt instruction -> (b) tool the model must call -> (c) `before_tool_callback`/`after_tool_callback` enforcing arguments or results -> (d) function node the workflow always runs. Each rung removes one thing the model can get wrong.
- Idempotent tools (write-if-changed, deterministic file paths, "already committed" checks for git) matter twice: for resume (at-least-once) and for node retries.
- Tool functions written as plain Python with a thin `ToolContext` adapter can be reused unchanged as workflow function nodes later.

### Gaps
- No Google-authored guidance specific to git or filesystem tools for ADK was found; the Bash tool and Environment Toolset pages were not read.
- The tool performance page (parallel execution) was downloaded but not read in detail.

## How do output_schema and Pydantic models, plus validation-and-retry loops, make LLM output machine-checkable?

### Takeaway
`output_schema` forces an agent's final answer into a typed shape and (with `output_key`) stores the parsed object in state; node-level `input_schema`/`output_schema` validate the hand-off between any two nodes. A generator plus Python-critic loop is a few lines in a dynamic workflow, and node `RetryConfig` covers transient failures.

### Cited Findings
- `output_schema` accepts `type[BaseModel]`, `list[type[BaseModel]]`, `list[primitive]`, raw dict schemas or a genai `Schema`. "The ADK supports using `output_schema` and `tools` together. It works by exposing tools during the thought loop and enforcing structure only on the final output." — [llm_agent.py @ v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/agents/llm_agent.py)
- Docs: some models accept schema and tools in one request; "For other models, ADK adds a `set_model_response` function tool". — [LLM agents](https://adk.dev/agents/llm-agents/). The same page still contains older example comments saying "using output_schema prevents tool use" — internally inconsistent; the source docstring above is the current behaviour.
- With `output_key` and `output_schema` both set, "ADK parses the response against the schema first and stores the parsed value rather than the response text. A `BaseModel` schema is stored as a `dict`". — [LLM agents](https://adk.dev/agents/llm-agents/)
- `input_schema` on an `LlmAgent` is "The input schema when agent is used as a tool"; in a graph, `input_schema` on an agent validates the preceding node's structured output and delivers it as the agent's input. — [llm_agent.py @ v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/agents/llm_agent.py), [Data handling](https://adk.dev/graphs/data-handling/)
- Function nodes coerce inputs: `dict` -> `BaseModel` when annotated, `list[dict]` -> `list[BaseModel]`, `types.Content` -> `str`, everything else via Pydantic `TypeAdapter`. — [_function_node.py @ v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/workflow/_function_node.py)
- Generate-and-review and iterative-refinement are documented multi-agent patterns (legacy form: `LoopAgent` + a checker agent that escalates). — [Workflow patterns](https://adk.dev/workflows/patterns/)
- The dynamic-workflow loop example pairs an LLM generator with a non-LLM `compile_lint_check` node and an LLM fixer (snippet in the workflow section above). — [Dynamic workflows](https://adk.dev/graphs/dynamic/)
- `ReflectAndRetryModelPlugin` "asks the model to try again when a response ends with an error, such as a malformed function call". — [Plugins](https://adk.dev/plugins/)

### Inferences
- Composed, not executed:
  ```python
  from pydantic import BaseModel
  from google.adk import Agent

  class Task(BaseModel):
      id: str
      title: str
      depends_on: list[str] = []

  class TaskList(BaseModel):
      tasks: list[Task]

  task_breaker = Agent(
      name="task_breaker", model="gemini-flash-latest",
      instruction="Break the plan in {plan_md} into tasks.",
      output_schema=TaskList, output_key="tasks",   # state["tasks"] holds a dict
  )
  ```
  A following Python node can then check invariants the schema cannot express (unique IDs, no dependency cycles, every requirement covered) and either route back with the findings or fail.
- Schema validation catches shape errors; semantic checks belong in a Python critic node. Feeding the critic's findings back as the fixer's input (rather than re-running the generator blind) is the pattern the docs example uses.
- Typed node inputs and outputs are the natural "artifact contract": if the Python replacement returns the same Pydantic type, downstream nodes do not change.

### Gaps
- Not established: what Python ADK does when the model's final text fails `output_schema` validation (raise, retry, or store raw text). The docs sentence I found on this refers to Kotlin.
- Not verified: whether a `Workflow` node's `output_schema` failure is retried under `RetryConfig` by default.

## How does ADK evaluation work, and how can it act as a regression safety net while swapping an LLM step for Python?

### Takeaway
ADK ships three complementary nets: eval sets scored by criteria (`adk eval`, `AgentEvaluator` under pytest, or the web UI), record-and-replay conformance tests (`adk conformance`), and always-on efficiency metrics (model calls, tool calls, tokens, duration) that show whether a swap actually cut cost. Record a baseline before the swap, run the same cases after it.

### Cited Findings
- Two dataset forms: test files (`*.test.json`, one session, "a form of unit testing") and evalsets (multiple, longer sessions, "well-suited for integration tests"). Each turn holds `user_content`, expected `intermediate_data.tool_uses`, `intermediate_responses` and `final_response`; `session_input` can seed initial `state`. Both are backed by the Pydantic `EvalSet`/`EvalCase` models. — [Evaluate](https://adk.dev/evaluate/)
- Built-in criteria: `tool_trajectory_avg_score`, `response_match_score` (ROUGE-1), `final_response_match_v2` (LLM-judged), `rubric_based_final_response_quality_v1`, `rubric_based_tool_use_quality_v1`, `rubric_based_multi_turn_trajectory_quality_v1`, `hallucinations_v1`, `safety_v1`, `per_turn_user_simulator_quality_v1`, `multi_turn_task_success_v1`, `multi_turn_trajectory_quality_v1`, `multi_turn_tool_use_quality_v1`. Defaults when none are given: `tool_trajectory_avg_score` 1.0 and `response_match_score` 0.8. — [Evaluate](https://adk.dev/evaluate/)
- `tool_trajectory_avg_score` match types: `EXACT` (default), `IN_ORDER`, `ANY_ORDER`; score is 1.0 or 0.0 per invocation, averaged. Config form: `{"criteria": {"tool_trajectory_avg_score": {"threshold": 1.0, "match_type": "IN_ORDER"}}}`. — [Evaluation criteria](https://adk.dev/evaluate/criteria/)
- Rubric criteria take `threshold`, `judge_model_options` (`judge_model`, `num_samples`) and a list of `rubrics` (`rubric_id`, `rubric_content.text_property`); rubrics can also be attached per eval case. — [Evaluation criteria](https://adk.dev/evaluate/criteria/)
- Efficiency criteria `tool_call_count_v1`, `inference_call_count_v1`, `token_usage_v1`, `invocation_duration_v1` are "always on", "informational" and "never pass or fail an eval case"; the docs suggest comparing them across runs "to catch a change that keeps quality flat but doubles token usage". — [Evaluation criteria](https://adk.dev/evaluate/criteria/), [Evaluate](https://adk.dev/evaluate/)
- For CI/regression the docs recommend `tool_trajectory_avg_score` and `response_match_score`: "fast, predictable, and suitable for frequent automated checks". — [Evaluate](https://adk.dev/evaluate/)
- pytest integration (from docs):
  ```python
  from google.adk.evaluation.agent_evaluator import AgentEvaluator
  import pytest

  @pytest.mark.asyncio
  async def test_with_single_test_file():
      await AgentEvaluator.evaluate(
          agent_module="home_automation_agent",
          eval_dataset_file_path_or_dir="tests/integration/fixture/home_automation_agent/simple_test.test.json",
      )
  ```
  — [Evaluate](https://adk.dev/evaluate/)
- `AgentEvaluator.evaluate(agent_module: str | BaseNode | App, eval_dataset_file_path_or_dir, num_runs=..., agent_name=None, initial_session_file=None, print_detailed_results=True, artifact_service=None, output_file=None, app_name=None, eval_set_results_manager=None, parallelism=None)`; `evaluate_eval_set(agent_module, eval_set, criteria=None, eval_config=None, ...)`. — [agent_evaluator.py @ v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/evaluation/agent_evaluator.py)
- CLI: `adk eval <AGENT_MODULE_FILE_PATH> <EVAL_SET_FILE_PATH_OR_ID>... [--config_file_path=...] [--print_detailed_results]`; select cases with `file.json:eval_1,eval_2`. The 2.15.0 CLI also defines `--num_runs` and `--parallelism`. — [Evaluate](https://adk.dev/evaluate/), [cli_tools_click.py @ v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/cli/cli_tools_click.py)
- A folder's `test_config.json` holds the criteria. Custom metrics are Python functions `(eval_metric, actual_invocations, expected_invocations, conversation_scenario) -> EvaluationResult`, sync or async, registered under `"custom_metrics": {"name": {"code_config": {"name": "pkg.module.fn"}}}` (Python v1.18.0+). — [Evaluate](https://adk.dev/evaluate/), [Custom metrics](https://adk.dev/evaluate/custom_metrics/)
- Conformance testing: `adk conformance record tests/<category>/<case> none` records `generated-recordings.yaml` and `generated-session.yaml` from a `spec.yaml` (agent, user messages) while `adk web` runs with `--extra_plugins=google.adk.cli.plugins.recordings_plugin.RecordingsPlugin`; `adk conformance test` in replay mode "runs your agent and compares its live LLM requests, responses, and tool calls directly against your previously recorded interactions". Live mode "is a work in progress". It "fails if things don't match", so it suits CI. — [Evaluate](https://adk.dev/evaluate/)
- User simulation (v1.18.0+): a `ConversationScenario` (`starting_prompt`, `conversation_plan`, optional `user_persona` such as `EXPERT`, `NOVICE`, `EVALUATOR`) lets an LLM play the user. It cannot be combined with `tool_trajectory_avg_score`, `response_match_score` or `final_response_match_v2`. — [User simulation](https://adk.dev/evaluate/user-sim/), [Evaluate](https://adk.dev/evaluate/)
- Environment simulation (v1.24.0+): intercepts tool calls during eval via `before_tool_callback` or a plugin and returns injected or LLM-mocked responses, "without modifying the agent itself". — [Environment simulation](https://adk.dev/evaluate/environment_simulation/)
- New in 2.15.0: `pass@k` / `pass^k` multi-run criteria ("can solve a task at least once" versus "reliably on every run") in `multi_run_config`, and a `tool_parameter_match` criterion giving partial credit per argument. — [CHANGELOG](https://github.com/google/adk-python/blob/main/CHANGELOG.md)
- Web UI: `adk web` Eval tab can save the current session as an eval case and run it; the Trace tab shows per-event request, response and graph. — [Evaluate](https://adk.dev/evaluate/)

### Inferences
- Swap procedure this supports: (1) capture eval cases from real sessions while the step is still an LLM; (2) record the efficiency numbers; (3) replace the step; (4) rerun — quality criteria must hold and `inference_call_count_v1` / `token_usage_v1` should drop; (5) re-record conformance baselines, because replay mode will, by design, flag the removed model call as a deviation.
- `tool_trajectory_avg_score` with `EXACT` will fail after a swap that removes a tool call the model used to make (the trajectory legitimately changed). Either update the expected trajectory as part of the swap, use `IN_ORDER`, or assert on outcomes instead.
- For a spec pipeline, outcome checks are more stable than trajectory checks: a custom metric (or a plain pytest assertion on final session state and written files) that validates the produced artifacts with the same Python validators the pipeline uses.
- `num_runs` plus `pass^k` gives a direct measure of the thing migration is meant to improve: run-to-run reliability of a step.
- Since `AgentEvaluator.evaluate` accepts a `BaseNode` or `App`, a `Workflow` root can be evaluated the same way as an agent root.

### Gaps
- Not verified: how eval treats human-input pauses (`RequestInput`) in a workflow; the changelog mentions HITL tools being skipped in eval traces by a plugin, which I did not investigate.
- Not verified: whether Python-node outputs appear in `intermediate_data` for trajectory metrics (tool trajectory is defined over tool calls).
- The Optimization page (`adk.dev/optimize/`) was downloaded but not read.
- Some LLM-judged criteria need the Vertex Gen AI Evaluation Service or a Gemini key ([Evaluate](https://adk.dev/evaluate/)); which ones work with other judge models was not checked.

## How do you unit test ADK agents, tools and callbacks?

### Takeaway
There is no dedicated testing page in the current docs. The practical approach, taken from ADK's own test suite, is: test tools, validators and callbacks as plain Python; test agents and workflows through `InMemoryRunner` with a fake `BaseLlm` that returns scripted responses.

### Cited Findings
- `InMemoryRunner(agent=None, *, node=None, app_name=None, plugins=None, app=None, ...)` "uses in-memory implementations for artifact, session, and memory services". `Runner` requires exactly one of `app`, `agent`, `node`. — [runners.py @ v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/runners.py)
- `await runner.run_debug(user_messages, *, user_id='debug_user_id', session_id='debug_session_id', run_config=None, quiet=False, verbose=False) -> list[Event]` handles session creation and returns all events; documented as "for debugging and experimentation only". — [runners.py @ v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/runners.py)
- `runner.run_async(*, user_id, session_id, invocation_id=None, new_message=None, state_delta=None, run_config=None, ...)` is the production entry point and the one used to resume. — [runners.py @ v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/runners.py)
- ADK's own tests define `MockModel(BaseLlm)` with `MockModel.create(responses=[...])` (strings, `Part`s or `LlmResponse`s), which records `requests` and yields the next scripted `LlmResponse` from `generate_content_async(self, llm_request, stream=False)`. It lives in `tests/unittests/testing_utils.py`, which is in the repository but not in the published wheel or sdist. — [testing_utils.py @ v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/tests/unittests/testing_utils.py)
- `LlmAgent.model` accepts `str | BaseLlm`, so a fake model object can be passed directly. — [llm_agent.py @ v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/agents/llm_agent.py)
- "Unit test your callback functions using mock context objects. Perform integration tests to ensure callbacks function correctly within the full agent flow." — [Callback patterns](https://adk.dev/callbacks/design-patterns-and-best-practices/)
- `.test.json` files run through `AgentEvaluator` are described as "a form of unit testing" for agent behaviour. — [Evaluate](https://adk.dev/evaluate/)

### Inferences
- Composed, not executed — a scripted model and an end-to-end workflow test:
  ```python
  import pytest
  from google.genai import types
  from google.adk.models.base_llm import BaseLlm
  from google.adk.models.llm_response import LlmResponse
  from google.adk.runners import InMemoryRunner

  class ScriptedLlm(BaseLlm):
      model: str = "scripted"
      replies: list[str]
      calls: int = 0
      async def generate_content_async(self, llm_request, stream=False):
          reply = self.replies[self.calls]; self.calls += 1
          yield LlmResponse(content=types.Content(role="model", parts=[types.Part(text=reply)]))

  @pytest.mark.asyncio
  async def test_pipeline_runs_validator_in_python():
      llm = ScriptedLlm(replies=["# Spec\n## Requirements\n## Acceptance Criteria\n"])
      runner = InMemoryRunner(node=build_workflow(model=llm), app_name="t")
      events = await runner.run_debug("Add login", quiet=True)
      assert llm.calls == 1                     # the validator made no model call
  ```
- Layering that follows from the architecture: (1) pure functions (validators, parsers, renderers) with ordinary pytest and no ADK imports; (2) tools and callbacks with a stub context exposing `state` and `actions`; (3) function nodes and custom agents through `InMemoryRunner`; (4) LLM-bearing paths with a scripted model for control flow, and with eval sets for quality.
- Asserting on the scripted model's call count is a cheap, deterministic test that a migrated step no longer reaches the model.
- Copying the ~80-line `MockModel` from the ADK repo into the project's test helpers is reasonable; it is not a public API, so pin it to your own copy.

### Gaps
- I found no official ADK documentation page on unit testing or on mocking models; the approach above is derived from the repository's own tests.
- `Context` construction for isolated callback/tool tests (what a minimal valid instance needs) was not worked out; ADK's `create_invocation_context` test helper exists in the same file but was not read.

## How do human-in-the-loop approval gates work?

### Takeaway
There are three mechanisms: a `RequestInput` node in a workflow (no model involved; the natural fit for "user approves the spec before planning"), tool confirmation on a `FunctionTool` or function node (`require_confirmation` or `request_confirmation()`), and `LongRunningFunctionTool` for approvals completed out of band. Pausing and resuming relies on the event log; turn on `ResumabilityConfig` to resume an invocation after interruption.

### Cited Findings
- Workflow human-input node (from docs):
  ```python
  from google.adk.events import RequestInput
  from google.adk import Workflow

  def step1(): # Human input step
    yield RequestInput(message="Enter a number:")

  def step2(node_input):
    return node_input * 2

  root_agent = Workflow(name="root_agent", edges=[('START', step1, step2)])
  ```
  "These nodes do not require artificial intelligence (AI) models to run". `RequestInput` options: `message`, `payload`, `response_schema`. — [Human input](https://adk.dev/graphs/human-input/)
- "A response schema does not reformat a human reply to fit the specified structure. The reply must already be in that format"; collect structured data in the client or place an agent node after the pause to convert it. — [Human input](https://adk.dev/graphs/human-input/)
- `rerun_on_resume`: `False` (leaf default) routes the reply onward as the node's output; `True` re-runs the node body and is required for any node that calls `ctx.run_node`. In a dynamic workflow: `user_response = await ctx.run_node(get_user_approval)` then branch on it in Python. — [Human input](https://adk.dev/graphs/human-input/), [Dynamic workflows](https://adk.dev/graphs/dynamic/)
- On the wire, a `RequestInput` is emitted as a function call named `adk_request_input`; the reply is a `FunctionResponse` with the interrupt id as `id` and the same name. `RequestInput` has an `interrupt_id` field. — [_workflow_hitl_utils.py](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/workflow/utils/_workflow_hitl_utils.py), [request_input.py](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/events/request_input.py) @ v2.15.0
- Tool confirmation (Python v1.14.0+): `FunctionTool(reimburse, require_confirmation=True)` or `require_confirmation=<callable returning bool>` for a threshold. Advanced form inside the tool: if `tool_context.tool_confirmation` is empty, call `tool_context.request_confirmation(hint=..., payload={...})` and return a pending status; on re-entry read `tool_confirmation.payload` / `.confirmed`. "ADK only rejects the call for you on the `require_confirmation=True` path". — [Action confirmations](https://adk.dev/tools-custom/confirmation/), [Human input](https://adk.dev/graphs/human-input/)
- The confirmation reply is a `FunctionResponse` named `adk_request_confirmation` with `{"confirmed": true, "payload": {...}}`, sent to `/run` or `/run_sse` or straight to the runner. — [Action confirmations](https://adk.dev/tools-custom/confirmation/)
- Function nodes also accept `require_confirmation` (bool or predicate); it needs `rerun_on_resume=True`, which `@node` enables automatically when not set explicitly. — [_function_node.py @ v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/workflow/_function_node.py)
- `LongRunningFunctionTool(func)`: the function returns an initial result (for example a ticket id and `status: pending`), "then the agent run is ended / paused"; the client later sends a `FunctionResponse` with the same call id carrying the intermediate or final result. ADK appends a note to the tool description telling the model not to call it again while pending. — [Function tools](https://adk.dev/tools-custom/function-tools/), [long_running_tool.py @ v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/tools/long_running_tool.py)
- Resumability (Python v1.16.0+): `App(name=..., root_agent=..., resumability_config=ResumabilityConfig(is_resumable=True))`; resume with `runner.run_async(user_id=..., session_id=..., invocation_id=...)` or POST `/run_sse` with `invocation_id`. It is "best-effort": tools are at-least-once and in-memory state is lost. "Resuming a workflow from the ADK Web user interface or using the ADK command line (CLI) tool is not currently supported." "Do not modify a stopped agent workflow before resuming it." — [Resume agents](https://adk.dev/runtime/resume/), [apps/_configs.py @ v2.15.0](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/apps/_configs.py)
- With resumability on, Long Running Functions, Confirmations and Authentication "change how these features operate". — [Resume agents](https://adk.dev/runtime/resume/)
- Dynamic workflows: "if a dynamic workflow is resumed, only failed or interrupted worker nodes are re-executed". — [Dynamic workflows](https://adk.dev/graphs/dynamic/)

### Inferences
- Composed, not executed — spec approval gate inside the dynamic pipeline:
  ```python
  from google.adk import Context
  from google.adk.events import RequestInput
  from google.adk.workflow import node

  @node(rerun_on_resume=False)
  async def approve_spec(ctx: Context, node_input: str):
      yield RequestInput(message="Approve this spec? (yes/no)", payload=node_input)

  # inside the rerun_on_resume=True orchestrator:
  #   answer = await ctx.run_node(approve_spec, spec)
  #   if str(answer).strip().lower() != "yes":
  #       return "Spec rejected"
  ```
- An approval gate as a `RequestInput` node is deterministic by construction: the model cannot skip it, unlike "ask the user to confirm before planning" written in an instruction.
- Because an orchestrator with `rerun_on_resume=True` re-executes its body on resume and replays completed children from checkpoints, code in the orchestrator body outside `ctx.run_node` calls must be side-effect free or idempotent.
- "Do not modify a stopped workflow before resuming" means a migration (swapping a node) should be deployed between runs, not while approvals are pending.

### Gaps
- Not established: whether `ResumabilityConfig(is_resumable=True)` is required for `RequestInput` pauses in a `Workflow`, or only for resuming failed invocations; the human-input page does not say.
- Not verified: the exact client payload shape expected in the `adk_request_input` response for `response_schema` replies.
- The "Human in the loop with Policy" section of the patterns page was not read.

## What do Google's own posts, codelabs and samples say about LLM reasoning versus code, cost and latency, and stable interfaces for later swaps?

### Takeaway
Google's 2026 position is explicit: put fixed procedure in code and reserve the model for steps that need reasoning; ADK 2.0 was built for that split. I found no Google source that spells out "keep state keys stable so an LlmAgent can be swapped for Python later", but the node model (same edge, same input/output schema, any node type) supports it directly.

### Cited Findings
- "Why we built ADK 2.0" (Google Developers Blog, 2026-07-01; Swapnil Agarwal, Alan Blount, Frank Guan): LLM orchestration is "slow, expensive, and exhibit variance compared to a workflow or deterministic code"; "Executing deterministic logic via an LLM loop incurs high token costs and latency"; "the agent could get confused and skip a step due to slightly different context conditions"; "Workflows separate execution routing from language processing"; "Before building an autonomous agent, ask if an agent is actually the right tool for the job." — [Why we built ADK 2.0](https://developers.googleblog.com/en/why-we-built-adk-20/)
- Same post, when to use which: a workflow when "The business logic or execution sequence is predefined"; an agent when "The task involves processing unstructured or ambiguous inputs". — [Why we built ADK 2.0](https://developers.googleblog.com/en/why-we-built-adk-20/)
- Same post, benchmark: about 5,152 tokens per run for a vanilla LLM agent versus 2,265 for the ADK 2.0 workflow, and 7.2 s versus 5.7 s, labelled "illustrative benchmark results using gemini-3.5-flash & mock API responses". No sample size or variance is given. — [Why we built ADK 2.0](https://developers.googleblog.com/en/why-we-built-adk-20/)
- Same post, security: even if an LLM node is manipulated, the runtime "lacks the pathways (edges or nodes) to execute unauthorized actions". — [Why we built ADK 2.0](https://developers.googleblog.com/en/why-we-built-adk-20/)
- Docs: "as your instructions and procedures become longer and more complicated, making sure that the agent is following each step and guideline becomes more complicated and less reliable"; "Moving from prompt-based agents to graph-based workflow agents allows you to explicitly break out the tasks of a procedure"; each node "can be an AI agent, Tool, or your programmed code". — [Graph-based agent workflows](https://adk.dev/graphs/)
- Docs: "You can continue to build standard ADK agents with long prompts, tools, and use them in graph-based workflow agents." — [Graph-based agent workflows](https://adk.dev/graphs/)
- "Developer's guide to multi-agent patterns in ADK" (Google Developers Blog, 2025-12-16, Shubham Saboo; written for 1.x): the sequential pipeline is "linear, deterministic, and refreshingly easy to debug"; "use the output_key to write to the shared session.state"; parallel agents should write unique keys; "Do not build a nested loop system on day one. Start with a sequential chain, debug it, and then add complexity." — [Developer's guide to multi-agent patterns in ADK](https://developers.googleblog.com/en/developers-guide-to-multi-agent-patterns-in-adk/)
- Google Cloud architecture guidance (search-result snippet only; page not opened): a sequential pattern "can reduce latency and operational costs compared to a pattern that uses an AI model to orchestrate task workflow", at the cost of flexibility. — [Choose a design pattern for your agentic AI system](https://docs.cloud.google.com/architecture/choose-design-pattern-agentic-ai-system)
- Official 2.0 samples are in the main repo: `contributing/samples/workflows` and `contributing/samples/multi_agent`. — [Welcome to ADK 2.0](https://adk.dev/2.0/)
- 2.15.0 removed the interactive Visual Agent Builder from ADK Web, with the stated reason that "Developers increasingly build agents by co-building with a coding agent rather than wiring nodes by hand". — [CHANGELOG](https://github.com/google/adk-python/blob/main/CHANGELOG.md)

### Inferences
- A workable "stable interface" for this framework, derived from the mechanisms rather than quoted from Google: (1) every pipeline stage is one named node; (2) its contract is a typed `node_input` and a typed output (Pydantic), plus a documented set of session-state keys and artifact filenames it reads and writes; (3) the orchestrator refers only to node names and contracts. An `Agent` with `output_schema`/`output_key` and a `@node` function returning the same model then satisfy the same contract.
- Keep `output_key` names stable even after a step becomes Python (write the same key via `Event(state=...)` or `ctx.state`), because downstream agent instructions template from state with `{key}`.
- Prioritise migrating orchestration and gating first (they are pure procedure and the blog's cost argument applies most), then validators and parsers, then file and git operations behind tools, and leave drafting and judgement to the model.
- The benchmark is a single illustrative run with mocked APIs; treat "about 50% fewer tokens" as directional, and measure with the efficiency criteria on your own pipeline.

### Gaps
- No Google source was found that explicitly describes swapping an `LlmAgent` for a `BaseAgent` or function later, or that prescribes stable state-key contracts for that purpose.
- Codelabs were found but not read: [ADK 2 Orchestration: Graph, Collaborative & Dynamic Workflows](https://codelabs.developers.google.com/adk2/instructions) and [Building AI Agents with ADK: Orchestrating Graph Workflows](https://codelabs.developers.google.com/devsite/codelabs/build-agents-with-adk-graph-workflows).
- `google/adk-samples` and the `contributing/samples/workflows` directory were not inspected (the latter URL was confirmed to exist).
- Third-party articles surfaced by search (a Medium post on LLM agents versus workflows in ADK; a DEV post on deterministic custom agents; an arXiv preprint titled "Progressive Crystallization: Turning Agent Exploration into Deterministic, Lower-Cost Workflows in Production") were not read and are not used here.

## What observability exists to decide what to migrate first?

### Takeaway
ADK emits OpenTelemetry traces and metrics per agent, workflow, tool and model call, carries token usage on every model event, and reports model-call, tool-call, token and duration figures in every eval run. Together these give a per-step cost and latency ranking without extra instrumentation.

### Cited Findings
- Traces (Python v1.17.0+) follow the OTel GenAI semantic conventions with spans `invoke_agent {agent.name}`, `invoke_workflow {workflow.name}`, `execute_tool {tool.name}`, `generate_content {model.name}`; export with `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` under `adk web` / `adk api_server`, `--otel_to_cloud` for Google Cloud Trace, or programmatically via `google.adk.telemetry.setup.maybe_set_otel_providers()`. — [Traces](https://adk.dev/observability/traces/)
- Metrics (Python v1.32.0+): `gen_ai.invoke_agent.duration`, `gen_ai.invoke_workflow.duration`, `gen_ai.execute_tool.duration`, `gen_ai.invoke_agent.inference_calls`, `gen_ai.invoke_agent.tool_calls`, `gen_ai.client.operation.duration`, `gen_ai.client.token.usage` (split by `gen_ai.token.type`), dimensioned by `gen_ai.agent.name`, tool name and model. — [Metrics](https://adk.dev/observability/metrics/)
- Experimental per-invocation token totals (`adk.experimental.invoke_agent.input_tokens`, `.output_tokens`, `.total_tokens`, cache-read and reasoning breakdowns, and `invoke_workflow` equivalents) are off by default; enable with `ADK_EXPERIMENTAL_TELEMETRY=true` or `RunConfig(telemetry=TelemetryConfig(adk_experimental_telemetry_opt_in=True))`. Workflow rows also need `ADK_TELEMETRY_SCHEMA_VERSION_OPT_IN=2` outside Agent Engine. Names "can still change between releases"; nested workflow totals are also folded into enclosing workflows, so summing double counts. — [Metrics](https://adk.dev/observability/metrics/)
- `LlmResponse` (and therefore `Event`, its subclass) has `usage_metadata: types.GenerateContentResponseUsageMetadata | None`, plus `cache_creation_token_count`, `model_version`, `finish_reason`. — [llm_response.py](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/models/llm_response.py), [event.py](https://github.com/google/adk-python/blob/v2.15.0/src/google/adk/events/event.py) @ v2.15.0
- `LoggingPlugin` prints structured activity to the console; `DebugLoggingPlugin` records "complete interaction data as human-readable YAML appended to `adk_debug.yaml`", including session state. Both attach via `App(plugins=[...])`. — [Logging](https://adk.dev/observability/logging/)
- `BigQueryAgentAnalyticsPlugin` logs agent activity to BigQuery; `AutoTracingPlugin` wraps functions in your own packages in OTel spans. — [Plugins](https://adk.dev/plugins/)
- `adk web` has a Trace tab grouping events per user message, with Event, Request, Response and Graph views. — [Evaluate](https://adk.dev/evaluate/)
- Eval efficiency criteria (`tool_call_count_v1`, `inference_call_count_v1`, `token_usage_v1`, `invocation_duration_v1`) are reported on every eval "with no configuration and no extra model calls". — [Evaluation criteria](https://adk.dev/evaluate/criteria/)
- Many third-party observability integrations are listed (Langfuse, Phoenix, Arize AX, MLflow, Datadog, W&B Weave, AgentOps and others). — [llms.txt index](https://adk.dev/llms.txt)

### Inferences
- Composed, not executed — a minimal per-step token ledger as a plugin:
  ```python
  from google.adk.plugins import BasePlugin

  class StepCostPlugin(BasePlugin):
      def __init__(self):
          super().__init__(name="step_cost")
          self.rows = []
      async def after_model_callback(self, *, callback_context, llm_response):
          u = llm_response.usage_metadata
          if u:
              self.rows.append((callback_context.agent_name, u.prompt_token_count,
                                u.candidates_token_count))
          return None
  ```
- A ranking for "what to migrate first" can be built from: tokens and model calls per agent (`gen_ai.client.token.usage` by `gen_ai.agent.name`), latency per agent, and failure or retry rate of each step (eval pass rate over `num_runs`). Steps that are expensive, frequent, and already passing a deterministic check are the best candidates.
- After migration the same dashboards show the step as a workflow/tool span with no `generate_content` child, which is a direct confirmation the model call is gone.

### Gaps
- Not verified: whether plain function nodes get their own span or metric datapoint in 2.15.0 (the metrics page says "an app built on the `Workflow` engine records per-node datapoints", without naming the metric).
- No built-in cost-in-currency figure was found; cost has to be computed from token counts.
- The logging page was only sampled.

## What general industry guidance on this migration pattern transfers to ADK?

### Takeaway
The widely cited guidance agrees with Google's: default to predefined code paths, use model-directed control only where flexibility pays for its cost and latency, and treat tools as an interface that deserves the same care as prompts. ADK's `Workflow` maps one-to-one onto Anthropic's workflow patterns.

### Cited Findings
- Anthropic, "Building effective agents" (2024-12-19): "Workflows are systems where LLMs and tools are orchestrated through predefined code paths", whereas in agents "LLMs dynamically direct their own processes and tool usage". — [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- Same: "we recommend finding the simplest solution possible, and only increasing complexity when needed. This might mean not building agentic systems at all"; "Agentic systems often trade latency and cost for better task performance"; workflows "offer predictability and consistency for well-defined tasks". — [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- Same, named patterns: prompt chaining (with programmatic checks gating intermediate steps), routing, parallelization, orchestrator-workers, evaluator-optimizer. — [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- Same, tools: "Tool definitions and specifications should be given just as much prompt engineering attention as your overall prompts"; "Poka-yoke your tools. Change the arguments so that it is harder to make mistakes" (example: requiring absolute file paths). — [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
- 12-factor agents (HumanLayer): successful "AI agent" products are "mostly deterministic code, with LLM steps sprinkled in at just the right points". Factor titles include 4 "Tools are just structured outputs", 5 "Unify execution state and business state", 6 "Launch/Pause/Resume with simple APIs", 7 "Contact humans with tool calls", 8 "Own your control flow", 10 "Small, Focused Agents", 12 "Make your agent a stateless reducer". — [12-factor-agents](https://github.com/humanlayer/12-factor-agents)

### Inferences
- Mapping to ADK 2.x: prompt chaining with gates = a `Workflow` sequence with Python validator nodes; routing = `Event(route=...)`; parallelization = fan-out plus `JoinNode` or `asyncio.gather` over `ctx.run_node`; evaluator-optimizer = the generate / check / fix loop; "own your control flow" = a dynamic-workflow orchestrator node; "launch/pause/resume" and "contact humans" = `RequestInput`, tool confirmation and resumability; "small, focused agents" = one single-turn `Agent` per node with its own `input_schema`/`output_schema`.
- "LLM as a fallback, code as the default" can be implemented per node: try the Python path first and route to an LLM node only when the deterministic path reports it cannot handle the input (a route value such as `NEEDS_LLM`).

### Gaps
- Only the titles of the twelve factors and one quotation were retrieved from the 12-factor repository; the individual factor pages were not read.
- I did not find, in the sources read, a named and widely cited write-up of the specific "start LLM-heavy, then replace steps with code" migration path; the closest lead (the arXiv "Progressive Crystallization" preprint) was not read.
