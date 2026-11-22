# adk_review as a reference setup for a spec-driven framework on Google ADK

What `adk_review` actually does, read from its source on 2026-11-20, so the new project can copy what works. This is
a description, not a review of its quality.

- Source read: `/Users/emrec/Projects/playground/adk_review` (read only; nothing was run, `.env` and `.venv` were not
  read).
- Evidence is cited as `path:line`, relative to that folder. `02:L<n>` means line `n` of
  `/Users/emrec/Projects/playground/adk_spec/reports/02-adk-spec-framework-architecture-and-roadmap.md`.
- "Stated reason" means the reason the project itself gives in a comment, a docstring or a guide. Those reasons,
  and the measurements they quote, were not re-verified here.
- Not verifiable from this project: anything about `google-adk` 2.15.0, or about what the pinned ADK's own package
  metadata requires (that lives under `.venv`, which was out of bounds).

Contents: 1 Toolchain and versions, 2 Layout and layering, 3 ADK application, 4 Code versus model, 5 Providers,
6 Plugins, callbacks, tools, safety, 7 Testing, 8 Cross-platform, 9 Entry points and configuration, 10 Copilot
files, 11 Conventions, 12 Comparison with the plan, 13 What transfers and what does not.

---

## 1. Toolchain and version policy

### 1.1 Python, uv, git

| Item | Value | Evidence | Stated reason |
|---|---|---|---|
| Python bound | `requires-python = ">=3.14,<3.15"` | `pyproject.toml:9` | The held LiteLLM release names Python below 3.15 and its `fastuuid` has no 3.15 wheel; with no upper bound `uv tool install` took Python 3.15 (`pyproject.toml:5-8`) |
| Interpreter pin | `3.14` | `.python-version:1`; lock says `requires-python = "==3.14.*"` (`uv.lock:3`) | |
| uv floor | `required-version = ">=0.12"` | `pyproject.toml:86-87` | An older uv stops with a sentence instead of misreading the lock's span |
| uv in pipelines | exactly `0.13.6` in every pipeline | `.github/workflows/ci.yml:34-36`, `.github/workflows/copilot-setup-steps.yml:23-25`, `azure-pipelines.yml:33` | `required-version` reads as a floor, so setup-uv took the newest uv on every run; and none newer than the pinned `setup-uv` holds a checksum for (`ci.yml:32-33`, `CLAUDE.md:344-347`) |
| git | 2.41 or later, with the CVE-2024-32465 fix | `README.md:23-26`, `adk_review/collect/git.py:272-273` | `--attr-source` needs 2.41; without the fix git ignores `GIT_NO_LAZY_FETCH` |
| Build backend | `hatchling>=1.27`, wheel packages `["adk_review"]` | `pyproject.toml:40-45` | |
| Workspace | one uv workspace, member `tui`, one lock | `pyproject.toml:75-79`, `uv.lock:9-13` | The terminal front end is its own application; `uv sync --locked` and `uv tool install` of the reviewer take none of it |

### 1.2 Pins

| Package | Spec in `pyproject.toml` | Version in `uv.lock` | Stated reason for the pin |
|---|---|---|---|
| `google-adk` | `==2.14.1`, no extra (`pyproject.toml:14`) | 2.14.1 (`uv.lock:530-531`) | "a bump lands only measured live on both arms, the demo's review recorded and compared with the last one"; no extra because only LiteLLM is needed beside it (`pyproject.toml:11-13`) |
| `litellm` | `==1.106.2` (`pyproject.toml:18`) | 1.106.2 (`uv.lock:868-869`) | Pinned at the lock's version for installs that read no lock (`uv tool install`, pip, pre-commit); an unpinned install took a release three days old or less, the window in which 1.82.7 and 1.82.8 shipped a credential stealer (`pyproject.toml:15-17`) |
| `ruff` | `==0.17.5` (`pyproject.toml:27`) | 0.17.5 (`uv.lock:1497-1498`) | A runtime dependency: the `lint`, `pitfalls` and `simplify` rules run it; ruff 0.15 refused a selected code and 0.16 silently ran without it (`pyproject.toml:23-26`) |
| `pyrefly` | `==1.4.1` (`pyproject.toml:28`) | 1.4.1 (`uv.lock:1276-1277`) | A runtime dependency: the `types` rule runs it; pinned as ruff is |
| `python-dotenv` | `>=1.0` (`pyproject.toml:19`) | 1.2.4 (`uv.lock:1335-1336`) | not pinned |
| `truststore` | `>=0.10` (`pyproject.toml:22`) | 0.10.5 (`uv.lock:1662-1663`) | not pinned; OS certificate store (`pyproject.toml:20-21`) |
| `google-genai` | not named | 2.34.0 (`uv.lock:586-587`) | transitive, through `google-adk` (`uv.lock:533-540`) |
| `pydantic` | not named | 2.14.3 (`uv.lock:1195-1196`) | transitive |
| `pytest` (dev) | `>=8.0` (`pyproject.toml:49`) | 9.2.0 (`uv.lock:1295-1296`) | |
| `pytest-asyncio` (dev) | `>=0.24` (`pyproject.toml:50`) | 1.5.0 (`uv.lock:1311-1312`) | |
| `textual` (tui member) | `>=8.0,<9.0` (`tui/pyproject.toml:10`) | 8.2.8 (`uv.lock:1573-1574`) | The member's dependency alone |

Not in the lock at all: `mcp`, `a2a-sdk`, `typer`, `sqlalchemy`, `hypothesis`, `import-linter`, `mutmut`,
`cosmic-ray`, `ag-ui-adk` (a name search of `uv.lock` finds none of them). The project deliberately avoids `mcp`
(`adk_review/judge/config.py:151-152`).

### 1.3 Release-age cooldown

- `[tool.uv] exclude-newer = "P3D"`: a release resolves only three days after it is published
  (`pyproject.toml:81-85`). The lock records the span, not a date (`uv.lock:5-7`), so `uv sync --locked` holds day
  after day.
- `uv tool install` reads neither the lock nor `[tool.uv]`, so the install path repeats the cooldown and feeds the
  lock in as constraints (`Makefile:29-33`):
  `uv export --frozen --no-hashes --no-dev --no-emit-project --quiet --output-file "$(LOCKED)"` then
  `uv tool install --reinstall --exclude-newer P3D --constraints "$(LOCKED)" .`
- With no checkout: `uv tool install --exclude-newer P3D git+<repository-url>` (`README.md:43-48`).
- Make variables that call Python use `uv run --no-project`, because a plain `uv run` on every `make` synced the
  environment and rewrote a stale lock (`Makefile:6-13`).

### 1.4 Dependabot (`.github/dependabot.yml`)

- Two ecosystems, `uv` and `github-actions`, weekly, each with `cooldown: default-days: 3`
  (`dependabot.yml:9-14`, `25-30`). A test holds the cooldown to the lock's span for both ecosystems, with no
  package excluded (`tests/test_copilot.py:105-115`).
- Grouping: one pull request for all Python packages `pyproject.toml` names, except `google-adk` and `litellm`,
  which each get their own "so the rest never waits on a new measurement" (`dependabot.yml:1-3`, `15-18`). One
  pull request for the workflows' actions (`dependabot.yml:31-33`).
- Hold: `ignore` keeps `litellm` below `>=1.106.3`. Stated reason: "LiteLLM 1.107.0 shipped a credential stealer,
  and LiteLLM has not yet said its release accounts are safe again: ADK caps it below 1.106.3 for the same reason"
  (`dependabot.yml:19-24`). When lifted, `requires-python`'s upper bound is to be looked at again.
- Packages only the lock names are in no Dependabot pull request; they move with `uv lock --upgrade`, by hand
  (`dependabot.yml:4-5`, `CLAUDE.md:88-90`).

### 1.5 Procedure for accepting a version bump

There is no separate procedure document; the procedure is the sum of these statements:

1. A `google-adk` bump lands only after it is measured live on both arms, with the demo's review recorded and
   compared with the last one (`pyproject.toml:11`). The tools that do this are `--record DIR`
   (`adk_review/judge/plugins.py:363-389`) and the live scripts in section 7.4; linking them to this sentence is my
   reading, the file does not name them.
2. A pin and the lock move together (`CLAUDE.md:92-93`).
3. LiteLLM is not bumped past the hold by hand either (`CLAUDE.md:90-91`).
4. An actions bump must move the README's sample workflow in the same pull request; a test fails until it does
   (`dependabot.yml:5-6`, `tests/test_copilot.py:91-102`). Each action is pinned by full commit SHA with its tag in a
   comment (`ci.yml:28-34`).
5. The gate is lint, type check and the offline suite on Windows, Linux and macOS (`ci.yml:20-42`).
6. Uses of ADK private API are placed so an upgrade that moves them fails at import, at once:
   `google.adk.utils._schema_utils.validate_schema` (`plugins.py:30`, reason at `plugins.py:210-211`); tests also
   touch `google.adk.cli.utils._nested_agent_loader` and `google.adk.models.lite_llm._to_litellm_response_format`
   (`tests/test_wiring.py:30`, `131`).

---

## 2. Project layout and layering

### 2.1 Packages

The package is grouped by the steps of a review; each group may import only itself and the groups before it:
`core` → `collect` → `judge` → `deliver` (`README.md:278-280`, `adk_review/review.py:7-13`).

| Group | May import | Responsibility | Evidence |
|---|---|---|---|
| `core/` | nothing else in the package | The pure domain: `findings.py` (`Finding`, `Review`, `Checked`, severity scale), `rules.py` (the three rule kinds and `run_rule`), `guidelines.py`, `profiles.py` (check ids, `state_key`, profiles), `verdict.py` (grounding, folding, deciding, exit codes), `secrets.py`, `text.py`, `paths.py`, `evidence.py`, `blast.py`, `health.py` | `adk_review/core/__init__.py:1-6`, `README.md:284` |
| `collect/` | `core` | "Driven adapters that gather what the checks read": read-only git, diffs, ruff and pyrefly adapters | `adk_review/collect/__init__.py:1`, `README.md:285` |
| `judge/` | `core`, `collect` | Everything ADK: `catalog.py`, `checks.py` (rules as a node), `agents.py`, `settings.py`, `config.py`, `plugins.py`, `graph.py`, `run.py`, `tools.py`, `verify.py`; plus the check folders `rules/`, `guidelines/` and the helper door `rule_helpers/` | `adk_review/judge/__init__.py:1-7`, `README.md:286` |
| `deliver/` | `core` alone | The report in all its forms; the driver hands it everything else as values | `adk_review/deliver/__init__.py:1`, `README.md:287` |
| package root | everything | `review.py` (the command, the driver), `push.py`, `commit.py`, `login.py`, `agent.py` (ADK loader entry), `__init__.py`, `config.toml` | `README.md:288` |
| `tui/` (separate project) | `adk_review` as any user would | Terminal front end on Textual; nothing in `adk_review` imports it | `CLAUDE.md:237-241` |

Other top-level folders: `tests/` (the only place tests live, `CLAUDE.md:374`), `scripts/` (demo builder and live
measurements), `docs/reports/` (working notes), `.github/`, `.vscode/`.

### 2.2 How the layering is enforced

It is enforced by a test file of the project's own, `tests/test_layering.py`, reading the syntax tree. No
`import-linter` or similar tool is used (none is in `pyproject.toml` or `uv.lock`).

- No group imports a group after it (`tests/test_layering.py:58-67`).
- `deliver/` reaches only `core` (`:70-77`).
- The package imports its own modules only relatively; an absolute `adk_review.…` import would slip past the
  direction test, so it is forbidden (`:80-90`).
- `core/`, the check files and the helper door import none of `google`, `litellm`, `subprocess`, `httpx`,
  `asyncio`, `os`, `socket`, `urllib`, `http`, `ssl` (`:28`, `:93-102`).
- A guideline imports `core` alone; a rule imports one door, `judge/rule_helpers/`, which imports `core` alone and
  lists in `__all__` exactly what it passes on (`:105-137`, `adk_review/judge/rule_helpers/__init__.py:16-103`).
- Each check folder holds one check per file, named after it, and nothing else, not even `__init__.py`
  (`:149-159`).
- Each group's `__init__.py` docstring states what it may import (`:191-195`).
- Every program `collect/` starts goes through one function, `started`, so a stopped run can end it (`:162-183`).

### 2.3 How the pure core is kept free of ADK and LLM imports at runtime

The syntax tree cannot see what an import loads, so four tests run a fresh interpreter with
`sys.modules['google'] = None`:

- `core/` and every check import with ADK absent and load none of the forbidden modules (`:198-220`).
- `--list-checks`, `--explain`, `--try`, `--version`, a usage error, and the two hooks start without the engine
  (`:223-247`).
