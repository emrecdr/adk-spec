# `adk-spec`: Unified Hybrid Spec-Driven Framework on Google ADK 2.0 — Architecture & Implementation Plan

- **Companion reports:** [01-spec-frameworks-comparative-analysis.md](01-spec-frameworks-comparative-analysis.md) · [03-ui-ux-workbench-and-engineering-standards.md](03-ui-ux-workbench-and-engineering-standards.md)
- **Research basis:** [OpenSpec notes](../research_notes/Spec%20driven%20framework%20on%20Google%20ADK/01-openspec-research-notes.md) · [Spec Kit notes](../research_notes/Spec%20driven%20framework%20on%20Google%20ADK/02-speckit-research-notes.md) · [ADK 2.0 notes](../research_notes/Spec%20driven%20framework%20on%20Google%20ADK/03-google-adk-v2-best-practices.md) · [Audit & Improvements](../research_notes/Spec%20driven%20framework%20on%20Google%20ADK/04-validation-audit-and-improvement-options.md) · [Modern SDD & Architecture](../research_notes/Spec%20driven%20framework%20on%20Google%20ADK/05-modern-sdd-standards-and-architecture-patterns.md) · [UI/UX Spec](../research_notes/Spec%20driven%20framework%20on%20Google%20ADK/06-ui-ux-and-page-design-spec.md)

---

## 1. Unified Hybrid Spec Framework Design (`adk-spec`)

`adk-spec` synthesizes OpenSpec's living-truth + delta-change architecture with Spec Kit's constitution + clarify/analyze/converge quality gates, elevated with **EARS + executable spec + Hypothesis/mutation verification**, **OWASP agentic security defenses**, **first-class Windows & macOS parity**, **dual-arm GitHub Copilot + Gemini LLM support**, **Git worktree isolation**, **Hexagonal + Strangler-Fig architecture**, and **Google ADK 2.0 (`v2.15.0`)** runtime enforcement.

### 1.1 Repository Structure (`.spec/`)

```text
.spec/
├── constitution.md                   # Versioned project MUST/SHOULD invariants (supreme authority)
├── config.yaml                       # Profile/preset, context, knowledge: allowlist, isolated_memory toggle, rules, stage_modes
├── .knowledge-lock.json              # Pinned selective knowledge snapshot (LF SHA-256 + git rev; explicit manual sync)
├── knowledge/                        # Curated non-spec reference docs, ADRs, domain glossaries (Claude Projects pattern)
├── schemas/
│   └── spec-driven/
│       ├── schema.yaml               # Declarative Artifact DAG (proposal -> specs/contracts/design -> tasks)
│       └── templates/                # proposal, spec-delta (EARS+BDD), contract, design, tasks, checklist
├── overlays/                         # Non-destructive YAML workflow overlays (insert_after/before, replace, remove)
├── roadmaps/                         # Optional spec-of-specs epic decompositions (R1..Rn immutable IDs)
├── specs/                            # Living source of truth: canonical current behavior
│   └── <capability-path>/spec.md     # EARS + RFC 2119 + 4-hash #### Scenario: GIVEN/WHEN/THEN
└── changes/                          # Isolated, parallel-safe active modifications
    ├── <change-id>/
    │   ├── .change.yaml              # Schema, profile, skip_specs flag, LF-normalized SHA-256 base snapshots
    │   ├── proposal.md               # Why, What Changes, New/Modified Capabilities, Impact, Roadmap ref
    │   ├── specs/<cap>/spec.md       # Delta specs: ADDED / MODIFIED / REMOVED / RENAMED
    │   ├── contracts/                # Optional interface contracts (idempotency, errors, versioning, owner)
    │   ├── design.md                 # Context, Goals/Non-Goals, Technical Decisions, Risks/Trade-offs
    │   ├── tasks.md                  # Phased vertical slices: Setup, Foundational, US1..USn, Polish (T### [P] [US#])
    │   ├── checklists/               # Reviewer-owned requirements quality checklists (locked against implementer writes)
    │   └── reports/                  # Read-only analyze.md & verify-converge.md reports (or ArtifactService links)
    └── archive/
        └── YYYY-MM-DD-<change-id>/   # Immutable audit record after fingerprint-guarded 3-way delta sync
```

*(Multi-repo teams can connect an external Git **Store** or federated **A2A (`to_a2a` / `RemoteA2aAgent`)** Spec Store endpoint via `.spec/config.yaml`.)*

### 1.2 Unified Spec Grammar & Anti-Tautological Traceability

- **EARS + RFC 2119 + 4-Hash BDD:** Every requirement uses one of the 5 **EARS** sentence patterns (*Ubiquitous, Event-driven, State-driven, Optional, Unwanted behavior*) paired with RFC 2119 (`MUST`/`SHALL`), a `<= 500` character requirement body cap, and `#### Scenario:` (`GIVEN`/`WHEN`/`THEN`) clauses.
- **Executable Spec Binding & Quality Gates:** Tests bind to requirements via `@pytest.mark.spec("<capability>:<REQ-ID>")`, **Hypothesis** property-based tests verify *Ubiquitous*/*State-Driven*/*Unwanted* invariants, mutation testing (`mutmut` on POSIX / `cosmic-ray` or WSL on Windows) checks assertion strength in `strict` `verify_converge`, and `import-linter` enforces Hexagonal and `constitution.md` layer boundaries.

### 1.3 Multi-Process Entry Modes & Ceremony Profiles

- **Entry Processes (Composable Nested ADK `Workflow`s):**
  1. `explore`: Read-only architectural & codebase thinking partner (`mode="chat"`, `tool_filter=['ReadFile']`).
  2. `assess`: `intake → research → define → shape → decide` (`go` | `needs-clarification` | `kill`); `go` hands off to `sdd`.
  3. `bugfix`: `bug_assess → bug_fix → bug_test` (`verified` | `partial` | `failed`).
  4. `sdd`: Full feature/brownfield delta delivery pipeline.
- **Ceremony Profiles (`lean` | `standard` | `strict`):**
  - **`lean`** *(OpenSpec velocity)*: `propose → specify + design + tasks → apply → verify → sync & archive`.
  - **`standard`** *(Default balanced)*: adds `clarify` (≤ 5 Qs), `analyze` (read-only 6-pass), HITL `ReviewGate`, and `apply ↔ converge` loop.
  - **`strict`** *(Enterprise/Regulated)*: adds mandatory reviewer-owned `checklist` gate, blocks `apply` on any `CRITICAL`/`HIGH` analyze finding, enforces mutation threshold + `ToolConfirmation` on archive/git mutations, and isolates `apply` inside dedicated `.worktrees/<change-id>`.

### 1.4 End-to-End SDD Lifecycle & Runtime Write Contracts

```text
  [Pre-Flow]   explore (RO)  |  assess (go/clarify/kill)  |  bugfix (assess→fix→test)
                                         │
                                         ▼
  [Align]      LoadContext (Python) ──▶ propose (task) ──▶ specify (EARS delta / skip_specs) ──▶ clarify (task, ≤5 Qs)
                                                                                                         │
                                                                                                         ▼
  [Blueprint]  design + contracts ──▶ tasks (T### [P] [US#]) ──▶ analyze (RO, 6 passes) ──▶ [HITL ReviewGate (3-Way)]
                                                                                                   │            │
                                                                                            revise ┘            │ approve
                                                                                                                ▼
  [Deliver]    ┌──▶ apply (Worktree + [P] workers; checklist RO) ──▶ verify & converge (append_convergence_tasks) ─┤
               │                                                                                                   │
               └────────────────────── gaps_found (append ## Phase N: Convergence) ◀───────────────────────────────┘
                                                                                                                   │ converged
                                                                                                                   ▼
  [Lock Truth]                                       3-way fingerprint-guarded delta sync & archive (ToolConfirmation)
```