- Importing the command loads no `litellm` (`:250-259`).
- A review whose profile names no guideline runs with ADK absent (`:262-295`); the login too (`:318-330`).

The mechanisms that make those pass:

- `adk_review/__init__.py` imports nothing and answers `agent` lazily through PEP 562 `__getattr__`
  (`adk_review/__init__.py:11-17`). Stated reason: with an eager `from . import agent`, importing
  `core.findings` loaded 187 `google.adk` modules and failed with ADK absent (`:3-8`).
- `review.py` imports ADK and the judge's engine modules inside the functions where a review starts, never at its
  top (`adk_review/review.py:80-84`, `1037-1045`). Measured start times are quoted at `review.py:859-863`.
- `judge/settings.py` reads the environment and builds nothing; `judge/config.py` builds models
  (`adk_review/judge/settings.py:1-6`).
- `judge/checks.py` and `judge/run.py` import ADK under `TYPE_CHECKING` or inside the builder function
  (`adk_review/judge/checks.py:29-33`, `152`; `adk_review/judge/run.py:33-37`, `119`).
- LiteLLM is imported only inside `_litellm()` and `LiteLlm` only inside `_bounded()`
  (`adk_review/judge/config.py:171-208`).
- Nothing is built at import in `judge/graph.py`; only `agent.py` builds the chat app at import, and only ADK's
  loader imports `agent.py` (`adk_review/agent.py:1-11`, `adk_review/judge/graph.py:14-20`).

---

## 3. How the ADK application is constructed

### 3.1 ADK surface actually used

| Purpose | Class or function | Import | Evidence |
|---|---|---|---|
| Application object | `App(name=, root_agent=, plugins=)` | `google.adk.apps.app` | `judge/graph.py:31`, `208`; `judge/verify.py:24`, `224` |
| Graph | `Workflow(name=, edges=, max_concurrency=)` | `google.adk.workflow` | `judge/graph.py:34`, `154`, `161`; `judge/verify.py:219-223` |
| Deterministic node | `FunctionNode(func=, name=)` | `google.adk.workflow` | `judge/graph.py:155`; `judge/checks.py:152`, `179`; `judge/run.py:119`, `137` |
| Fan-in | `JoinNode(name=)` | `google.adk.workflow` | `judge/graph.py:152`; `judge/verify.py:221` |
| Model agent | `LlmAgent` | `google.adk.agents` | `judge/graph.py:29`; `judge/agents.py:18`; `judge/verify.py:23` |
| Node context | `Context` (`ctx.state`, `ctx.session.events`, `ctx.invocation_id`) | `google.adk.agents.context` | `judge/graph.py:30`, `61-65`; `judge/run.py:121-135` |
| Routing | `Event(route=...)` | `google.adk.events` | `judge/graph.py:32`, `65` |
| Runner | `InMemoryRunner(app=app)` | `google.adk.runners` | `review.py:1039`, `1060`; `judge/verify.py:26`, `224`; `judge/run.py:21` |
| Session service | the runner's own in-memory one: `runner.session_service.create_session(..., state=)` and `get_session` | | `judge/run.py:57-58`, `72` |
| Plugins | `BasePlugin`; ADK's `DebugLoggingPlugin` | `google.adk.plugins.base_plugin`, `.debug_logging_plugin` | `judge/plugins.py:29`; `judge/graph.py:33`, `183` |
| Callback and tool context | `CallbackContext`, `ToolContext`, `BaseTool`, `State` | `google.adk.agents.callback_context`, `google.adk.tools.tool_context`, `.base_tool`, `google.adk.sessions.state` | `judge/agents.py:19-20`; `judge/tools.py:24-25` |
| Models | `FallbackModel`, `BaseLlm`, `Gemini`, `LLMRegistry`, `LiteLlm` (lazy) | `google.adk.models`, `.base_llm`, `.google_llm`, `.registry`, `.lite_llm` | `judge/config.py:24-27`, `177` |
| Responses | `LlmResponse` | `google.adk.models.llm_response` | `judge/plugins.py:28` |
| Request config | `types.GenerateContentConfig`, `HttpOptions`, `HttpRetryOptions`, `ThinkingConfig`, `UserContent`, `ModelContent` | `google.genai.types` | `judge/config.py:246-258`; `judge/run.py:59` |
| Tracing | `SqliteSpanExporter` with a private `TracerProvider` | `google.adk.telemetry.sqlite_span_exporter` | `review.py:262-273` |
| Env helper | `is_enterprise_mode_enabled()` | `google.adk.utils.env_utils` | `judge/config.py:28`, `92`, `216`, `375` |

Not used anywhere in the package (searched): `RunConfig` (only one test builds one,
`tests/test_failures.py:208`, `226`), any artifact or memory service, `ResumabilityConfig`, `RequestInput`,
`ToolConfirmation`, `static_instruction`, `BuiltInPlanner` (named only to say why it is not used,
`judge/config.py:239-244`), `ContextCacheConfig`, `ReflectAndRetry*`, `EnvironmentToolset`, `LocalEnvironment`,
`TelemetryConfig`, the `@node` decorator, a node `retry_config`, `LlmAgent(mode=...)`, `input_schema`, evaluation
sets or `AgentEvaluator`.

### 3.2 One builder, two shapes

`build_app` owns both the graph and the plugin roster "so a plugin added for one shape is on the other"
(`judge/graph.py:14-15`). The command uses `chat=False` over state it seeds; `adk web` uses `chat=True`.

The graph (`judge/graph.py:150-161`):

```python
agents = tuple(build_guideline(guideline) for guideline in checks.guidelines)
rules = build_checks(checks.rules, evidence, gathered)
middle = (rules, *((agents,) if agents else ()), JoinNode(name="join_guidelines"))
if not chat:
    return Workflow(name=NAME, edges=[("START", *middle)], max_concurrency=CONCURRENCY)
gate, asked = FunctionNode(func=_scoped, name="scoped"), FunctionNode(func=_asked, name="asked")
edges = [
    ("START", _intake(), gate),
    (gate, {True: rules, False: asked}),
    (*middle, build_grounding(checks, fail_on), _verdict()),
]
return Workflow(name=NAME, edges=edges, max_concurrency=CONCURRENCY)
```

- Command shape: `START → checks (FunctionNode) → guidelines in parallel (tuple of LlmAgent) → JoinNode`.
- Chat shape: `START → intake (LlmAgent with tools) → gate (FunctionNode) → {True: checks, False: asked}`, then the
  same middle, then `grounded (FunctionNode) → verdict (LlmAgent)`.
- `"START"` is the string, not an imported symbol (`judge/graph.py:154`, `157`; `judge/verify.py:221`). A tuple of
  nodes inside an edge chain is a fan-out; a dict is a route table keyed by the value in `Event(route=...)`.
- `CONCURRENCY = 3`, "what a free-tier quota tolerates" (`judge/config.py:78-79`).
- Agents are built per call because "an agent object belongs to one parent"; with no guideline the fan-out is left
  out because "ADK refuses an empty fan-out" (`judge/graph.py:147-148`).

The app (`judge/graph.py:185-208`):

```python
plugins = [
    *([RefuseUnready(roles=..., presets=...)] if chat else []),
    StopAtRateLimit(per_turn=chat),
    *([OneTurn(frozenset({*named, VERDICT}))] if chat else []),
    RedactSecretsPlugin(),
    *debug,          # DebugLoggingPlugin(output_path=debug_log, include_session_state=False)
    *kept,           # Recorder(Path(record).expanduser())
    UsageLedger(ceiling=ceiling, named=named, per_turn=chat),
    ReportProviderErrors(),
    progress,
]
workflow = build_workflow(chat=chat, checks=checks, evidence=evidence, fail_on=fail_on, gathered=gathered)
return App(name=NAME, root_agent=workflow, plugins=plugins)
```

A second, separate app runs the verifiers under the same plugin instances: one `Workflow` fanning out
`verifier_<n>` agents into a `JoinNode`, in its own `InMemoryRunner` (`judge/verify.py:218-229`).

### 3.3 A judging agent

Every guideline is built the same way from its one-file definition (`judge/agents.py:220-260`), abbreviated:

```python
return LlmAgent(
    model=build_model(role=guideline.id, preset=guideline.models),
    name=key,                                  # state_key(check_id), e.g. guideline_security
    description=f"Judges the change for {guideline.title}.",
    instruction=(f"{guideline.role} ... {placeholder(BLAST, optional=True)}## The change\n"
                 f"{fenced('change', placeholder(DIFF))}\n\n{REMINDER}"),
    before_agent_callback=without_evidence,
    include_contents="none",
    generate_content_config=request_config(guideline.thinking_budget),
    output_schema=Review,
    output_key=key,
)
```

The verifier has the same shape with `output_schema=Judgements` (`judge/verify.py:80-106`). The chat verdict agent
has `include_contents="none"`, `output_key`, no schema (`judge/graph.py:93-121`). The chat intake is the only
agent with tools: `tools=[inspect_repository, changed_files]`, `before_tool_callback=[one_repository]`
(`judge/graph.py:72-90`).

### 3.4 How it is run

One seeded run, shared by the guidelines' graph and the verifiers' (`judge/run.py:55-75`):

```python
ids = {"app_name": runner.app_name, "user_id": USER, "session_id": session_id}
await runner.session_service.create_session(**ids, state=state)
message = types.UserContent(prompt)
async with asyncio.timeout(RUN_DEADLINE_S):
    async for event in runner.run_async(user_id=USER, session_id=session_id, new_message=message):
        if event.error_code:
            errors[event.author] = f"{event.error_code}: {event.error_message}"
```

- The driver builds the app, one `InMemoryRunner`, and one `asyncio.Runner()` loop shared by the run and its second
  opinion (`review.py:1049-1085`). Stated reason: `asyncio.run` closes its loop, and a client a library kept from
  the first run met a closed loop at the second (`review.py:1033-1036`).
- The seed is `{DIFF: evidence["diff"], IGNORED: [...]}` and the one user message is the fixed word `review`
  (`review.py:1064-1071`, `judge/plugins.py:324-325`).
- No `run_config` is passed (`judge/run.py:65`). Whatever escapes the engine is caught and returned as the run's
  failure; the state is read back either way (`judge/run.py:62-75`).
- Timeouts: `REQUEST_TIMEOUT_S = 180` per call, `RUN_DEADLINE_S = 600` per run (`judge/config.py:73-77`).

### 3.5 How state and outputs flow

- In: session state seeded at `create_session(state=...)`, so the diff is "in no event a debug log could carry"
  (`judge/checks.py:129-131`, `review.py:1031-1032`).
- Into instructions: `{key}` or `{key?}` placeholders, written through one helper (`judge/agents.py:95-98`).
- Out of agents: `output_key`; with `output_schema`, ADK puts the parsed dict in state (`core/findings.py:3-6`).
- Out of function nodes: `ctx.state[key] = value` (`judge/checks.py:169-175`, `judge/run.py:135`).
- Out of tools: `tool_context.state[...]` (`judge/tools.py:64-67`).
- Read back: `read_back(state, key, schema, missing)` validates the dict into the schema, or returns a reason
  string (`judge/agents.py:263-275`); `run.why(agent, default)` gives the agent's own error event, else the
  engine's failure (`judge/run.py:50-52`).
- Every key more than one module uses is a constant in `judge/agents.py` (`SCOPE`, `REPOSITORY`, `DIFF`,
  `IGNORED`, `BLAST`, `QUOTABLE`, `FINDINGS`, `FAILURE`, `judge/agents.py:42-50`). A check's key is its id through
  `state_key`: `rule.no-print` → `rule_no_print`, because an ADK agent name and state key must be identifiers
  (`core/profiles.py:34-37`). A test holds every placeholder to a key something writes
  (`tests/test_engine.py:1320-1353`).
- `temp:` keys last one turn; chat's scope and the failure note use them so a later turn starts clean
  (`judge/agents.py:42`, `50`; `judge/plugins.py:245-246`).
- In chat, the grounding node reads only what this turn wrote, by filtering `ctx.session.events` on
  `invocation_id` and `actions.state_delta` (`judge/run.py:121-128`).

### 3.6 How the root agent is exposed to ADK tooling

`adk_review/agent.py:13-30`:

```python
config = load_config(CONFIG)
policy = config["review"]
checks = select(catalog(registries()), config["profiles"], DEFAULT)
app = build_app(chat=True, checks=checks, fail_on=policy["fail_on"],
                gathered=gathering(checks, policy["diff_cap"], policy["skip"], policy["scan"], policy["third_party"]),
                ceiling=policy["max_tokens"] or None)
root_agent = app.root_agent
```

- Both `app` and `root_agent` are exported: the loader prefers `app`, and a bare `root_agent` would lose the plugins
  (`CLAUDE.md:221-222`, `tests/test_wiring.py:17-23`).
- `root_agent.name` must equal the folder name, `adk_review` (`judge/graph.py:56`, `CLAUDE.md:202`).
- No sub-package module may be named `agent.py`: `adk web`'s nested loader treats any folder holding one, up to
  five levels deep, as an agent. That is why the graph lives in `judge/graph.py`
  (`judge/graph.py:17-20`, `tests/test_wiring.py:26-33`, `tests/test_layering.py:140-146`).
- It is served with `uv run adk web --no_use_local_storage .` from the repository root (`Makefile:35-38`). Stated
  reason: by default ADK keeps each session in `.adk/session.db`, which holds the reviewed diffs unredacted.

### 3.7 ADK behaviours the project recorded (each with the place it is written down)

- An exception that escapes an agent tears the whole `Workflow` down and loses siblings in flight; a node that
  raises ends the run (`judge/plugins.py:179-181`, `judge/checks.py:11-12`).
- ADK validates a structured reply and raises on a mismatch, ending the run (`judge/plugins.py:205-208`).
- Returning a response from the model-error hook yields it in the exception's place; the after-model hook then
  receives what the error hook substituted (`judge/plugins.py:181-183`, `447-448`).
- After-model hooks run on every streamed partial under `adk web`'s Token Streaming; a hook that reads the answer
  must pass a `partial` one by (`judge/plugins.py:212`, `522`; `tests/test_failures.py:199-232`).
- ADK hands a workflow node its predecessor's output as a user turn and keeps other agents' replies as context
  (`judge/plugins.py:332-335`).
- Returning content from `before_agent_callback` skips the agent, and ADK saves that content under its
  `output_key` through its schema (`judge/agents.py:130-131`). The plugin's before-agent hook runs before the
  agent's own guard, and no after-agent hook runs for a skipped agent (`judge/plugins.py:409-410`).
- `before_run_callback` runs once a turn, and a `Content` it returns ends the turn as its answer
  (`judge/plugins.py:296-297`).
- ADK awaits an async tool but calls a sync one inline on the loop (`judge/tools.py:54-55`).
- An agent given tools beside an `output_schema` gets a tool instead of a response schema on some models
  (`judge/plugins.py:246-248`).
- ADK's session service answers `None` for a session it does not hold (`judge/run.py:72-74`).
- ADK restores the variables set before it loads `.env`, so the shell wins (`CLAUDE.md:112-113`).
- ADK logs a failed node with its whole traceback through `google_adk`, warns `EXPERIMENTAL` on tool declarations,
  and genai warns on every Gemini call; all three are silenced once per process (`review.py:1388-1397`).
- ADK declares `LlmAgent(BaseAgent, abc.ABC)` with no abstract method, so pyrefly needs
  `direct-abstract-base-instantiation = "ignore"` (`pyproject.toml:123-125`).
- `maybe_set_otel_providers` also exports to any `OTEL_EXPORTER_OTLP_*` endpoint, so `--trace` builds its own
  provider (`review.py:262-273`).

---

## 4. The code-versus-model split

### 4.1 The stated principle

"The order is the architecture: deterministic evidence and rules first, model judgement second, deterministic
decision last; a model never decides whether the build passes" (`review.py:52-54`; `README.md:242-274`).

### 4.2 Who decides what

| Decision | Decided by | Where |
|---|---|---|
| What is reviewed: repository, head, base, scope, which files are read | Python | `review.py:758-798`, `858-936`; `collect/git.py` |
| Whether the model arm can run at all | Python, before anything is spent, exit 2 | `judge/config.py:261-298`, `review.py:864-870` |
| The evidence: diffs, texts, tree, blast radius, callers | Python, before any model call | `collect/git.py:1104-1128`; `README.md:251-256` |
| Every rule's finding | Python, one class per file, run by `run_rule` | `core/rules.py:438-470`, `judge/checks.py:66-89` |
| Credentials | Python only; every model call is redacted, so no guideline ever sees a key | `README.md:960-965`, `judge/plugins.py:140-173` |
| Whether a change is exploitable, untested, too complex, incorrect, inefficient, fixed at the wrong depth | A model: the six guidelines | `judge/guidelines/*.py`, e.g. `security.py:8-15` |
| Whether a finding really holds (`--verify`) | A second model, with limits set by code | `judge/verify.py:247-286` |
| Whether a model's finding is kept | Python: it must quote whole lines of its own file's diff | `core/verdict.py:254-302` |
| A finding's line number | Python: read off the diff, never taken from the model | `core/verdict.py:273-275`, `292` |
| Which of several findings on one span survives | Python | `core/verdict.py:557-610` |
| The verdict and exit code | Python | `core/verdict.py:619-630` |
| Chat: whether a turn goes on to a review | Python gate on a state key | `judge/graph.py:61-65` |
| Chat: confirming the scope from a conversation | A model, through two tools, behind a guard | `judge/graph.py:72-90` |
| Chat: writing the verdict as prose | A model that "decides nothing"; the verdict line is given to it | `judge/graph.py:93-121`, `judge/run.py:112-137` |

### 4.3 How the line is drawn in the code

- A check is either a rule (code) or a guideline (model). Both are one class in one file, found by the same
  catalog (`judge/catalog.py:154-189`, `223-231`), named by one id scheme, `rule.<name>` or `guideline.<name>`
  (`core/profiles.py:24-31`), written to state under `state_key(id)`, reported in its own section, and switched on
  by the same profile lists in `config.toml` (`adk_review/config.toml:72-136`).
- A guideline file holds only what makes it that guideline: `id`, `title`, `role`, `thinking_budget`, optional
  `cleanup` and per-arm `models` (`core/guidelines.py:31-52`; `judge/guidelines/security.py:8-15` is 8 lines of
  class). Everything else about the agent is shared (`judge/agents.py:1-9`).
- A rule file names `id`, `severity`, `title`, `fix`, optional `why`, `bad` and `good` examples, and one `check`
  method (`core/rules.py:87-147`; `judge/rules/no_print.py:8-26`). The catalog runs each rule against its own
  examples at every start and refuses one that fails them, exit 2 (`judge/catalog.py:127-132`).
- Both kinds answer in a compatible shape, `Checked` for a rule and `Review` for a guideline, each a list of
  `Finding` (`core/findings.py:28-87`), and both become `Sourced(source=<check id>, finding, lines)` for the code
  that decides (`core/verdict.py:38-58`, `493-503`).
- On a tie the fold keeps code's reading: the order is rules first, then guidelines
  (`judge/catalog.py:209-212`, `core/verdict.py:597-610`).
- A profile with no guideline never imports ADK; the same `run_rules` runs straight from the driver
  (`review.py:1006-1025`).
- Code feeds the model: the blast radius and the callers of changed functions are computed in Python and shown to
  the guidelines as fenced context, "context, never evidence" (`judge/agents.py:143-162`, `247-250`).
- A rule may read an outside deterministic tool through an adapter (`collect/tools.py:15-19`,
  `core/rules.py:122-127`).
- Two recorded moves from model to code: secrets (a planted key was not reported by any guideline once redaction
  was on, so "a key must be found by code", `README.md:960-962`), and chat's grounding (the verdict agent once
  decided the verdict itself and reported an ungrounded blocker; a `FunctionNode` now does it with the command's
  own functions, `judge/run.py:112-118`).
- There is no shadow mode, stage registry or parity harness. What exists for comparing a model's behaviour before
  and after a change is section 7.4.

### 4.4 How model output is constrained

Before the call:

- Temperature zero on every judging call, on both arms; a model that cannot do that is refused before any call
  (`judge/config.py:246-248`, `281-298`, `323-334`; `tests/test_wiring.py:74-86`).
- `include_contents="none"`: the agent reads only its instruction (`judge/agents.py:255-256`). In chat a plugin
  also replaces the turn with one fixed word (`judge/plugins.py:328-348`).
- Every untrusted section sits between two marker lines carrying a per-process nonce, with a reminder after it
  (`judge/agents.py:70-92`, `101-104`). Details in section 6.4.
- Every string a model reads is capped in characters with the cut named, and the cut never falls inside a
  credential (`core/text.py:103-120`; caps at `judge/agents.py:53-69`, `judge/tools.py:31-33`).
- A token ceiling reserves each call's estimated cost first and refuses the call that would pass it
  (`judge/plugins.py:440-518`).

In the reply:

- `output_schema` is a Pydantic model that becomes the provider's response schema. `Review.findings` and
  `Judgements.judgements` are required lists, so an answer naming none is refused rather than read as "nothing
  found" (`core/findings.py:73-77`, `judge/verify.py:68-72`). Severity and verdict are `Literal`
  (`core/findings.py:17`, `judge/verify.py:61`). Every field carries a `description`, and a test holds each arm's
  converted schema to those descriptions (`tests/test_wiring.py:122-142`).
- The schemas are plain `BaseModel`, with no `extra="forbid"` and no PEP 695 `type` alias. Stated reason, measured:
  `extra="forbid"` sent Gemini `additionalProperties`, which its `response_schema` refused with a 400, and a PEP 695
  `type Severity` became a `$ref` whose description both arms dropped (`tests/test_wiring.py:127-130`).
- Field validators cut a model's title, suggestion, reason and code at fixed lengths instead of refusing the reply
  (`core/findings.py:47-70`).

After the reply:

- A reply that does not fit its schema, a cut one included, becomes that agent's own error, `SCHEMA_MISMATCH`,
  instead of ending the run (`judge/plugins.py:203-229`).
- `read_back` validates again when the state is read (`judge/agents.py:263-275`).
- Grounding: a finding stays only where its quote is whole lines of its own file's diff, in one hunk, as the model
  saw them; the rest are dropped and counted (`core/verdict.py:254-302`).
- A dropped or refuted finding at the bar is a hole, never an approval (`core/verdict.py:80-84`, `619-630`).
- A verifier's `refuted` drops a finding, with the reason named; a security rule's finding is kept as disputed;
  `unsure`, no judgement, or a failed verifier keeps the finding (`judge/verify.py:269-286`, `236-244`).

Failure handling ("did not look must never read as found nothing", `CLAUDE.md:281`):

- A provider error becomes the agent's own error event; a schema agent's `output_key` stays unwritten
  (`judge/plugins.py:231-255`).
- A guideline with no evidence is skipped by `before_agent_callback` and later read as a check that could not look
  (`judge/agents.py:107-140`, `judge/run.py:129-134`).
- A rule that raises or cannot read a file answers `Checked(could_not_look=...)` (`core/rules.py:444-470`).
- Any hole makes the verdict `DEGRADED`, exit 3 (`core/verdict.py:628-629`).

Retries:

- In the clients, one constant: `RETRY_ATTEMPTS = 3` (`judge/config.py:69-72`). Gemini's ride on the request's
  `HttpRetryOptions`; Copilot's are the OpenAI SDK's `max_retries` (`judge/config.py:153-157`, `246-258`).
- No node `retry_config`: it "would re-run a whole guideline, and with the error plugin turning errors into
  answers it would never see one" (`README.md:1074-1076`).
- A fallback model on a 429, a 5xx or a timeout (`judge/config.py:120-161`).
- After a 429 nothing got past, no later call of the run is sent (`judge/plugins.py:258-291`).

---

## 5. Provider handling (brief)

- Selection: `REVIEW_PROVIDER`, `copilot` when unset or blank, validated in one place
  (`judge/settings.py:25-35`). Defaults: `gpt-4.1` on Copilot, `gemini-2.5-flash` on Gemini
  (`judge/settings.py:16`).
- Settings versus construction: `judge/settings.py` reads names and paths and imports no ADK
  (`judge/settings.py:1-14`); `judge/config.py` is "the only file in the reviewer that names a provider"
  (`judge/config.py:3`).
- Per-role models, most specific first: `REVIEW_<ROLE>_MODEL`, the guideline file's `models` for the arm,
  `REVIEW_MODEL`, the arm's default (`judge/settings.py:38-48`). Reserved roles: `verifier`, `fallback`
  (`core/guidelines.py:16-18`).
- Construction (`judge/config.py:120-157`): on Gemini a plain model-name string, or
  `FallbackModel(models=names, retriable_status_codes=_FALL_BACK_ON)`; on Copilot
  `Bounded(model="github_copilot/<name>", max_retries=RETRY_ATTEMPTS - 1, _skip_mcp_handler=True)`, where `Bounded`
  subclasses `LiteLlm` to hold one deadline over a call and all its retries and to raise a 408-status timeout a
  fallback can move on from (`judge/config.py:164-193`). `_FALL_BACK_ON` is ADK's default codes plus 408
  (`judge/config.py:160-161`).