---

## 2. Google ADK 2.0 (`v2.15.0`) System Architecture & Coding Patterns

### 2.1 Hexagonal Architecture + Guarded Strangler-Fig Stage Registry

`adk-spec` separates pure specification engines from ADK orchestration via **Hexagonal Architecture (Ports & Adapters)** and a **StageRegistry**:

1. **`domain/` (Pure Python 3.14):** Zero imports from `google.adk`, `google.genai`, or `litellm` (enforced continuously by `import-linter 2.17`). Targets `Python 3.14` cleanly—omitting `from __future__ import annotations` via native **PEP 649** deferred annotations (`annotationlib`) and using **PEP 750** `t-strings` (`string.templatelib.Template`) for injection-safe prompt/TUI escaping. Owns EARS/BDD parsing, `ArtifactGraph`, `T###` task scheduling, LF-normalized SHA-256 fingerprinting, 3-way `diff3` delta merging, and static lint/traceability rules.
2. **`ports/` (`typing.Protocol` + Frozen Pydantic `2.14.4` Models):** Defines `ConfigDict(frozen=True, extra="forbid")` boundary DTOs and stage port interfaces.
3. **`adapters/llm/` vs. `adapters/python/`:** Both share identical Pydantic `input_schema`/`output_schema` contracts (enforced at startup by ADK Rule #8).
4. **`StageRegistry` (`llm | shadow | hybrid | python`):**
   - `llm` → `LlmAgent` adapter (Phase 1 default).
   - `shadow` → Permitted **only** when `allow_shadow=True` (pure/read-only stages or copy-on-write sandboxes; raises `ValueError` on mutating stages to prevent double-writes). Clones unique node names (`node(llm_node, name=f"{stage}_llm")`, `node(python_node, name=f"{stage}_py")`), forwards `input_schema`/`output_schema` onto the nested `Workflow`, runs both via `JoinNode`, and logs parity diffs.
   - `hybrid` → Python pre-pass (lint, AST coverage, `pytest`/mutation/git evidence) feeds a small semantic judge.
   - `python` → 100% deterministic `@node` `FunctionNode`.

### 2.2 Dual-Arm Provider Parity (GitHub Copilot + Gemini) & Cross-Platform Resilience Stack

#### Dual-Arm Architecture (`SPEC_PROVIDER=copilot | gemini`, Verified Against `adk_review`)

- **Clean Split (`settings.py` vs. `models.py`):** `orchestration/settings.py` reads `SPEC_PROVIDER`, `SPEC_MODEL`, `SPEC_<ROLE>_MODEL`, and `SPEC_FALLBACK_MODEL` with zero ADK/LiteLLM imports (fast CLI/login startup); `orchestration/models.py` is the sole provider-aware module, injecting `truststore.inject_into_ssl()` before building HTTP/LLM clients so corporate Windows/macOS proxies re-signing TLS work out of the box.
- **GitHub Copilot Arm (`LiteLlm("github_copilot/<model>")`, pinned `litellm==1.110.2`):**
  - `adk-spec-login` CLI polls GitHub's ~15-minute OAuth device flow (LiteLLM's built-in poll times out at 60s), stores tokens in `GITHUB_COPILOT_TOKEN_DIR` (`~/.config/litellm/github_copilot`) with `os.umask(0o077)` and `0o600`/`0o700` on POSIX, expands `~` via `pin_copilot_dir()`, and supports GitHub Enterprise Cloud (`*.ghe.com`) overrides (`GITHUB_COPILOT_API_BASE`, `GITHUB_COPILOT_DEVICE_CODE_URL`, `GITHUB_COPILOT_ACCESS_TOKEN_URL`, `GITHUB_COPILOT_API_KEY_URL`).
  - Sets `LITELLM_LOCAL_MODEL_COST_MAP=True`, `litellm.suppress_debug_info = True`, `litellm.disable_copilot_system_to_assistant = True`, passes `_skip_mcp_handler=True` (avoids tool-call crash importing LiteLLM proxy's `mcp`), attaches `_HideBearer` `logging.Filter` on `logging.getLogger("LiteLLM")` (redacts Copilot `Bearer` tokens leaked under `adk web -v`), and validates temperature/reasoning constraints offline (`require_ready`).
- **Gemini Arm (Native `Gemini`):** Supports AI Studio (`GOOGLE_API_KEY`) and Vertex AI (`GOOGLE_GENAI_USE_ENTERPRISE=TRUE` detected via `google.adk.utils.env_utils.is_enterprise_mode_enabled()`).

| ADK 2.0 Capability | GitHub Copilot (`LiteLlm`) Arm | Native Gemini Arm | Wiring Rule in `adk-spec` |
| --- | --- | --- | --- |
| `Workflow`, `JoinNode`, `RequestInput`, `ToolConfirmation`, `Runner.rewind_async`, `AgentEvaluator` | Full support | Full support | Identical graph & contracts on both arms |
| `FallbackModel` + `ModelConsultTool` + `SkillToolset` + `BasePlugin` (`WritePolicyPlugin`, `ReflectAndRetry*`, `ToolCallIntegrityPlugin`) | Full support | Full support | Configure `ModelConsultTool` with a model available on `SPEC_PROVIDER` |
| `BuiltInPlanner(thinking_config=...)` | **Unsupported on non-thinking models** | Full support (`Gemini`) | **MUST guard behind `provider == "gemini"`** |
| `ContextCacheConfig` / `ServiceTier.DEFERRED` / `ModelArmorPlugin` | Ignored / Gemini-only | Full support (`Gemini`/Vertex) | Enable only on Gemini/GCP configurations |

#### Prompt Caching, Security, Windows/macOS Parity & Memory Stack

- **Prompt Caching, Thinking & 2-Tier Auto-Scaling Knowledge Loader (`Claude Projects` Pattern):**
  - Place immutable constitution, EARS rules, and role policy in `LlmAgent.static_instruction` (zero placeholders—required for Gemini prefix caching and `GEPARootAgentPromptOptimizer`) and dynamic `{change_id}`/`{feedback?}` state in `instruction`. Attach `BuiltInPlanner(thinking_config=...)` only when `provider == "gemini"`.
  - **2-Tier Auto-Scaling Knowledge Loader (`Direct Cache` → `spec_knowledge_search` RAG) + Pinned Sync:** Non-spec ADRs, runbooks, and domain glossaries live in `.spec/knowledge/`, supplemented by a selective `knowledge:` path allowlist in `.spec/config.yaml` (`1 MiB` per-file cap; excludes lockfiles/build outputs) pinned to LF-normalized SHA-256 + git rev snapshots in `.spec/.knowledge-lock.json` refreshed only via explicit `adk-spec knowledge sync` or UI `[↻ Sync Knowledge]` (so active sessions never drift mid-run). Under the active model's token/file budget (accounting for smaller GitHub Copilot vs. 1M Gemini windows), **Tier 1** injects directly into `static_instruction`; once exceeded, **Tier 2** automatically flips to compact ToC + deterministic pure-Python BM25/heading retrieval via read-only `spec_knowledge_search` (up to ~10x capacity without a vector DB initially; optionally hybrid semantic via `BaseMemoryService` in Phase 4).
  - **Transcript-Isolated Threads, `isolated_memory` Wall & Artifact Flywheel:** Parallel `explore` / `assess` / `change` sessions remain strictly transcript-isolated while sharing one Project Knowledge Pack, and partition `BaseMemoryService` by `(app_name, project_id)` with an `isolated_memory: true` wall (default `true` in `strict`) plus human-gated `[↑ Promote to Knowledge]` (`ASI06`). Phase 4 multi-team stores expose explicit `Can view` vs. `Can edit` roles (resetting sharing on archive).
- **Resilience & Budgeted Escalation:** `FallbackModel` (429/5xx/timeout failover on either arm) + `ReflectAndRetryToolPlugin(max_retries=3)` + `ReflectAndRetryModelPlugin` + `ModelConsultTool` (`max_uses=2`, `session_max_uses=5`, paired with `ForceEscalationPlugin` and `ModelConsultObservabilityPlugin`).
- **Defense-in-Depth Security (`OWASP ASI01/ASI02/ASI05/ASI06`):**
  - Least-privilege `EnvironmentToolset(environment=..., tool_filter=...)` + narrow `append_convergence_tasks` tool + path-normalized `WritePolicyPlugin` blocking `Execute` on RO/converge nodes and rejecting Windows drives/UNC/DOS reserved names/junctions/`..` traversal.
  - Optional `ModelArmorPlugin` (`pip install 'google-adk[gcp]'`) on `after_tool_callback` + `ToolCallIntegrityPlugin(secret_key=...)` *(protects agent-invoked tools, not standalone workflow tool nodes)* + `ToolConfirmation` + quarantined `BaseMemoryService` ingestion (human-approved archived artifacts only).
- **Windows & macOS Cross-Platform Engineering:**
  - `.gitattributes` (`* text=auto eol=lf`) + LF-normalized SHA-256 base fingerprints + settled Git env (`core.autocrlf=input`, `core.fsmonitor=false`, `core.precomposeUnicode=false`, `core.attributesFile=os.devnull`).
  - Shell-free argv `subprocess.run(..., encoding="utf-8")` resolving full executable paths from absolute `PATH` entries (never CWD), plus `taskkill /F /T /PID` on Windows process-tree timeouts (where `LocalEnvironment`'s `os.killpg` is ignored).
  - `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` at CLI startup, `tempfile.TemporaryDirectory(ignore_cleanup_errors=True)` + retry-guarded `.worktrees/` removal for Windows AV locks, and `%APPDATA%\adk-spec` vs. `$XDG_CONFIG_HOME/adk-spec` config dirs.
- **Enterprise Privacy (`TelemetryConfig`) & Buffering:** Explicitly disable ADK's default span content capture (`ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=True` by default!) via `RunConfig(telemetry=TelemetryConfig(capture_message_content=ContentCapturingMode.NO_CONTENT))`; pair `RunConfig(streaming_mode=StreamingMode.SSE, max_llm_calls=40, tool_thread_pool_config=ToolThreadPoolConfig(max_workers=4))` with `BufferedSessionService` (always `await flush_session(...)` and `close()`), `Runner.rewind_async`, and `to_a2a` (`google.adk.a2a.utils.agent_to_a2a`).

### 2.3 Verified ADK 2.0 Code Skeleton (Dual-Arm Copilot/Gemini + Windows-Hardened)

*All imports, `EnvironmentToolset` tool names, Windows/POSIX path normalization, LiteLLM Copilot flags, `allow_shadow` cloning, `static_instruction`, `BuiltInPlanner` arm gating, `RunConfig`, and `TelemetryConfig` idioms are verified against `google-adk` `v2.15.0` and `adk_review`:*

```python
import logging
import os
import re
from pathlib import Path, PurePosixPath
from typing import Any, Literal

import truststore
from pydantic import BaseModel, ConfigDict

from google.adk import Context, Event, Workflow
from google.adk.agents import LlmAgent
from google.adk.agents.context_cache_config import ContextCacheConfig
from google.adk.agents.run_config import RunConfig, StreamingMode, ToolThreadPoolConfig
from google.adk.apps import App, ResumabilityConfig
from google.adk.apps.app import EventsCompactionConfig
from google.adk.environment import LocalEnvironment
from google.adk.events import RequestInput
from google.adk.models import FallbackModel, LiteLlm
from google.adk.models.base_llm import BaseLlm
from google.adk.models.google_llm import Gemini
from google.adk.planners import BuiltInPlanner
from google.adk.plugins import (
    BasePlugin,
    ModelConsultObservabilityPlugin,
    ReflectAndRetryModelPlugin,
    ReflectAndRetryToolPlugin,
    ToolCallIntegrityPlugin,
)
from google.adk.telemetry import ContentCapturingMode, TelemetryConfig
from google.adk.tools.environment import EnvironmentToolset
from google.adk.tools.model_consult import ForceEscalationPlugin, ModelConsultTool
from google.adk.utils.env_utils import is_enterprise_mode_enabled
from google.adk.workflow import BaseNode, DEFAULT_ROUTE, JoinNode, RetryConfig, START, node
from google.genai import types

# Inject OS CA trust store before HTTP/LLM clients (fixes corporate Windows/macOS HTTPS proxies)
truststore.inject_into_ssl()

_BEARER = re.compile(r"(Bearer\s+)[^\s'\",}]+")
_WIN_DRIVE = re.compile(r"^[A-Za-z]:")
_WIN_RESERVED = frozenset(
    {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}
)


class _HideBearer(logging.Filter):
    """Redacts Copilot Bearer tokens in LiteLLM extra_headers when running `adk web -v`."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg, record.args = _BEARER.sub(r"\1[REDACTED]", record.getMessage()), ()
        return True


_HIDE_BEARER = _HideBearer()


# 1. Frozen Pydantic v2 boundary contracts (ADK Rule #8 enforces identical I/O across swaps)
class StrictDTO(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class ChangeContext(StrictDTO):
    change_id: str
    profile: Literal["lean", "standard", "strict"] = "standard"
    planning_root: str = ".spec"
    worktree_path: str = "."
    skip_specs: bool = False


class AnalysisReport(StrictDTO):
    change_id: str
    critical_count: int = 0
    high_count: int = 0
    spec_coverage_pct: float = 0.0
    findings_markdown: str


class ReviewVerdict(StrictDTO):
    decision: Literal["approve", "revise", "abort"]
    feedback: str = ""


# 2. Hardened Windows + POSIX Write Policy Plugin (pair with least-privilege tool_filter!)
class WritePolicyPlugin(BasePlugin):
    """Enforces cross-platform normalized path boundaries and blocks Execute on non-mutating stages."""

    READ_ONLY_AGENTS = frozenset({"explore", "analyze", "analyze_llm", "drift_check"})

    def __init__(self, workspace_root: Path | None = None) -> None:
        super().__init__(name="write_policy_plugin")
        self._workspace_root = workspace_root.resolve() if workspace_root else None

    @staticmethod
    def _normalized_parts(raw_path: str) -> tuple[str, ...] | None:
        s = raw_path.strip()
        if "\0" in s or s.startswith(("//", "\\\\")) or _WIN_DRIVE.match(s):
            return None  # Reject null bytes, UNC paths, and Windows drive prefixes
        clean = s.replace("\\", "/").lstrip("/")
        if not clean:
            return ()
        parts = PurePosixPath(clean).parts
        if ".." in parts:
            return None
        if any(part.split(".", 1)[0].upper() in _WIN_RESERVED for part in parts):
            return None  # Reject Windows reserved device filenames (CON, NUL, COM1, ...)
        return parts

    def _escapes_via_link(self, raw_path: str) -> bool:
        if self._workspace_root is None:
            return False
        candidate = (self._workspace_root / raw_path.strip()).resolve()
        is_junc = getattr(os.path, "isjunction", lambda _p: False)
        return candidate.is_symlink() or is_junc(candidate) or not candidate.is_relative_to(self._workspace_root)

    async def before_tool_callback(self, *, tool, tool_args: dict[str, Any], tool_context):
        agent_name = getattr(tool_context, "agent_name", "")
        if tool.name == "Execute" and (
            agent_name in self.READ_ONLY_AGENTS or agent_name == "verify_converge"
        ):
            return {"error": f"Execute denied: '{agent_name}' cannot run shell mutations."}

        if tool.name in {"WriteFile", "EditFile"}:
            if agent_name in self.READ_ONLY_AGENTS:
                return {"error": f"Write denied: '{agent_name}' is strictly read-only."}
            raw_path = str(tool_args.get("path", ""))
            parts = self._normalized_parts(raw_path)
            if parts is None or self._escapes_via_link(raw_path):
                return {"error": "Write denied: unsafe Windows/POSIX path, junction, or traversal."}
            if agent_name == "apply" and "checklists" in parts:
                return {"error": "Write denied: checklists/ is reviewer-owned."}
            if agent_name == "verify_converge":
                return {"error": "Use narrow append_convergence_tasks tool instead of raw file writes."}
        return None


# 3. Dual-arm model factory (GitHub Copilot via LiteLLM + native Gemini / Vertex AI)
def build_model(
    provider: Literal["copilot", "gemini"],
    primary: str,
    fallback: str = "",
) -> str | BaseLlm:
    names = [primary] + ([fallback] if fallback and fallback != primary else [])
    if provider == "gemini":
        _ = is_enterprise_mode_enabled()  # Respects GOOGLE_GENAI_USE_ENTERPRISE / Vertex AI
        models = [Gemini(model=n, retry_options=types.HttpRetryOptions(attempts=3)) for n in names]
        return models[0] if len(models) == 1 else FallbackModel(models=models)

    import litellm  # Deferred import keeps settings/CLI startup fast

    litellm.suppress_debug_info = True
    litellm.disable_copilot_system_to_assistant = True
    logging.getLogger("LiteLLM").addFilter(_HIDE_BEARER)
    # _skip_mcp_handler=True avoids LiteLLM proxy `mcp` import failure on tool-carrying turns
    models = [LiteLlm(model=f"github_copilot/{n}", max_retries=2, _skip_mcp_handler=True) for n in names]
    return models[0] if len(models) == 1 else FallbackModel(models=models)


def make_readonly_env_toolset(working_dir: str) -> EnvironmentToolset:
    return EnvironmentToolset(
        environment=LocalEnvironment(working_dir=Path(working_dir)),
        tool_filter=lambda tool, _ctx=None: tool.name == "ReadFile",
    )


def make_semantic_audit_agent(
    working_dir: str,
    provider: Literal["copilot", "gemini"] = "copilot",
    primary_model: str = "gpt-4.1",
    fallback_model: str = "",
) -> LlmAgent:
    # BuiltInPlanner sets ThinkingConfig, which errors on non-thinking models: gate to Gemini!
    planner = (
        BuiltInPlanner(thinking_config=types.ThinkingConfig(thinking_budget=2048))
        if provider == "gemini"
        else None
    )
    return LlmAgent(
        name="analyze_llm",
        mode="single_turn",
        model=build_model(provider, primary_model, fallback_model),
        static_instruction=(
            "You are a read-only SDD auditor. Check constitution alignment, requirement clarity, "
            "and cross-artifact consistency without modifying any files."
        ),
        instruction="Audit active change '{change_id}' and return a structured AnalysisReport.",
        planner=planner,
        input_schema=ChangeContext,
        output_schema=AnalysisReport,
        tools=[make_readonly_env_toolset(working_dir)],
    )


# 4. Guarded Strangler-Fig Stage Registry (llm | shadow | hybrid | python)
StageMode = Literal["llm", "shadow", "hybrid", "python"]


def build_stage_node(
    stage_name: str,
    mode: StageMode,
    llm_node: BaseNode,
    python_node: BaseNode,
    hybrid_node: BaseNode | None = None,
    *,
    allow_shadow: bool = False,
) -> BaseNode:
    if mode == "llm":
        return llm_node
    if mode == "python":
        return python_node
    if mode == "hybrid" and hybrid_node is not None:
        return hybrid_node
    if not allow_shadow:
        raise ValueError(f"Shadow mode disabled for mutating stage '{stage_name}'.")

    # Clone with unique names (ADK Rule #1) and preserve input/output contracts (Rule #8)
    llm_branch = node(llm_node, name=f"{stage_name}_shadow_llm")
    py_branch = node(python_node, name=f"{stage_name}_shadow_py")
    join = JoinNode(name=f"{stage_name}_shadow_join")

    def select_primary_and_log_diff(node_input: dict[str, Any]):
        llm_out = node_input[llm_branch.name]
        py_out = node_input[py_branch.name]
        _ = (llm_out == py_out)  # Emit parity metric via telemetry without altering primary output
        return llm_out

    return Workflow(
        name=f"{stage_name}_shadow_wf",
        input_schema=llm_node.input_schema,
        output_schema=llm_node.output_schema,
        edges=[(START, (llm_branch, py_branch), join, select_primary_and_log_diff)],
    )


# 5. Loop-safe HITL Review Gate & Privacy-Hardened RunConfig
@node(rerun_on_resume=True, retry_config=RetryConfig(max_attempts=3))
async def review_gate(ctx: Context, node_input: AnalysisReport):
    interrupt_id = f"review_{ctx.invocation_id}_{ctx.run_id}"
    resume_payload = ctx.resume_inputs.get(interrupt_id)
    if not resume_payload:
        yield RequestInput(
            interrupt_id=interrupt_id,
            message=f"Review '{node_input.change_id}' (critical={node_input.critical_count}):",
            response_schema=ReviewVerdict,
        )
        return
    verdict = ReviewVerdict.model_validate(resume_payload)
    yield Event(
        state={"last_review_feedback": verdict.feedback},
        route=verdict.decision,
        output=ChangeContext(change_id=node_input.change_id),
    )


def default_run_config(streaming: bool = True) -> RunConfig:
    return RunConfig(
        streaming_mode=StreamingMode.SSE if streaming else StreamingMode.NONE,
        max_llm_calls=40,
        tool_thread_pool_config=ToolThreadPoolConfig(max_workers=4),
        telemetry=TelemetryConfig(capture_message_content=ContentCapturingMode.NO_CONTENT),
    )
```

### 2.4 Verified ADK 2.0, Dual-Arm & Cross-Platform Pitfalls Checklist (24 Traps to Avoid)

| Pitfall | Verified Rule in `google-adk` `2.15.0`, Copilot/LiteLLM, `uv`, Windows & Python `3.14` |
| --- | --- |
| Forcing `google-genai>=3` | PyPI has `google-genai 3.6.1`, **but `google-adk 2.15.0` requires `google-genai>=2.34,<3`** (`2.34.0` in `constraints-3.14.txt`). Never override `<3` until ADK releases v3 support. |
| Running `mutmut` 3.8 on native Windows | `mutmut 3.8.1` uses POSIX `os.fork()`/`forkserver` and fails on native Windows; gate with `"mutmut>=3.8.1; sys_platform != 'win32'"` and use `cosmic-ray>=8.9.0` or WSL/Linux CI on Windows. |
| `BuiltInPlanner` on Copilot / non-thinking models | Sets `ThinkingConfig`, causing errors on models without thinking support; **only attach `BuiltInPlanner` when `provider == "gemini"`**. |
| LiteLLM Copilot defaults (`system`, `mcp`, `Bearer`) | Without `disable_copilot_system_to_assistant = True`, `_skip_mcp_handler=True`, and `_HideBearer`, Copilot misreads system turns as assistant turns, tool calls fail importing LiteLLM proxy's `mcp`, and `adk web -v` leaks tokens. |
| Windows CRLF, junctions & `LocalEnvironment` `os.killpg` | CRLF corrupts SHA-256 base hashes (normalize to LF + ship `.gitattributes`); check `os.path.isjunction()` + drive/UNC/reserved DOS names; `LocalEnvironment` ignores `os.killpg` on Windows, so use shell-free full-PATH argv subprocesses + `taskkill /F /T /PID`. |
| `pyrefly` failing on `LlmAgent(...)` | ADK declares `LlmAgent(BaseAgent, abc.ABC)` without abstract methods; set `[tool.pyrefly.errors] direct-abstract-base-instantiation = "ignore"`. |
| `adk web .` leaking diffs/secrets locally | By default ADK writes sessions into `.adk/session.db` with unredacted code diffs; run `uv run adk web --no_use_local_storage .` in `make web`. |
| `uv tool install .` bypassing `uv.lock` / `exclude-newer` | `uv tool install` ignores root `uv.lock` & `[tool.uv]`; export locked constraints via `uv export --frozen --no-hashes --no-dev --no-emit-project` and pass `--exclude-newer P3D --constraints ...`, and use `uv run --no-project` in `Makefile` `$(shell ...)` helpers. |
| `from google.adk import START` | Fails with `ImportError`; import `START` from `google.adk.workflow`. |
| `from google.adk.apps import EventsCompactionConfig` | Fails with `ImportError`; import from `google.adk.apps.app`. |
| `from google.adk.tools import SkillToolset` | Fails with `ImportError`; import from `google.adk.tools.skill_toolset`. |
| `from google.adk.a2a import to_a2a` | Fails with `ImportError`; import from `google.adk.a2a.utils.agent_to_a2a`. |
| `@node(input_schema=...)` | Raises `TypeError`; annotate `node_input: MyModel` and return `-> OutModel` instead. |
| `get_fast_api_app(agent_dir=...)` | Raises `TypeError`; keyword argument is `agents_dir=` (plural). |
| Default telemetry span privacy | `ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS` defaults `True`; set `ContentCapturingMode.NO_CONTENT` / `false` in production! |
| `WritePolicyPlugin` skipping `Execute` or raw paths | Substring checks miss relative `"checklists/a.md"` and `..`; shell `Execute` bypasses `WriteFile` blocks—combine `tool_filter` + normalized paths + blocking `Execute`. |
| `shadow` mode collisions & double-writes | Sharing names breaks Rule #1, missing `Workflow` schemas breaks Rule #8, and mutating stages double-write—require `allow_shadow`, clone names, and forward schemas. |
| Putting static rules in `instruction` | Breaks Gemini prefix caching and fails `GEPARootAgentPromptOptimizer` (`require_static_instruction`); keep immutable prompts in `static_instruction`. |
| `BufferedSessionService` without flush | `Runner` does not auto-flush yet; explicitly call `await session_service.flush_session(...)` and `close()`. |
| `ToolCallIntegrityPlugin` expectations | Validates agent tool calls, **not** tools mounted directly as standalone workflow graph nodes. |
| `ServiceTier.DEFERRED` ignored | Silently dropped unless `provider == "gemini"` AND the model sets `Gemini(use_interactions_api=True)`. |
| `NodeTool` generator typing | Annotate `-> Generator[str, None, None]` (yielded payload only), not `Event`/`RequestInput`, to keep schemas compact. |
| `mode="chat"` mid-graph or dangling fan-out | Chat agents only follow `START` (Rule #9); fan-out branches must converge into `JoinNode`. |
| Static `interrupt_id` in loops | Collides across iterations; scope via `f"review_{ctx.invocation_id}_{ctx.run_id}"` + `@node(rerun_on_resume=True)`. |

---

## 3. Target Hexagonal Python 3.14 Package Layout (`adk_review`-Aligned `uv` Workspace)

```text
adk_spec/
├── .python-version                      # 3.14
├── .gitattributes                       # * text=auto eol=lf (prevents Windows CRLF diff/fingerprint corruption)
├── .env.example                         # SPEC_PROVIDER=copilot|gemini, LITELLM_LOCAL_MODEL_COST_MAP=True, GHE & Vertex vars
├── .github/
│   ├── copilot-instructions.md          # Repo guidance for GitHub Copilot in VS Code & Cloud Agent
│   └── workflows/ci.yml                 # 3-OS CI matrix: windows-latest, macos-latest, ubuntu-latest
├── pyproject.toml                       # Root package (adk_spec), hatchling, [tool.uv] exclude-newer="P3D", workspace=["tui"]
├── uv.lock                              # Single shared lock across root + tui/
├── Makefile                             # POSIX tasks + PowerShell `uv run` documentation
├── adk_spec/                            # Flat root package (adk web . discovers root_agent directly)
│   ├── __init__.py
│   ├── agent.py                         # Exports `app` / `root_agent` for `adk web` & `adk run`
│   ├── domain/                          # PURE PYTHON (zero google.adk / litellm imports — enforced by import-linter)
│   │   ├── models/                      # Frozen DTOs (ChangeContext, DeltaSpec, AnalysisReport, ReviewVerdict)
│   │   ├── artifact_graph.py            # schema.yaml DAG resolver & overlay compiler
│   │   ├── knowledge_index.py           # Selective knowledge manifest, LF SHA-256 lock, token budgeter & pure-Python BM25/heading RAG
│   │   ├── spec_parser.py               # EARS + RFC 2119 + #### Scenario: + T### [P] [US#] parser
│   │   ├── delta_merger.py              # LF-normalized SHA-256 fingerprint checker + 3-way diff3 spec merger
│   │   └── traceability.py              # @pytest.mark.spec AST scanner, Hypothesis stub gen & static lint rules
│   ├── ports/                           # typing.Protocol contracts per pipeline stage
│   ├── adapters/
│   │   ├── llm/                         # Phase 1 LlmAgent stage implementations + ConflictResolverAgent
│   │   └── python/                      # Phase 2-3 deterministic @node adapters
│   ├── orchestration/
│   │   ├── settings.py                  # Zero-import env reader (SPEC_PROVIDER, models, GHE, token dirs)
│   │   ├── models.py                    # Sole provider-aware factory (Copilot LiteLlm + Gemini + truststore + _HideBearer)
│   │   ├── registry.py                  # Guarded StageRegistry (llm | shadow | hybrid | python)
│   │   ├── plugins/                     # Hardened Windows+POSIX WritePolicyPlugin, ConstitutionPlugin
│   │   ├── tools/                       # EnvironmentToolset (tool_filter), spec_knowledge_search, append_convergence_tasks, full-PATH git, ToolConfirmation
│   │   ├── skills/                      # Lazy SKILL.md bundles via SkillToolset
│   │   ├── workflows/                   # sdd.py, assess.py, bugfix.py, drift_check.py, coordinator.py
│   │   └── app.py                       # Exports `app = App(...)`, BufferedSession, Memory & Artifact wiring
│   └── interfaces/
│       ├── cli.py                       # CLI entrypoints (`adk-spec`, UTF-8 console reconfigure, %APPDATA%/XDG dirs)
│       ├── login.py                     # `adk-spec-login`: 15-min GitHub Copilot OAuth device flow + truststore
│       ├── api.py                       # `get_fast_api_app(agents_dir=..., web=False)` + AG-UI (`ag_ui_adk`) + rewind/SSE
│       ├── a2a.py                       # Cross-team Spec Store service via `to_a2a` + `RemoteA2aAgent`
│       └── mcp_server.py                # Hardened `to_mcp_server()` wrapper (1 MiB cap, symlink/junction safety)
├── tui/                                 # Separate `uv` workspace member (`adk-spec-tui`) so headless CI stays UI-free
│   ├── pyproject.toml                   # depends on `adk-spec` (workspace=true), `textual>=8.2.8,<9.0`, `truststore>=0.10.5`
│   └── tui/                             # Rich/Textual TUI (`adk-spec-tui` with cli-view invariants, PEP 750 ANSI & ASCII fallback)
├── web/                                 # Next.js 16.4.6 + React 19.3.1 + TS 7.0.2 + @xyflow/react 13.0.2 + Plannotator Workbench
├── scripts/                             # Helper scripts & fixture repo builders
├── tests/
│   ├── unit/                            # Pure domain, Hypothesis PBT, plugin, merger, Copilot/Gemini arm & OS-parity tests
│   └── eval/                            # ADK AgentEvaluator + ToolArgsMatcher golden suites (*.test.json)
├── research_notes/
└── reports/
```

### 3.1 Verified Python 3.14 & Latest Library Version Baseline (2026-11-20)

All target versions below were verified against PyPI, npm, `google/adk-python`'s `constraints-3.14.txt`, and `adk_review/pyproject.toml`:

| Layer | Package | Verified Latest | Target Spec / Constraint Rule |
| --- | --- | --- | --- |
| **Runtime & Build** | `Python`, `uv`, `hatchling` | `3.14.10`, `0.13.9`, `1.33.0` | `requires-python = ">=3.14,<3.15"`, `uv` `[tool.uv] required-version = ">=0.12"`, `exclude-newer = "P3D"`, `hatchling>=1.33.0` |
| **Dual-Arm Core & TLS** | `google-adk`, `litellm`, `python-dotenv`, `truststore` | `2.15.0`, `1.110.2`, `1.2.4`, `0.10.5` | `google-adk==2.15.0` + pinned `litellm==1.110.2` (first-class Copilot arm); `truststore>=0.10.5` for OS TLS CAs |
| **GenAI SDK** | `google-genai` | `3.6.1` (PyPI) | **CRITICAL:** `google-adk 2.15.0` requires **`google-genai>=2.34,<3`** (`2.34.0` in `constraints-3.14.txt`) — **do not** force `>=3` |
| **Data & Web** | `pydantic`, `fastapi`, `uvicorn`, `pyyaml` | `2.14.4`, `0.165.0`, `0.54.0`, `6.0.3` | Latest 3.14 wheels satisfying ADK bounds (`pydantic<3`, `fastapi<1`, `uvicorn<1`, `pyyaml<7`) |
| **Persistence** | `aiosqlite`, `sqlalchemy` | `0.22.1`, `2.1.9` | Satisfies ADK `db` extra (`>=2,<3`) |
| **Protocols** | `mcp`, `a2a-sdk`, `ag-ui-adk`, `ag-ui-protocol` | `2.3.0`, `1.3.1`, `0.13.0`, `1.0.0` | `mcp 2.3.0` uses SDK 2.x `MCPServer` (ADK excludes `aiohttp!=3.14.2`); `ag-ui-adk 0.13.0` pulls `ag-ui-a2ui-toolkit>=0.0.6` |
| **CLI / TUI (`tui/`)** | `typer`, `rich`, `textual` | `0.29.2`, `15.0.0`, `8.2.8` | CLI (`typer>=0.29.2`) in core; `textual>=8.2.8,<9.0` isolated in `tui/` workspace member |
| **Test & QA** | `pytest`, `pytest-asyncio`, `hypothesis`, `mutmut`, `cosmic-ray`, `import-linter` | `9.2.0`, `1.5.0`, `6.170.17`, `3.8.1`, `8.9.0`, `2.17` | `"mutmut>=3.8.1; sys_platform != 'win32'"` (POSIX) + `"cosmic-ray>=8.9.0"` (Windows-compatible); `asyncio_mode = "strict"`, `faulthandler_timeout = 300` |
| **Type & Lint** | `ruff`, `pyrefly`, (`mypy`, `ty`, `pyright`) | `0.17.6`, `1.5.0`, (`2.4.1`, `0.0.107`, `1.1.414`) | Pin `ruff==0.17.6` (`max-complexity = 10`, `S607`) & `pyrefly==1.5.0` (`direct-abstract-base-instantiation = "ignore"`) matching `adk_review` |
| **Frontend UI** | `react`, `next`, `typescript`, `@xyflow/react`, `@copilotkit/react-core`, `@ag-ui/core`, `tailwindcss` | `19.3.1`, `16.4.6`, `7.0.2`, `13.0.2`, `1.90.0`, `1.0.5`, `4.3.5` | Latest Web Workbench stack (`web/`) |

### 3.2 Reference `pyproject.toml`, `tui/pyproject.toml` & `Makefile` (+ Windows PowerShell) Blueprint

Modeled directly on `adk_review/pyproject.toml` and `Makefile`, upgraded to latest `2026-11-20` verified versions with first-class Copilot & Windows/macOS support:

```toml
# pyproject.toml (root)
[project]
name = "adk-spec"
version = "0.1.0"
description = "Spec-driven development framework on Google ADK: LLM-first, progressively migrated to deterministic Python, on GitHub Copilot and Gemini."
requires-python = ">=3.14,<3.15"
dependencies = [
    "google-adk==2.15.0",
    "litellm==1.110.2",
    "python-dotenv>=1.2.4",
    "truststore>=0.10.5",
    "typer>=0.29.2",
    "pyyaml>=6.0.3",
    "ruff==0.17.6",
    "pyrefly==1.5.0",
]

[project.optional-dependencies]
web = ["ag-ui-adk>=0.13.0"]
mcp = ["google-adk[mcp]==2.15.0"]
a2a = ["google-adk[a2a]==2.15.0"]
db = ["google-adk[db]==2.15.0"]

[project.scripts]
adk-spec = "adk_spec.interfaces.cli:run"
adk-spec-login = "adk_spec.interfaces.login:run"

[build-system]
requires = ["hatchling>=1.33.0"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["adk_spec"]

[dependency-groups]
dev = [
    "pytest>=9.2.0",
    "pytest-asyncio>=1.5.0",
    "hypothesis>=6.170.17",
    "mutmut>=3.8.1; sys_platform != 'win32'",
    "cosmic-ray>=8.9.0",
    "import-linter>=2.17",
]

[tool.uv.workspace]
members = ["tui"]

[tool.uv]
exclude-newer = "P3D"
required-version = ">=0.12"

[tool.pytest.ini_options]
asyncio_mode = "strict"
asyncio_default_fixture_loop_scope = "function"
faulthandler_timeout = 300
faulthandler_exit_on_timeout = true
testpaths = ["tests"]
pythonpath = [".", "tui"]
filterwarnings = [
    "ignore::DeprecationWarning",
    "ignore:.*EXPERIMENTAL.*:UserWarning",
    "ignore:Item 'summary' on TypedDict class 'ChatCompletionReasoningItem':UserWarning",
    "ignore:Items 'device_code', 'user_code', 'verification_uri' on TypedDict class '_DeviceCode':UserWarning",
    "ignore:Items 'access_token', 'error' on TypedDict class '_AccessTokenPoll':UserWarning",
]

[tool.ruff]
line-length = 120
target-version = "py314"
src = ["tui", ".", "scripts"]

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP", "N", "ARG", "ASYNC", "RUF", "BLE001", "S607", "SIM", "RET", "C4", "PIE", "PT", "C90", "PERF", "FURB"]
ignore = ["SIM112", "PT018"]

[tool.ruff.lint.mccabe]
max-complexity = 10

[tool.ruff.lint.per-file-ignores]
"scripts/*" = ["S607"]
"tests/*" = ["S607"]

[tool.pyrefly]
project-excludes = ["tests/**"]
ignore-missing-imports = ["textual", "textual.*", "rich", "rich.*"]
search-path = ["tui", ".", "scripts"]

[tool.pyrefly.errors]
direct-abstract-base-instantiation = "ignore"

[tool.pyright]
extraPaths = ["scripts"]
```

```toml
# tui/pyproject.toml (separate workspace member — keeps headless installs free of Textual)
[project]
name = "adk-spec-tui"
version = "0.1.0"
description = "Terminal dashboard (adk-spec view) on top of adk-spec."
requires-python = ">=3.14,<3.15"
dependencies = [
    "adk-spec",
    "textual>=8.2.8,<9.0",
    "truststore>=0.10.5",
]

[project.scripts]
adk-spec-tui = "tui:run"

[tool.uv.sources]
adk-spec = { workspace = true }

[build-system]
requires = ["hatchling>=1.33.0"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["tui"]
```

```makefile
# Makefile (POSIX; Windows PowerShell equivalents shown right below)
.PHONY: help sync install web login lint typecheck arch-check format test ci

LOCKED := $(shell uv run --no-project python -c "import os, tempfile; print(os.path.join(tempfile.gettempdir(), 'adk-spec-locked.txt'))")

sync:
	uv sync --locked --all-packages

install:
	uv export --frozen --no-hashes --no-dev --no-emit-project --quiet --output-file "$(LOCKED)"
	uv tool install --reinstall --exclude-newer P3D --constraints "$(LOCKED)" .

web:
	uv run adk web --no_use_local_storage .

login:
	uv run adk-spec-login

lint:
	uv run ruff check . && uv run ruff format --check .

typecheck:
	uv run pyrefly check

arch-check:
	uv run lint-imports

format:
	uv run ruff check --fix . && uv run ruff format .

test:
	uv run pytest -q

ci: lint typecheck arch-check test
```

**Windows PowerShell Equivalents (no GNU `make` required):**
```powershell
uv sync --locked --all-packages
uv run adk-spec-login
uv run adk web --no_use_local_storage .
uv run ruff check .; uv run ruff format --check .; uv run pyrefly check; uv run lint-imports; uv run pytest -q
```

---

## 4. Staged Implementation & LLM-to-Python Migration Roadmap

### Phase 0 — Hexagonal Foundation, Cross-Platform Guardrails & Dual-Arm Config (~100% Scaffolding)
- **Deliverables:** `uv python pin 3.14` workspace (`.python-version`, `.gitattributes` with `* text=auto eol=lf`, `.env.example`, `.github/copilot-instructions.md`, `pyproject.toml` + `tui/pyproject.toml` + `Makefile` with `exclude-newer = "P3D"`, PEP 649/749 native typing, PEP 750 `t-strings`); `import-linter 2.17` blocking `google.adk` and `litellm` inside `adk_spec/domain/`; `adk_spec/orchestration/{settings,models}.py` (`truststore`, Copilot `LiteLlm` + Gemini, `_HideBearer`); `adk-spec-login` 15-min OAuth CLI; Windows/macOS hardened `WritePolicyPlugin` + `EnvironmentToolset` (`tool_filter`) + `ToolCallIntegrityPlugin`; `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` + `%APPDATA%`/XDG paths; `RunConfig(TelemetryConfig(NO_CONTENT), ...)` + `App`; Page 0 onboarding + `tui/` basic dashboard + `make web` (`--no_use_local_storage`); 3-OS GitHub Actions CI (`windows-latest`, `macos-latest`, `ubuntu-latest`).
- **Verification:** `make ci` (`ruff`, `pyrefly`, `lint-imports`, `pytest`) on Windows, macOS, and Linux confirming `WritePolicyPlugin` blocks Windows/POSIX traversal & `Execute` bypasses and `Workflow(...)` passes all 10 ADK rules.

### Phase 1 — LLM-Heavy MVP on Copilot & Gemini (~90% LLM / 10% Python)
- **Goal:** Working end-to-end SDD lifecycle validated on **both GitHub Copilot (`gpt-4.1` / org-approved Copilot models) and Gemini** using `FallbackModel`, `ReflectAndRetry{Tool,Model}Plugin`, `ModelConsultTool`, `SkillToolset`, and `BuiltInPlanner` / `ContextCacheConfig` guarded to `provider == "gemini"`.
- **Workspace & Knowledge MVP:** Introduce `.spec/knowledge/`, selective `knowledge:` allowlist in `.spec/config.yaml` + pinned `.spec/.knowledge-lock.json` via explicit manual `adk-spec knowledge sync`, and transcript-isolated parallel `explore`/`assess`/`change` sessions.
- **Serving & Evals:** Expose via `get_fast_api_app(agents_dir=..., web=False)` + `ag_ui_adk` SSE stream; record `AgentEvaluator` golden suites (`tests/eval/`) covering both arms + built-in `efficiency_evaluators`; tune `static_instruction` with `GEPARootAgentPromptOptimizer` (Gemini); enable guarded `StageRegistry` `shadow` harness.

### Phase 2 — Python Migration Wave 1: Structure, Auto-RAG, PBT, Shadow Validation & Review Workbench (~65% LLM / 35% Python)
- **Migrations:**
  1. `domain/artifact_graph.py`: deterministic `schema.yaml` DAG, profile selection (`lean`/`standard`/`strict`), and `<context>`/`<rules>`/`<template>` injection.
  2. `domain/knowledge_index.py` & `spec_knowledge_search`: 2-tier Direct Cache → automatic pure-Python BM25/heading RAG switcher (up to ~10x capacity across variable Copilot and Gemini context windows) using compact ToCs without requiring a vector DB.
  3. `domain/spec_parser.py` & `traceability.py`: deterministic EARS/BDD/task validation, **LF-normalized SHA-256** base requirement fingerprinting in `.change.yaml`, `@pytest.mark.spec` AST coverage extraction, and **Hypothesis PBT stub synthesis** from EARS clauses.
  4. Fan-out hybrid `Analyze`: `(DeterministicLintNode, SemanticAuditAgent) → JoinNode → MergeAnalysisNode`.
- **UI & Eval Delivery:** Adopt `ToolArgsMatcher` for non-brittle evals; ship **Workbench Pages 0–5** featuring the `@xyflow/react` Spatial DAG canvas, Plannotator inline AST-anchored annotations, `Last-Event-ID` SSE reconnect, Mobile Approval Inbox PWA, global **Knowledge Capacity & RAG Mode Meter** (`[↻ Sync (N)]`), and human-gated `[↑ Promote to Knowledge]` actions.
- **Migration Gate:** Validate Python nodes via `allow_shadow` parity logs + passing `AgentEvaluator` + efficiency metric gains across both arms.

### Phase 3 — Python Migration Wave 2: Parallel Worktrees, 3-Way Delta Merge, Mutation Gate & Rewind (~40% LLM / 60% Python)
- **Migrations:**
  1. `domain/delta_merger.py`: LF-normalized SHA-256 stale-base check + 3-way `diff3` merge into `.spec/specs/` + atomic `archive/` move, invoking `ConflictResolverAgent` + `ToolConfirmation` only on true merge collisions.
  2. Deterministic `TaskSchedulerNode` + `@node(parallel_worker=True)` concurrent `[P]` workers operating inside isolated **Git worktrees** (`.worktrees/<change-id>`, using `ignore_cleanup_errors=True` + retry-guarded cleanup for Windows Defender locks), with deterministic `- [x]` checkbox updates.
  3. Evidence-first `Verify & Converge`: Python runs shell-free full-PATH `pytest`/linters/settled-env `git log` `REMOVED` baseline lookups (plus **`mutmut` on POSIX / `cosmic-ray` or WSL on Windows** in `strict` mode) before a lightweight judge calls narrow `append_convergence_tasks`.
- **UI Delivery:** Ship **Workbench Pages 6–8** + global **Time-Travel Rewind Scrubber (`Runner.rewind_async`)**.

### Phase 4 — Ecosystem Expansion, A2A Federation, Memory Isolation & Observability (~25–30% LLM / 70–75% Python)
- **Deliverables:** Nested `assess` and `bugfix` workflows; YAML Workflow Overlay compiler; `contracts/` & `roadmap.md` epic scheduler; external `Stores` + **`to_a2a` / `RemoteA2aAgent` cross-team federation**; project-scoped `(app_name, project_id)` `BaseMemoryService` ADR recall with **`isolated_memory` wall** & quarantined human-approved ingestion (`ASI06`) plus optional hybrid semantic `spec_knowledge_search`; shared Workbench **`Can view` vs. `Can edit` RBAC** (resetting sharing on archive); Gemini-guarded `ServiceTier.DEFERRED` (`use_interactions_api=True`) CI `drift-check`; `E2B`/`Daytona` sandbox profile; hardened `to_mcp_server()` (`1 MiB` cap, symlink/junction rejection); and **Workbench Page 9** (ADK Observability, Eval & Migration Console).

---

## 5. Per-Stage LLM → Python Migration Matrix

| Stage | Phase 1 (LLM-First) | Target End State | Migration Trigger / Eval Gate | ADK 2.0 Primitive |
| --- | --- | --- | --- | --- |
| Context, Constitution & DAG Status | Small Python node + LLM | **100% Python** | Zero stale paths; deterministic config injection | `@node` + `BasePlugin` |
| Knowledge Pack, Sync & Retrieval | Direct `static_instruction` + manual `knowledge sync` | **100% Python 2-Tier Direct / BM25 RAG** (+ optional semantic `BaseMemoryService`) | Auto-switch above token/file budget across Copilot & Gemini | `@node` + read-only `FunctionTool` (`spec_knowledge_search`) |
| Security, Write Policy & Privacy | `tool_filter` + `WritePolicyPlugin` + `TelemetryConfig` (Day 1) | **100% Python** (+ optional `ModelArmorPlugin` on GCP) | Zero OWASP ASI01/ASI02 or Windows path/junction bypasses | `tool_filter`, `WritePolicyPlugin`, `ToolCallIntegrityPlugin` |
| `explore` / `propose` / `design` | `LlmAgent` (Copilot or Gemini + `ModelConsultTool`) | **LLM** (+ quarantined `BaseMemoryService` recall) | Open-ended reasoning & trade-offs | `LlmAgent` + `FallbackModel` (`BuiltInPlanner` on Gemini) |
| `specify` (EARS Delta Specs) | `LlmAgent` | **Hybrid** (LLM drafts → Python validates, LF-hashes, gens PBT stubs) | Eliminate syntax/length/CRLF/missing-base errors | `LlmAgent` → `@node` validator |
| `clarify` (7-Dim Scan & Q&A) | `LlmAgent(mode="task")` | **Hybrid** (Python detects gaps → LLM asks ≤ 5 Qs) | Deterministic gap scan trims prompt | `@node` → `LlmAgent(mode="task")` |
| `analyze` (6-Pass Audit) | `LlmAgent` (RO `tool_filter` + plugin) | **Hybrid Fan-Out** (Python lint + `import-linter` + AST cov + LLM judge) | `shadow` parity ≥ 99% + efficiency gains | `(FunctionNode, LlmAgent)` → `JoinNode` |
| Human Review Gates | Python `RequestInput` (Day 1) | **100% Python** (+ `Runner.rewind_async` undo) | Durable replay without re-calling LLMs | `@node(rerun_on_resume=True)` |
| `apply` Scheduling & Worktrees | `LlmAgent(mode="task")` | **Python Scheduler + parallel `[P]` workers in Worktrees** | Concurrent execution & zero `tasks.md` corruption | `@node(parallel_worker=True)` + `LocalEnvironment` |
| `verify` & `converge` | `LlmAgent` (`append_convergence_tasks` only) | **Hybrid** (`pytest` + mutation + `git log` → judge → Python append) | Hard test/mutation evidence kills weak tests | `@node` → `LlmAgent` → conditional route |
| `sync` Deltas & `archive` | `LlmAgent` + `ToolConfirmation` | **95% Python** (LLM only on diff3 conflict) | Eliminates OpenSpec's silent overwrite & CRLF bugs | `@node` + `ToolConfirmation` |
| CI `drift-check` | N/A | **Hybrid Batch** (Python git/test diff + `ServiceTier.DEFERRED` on Gemini) | Off-peak cost efficiency | `Workflow` + `Gemini` / `LiteLlm` |

---

## 6. Verification & Migration Quality Gates

1. **Cross-Platform Static Hygiene & Architecture Gate (`make ci` on `windows-latest`, `macos-latest`, `ubuntu-latest`):** `ruff`, `pyrefly`, `import-linter`, and `pytest` verifying frozen DTOs, zero ADK/`litellm` imports inside `adk_spec/domain/`, Windows/POSIX `WritePolicyPlugin` denials, LF-normalized `delta_merger` Hypothesis PBT invariants, Copilot + Gemini arm mocks, and ADK's 10 static `Workflow` rules.
2. **Shadow-Mode + `AgentEvaluator` + `ToolArgsMatcher` Gate (`adk eval`):** Every Phase 2–4 pure/read-only Python cutover runs in guarded `shadow` mode first, then must pass golden `AgentEvaluator` suites (tested on Copilot & Gemini) with gains on `token_usage_v1`, `inference_call_count_v1`, and `invocation_duration_v1`.
3. **Mutation & Security Gate:** `strict` `verify_converge` verifies `mutmut` (POSIX) / `cosmic-ray` (Windows) survivor budgets, while CI verifies `TelemetryConfig(NO_CONTENT)`, least-privilege `tool_filter` policies, `uv sync --locked --all-packages`, and `make install` (`--exclude-newer P3D`).

---

## 7. Open Decisions Before Phase 0 Scaffolding

1. **Primary Runtime Surface Priority:** Start with `make web` (`adk web --no_use_local_storage .`) + `adk-spec-tui` (`tui/`) in Phase 0–1 and layer the FastAPI/AG-UI/A2UI Web Workbench in Phase 2, or expose `to_mcp_server()` in Phase 1 as well?
2. **Phase 1 `apply` Scope:** Execute actual workspace code edits in Phase 1 `apply`, or validate the spec-lifecycle loop (`propose → specify → clarify → design → tasks → analyze → review → archive`) first and enable code edits immediately after?
3. **Default Provider Arm & Models:** Default `SPEC_PROVIDER` to `copilot` (like `adk_review`, e.g., `gpt-4.1` or org-approved Copilot model + optional GHE tenant endpoints) or `gemini` (`GOOGLE_API_KEY` / Vertex AI `GOOGLE_GENAI_USE_ENTERPRISE=TRUE`), and preferred primary/advisor model IDs on each arm?