- Copilot workarounds: `LITELLM_MODE=PRODUCTION` and `LITELLM_LOCAL_MODEL_COST_MAP=True` set before importing
  LiteLLM, and the token folder's `~` expanded for it (`judge/config.py:196-208`,
  `judge/settings.py:101-110`); `litellm.suppress_debug_info`, `litellm.disable_copilot_system_to_assistant`
  (`judge/config.py:141-145`); a `logging.Filter` that hides bearer tokens in LiteLLM's log
  (`judge/config.py:54-68`, `148`); no retries requested on the request, since ADK forwards them as `num_retries`
  around the SDK's own (`judge/config.py:226-235`).
- Thinking: set as `thinking_config` on the request, only on Gemini; LiteLLM never forwards it
  (`judge/config.py:239-249`). A test asserts `agent.planner is None` on both arms (`tests/test_wiring.py:306-319`).
- Readiness, `require_ready` (`judge/config.py:261-384`): Copilot needs a non-empty cached token and a model
  LiteLLM will send temperature 0; Gemini asks google-genai itself by building and closing a client, and refuses a
  name ADK would send to another provider's class.
- Login, `adk_review/login.py`: GitHub's device flow with GitHub's own window, about fifteen minutes, where
  LiteLLM polls for sixty seconds (`login.py:1-13`, `141`, `155-171`); `os.umask(0o077)` first, then files `0o600`
  and folder `0o700` (`login.py:42-53`, `109`); Enterprise endpoints read from `.env`
  (`login.py:174-187`); the token exchanged once at once so a seatless account fails here (`login.py:197-229`).
- `truststore.inject_into_ssl()` before any client is built, in both `config.py` and `login.py`
  (`judge/config.py:44-48`, `login.py:36-37`).
- The report names the model, the arm, and Vertex AI or an Enterprise host (`judge/config.py:82-117`).

---

## 6. Plugins, callbacks and tools

### 6.1 Plugins (all in `adk_review/judge/plugins.py`), in registration order

| Plugin | Hooks | What it does | Lines |
|---|---|---|---|
| `RefuseUnready` (chat only) | `before_run_callback` | Asks `require_ready` once a turn, in a thread; if the arm cannot run, answers the turn before any agent runs | `294-321` |
| `StopAtRateLimit` | `before_run`, `before_model`, `on_model_error` | Remembers the first 429 that got past retries and fallback; answers every later call `RATE_LIMITED`, unsent | `258-291` |
| `OneTurn` (chat only) | `before_model_callback` | Replaces a judging agent's conversation with one fixed user turn, `review` | `324-348` |
| `RedactSecretsPlugin` | `before_model`, `after_tool` | Scrubs secret shapes from every request's text parts, the system instruction and every tool result; fail-closed: on any error it returns `REDACTION_FAILED` and the call is not made | `140-173` |
| `DebugLoggingPlugin` (ADK's, on `--debug-log`) | | Logs each request as sent, after redaction, with `include_session_state=False` | `judge/graph.py:181-183` |
| `Recorder` (on `--record`) | `before_model`, `after_model` | Keeps each model answer in a folder under a hash of the request as the model read it, nonces replaced by placeholders | `351-389` |
| `UsageLedger` | `before_run`, `before_model`, `after_model` | Counts calls, tokens and cached tokens per agent; with a ceiling, reserves each call's estimate and refuses the call that would pass it (`TOKEN_CEILING`) | `440-550` |
| `ReportProviderErrors` | `before_model`, `after_model`, `on_model_error` | Turns a provider error into the agent's own error response, and a schema mismatch into `SCHEMA_MISMATCH` | `176-255` |
| `Progress` | `before_agent`, `after_agent` | Times each agent and, when asked, prints a start and finish line per guideline | `392-437` |

Order is deliberate: the first plugin to answer short-circuits the rest; redaction comes before the log and the
recorder so each records the request as the model reads it (`judge/graph.py:181-206`,
`.github/instructions/reviewer.instructions.md:117-123`). Every hook is keyword-only and marked `@override`,
because "a misnamed parameter would build fine and fail on the first live call" (`judge/plugins.py:7-8`).

The stated rule for plugin versus callback: "A callback is per agent and is where 'this agent's tools are guarded'
belongs. A plugin is registered once on the `App` and applies to every agent" (`judge/plugins.py:3-7`).

### 6.2 Agent-level callbacks

- `before_agent_callback=without_evidence` on every guideline: skips the agent when nothing was gathered or an
  earlier call of the turn failed (`judge/agents.py:119-140`, `254`).
- `before_tool_callback=[one_repository]` on the intake (`judge/graph.py:89`, `judge/tools.py:103-119`). A test
  holds every agent that has tools to carrying it (`tests/test_wiring.py:89-100`).

### 6.3 Tools

- Two tools, both plain async functions listed in `tools=[...]`: `inspect_repository(repo, base, head,
  tool_context)` and `changed_files(tool_context)` (`judge/tools.py:36-100`).
- ADK builds the schema from the signature and docstring, "so the docstring is prompt material"; the
  `tool_context` parameter is filled by ADK (`judge/tools.py:3-8`).
- Every tool returns a `{"status": "success" | "error", ...}` dict and never raises at the model
  (`judge/tools.py:5-6`, `65`, `84-88`).
- Blocking work goes through `asyncio.to_thread` (`judge/tools.py:54-56`, `86`).
- Output is capped with the cut named (`judge/tools.py:31-33`, `89-99`).
- Restriction: tool arguments are untrusted. The guard refuses a `repo` that is not a directory, or not the first
  repository the conversation confirmed (`judge/tools.py:103-119`). No tool takes a file path, and the intake reads
  no diff (`judge/tools.py:9-12`).
- There is no tool that writes, runs a command or edits a file. The project writes nothing into the repository it
  reviews (`CLAUDE.md:290-292`).

### 6.4 Safety measures

Secrets:

- Redaction on every request and tool result, fail-closed (`judge/plugins.py:140-173`); shapes shared with the
  secrets rules (`core/secrets.py:342-392`).
- No cap cuts inside a credential (`core/text.py:106-120`); git's hunk-header function guess is stripped because a
  credential cut there reached the model (`CLAUDE.md:307-309`).
- The diff is seeded as session state, never carried in an event; the debug log excludes session state
  (`judge/checks.py:129-131`, `judge/graph.py:181-183`).
- Bearer filter on LiteLLM's logger (`judge/config.py:54-68`). Token files owner-only (`login.py:42-53`, `109`).
  Recorder folder `0o700` (`judge/plugins.py:387`).
- `adk web --no_use_local_storage` (`Makefile:35-38`). Tracing to a local SQLite file only (`review.py:262-273`).
- The assistants' rule: never read, print or quote `.env`, a key, or the Copilot token folder
  (`CLAUDE.md:114-117`); VS Code never auto-approves a command naming `.env` (`.vscode/settings.json:26-33`).

Prompt injection:

- Fences with a nonce drawn once per process (`BOUNDARY`), and a second nonce no guideline is shown
  (`JUDGED_BOUNDARY`) around text that holds a guideline's own words (`judge/agents.py:70-79`).
- The content is never escaped, because a guideline quotes the diff verbatim and grounding holds the quote to the
  real lines (`judge/agents.py:72-74`).
- A reminder is the last thing each instruction says (`judge/agents.py:87-92`).
- Only the instruction and one fixed turn are read (`include_contents="none"`, `OneTurn`).
- On Copilot the instruction is sent as the system turn (`judge/config.py:142-145`).
- Paths and other branch text placed in a prompt are flattened to one line (`judge/agents.py:155-156`).
- Code-side rules: `reviewer-instructions` flags text that addresses the reviewing model, after NFKC
  normalisation and tag-character decoding (`judge/rules/reviewer_instructions.py:1-47`); `hidden-text` and
  `steering-files` are in the default or full profiles (`config.toml:84-89`, `112-118`).
- A model cannot remove a security rule's finding, and a refuted finding at the bar is a hole
  (`judge/verify.py:278-284`, `core/verdict.py:625-628`).
- The report's safety steps keep branch or model text from forging headings, CI commands, links or mentions
  (`deliver/report.py:44-92`, `1819`; `README.md:1216-1226`).

Paths, processes and writes:

- `--path` values that start at a root or drive, or contain `..`, are refused (`review.py:539-554`).
- Programs run by full path from `PATH`'s absolute entries, as argv lists, with a timeout; details in section 8.
- git: read-only verbs only, in a fixed environment (`collect/git.py:109-141`).
- Ruff and pyrefly run on copies in a temporary folder, under names the rule chooses, never in the checkout
  (`collect/ruff.py:264-290`).
- Output files: written to a temporary file beside the target and moved over it; an earlier file is removed first;
  a link is removed, never written through (`review.py:703-744`).

Budget:

- Token ceiling, concurrency bound, per-call and per-run deadlines, rate-limit stop (sections 3.4, 4.4, 6.1).

---

## 7. Testing

### 7.1 Running the real engine with a fake model

- `tests/conftest.py` defines `FakeModel(Gemini)` with `supported_models()` returning `[r"fake.*"]` and registers
  it with `LLMRegistry.register(FakeModel)` (`tests/conftest.py:186-223`). Setting `REVIEW_MODEL=fake` makes the
  project's real `build_model()` hand its agents the fake: "nothing in the reviewer is patched", and the real
  loader, Runner, `Workflow`, callbacks and plugins all run (`tests/conftest.py:1-14`).
- The fake answers the canned payload the request's `response_schema` accepts, else a sentence
  (`tests/conftest.py:123-131`, `196-220`), and reports fixed usage so the ledger has numbers.
- `fake_provider` fixture, keyed on text in the system instruction: `raises_when`, `answers_when`, `calls_when`
  (a `types.FunctionCall`, to simulate a tool call), `replays(folder)` (`tests/conftest.py:134-180`, `226-231`).
- `load_agent(monkeypatch, provider="gemini", model="fake")` deletes the package from `sys.modules` and imports
  `adk_review.agent` afresh; `load_command` does the same for the command and stubs `load_dotenv`; `cli` is the
  fixture form (`tests/conftest.py:760-770`, `824-836`).
- `Chat(module, state, run_config)` holds one conversation over several turns through `InMemoryRunner`;
  `run_turn` is one turn; `asked` records each request as the model received it, after every plugin
  (`tests/conftest.py:855-918`).
- `confirms(fake_provider, repo)` makes chat's intake call its tool as a model would (`tests/conftest.py:898-901`).

### 7.2 The Copilot arm offline

- With ADK's client replaced: `monkeypatch.setattr(LiteLLMClient, "acompletion", answer)` returning a
  `litellm.ModelResponse`, a cached-token fixture, and `load_command(monkeypatch, "copilot", "gpt-4.1")`; the whole
  review then runs through ADK's LiteLLM wrapper (`tests/test_engine.py:191-216`, `218-246`;
  `tests/test_wiring.py:264-303`).
- With only the network replaced, below LiteLLM: `monkeypatch.setattr(httpx.AsyncClient, "send", send)`, used
  where LiteLLM's own routing is the thing under test (`tests/test_engine.py:278-310`). Stated reason: a LiteLLM
  1.106.0 regression passed every test above that level (`CLAUDE.md:356-359`).
- "A change to that path needs a test there" (`CLAUDE.md:356`).

### 7.3 Isolation, organisation, naming

- Autouse fixtures remove every `REVIEW_*`, Google and Copilot variable and point the Copilot token folder at one
  no test made (`tests/conftest.py:254-271`); the umask is restored after each test (`:242-251`).
  `pytest_configure` sets `LITELLM_MODE=PRODUCTION` and `LITELLM_LOCAL_MODEL_COST_MAP=True` before any import
  (`:234-239`). Tests assert the suite reads neither the developer's `.env` nor the network
  (`tests/test_wiring.py:152-186`).
- Real git repositories as fixtures: `demo_repo` (session scope, built by `scripts/make_demo_repo.py`),
  `hostile_repo` (a branch per way a change once hid from the review), shallow and partial clones
  (`tests/conftest.py:274-277`, `485-706`). Fixture git runs with none of the developer's config (`:339-354`).
- Plugins are unit-tested by calling their hooks directly with `SimpleNamespace` stand-ins
  (`tests/test_engine.py:504-545`, `tests/test_failures.py:241-309`).
- Graph structure is asserted off `Workflow.graph.nodes` and `.graph.edges` (`tests/test_engine.py:1387-1402`,
  `tests/test_wiring.py:74-100`). A single node is run alone in a small `Workflow` (`tests/test_engine.py:1361-1379`).
- Schemas are checked as each arm's own converter writes them into the request (`tests/test_wiring.py:122-142`).
- Streaming is tested with `RunConfig(streaming_mode=StreamingMode.SSE)` and a fake that yields partials
  (`tests/test_failures.py:199-232`).
- Files by subject, all flat in `tests/`: `test_wiring.py` (loader, arms, agent shape), `test_engine.py`
  (retries, ceiling, second opinion, fences, state keys, checks node), `test_failures.py` (provider errors, login,
  hooks), `test_reviewer.py` (grounding, secrets, plugins, report), `test_command.py` (the CLI end to end),
  `test_catalog.py`, `test_rules.py`, `test_rule_helpers.py`, `test_git_tools.py`, `test_measures.py`,
  `test_callbacks.py`, `test_layering.py`, `test_portability.py`, `test_docs.py`, `test_copilot.py`,
  `test_tui.py`, `test_tui_azure.py`.
- Settings: `asyncio_mode = "strict"` so async tests carry `@pytest.mark.asyncio`; `faulthandler_timeout = 300`
  with exit on timeout; `testpaths = ["tests"]`; `pythonpath = [".", "tui"]` (`pyproject.toml:53-73`).
- A test is named as the sentence it proves; a helper several tests need goes into `conftest.py`, never into the
  package (`CLAUDE.md:374-376`). Tests are not type-checked (`pyproject.toml:114-117`).

### 7.4 What `scripts/` measures against real models

All three live scripts run the command as a subprocess and read its `--json` report; each calls a provider and is
run "only when the task says so" (`CLAUDE.md:77-78`).

| Script | Measures | Evidence |
|---|---|---|
| `scripts/measure.py --runs N` | Per planted defect on the demo branch: in how many runs a guideline named it and at what severity; findings on no planted defect (an upper bound on false ones); the model's own blockers; verdicts across runs; dropped findings; tokens and time | `scripts/measure.py:1-17` |
| `scripts/labelled_set.py --runs K` | Branches each holding one known defect, or none: found, and by which guideline; missed; and on clean branches the false findings at every severity, run by run | `scripts/labelled_set.py:1-21` |
| `scripts/injection_suite.py --runs K` | Whether a payload beside a known defect (plain, wrapped, tag characters, look-alike letters, fake end marker, "already approved", a file path) makes a guideline lose that defect | `scripts/injection_suite.py:1-12` |
| `scripts/make_demo_repo.py` | Not a measurement: builds the golden demo repository, offline and repeatable | `scripts/make_demo_repo.py:1-25` |

The scripts' own logic (building branches, scoring) is tested offline with `subprocess.run` replaced
(`tests/test_portability.py:316-606`). Record and replay closes the loop: `--record` keeps live answers, and a
test shows a fake answering only from the recording reproduces the review exactly
(`tests/test_command.py:3379-3394`).

### 7.5 What "the docs are tested" means

- Every guide (`CLAUDE.md`, `GUIDE.md`, `tui/README.md`, every Markdown file under `.github/`) may name only
  backticked paths that exist in the working tree (`tests/test_docs.py:19-45`).
- `README.md` must name every module at the package's root (`tests/test_docs.py:74-77`).
- `GUIDE.md` must hold every flag the argument parser takes and no other, the checks table exactly as
  `--list-checks` prints it, every JSON field in order, and each limit equal to the constant it names
  (`tests/test_docs.py:80-113`).
- The files under `.github` are held to their formats (`tests/test_copilot.py`, section 10).
- Every sentence the package prints is held to a style: at most 20 words, no `;` joining two
  (`tests/conftest.py:294-302`, `tests/test_command.py:3055-3102`).
- The docs carry no dates and no counts of the repository's current state (`CLAUDE.md:384-385`).

---

## 8. Cross-platform practice

Hard rule: "Support Windows and macOS alike, and Linux: every change works, and is tested, on each"; a test is
skipped on one system only where what it tests cannot exist there, and its reason says so (`CLAUDE.md:20-23`).

| Area | What is done | Evidence | Stated reason |
|---|---|---|---|
| CI | Lint, type check and suite on `windows-latest`, `ubuntu-latest`, `macos-latest`, `fail-fast: false`, 20-minute timeout | `.github/workflows/ci.yml:20-42`; mirrored in `azure-pipelines.yml:11-40` | "Windows is proven here, not argued" (`ci.yml:1-2`); a hung git once hung a review |
| Line endings in the repository | `* text=auto eol=lf` | `.gitattributes:1-3` | A commit made on Windows changes no line endings |
| Line endings in written files | Every file a script or fixture commits, and every report, is written with `newline="\n"` | `CLAUDE.md:341`; `review.py:728-733`; `scripts/make_demo_repo.py:565`; `tests/conftest.py:386-391`, `402` | Text mode writes `\r\n` on Windows and git commits it; a `\r` after `#!/bin/sh` names no shell |
| Line endings in git's answers | `core.autocrlf=input` fixed for every git call | `collect/git.py:88-99` | A checkout Windows wrote with CRLF over LF blobs read as changed in every line |
| Line splitting | `lines_of` splits at `\n` only, CRLF as one break | `core/text.py:87-93` | `str.splitlines` breaks at form feed and U+2028 and put every later line one off |
| Console encoding | `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` at the start of each command that prints | `review.py:764-765`, `login.py:110-111`, `commit.py:53-54`; held by `tests/test_portability.py:78-91` | A Windows console is a code page, and a report holds an em dash |
| Subprocess decoding | Every `subprocess.run` that decodes passes `encoding=`; git's output is read as bytes and decoded as UTF-8 in code | `tests/test_portability.py:32-45`; `collect/git.py:243-247` | `text=True` alone decodes with the console's encoding; text mode reads a lone `\r` as a line break |
| File encodings | `.env` that is not UTF-8 is a sentence and exit 2; `config.toml` read as `utf-8-sig` | `review.py:759-763`, `login.py:181-186`; `judge/catalog.py:77` | Windows PowerShell 5.1's `>` writes UTF-16; Notepad saves a BOM |
| Finding programs | Full path from `PATH`'s absolute entries only; `NoDefaultCurrentDirectoryInExePath=1`; a bare name is never launched | `collect/git.py:144-158` | Windows searches the current directory first, and it can be the checkout under review |
| Tools beside the interpreter | `sysconfig.get_path("scripts")` plus `ruff.exe` or `ruff` by `os.name` | `collect/ruff.py:395-399`, `collect/pyrefly.py:642` | An installed command's environment is never activated, so never on `PATH` |
| Timeouts and process trees | On timeout on Windows: `taskkill.exe /F /T /PID`, then read the output to its end, then kill | `collect/git.py:193-209`; Windows-only test at `tests/test_git_tools.py:413` | Git for Windows' `git.exe` runs the real git as a child that holds the output open |
| Stopping | `SIGTERM` handler raises a `BaseException` and kills every started program | `review.py:635-644`, `1398-1400`; `collect/git.py:161-190` | No signal reaches a thread waiting on a process. The signal tests are skipped on Windows, which "ends a process without a signal its code can catch" (`tests/test_command.py:3559`, `3599`) |
| Temporary folders | `tempfile.gettempdir()`, never `/tmp/`; `TemporaryDirectory(ignore_cleanup_errors=True)` | `tests/test_portability.py:48-50`; `collect/ruff.py:265-267`, `collect/pyrefly.py:112`, `472`, `push.py:138` | On Windows another process, a virus scan, can hold a file after it was read, and the removal raised after the work was done |
| Files Windows cannot hold | Copies for ruff and pyrefly are written under names the rule chooses; ruff runs `--no-cache` | `collect/ruff.py:270-272`, `286-290` | `x.py` beside `X.py/y.py` collides on a case-insensitive disk; Windows holds no `nul.py` or `a:b.py`; a cache file could be held open |
| Atomic writes | The temporary file is closed before `os.replace` | `review.py:737-740` | "Windows moves no open file" |
| Writable-folder test | Make and remove a file in the folder | `review.py:691-700` | Windows reads a folder's own mode as no bar to a file in it |
| Path comparison | `os.path.normcase`, and a case- and Unicode-form-folded compare | `review.py:673`; `core/paths.py:238-240`; `core/rules.py:426-435` | Windows and macOS read two spellings of one file alike |
| Path input | `\` accepted as `/` in `--path`; a root or drive refused via `PureWindowsPath(...).anchor` | `review.py:544-549` | |
| Paths handed to a shell | Printed commands use POSIX quoting, or on Windows a form both cmd and PowerShell read, or no command at all; paths with forward slashes | `deliver/report.py:856-880` | Git Bash drops a backslash; `$`, backtick, `%`, `!` expand in one shell or the other |
| macOS Unicode | `core.precomposeUnicode=false` | `collect/git.py:94`, `121` | macOS's precomposed names found no file committed in NFD |
| Repository ownership | `safe.directory` set to the one repository named | `collect/git.py:137`; `tests/conftest.py:52-56` | On a company Windows machine git refuses a checkout another account owns |
| File modes | `umask(0o077)`, `chmod 0o600` and `0o700`, unconditionally; their tests are skipped on Windows | `login.py:42-53`, `109`; `tests/test_failures.py:949`, `962` | "a Windows file has no owner/group/other modes to narrow" |
| Symbolic links | Tests that need one skip where the account may not make one | `tests/test_command.py:2341`, `tests/test_git_tools.py:1199` | A link needs a privilege on Windows |
| Hooks | Tests run hook scripts through git's own `sh`, found beside `git.exe` on Windows | `tests/conftest.py:372-383` | Git for Windows runs a hook through its own shell |
| Certificates | `truststore.inject_into_ssl()`; `UV_SYSTEM_CERTS=true` advised for uv itself | `judge/config.py:44-48`; `README.md:49-50` | Measured on a company Windows machine behind a TLS-inspecting proxy |
| Lint exception | `SIM112` ignored | `pyproject.toml:98-100` | It would upper-case Windows' own `SystemRoot` and `NoDefaultCurrentDirectoryInExePath` |
| macOS install | Needs Xcode Command Line Tools | `README.md:27-29` | `watchdog` 6, which ADK needs, has no Python 3.14 wheel on macOS |
| Config and state directories | Only in the `tui/` member: `%APPDATA%` and `%LOCALAPPDATA%` on Windows, `$XDG_CONFIG_HOME` or `~/.config` and `$XDG_STATE_HOME` or `~/.local/state` elsewhere | `tui/tui/config.py:28-46`, `tui/README.md:45-50` | The reviewer itself has no per-user config folder: its `config.toml` is in the package (`judge/catalog.py:31`) and the Copilot token folder is `~/.config/litellm/github_copilot` on every system (`judge/settings.py:94-98`) |
| TUI on Windows | Console window suppressed for child processes, process tree killed with `taskkill`, system clipboard, key choices safe in the classic console, `az.cmd` run with fixed arguments | `tui/tui/git_sync.py:139`, `181-200`; `tui/tui/app.py:1604-1608`; `tui/tui/clipboard.py:29`, `59`; `tui/tui/azure_client.py:6`; `CLAUDE.md:265-270` | |

`Makefile` targets are POSIX `make`; every target is a thin wrapper over a `uv run` command that also works typed
directly, and the README shows the Windows form where it differs (`README.md:106`).

---

## 9. Entry points, configuration, installation

### 9.1 Commands

| Command | Entry | Purpose | Evidence |
|---|---|---|---|
| `adk-review` | `adk_review.review:run` | The review; also `--dry-run`, `--list-checks`, `--explain`, `--try` | `pyproject.toml:35`; `review.py:1403-1411` |
| `adk-review-push` | `adk_review.push:run` | git pre-push hook, rules only | `pyproject.toml:36`; `push.py:1-22` |
| `adk-review-commit` | `adk_review.commit:run` | git pre-commit hook, rules only | `pyproject.toml:37`; `commit.py:1-13` |
| `adk-review-login` | `adk_review.login:run` | One-time Copilot device-flow login | `pyproject.toml:38` |
| `python -m adk_review.review` | same module | The command spelled long | `review.py:1410-1411` |
| `adk web --no_use_local_storage .`, `adk run` | `adk_review/agent.py` | The same graph as a chat | `Makefile:35-38`, `agent.py:1` |
| `adk-review-tui` | `tui:run` (workspace member) | Terminal front end | `tui/pyproject.toml:16-17` |
| pre-commit hook ids `adk-review`, `adk-review-commit` | | | `.pre-commit-hooks.yaml:12-32` |

Structure of a command: `run()` does process-wide settings once (`settle()`: warning filters, log handlers, the
`SIGTERM` handler) and calls `main(argv)`, which stays a function of its arguments and wraps everything so that no
error ends as Python's own exit 1 (`review.py:1356-1407`). Argument parsing is `argparse`, with every usage error
ending by naming `--help` (`review.py:276-302`).

Exit codes: 0 approved, 1 a finding at the bar, 2 a usage error before any model call, 3 a hole, 130 Ctrl-C,
143 SIGTERM (`core/verdict.py:24-28`, `GUIDE.md:102-117`).

### 9.2 Configuration

- `adk_review/config.toml`, shipped inside the package beside `review.py`, is the one policy file: `[review]`
  holds each flag's default, `[profiles]` holds named lists of check ids (`config.toml:1-9`, `65-136`). It is read
  whole: an unknown section or key, a missing key, or a wrong type is a sentence and exit 2
  (`judge/catalog.py:71-94`). Nothing is read from the repository under review (`CLAUDE.md:169-170`).
- `.env` at the checkout's root, copied from `.env.example`, holds the provider, models and keys
  (`.env.example:1-3`). The command loads it without overriding, so the shell wins (`review.py:758-760`). An
  installed command reads the shell alone.
- Environment variables (`GUIDE.md:276-295`): `REVIEW_PROVIDER`, `REVIEW_MODEL`, `REVIEW_VERIFIER_MODEL`,
  `REVIEW_<ID>_MODEL`, `REVIEW_FALLBACK_MODEL`, `REVIEW_REGISTRIES`; `GOOGLE_API_KEY`,
  `GOOGLE_GENAI_USE_ENTERPRISE`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`; `GITHUB_COPILOT_TOKEN_DIR`,
  `GITHUB_COPILOT_ACCESS_TOKEN_FILE`, `GITHUB_COPILOT_API_KEY_FILE`, `GITHUB_COPILOT_API_BASE`,
  `GITHUB_COPILOT_DEVICE_CODE_URL`, `GITHUB_COPILOT_ACCESS_TOKEN_URL`, `GITHUB_COPILOT_API_KEY_URL`,
  `GITHUB_COPILOT_CLIENT_ID`; `SSL_CERT_FILE`; `LITELLM_LOCAL_MODEL_COST_MAP`.
- The front end's own config: `tui/.tui.toml` in a checkout, or `tui.toml` in the per-user folder
  (`tui/README.md:45-46`).

### 9.3 How users install and run it

- From a checkout: `uv sync --locked`, then `uv run adk-review ...` (`README.md:33-37`).
- As a command on `PATH`: `make install` in a checkout (every dependency at the lock's version), or
  `uv tool install --exclude-newer P3D git+<repository-url>` with none (`README.md:39-50`, `Makefile:29-33`).
- The installed command is a copy; to update, `git pull` and `make install` again, or `--reinstall`
  (`README.md:52-59`).
- In a pipeline: the reviewer checked out at a pinned commit beside the repository under review, run with
  `uv run --locked python -m adk_review.review ...`, the exit code as the verdict, `--json` for later steps
  (`README.md:764-843`).
- Two guides: `README.md` for developers (architecture, how to write a check) and `GUIDE.md` for users (every
  flag, check, JSON field and limit) (`CLAUDE.md:10-11`).

---

## 10. The repository's GitHub Copilot files

| File | Used for | Evidence |
|---|---|---|
| `.github/copilot-instructions.md` | The short form of `CLAUDE.md` for GitHub Copilot wherever it runs: hard rules, secrets rule, commands, the rules the tests enforce, style. A rule that changes in one changes in the other | `.github/copilot-instructions.md:1-16`; `CLAUDE.md:389-392` |
| `.github/instructions/reviewer.instructions.md` | Path-specific rules, `applyTo: "adk_review/**"`: layering, check shape, state keys, plugins | `:1-3` |
| `.github/instructions/tests.instructions.md` | `applyTo: "tests/**"`: the fixtures, naming, async | `:1-3` |
| `.github/instructions/docs.instructions.md` | `applyTo: "**/*.md"`: what the docs tests hold, no dates, no counts | `:1-3` |
| `.github/skills/new-rule/SKILL.md`, `new-guideline/`, `review-a-branch/`, `update-docs/` | Procedures for the recurring tasks, each a slash command in VS Code's chat; front matter `name` and `description` | e.g. `.github/skills/new-rule/SKILL.md:1-4` |
| `.github/agents/reviewer-author.agent.md` | A custom agent that implements a change "the way its tests demand" | `:1-16` |
| `.github/workflows/copilot-setup-steps.yml` | The cloud agent's environment: checkout, pinned uv, `uv sync --locked --all-packages`; calls no model | `:1-26` |
| `.github/pull_request_template.md` | A five-item checklist: gate green, guides updated, imports one way, both arms, no dates or `.env` | `:1-9` |
| `.vscode/settings.json`, `extensions.json` | Recommends Copilot Chat, Ruff, Pyrefly; lets an agent run the offline gate without asking; a command naming `.env` always asks | `.vscode/settings.json:26-33` |

Claude Code loads none of the `.github` files by itself; `CLAUDE.md` tells it which skill file to read before each
recurring task (`CLAUDE.md:398-403`).

Tests hold these files to their formats (`tests/test_copilot.py`): each `applyTo` glob matches a real file
(`:41-45`); each agent is named after its file and has a description (`:48-53`); each skill's `name` equals its
folder, matches `[a-z0-9-]{1,64}`, and has a description of at most 1024 characters (`:56-61`); the setup job is
named `copilot-setup-steps` with a timeout of at most 59 minutes (`:64-68`); and the pipeline and Dependabot
checks of section 1.

---

## 11. Conventions a sibling project would be expected to follow

From "Hard rules for every change" (`CLAUDE.md:13-26`):

1. Validate before implementing: reproduce each finding first (a probe, a measurement, or a failing test) and
   confirm its cause in the code. A finding that does not reproduce is reported, never fixed.
2. Size a change to its benefit: prefer the smallest fix, a sentence in the guide that names the limit, or no
   change, and say which was chosen and why.
3. Windows, macOS and Linux alike, each tested.
4. Make the user's life easier: a sensible default wherever one fits, an example of each common task ready to
   copy, and every message, error or report naming what to do next.

From the rest of `CLAUDE.md`, the instructions and the tests:

- Imports one way, relative only; the pure core imports no model, process or network module.
- One file per check, named after it; nothing else in a check folder; the catalog refuses anything else.
- Exactly one module builds a provider's model; another only reads the environment. Both arms first-class, Copilot
  first and the default; every change works, is tested and is measured live on each (`CLAUDE.md:107-108`,
  `213-215`).
- `agent.py` exports `app` and `root_agent`; `root_agent.name` equals the folder; no sub-package `agent.py`.
- State keys spelled once as constants; instructions read them through `placeholder`.
- Tools return a `{status: ...}` dict and never raise at the model (`CLAUDE.md:287`).
- A failure is an answer, never a crash; "did not look" never reads as "found nothing"; no error ends in Python's
  exit 1.
- Every string a model reads, and each string a model writes into a result, is capped with the cut named
  (`CLAUDE.md:316-319`).
- Every sentence the package prints is ASD-STE100: one command, at most 20 words, no `;`; an error a person can
  act on names what to do next; an error's text ends with no full stop (`CLAUDE.md:322-335`).
- Programs by full path, argv lists, timeouts; `encoding=` on every decoding `subprocess.run`; no `/tmp/`;
  `ignore_cleanup_errors=True`; `newline="\n"` (`CLAUDE.md:288-290`, `338-343`).
- Workflow actions pinned by full commit SHA, the same in every workflow and in the README's sample; uv by one
  exact version in every pipeline (`CLAUDE.md:343-347`).
- The suite is fully offline; a model call is made only when the task says so; never read `.env` or the token
  folder; never run the login (`CLAUDE.md:77-78`, `114-117`, `351`).
- Tests live only in `tests/`, each named as the sentence it proves.
- The docs are tested; they carry no dates and no static counts; a new flag, check, field or limit fails the suite
  until the guide says it.
- Comments and docstrings are plain prose that says why, often with the measurement that settled the decision.
  Commit subjects are plain-prose sentences stating what changed and what was learned (`CLAUDE.md:405-407`).
- Style: Ruff, line length 120, target `py314`, McCabe complexity at most 10 (`pyproject.toml:89-105`);
  `from __future__ import annotations` at the top of nearly every module (e.g. `judge/graph.py:23`,
  `judge/agents.py:12`, `judge/config.py:11`).

---

## 12. Comparison with the new project's plan

The plan says it is "modeled on" `adk_review` (`02:L503`), "verified against" it (`02:L101`, `L134`, `L486`) and
"`adk_review`-aligned" (`02:L430`). Each place it attributes something to `adk_review`, or copies its setup, is
listed below. "Same" means the two agree; "Differs" means they do not; "Not in adk_review" means the plan's item
has no counterpart there, so `adk_review` cannot be evidence for it.

### 12.1 Versions and pins

| Plan | adk_review | Result |
|---|---|---|
| "Google ADK 2.0 (`v2.15.0`)", `google-adk==2.15.0` (`02:L10`, `L84`, `L491`, `L513`) | `google-adk==2.14.1` (`pyproject.toml:14`, `uv.lock:530-531`) | Differs. adk_review cannot verify anything about 2.15.0. Its stated policy is that an ADK bump lands only after a live measurement on both arms (`pyproject.toml:11`) |
| `litellm==1.110.2` "pinned" (`02:L104`, `L491`, `L514`) | `litellm==1.106.2` (`pyproject.toml:18`), with a Dependabot hold on `>=1.106.3` (`dependabot.yml:19-24`) and "bump LiteLLM by hand no further either" (`CLAUDE.md:90-91`) | Differs, and it crosses the hold. adk_review's stated reason is a compromised 1.107.0 release and that "ADK caps it below 1.106.3" |
| `ruff==0.17.6`, `pyrefly==1.5.0` "matching `adk_review`" (`02:L498`, `L519-520`) | `ruff==0.17.5`, `pyrefly==1.4.1` (`pyproject.toml:27-28`) | Differs: the versions do not match. The settings named beside them do (`max-complexity = 10`, `S607`, `direct-abstract-base-instantiation = "ignore"`: `pyproject.toml:97`, `105`, `125`) |
| ruff and pyrefly in runtime `dependencies` (`02:L519-520`) | Same placement, for a stated reason: the reviewer's own rules run them on the code under review (`pyproject.toml:23-26`) | Same placement; the reason is specific to code review |
| `truststore>=0.10.5`, `python-dotenv>=1.2.4` (`02:L515-516`) | `truststore>=0.10`, `python-dotenv>=1.0`; the lock holds 0.10.5 and 1.2.4 (`pyproject.toml:19`, `22`; `uv.lock:1662-1663`, `1335-1336`) | Differs in the floors; the plan's floors equal adk_review's locked versions |
| `hatchling>=1.33.0` (`02:L490`, `L534`) | `hatchling>=1.27` (`pyproject.toml:41`) | Differs |
| `pytest>=9.2.0`, `pytest-asyncio>=1.5.0` (`02:L542-543`) | `pytest>=8.0`, `pytest-asyncio>=0.24`; lock 9.2.0 and 1.5.0 (`pyproject.toml:49-50`) | Differs in the floors |
| `textual>=8.2.8,<9.0` in `tui/` (`02:L473`, `L609`) | `textual>=8.0,<9.0`; lock 8.2.8 (`tui/pyproject.toml:10`) | Differs in the floor |
| `requires-python = ">=3.14,<3.15"`, `.python-version` 3.14 (`02:L434`, `L490`, `L511`) | Same (`pyproject.toml:9`, `.python-version:1`) | Same. adk_review ties the upper bound to the LiteLLM it holds (`pyproject.toml:5-8`) |
| `[tool.uv] exclude-newer = "P3D"`, `required-version = ">=0.12"` (`02:L553-555`) | Same (`pyproject.toml:81-87`) | Same |
| `google-genai>=2.34,<3` required by ADK, "2.34.0" (`02:L403`, `L492`) | Not named in `pyproject.toml`; locked at 2.34.0 under ADK 2.14.1 (`uv.lock:586-587`) | Consistent with the lock; the bound itself is not visible in adk_review |
| `pydantic 2.14.4`, `fastapi 0.165.0` (`02:L493`) | Lock: pydantic 2.14.3, fastapi 0.163.1 (`uv.lock:1195-1196`, `434-435`); neither is named in `pyproject.toml` | Differs from the lock; adk_review does not pin them |
| uv "0.13.9" as verified latest (`02:L490`) | Pipelines pin `0.13.6`, by the rule "none newer than the pinned `setup-uv` holds a checksum for" (`ci.yml:32-36`) | Differs if 0.13.9 is used in CI without moving the `setup-uv` pin |
| "upgraded to latest 2026-11-20 verified versions" (`02:L503`) | Every release waits three days (`pyproject.toml:82-85`) | A consequence to check, not a fact found: under the copied `exclude-newer = "P3D"`, an exact pin resolves only if that release was published at least three days before the lock is made |

### 12.2 Provider handling ("Verified Against `adk_review`", `02:L101-107`)

| Plan | adk_review | Result |
|---|---|---|
| `orchestration/settings.py` reads the environment with zero ADK or LiteLLM imports; `orchestration/models.py` is the sole provider-aware module (`02:L103`, `L458-459`) | `judge/settings.py` and `judge/config.py` (`judge/settings.py:1-14`, `judge/config.py:3`) | Same split. The file is `config.py`, not `models.py`, and both sit in `judge/` |
| `SPEC_PROVIDER`, `SPEC_MODEL`, `SPEC_<ROLE>_MODEL`, `SPEC_FALLBACK_MODEL` | `REVIEW_PROVIDER`, `REVIEW_MODEL`, `REVIEW_<ROLE>_MODEL`, `REVIEW_FALLBACK_MODEL` (`judge/settings.py:25-58`) | Same scheme, other prefix. adk_review also allows a per-arm model in the stage's own file (`core/guidelines.py:21-28`) |
| `truststore.inject_into_ssl()` before clients are built (`02:L103`, `L172-173`) | Same, in `judge/config.py:44-48` and again in `login.py:36-37` | Same |
| Copilot arm is `LiteLlm("github_copilot/<model>")` (`02:L104`), built in the skeleton as `LiteLlm(model=..., max_retries=2, _skip_mcp_handler=True)` (`02:L290`) | A subclass, `Bounded(LiteLlm)`, with one deadline over the call and its retries and a 408-status timeout; `max_retries=RETRY_ATTEMPTS - 1`, which is 2 (`judge/config.py:153-157`, `164-193`) | Differs: the plan has no overall deadline. adk_review measured nine minutes per call without it and a fallback never asked |
| `FallbackModel(models=models)` (`02:L282`, `L291`) | `FallbackModel(models=..., retriable_status_codes=FallbackModel.DEFAULT_STATUS_CODES | {408})` (`judge/config.py:138`, `157`, `161`) | Differs: without 408 a timeout is not a status the fallback moves on from (`tests/test_engine.py:159-161`) |
| Login: about 15 minutes, LiteLLM's own poll 60 s, `GITHUB_COPILOT_TOKEN_DIR`, `os.umask(0o077)`, `0o600`/`0o700`, `pin_copilot_dir()`, four GHE variables (`02:L105`) | Same (`login.py:1-13`, `42-53`, `109`, `118`, `141`, `149`, `174-187`; `judge/settings.py:94-110`; `.env.example:56-61`) | Same. The modes are applied unconditionally, not behind a POSIX check |
| Sets `LITELLM_LOCAL_MODEL_COST_MAP=True`, `suppress_debug_info`, `disable_copilot_system_to_assistant`, `_skip_mcp_handler=True`, `_HideBearer`, offline readiness check (`02:L106`) | Same (`judge/config.py:141-155`, `196-208`, `261-334`) | Same, with two omissions in the plan: `LITELLM_MODE=PRODUCTION`, which keeps LiteLLM from reading `.env` on import, and calling `pin_copilot_dir()` before importing LiteLLM (`judge/config.py:203-205`) |
| `import litellm` deferred, but `from google.adk.models import FallbackModel, LiteLlm` at module top (`02:L154`, `L284`) | `LiteLlm` is imported only inside `_bounded()`, from `google.adk.models.lite_llm` (`judge/config.py:177`); a test asserts the command loads no `litellm` (`tests/test_layering.py:250-259`) | Differs in where `LiteLlm` is imported. Whether the top-level form loads LiteLLM is not something adk_review shows |
| Gemini arm is "Native `Gemini`", built as `Gemini(model=n, retry_options=types.HttpRetryOptions(attempts=3))` (`02:L107`, `L281`) | A plain model-name string, which ADK resolves; a test asserts `isinstance(build_model(), str)` on Gemini (`judge/config.py:137-138`, `tests/test_wiring.py:55-71`). Retries are set on each request's `generate_content_config.http_options` (`judge/config.py:250-257`) | Differs |
| Vertex AI "detected via `is_enterprise_mode_enabled()`"; the skeleton calls it and discards the result (`02:L107`, `L280`) | Used for three things: naming Vertex AI in the report, retrying a 429 only there, and wording the readiness refusal (`judge/config.py:92`, `216`, `375`) | Same function, different use; in `build_model` adk_review does not call it |
| `BuiltInPlanner(thinking_config=...)` guarded to Gemini (`02:L113`, `L119`, `L307-312`, `L405`) | No `BuiltInPlanner` at all; `thinking_config` is set on the request, only on Gemini, and a test asserts `agent.planner is None` (`judge/config.py:239-249`, `tests/test_wiring.py:306-319`). Stated reason: the planner "only copied it onto the request's config", and LiteLLM never forwards it | Differs in mechanism and in the reason given |
| Default arm `copilot`, default model `gpt-4.1` "like `adk_review`" (`02:L737`, `L304`) | Same defaults (`judge/settings.py:16`, `32`) | Same. adk_review also records that GitHub has deprecated `gpt-4.1` in Copilot, and that Copilot's later GPT models and the o-series are refused because they cannot run at temperature 0 (`.env.example:11-13`, `23-24`; `CLAUDE.md:215-217`) |

### 12.3 The code skeleton ("verified against `google-adk` `v2.15.0` and `adk_review`", `02:L134`)

| Plan | adk_review | Result |
|---|---|---|
| `from google.adk import Context, Event, Workflow` (`02:L146`) | `Context` from `google.adk.agents.context`, `Event` from `google.adk.events`, `Workflow` from `google.adk.workflow` (`judge/graph.py:30-34`) | Differs in import paths; adk_review does not show whether the short form works |
| `from google.adk.apps import App, ResumabilityConfig` (`02:L150`) | `from google.adk.apps.app import App` (`judge/graph.py:31`) | Differs in path; `ResumabilityConfig` is not in adk_review |
| `from google.adk.plugins import BasePlugin, ...` (`02:L158-164`) | `from google.adk.plugins.base_plugin import BasePlugin` (`judge/plugins.py:29`) | Differs in path |
| `from google.adk.workflow import BaseNode, DEFAULT_ROUTE, JoinNode, RetryConfig, START, node` (`02:L169`) | `from google.adk.workflow import FunctionNode, JoinNode, Workflow`; the string `"START"`; `FunctionNode(func=, name=)` (`judge/graph.py:34`, `154-157`) | Differs: adk_review uses neither the `START` symbol nor the `@node` decorator |
| `_BEARER`, `_HideBearer`, `truststore`, `is_enterprise_mode_enabled`, `BaseLlm`, `Gemini`, `types` (`02:L143`, `L155-156`, `L168-190`) | Same code and imports (`judge/config.py:23-30`, `54-68`) | Same |
| `LlmAgent(mode="single_turn", static_instruction=..., instruction=..., planner=..., input_schema=..., output_schema=..., tools=[...])` (`02:L313-326`) | `LlmAgent(model, name, description, instruction, before_agent_callback, include_contents="none", generate_content_config, output_schema, output_key)`; no tools on a schema agent (`judge/agents.py:223-260`) | Not in adk_review: `mode`, `static_instruction`, `planner`, `input_schema`. adk_review records that tools beside an `output_schema` give some models a tool instead of a response schema (`judge/plugins.py:246-248`) |
| No temperature in the skeleton | Temperature 0 on every judging call, tested (`judge/config.py:246-248`, `tests/test_wiring.py:74-86`) | Differs |
| `StrictDTO` with `ConfigDict(frozen=True, extra="forbid")`, used as `output_schema=AnalysisReport` (`02:L194-211`, `L324`) | Plain `BaseModel` schemas. Measured: `extra="forbid"` sent Gemini `additionalProperties`, "which its `response_schema` has refused with a 400" (`tests/test_wiring.py:127-130`) | Differs, and adk_review's measurement speaks against using a `forbid` model as a response schema on the Gemini arm |
| "omitting `from __future__ import annotations`" (`02:L90`) | Present at the top of nearly every module (`judge/graph.py:23`) | Differs |
| `WritePolicyPlugin.before_tool_callback(self, *, tool, tool_args, tool_context)` returning `{"error": ...}` (`02:L251-269`) | Plugin hooks are keyword-only with the same parameter names (`judge/plugins.py:167-169`). adk_review has no before-tool plugin; its tool guard is an agent-level callback. Refusals are `{"status": "error", "error_message": ...}` (`judge/tools.py:110`) | Hook signature style same; the plugin itself and the `{"error": ...}` shape are not adk_review's |
| `EnvironmentToolset`, `LocalEnvironment`, `tool_filter`, `RequestInput`, `ctx.resume_inputs`, `@node(rerun_on_resume=True, retry_config=...)`, `RunConfig`, `TelemetryConfig`, `ToolThreadPoolConfig`, `ContextCacheConfig`, `ModelConsultTool`, `ForceEscalationPlugin`, `ReflectAndRetry*`, `ToolCallIntegrityPlugin`, shadow-mode cloning (`02:L148-169`, `L294-396`) | None of these appears in the package (section 3.1) | Not in adk_review. It rejects a node `retry_config` for its own agents (`README.md:1074-1076`) and passes no `RunConfig` |

### 12.4 Cross-platform (`02:L126-129`, `L407`)

| Plan | adk_review | Result |
|---|---|---|
| `.gitattributes` with `* text=auto eol=lf` | Same (`.gitattributes:3`) | Same |
| Settled git environment: `core.autocrlf=input`, `core.fsmonitor=false`, `core.precomposeUnicode=false`, `core.attributesFile=os.devnull` | Same four, plus `diff.suppressBlankEmpty=false`, set through `GIT_CONFIG_COUNT` and never `-c` (`collect/git.py:93-99`, `137-140`) | Same, partial: adk_review also drops every inherited `GIT_*`, sets `LC_ALL=C`, `GIT_CONFIG_GLOBAL` to the null device, `GIT_CONFIG_NOSYSTEM`, `GIT_ATTR_NOSYSTEM`, `GIT_NO_LAZY_FETCH`, `GIT_NO_REPLACE_OBJECTS`, and `safe.directory` (`collect/git.py:129-140`) |
| "Shell-free argv `subprocess.run(..., encoding="utf-8")`", full paths from absolute `PATH` entries | Full-path lookup same (`collect/git.py:144-158`). git itself runs through `subprocess.Popen` in bytes and is decoded in code; the `encoding=` rule is for `subprocess.run` calls that decode (`collect/git.py:193-209`, `243-247`; `tests/test_portability.py:32-45`) | Same rule, with that nuance |
| `taskkill /F /T /PID` on Windows timeouts, "where `LocalEnvironment`'s `os.killpg` is ignored" | `taskkill` used (`collect/git.py:203-205`). Stated reason: Git for Windows' `git.exe` runs the real git as its child | `taskkill` same; the `LocalEnvironment` reason is not adk_review's |
| `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` at CLI start | Same (`review.py:764-765`) | Same |
| `TemporaryDirectory(ignore_cleanup_errors=True)` | Same (`collect/ruff.py:267`) | Same |
| `%APPDATA%\adk-spec` versus `$XDG_CONFIG_HOME/adk-spec` in the CLI (`02:L129`, `L467`) | Only the `tui/` member has per-user folders (`tui/tui/config.py:34-46`). The reviewer's config is in the package, and its Copilot token is under `~/.config/litellm/github_copilot` on every system | Differs in where it applies |
| `os.path.isjunction()`, reserved DOS names, drive and UNC checks (`02:L176-179`, `L229-249`, `L407`) | No `isjunction` and no reserved-name check anywhere. The nearest things: `--path` refuses a root or drive, and tool copies avoid names Windows cannot hold (`review.py:544-549`, `collect/ruff.py:286-290`) | Not in adk_review |
| 3-OS CI matrix (`02:L439`, `L677`) | Same (`ci.yml:20-23`) | Same. Not carried into the plan: actions pinned by SHA, one exact uv version, `permissions: contents: read`, `persist-credentials: false`, `timeout-minutes`, `fail-fast: false`, concurrency cancel (`ci.yml:9-36`) |

### 12.5 Layout ("`adk_review`-Aligned `uv` Workspace", `02:L430-482`)

| Plan | adk_review | Result |
|---|---|---|
| Flat root package with `__init__.py` and `agent.py` exporting `app` and `root_agent` (`02:L443-445`) | Same (`agent.py:23-30`) | Same. Not carried over: `__init__.py` must import nothing and answer `agent` lazily; `root_agent.name` must equal the folder; no sub-package `agent.py` (section 3.6) |
| `domain/` with zero `google.adk` and `litellm` imports, "enforced by import-linter" (`02:L90`, `L446`) | `core/`, enforced by the project's own `tests/test_layering.py` plus fresh-interpreter probes; a wider forbidden list that includes `subprocess`, `asyncio`, `os`, `socket`, `urllib`, `http`, `ssl` (`tests/test_layering.py:28`, `198-220`) | Differs in the tool and in how strict "pure" is. adk_review's core does no file or process I/O; `collect/` does |
| `ports/`, `adapters/llm/`, `adapters/python/`, `orchestration/`, `interfaces/` (`02:L453-471`) | `core`, `collect`, `judge`, `deliver`, and root modules (section 2.1) | Differs: the hexagonal names are the plan's own. `collect/` calls itself "driven adapters" (`collect/__init__.py:1`) |
| `orchestration/app.py` exports `app = App(...)` (`02:L465`) | The builder is `judge/graph.py:build_app`; nothing is built at import except in `agent.py` (`judge/graph.py:16-17`) | Differs: adk_review avoids building the app at import of any module the command loads (`agent.py:3-10`) |
| `orchestration/plugins/`, `orchestration/tools/` as folders (`02:L461-462`) | One module each, `judge/plugins.py` and `judge/tools.py` | Differs in shape only |
| CLI entries `adk_spec.interfaces.cli:run`, `adk_spec.interfaces.login:run`; CLI on `typer` (`02:L496`, `L517`, `L529-531`) | Entries at the package root, `adk_review.review:run`, `adk_review.login:run`; `argparse` (`pyproject.toml:34-38`, `review.py:59`) | Differs |
| `tui/` as a separate workspace member depending on the root with `workspace = true`, script `tui:run` (`02:L472-474`, `L601-625`) | Same (`tui/pyproject.toml:1-27`) | Same |
| `tests/unit/` and `tests/eval/` with `AgentEvaluator` golden suites (`02:L477-479`) | Tests flat in `tests/`; no eval sets; live measurement by scripts (sections 7.3, 7.4) | Differs |
| `.github/copilot-instructions.md` and `workflows/ci.yml` (`02:L437-439`) | Those two, plus `dependabot.yml`, `instructions/`, `skills/`, `agents/`, `copilot-setup-steps.yml`, the pull request template | Partial: the plan lists two of them |
| `.env.example` with provider, `LITELLM_LOCAL_MODEL_COST_MAP=True`, GHE and Vertex variables (`02:L436`) | Same content (`.env.example:7-10`, `29-35`, `56-61`) | Same |

### 12.6 `pyproject.toml` and `Makefile` blueprint ("Modeled directly on", `02:L503-670`)

| Plan | adk_review | Result |
|---|---|---|
| `[project.optional-dependencies]` `web`, `mcp`, `a2a`, `db` using ADK extras (`02:L523-527`) | None. "No extra" (`pyproject.toml:12-13`) | Not in adk_review |
| Dev group adds `hypothesis`, `mutmut`, `cosmic-ray`, `import-linter` (`02:L544-547`) | `pytest`, `pytest-asyncio` only (`pyproject.toml:47-51`) | Not in adk_review |
| `[tool.pytest.ini_options]`, including the three LiteLLM `filterwarnings` lines (`02:L557-570`) | Identical (`pyproject.toml:53-73`) | Same. Two of those lines are written for "LiteLLM 1.106.2's Copilot authenticator" (`pyproject.toml:70-72`), not for the plan's 1.110.2 |
| `[tool.ruff]` and lint `select`, `ignore`, `mccabe` (`02:L572-582`) | Identical (`pyproject.toml:89-105`) | Same |
| `per-file-ignores`: `"scripts/*" = ["S607"]` (`02:L585`) | Only `scripts/make_demo_repo.py` and `scripts/measure.py`, plus `tests/*` (`pyproject.toml:107-112`) | Differs: broader in the plan |
| `[tool.pyrefly]`, `[tool.pyrefly.errors]`, `[tool.pyright]` (`02:L588-597`) | Identical (`pyproject.toml:114-128`) | Same |
| Makefile `LOCKED`, `sync`, `install`, `web`, `lint`, `typecheck`, `format`, `test` (`02:L631-659`) | Same commands (`Makefile:13`, `26-38`, `56-66`) | Same |
| `login:` target (`02:L643-644`) | `copilot-login:` with `$(ARGS)` (`Makefile:53-54`) | Differs in name |
| `arch-check: uv run lint-imports`, and `ci: lint typecheck arch-check test` (`02:L652-661`) | No such target; `ci: lint typecheck test` (`Makefile:68`). Layering is part of `pytest` | Not in adk_review |
| The pitfall rows on pyrefly, `adk web --no_use_local_storage`, and `uv tool install` with exported constraints and `uv run --no-project` (`02:L408-410`) | Each is in adk_review as described (`pyproject.toml:123-125`, `Makefile:6-13`, `29-38`) | Same |

### 12.7 Parts of adk_review's setup the plan does not carry over

These are in `adk_review` and bear on "use a similar ADK setup", but the plan does not mention them:

- The Dependabot configuration, its cooldown test and its hold (section 1.4).
- The explanatory comment beside each pin (the "why" of section 1.2).
- The per-call deadline wrapper and the 408 fallback code (section 5).
- Temperature zero for judging calls, and the readiness check that refuses models that cannot do it.
- The plugin roster that makes failures answers: `ReportProviderErrors`, `StopAtRateLimit`, `UsageLedger`,
  `RedactSecretsPlugin`, `RefuseUnready`, `OneTurn` (section 6.1). The plan names other plugins.
- Nonce fences and the reminder for untrusted text (section 6.4).
- The fake-model test harness (`LLMRegistry.register`, instruction-keyed fake provider, `LiteLLMClient`
  replacement for the Copilot arm) and record and replay (section 7).
- The tested docs and the tested Copilot files (sections 7.5, 10).
- The exit-code scheme and the `main` wrapper that never lets an error read as a result (section 9.1).
- The "hard rules" (section 11).

---

## 13. What transfers and what does not

### (a) Transfers directly to a spec-driven framework

Toolchain and repository:

- `pyproject.toml` structure: Python bound, `[tool.uv]` cooldown and floor, uv workspace with a UI member, pytest
  options, Ruff and Pyrefly settings (`pyproject.toml`).
- `Makefile` recipes: locked `sync`, `install` through exported constraints, `web` with
  `--no_use_local_storage`, `uv run --no-project` helpers.
- `.gitattributes`, `.python-version`, `.env.example` layout, `.gitignore` entries for `.env` and `.adk/`.
- `ci.yml` as written (three systems, SHA-pinned actions, one exact uv, read-only permissions, timeout), and
  `dependabot.yml` (cooldown, grouping, separate pull requests for ADK and LiteLLM, the hold).

ADK application skeleton:

- Package root pattern: lazy `__init__.py`; `agent.py` exporting `app` and `root_agent`; name equals folder; no
  nested `agent.py`; builders that build nothing at import (`__init__.py`, `agent.py`, `judge/graph.py`).
- `build_app` owning the graph and the plugin roster for both the command and chat shapes.
- `Workflow` wiring idioms: `FunctionNode` for deterministic steps, tuple fan-out into `JoinNode`,
  `max_concurrency`, a gate node returning `Event(route=...)` with a route table.
- `run_seeded` and the `Run` record: seed state at session creation, drain events, collect error events by
  author, bound the run with a deadline, read state back whatever happened (`judge/run.py:42-75`).
- State discipline: key constants in one module, `placeholder()`, `state_key()`, `read_back()`, `temp:` keys for
  per-turn values, a test tying placeholders to writers.
- The node-never-raises rule and the skip guard `before_agent_callback` that answers the schema.

Providers:

- `judge/settings.py` and `judge/config.py` nearly verbatim with a new variable prefix: arm selection, per-role
  models, fallback, the bounded LiteLLM wrapper, `request_config`, `require_ready`, error wording (`said`).
- `login.py` nearly verbatim.

Plugins and safety:

- `ReportProviderErrors`, `StopAtRateLimit`, `UsageLedger`, `RedactSecretsPlugin` with `core/secrets.py`,
  `Progress`, `Recorder`, `RefuseUnready`, `OneTurn`, and their order.
- `fenced()`, the two nonces and the reminder; `include_contents="none"`; flattening untrusted text placed in
  prompts; `core/text.py` (`cut_at`, `squash`, `lines_of`).
- Tool conventions: status envelopes, async tools off the loop, capped output, an agent-level
  `before_tool_callback` guard with a test that every tool-bearing agent carries it.
- `collect/git.py`'s process layer for any step that runs git or another program: `on_path`, `_environment`,
  `started` and `stop_programs`, the Windows process-tree stop.
- `deliver/report.py`'s text-safety helpers (`one_line`, `inert`, `safe_line`, `windows_word`) for anything that
  prints model or repository text.

The code-versus-model pattern:

- One file per unit of work, of two kinds (decided by code, judged by a model), sharing one id scheme, one state
  key scheme, one answer contract and one selection mechanism (profiles in a strictly loaded `config.toml`). This
  is the part most relevant to moving steps from LLM to Python: a step can change kind without its consumers
  changing.
- The order: evidence in Python, deterministic checks, model judgement, then Python verifies the model's claims
  against the evidence and decides.
- Schema design rules: required lists, `Literal` scales, described fields, plain `BaseModel`, length cuts by
  validator.
- "Did not look" as a first-class answer (`could_not_look`, unwritten `output_key`, holes that block approval).
- Code computing context for the model (as the blast radius does) and code taking precedence on a tie.
- A profile that needs no model importing no engine.

Testing and docs:

- The whole `tests/conftest.py` harness for models: `FakeModel` through `LLMRegistry`, `FakeProvider`,
  `load_agent`, `load_command`, `Chat`, `asked`, environment isolation fixtures, the two levels of Copilot-arm
  replacement, record and replay.
- `tests/test_layering.py`, `tests/test_docs.py`, `tests/test_copilot.py`, `tests/test_portability.py` as
  patterns; `tests/test_wiring.py`'s loader, arm, schema and guard tests.
- The command structure: `settle()`, `main()` wrapper, exit codes, `SIGTERM` handling, UTF-8 stdout.
- The `.github` Copilot files and `.vscode` settings as a structure, and the hard rules.

### (b) Specific to code review; does not transfer

- Diff handling: `collect/diff.py`, `collect/change.py`, the hunk, `quotable` and `framing` model in
  `core/evidence.py`, function-context widening, diff caps and the planning of runs in parts.
- Grounding as implemented (`drop_ungrounded`, `already_done`, `asks_to_remove`, placing a quote on diff lines)
  and folding by line span (`dedupe`). The principle transfers; this code is about diffs.
- `core/blast.py` (Python import graph), `core/health.py` (complexity bands), `callers_of`.
- Every file in `judge/rules/` and `judge/guidelines/`, the `Rule`, `FileRule` and `TreeRule` kinds, the
  `rule_helpers` door, and the ruff and pyrefly adapters (`collect/ruff.py`, `collect/pyrefly.py`,
  `collect/tools.py`). With them goes the reason ruff and pyrefly are runtime dependencies.
- `judge/verify.py`'s packing of findings by file, and the `Finding`, `Review`, `Judgement` schemas.
- `deliver/report.py`'s outputs: the review report, JSON schema 2, hand-off, comment, fingerprints, `--previous`,
  `--cache` keying.
- `push.py`, `commit.py`, `collect/history.py`, `.pre-commit-hooks.yaml`.
- Chat's intake tools (`inspect_repository`, `changed_files`) and the one-repository guard.
- `config.toml`'s `[review]` keys (`fail_on`, `diff_cap`, `skip`, `scan`, `third_party`) and the profiles' contents.
- The demo repository, the labelled set and the injection suite as content (the method transfers).
- The `tui/` Azure DevOps side; `docker-compose.yml` and `sonar-project.properties`.
- The read-only stance. adk_review never writes into the repository it works on, runs none of its code and takes
  no setting from it. A spec framework must write artifacts and drive implementation, so adk_review offers nothing
  to copy for: write tools or a write-policy plugin, shell execution tools, human-in-the-loop pauses and
  resumption, persistent or resumable sessions, artifact or memory services, multi-turn stage loops, static
  instructions and context caching, or evaluation sets. Each of those in the plan needs its own evidence.
- Temperature zero as a blanket rule: adk_review applies it to judging agents. Whether drafting agents should run
  at zero is not something it answers; note that its readiness check refuses Copilot models that cannot.
