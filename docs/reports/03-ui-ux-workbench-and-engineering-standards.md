# UI / UX Workbench & Engineering Standards Summary (`adk-spec`)

- **Detailed Specifications:** [06-ui-ux-and-page-design-spec.md](../research_notes/Spec%20driven%20framework%20on%20Google%20ADK/06-ui-ux-and-page-design-spec.md) · [05-modern-sdd-standards-and-architecture-patterns.md](../research_notes/Spec%20driven%20framework%20on%20Google%20ADK/05-modern-sdd-standards-and-architecture-patterns.md)
- **Companion Reports:** [01-spec-frameworks-comparative-analysis.md](01-spec-frameworks-comparative-analysis.md) · [02-adk-spec-framework-architecture-and-roadmap.md](02-adk-spec-framework-architecture-and-roadmap.md)

---

## 1. Multi-Surface Workbench Strategy (Python 3.14 + ADK + FastAPI + AG-UI 1.0 + A2UI)

AI spec tools fail developers when everything is flattened into a scrolling chat transcript ("the chat wall"). `adk-spec` adopts a decoupled 5-surface strategy driven by one **Python 3.14** + **Google ADK `2.15.0`** backend (`get_fast_api_app(agents_dir=..., web=False)` on `FastAPI 0.165.0` + `ag-ui-adk 0.13.0` + `StreamingMode.SSE` + `Last-Event-ID` cursor replay):

1. **Web Spec Workbench (`React 19.3.1` + `Next.js 16.4.6` + `TypeScript 7.0.2` + `@xyflow/react 13.0.2` + `@copilotkit/react-core 1.90.0` + `@ag-ui/core 1.0.5` + `Tailwind CSS 4.3.5`):** Spatial engineering studio for authoring EARS specs, attaching AST/line-range Plannotator annotations, watching live workflow DAGs, triaging findings, and resolving 3-way delta conflicts via declarative A2UI surfaces (`ag-ui-a2ui-toolkit`) mapped onto a vetted host catalog.
2. **Mobile Approval Inbox PWA (`<768px`):** High-density asynchronous triage cards (`What Changed`, `Why`, `Risk Tier`, collapsible diff) with gesture/keyboard shortcuts and deep-links to exact desktop React Flow nodes.
3. **ADK Built-In Dev UI (`adk web --no_use_local_storage .`):** Zero-boilerplate Day-1 inspector during Phase 0–1 for raw events, state deltas, and `RequestInput` resumes without persisting unredacted diffs/secrets to `.adk/session.db`.
4. **Rich Terminal Dashboard (`adk-spec-tui` in separate `uv` workspace member `tui/`):** Isolated package (`textual>=8.2.8,<9.0`, `truststore>=0.10.5`, `adk-spec = { workspace = true }`) keeping headless CI installs UI-free, inheriting OpenSpec `cli-view` invariants (`tasks.total > 0` completion guard, ascending progress sort, decoupled DAG chips, PEP 750 ANSI control-char sanitization) plus `--json` CI output.
5. **IDE & Team Federation (`to_mcp_server` via `mcp 2.3.0` + `to_a2a` via `a2a-sdk 1.3.1`):** Exposes workflows to coding assistants over hardened MCP (`1 MiB` payload cap, symlink checks) and federates shared Spec Stores over A2A JSON-RPC.

---

## 2. Ten Workbench Views Summary (Pages 0–9)

| Page / View | Primary User Job | Key Interactive / A2UI Surfaces | Backend / ADK Integration | Delivery Phase |
| --- | --- | --- | --- | --- |
| **0. Onboarding & Constitution** | Bootstrap uninitialized `.spec/` cleanly in <60s | Stack detector, starter `constitution.md` + `config.yaml`, profile picker (`lean`/`standard`/`strict`) | Read-only scan + explicit init confirmation | Phase 0 (CLI) / Phase 2 (Web) |
| **1. Overview & Spec Health** | Monitor project health, active changes & migration ROI | KPI strip, ascending active changes table, DAG chips (`✓`/`→`/`(skipped)`), drift & Model Armor alerts | `/api/spec/overview`, `ArtifactGraph` + `AgentEvaluator` | Phase 2 (TUI in Phase 0) |
| **2. Active Change IDE + DAG** | Draft & annotate `proposal`, deltas, `design`, `tasks`; scrub history | 3-pane split (isolated parallel session tabs, DAG rail, Plannotator editor / `@xyflow/react` canvas, Capacity/RAG pill, `[↑ Promote to Knowledge]` & Rewind scrubber) | `StreamingMode.SSE`, `Last-Event-ID`, `Runner.rewind_async` | Phase 2 (Rewind UI Phase 3) |
| **3. HITL Review Inbox (Desktop + PWA)** | Clear paused gates asynchronously without fatigue | Async queue, 4-step progressive review, contextual diffs, defensive 3-way Revise/Edit/Approve | `RequestInput` + `ResumabilityConfig`, `ToolConfirmation` + HMAC badge | Phase 2 |
| **4. Clarify & Discovery** | Resolve `[NEEDS CLARIFICATION]` markers fast | 7-dimension coverage matrix (`Clear`/`Partial`/`Missing`), ≤5 `ClarifyQuestionCard`s | `ClarifyAgent(mode="task")` pause/resume | Phase 2 |
| **5. Analysis & Checklists** | Audit 6-pass findings & manage reviewer checklists | Read-only lock banner, severity filter, `[Python]`/`[LLM]` badges, `Entity.field` & PBT matrix | Hybrid `Analyze` workflow + `WritePolicyPlugin` | Phase 2 |
| **6. Execution & Convergence** | Watch `[P]` workers, tests, mutation checks & `converge` loops | Vertical-slice swimlanes + React Flow worker graph, `.worktrees/<id>` cards, live `pytest`/`mutmut` logs | `@node(parallel_worker=True)`, `append_convergence_tasks` | Phase 3 |
| **7. Specs, Knowledge, Contracts & Maps** | Explore living truth, curated Knowledge Pack, API contracts & `roadmap.md` | Capability tree, Project Knowledge file picker + token bar + `[↻ Sync Now]` + `isolated_memory` toggle, `contracts/` viewer, `R1..Rn` DAG, A2A Store & `Can view`/`Can edit` roles | `.spec/{specs,knowledge}/`, `spec_knowledge_search`, `Stores`, `to_a2a` | Phase 3 (A2A/RBAC Phase 4) |
| **8. 3-Way Conflict & Archive** | Merge parallel deltas without data loss | 3-pane `Base SHA-256` \| `Live` \| `Delta` diff3 resolver, AI merge assist, Archive gate | `delta_merger.py`, `ConflictResolverAgent`, `ToolConfirmation` | Phase 3 |
| **9. ADK Eval & Migration** | Govern `llm` → `shadow` → `hybrid` → `python` cutovers | Guarded `StageRegistry` matrix, `AgentEvaluator` + `efficiency_evaluators` trends, privacy shield badge | `ModelConsultObservabilityPlugin`, `TelemetryConfig(NO_CONTENT)` | Phase 4 |

---

## 3. HITL Anti-Fatigue & Visual Design System Tokens

- **Quit-Earliest Progressive Ordering:** Review gates always lead with `1. Proposal` → `2. Spec Deltas` → `3. Design & Contracts` → `4. Tasks`.
- **Contextual Diffs + Defensive 3-Way Controls:** Pair side-by-side diffs and Plannotator inline annotations with **Revise with Feedback** and **Edit Inline** positioned clearly prior/adjacent to **Approve & Resume**.
- **Design Tokens:**
  - **Themes:** Dark-first (`#0B0F17` canvas, `#121826` elevated pane, `#1F2937` borders) + accessible Light mode.
  - **Severity & Provenance Pills:** `CRITICAL` (`#EF4444`), `HIGH` (`#F59E0B`), `MEDIUM` (`#38BDF8`), `LOW` (`#94A3B8`); `[Python]` (`#10B981`), `[LLM]` (`#8B5CF6`), `[Advisor]` (`#6366F1`), `[Human]` (`#14B8A6`).
  - **Typography & Breakpoints:** `Inter`/`Geist` (`14px`) + `JetBrains Mono` (`13px` tabular nums); `4px` spacing grid; `>=1440px` (3-pane IDE), `1024–1439px` (collapsible Copilot), `<768px` (Mobile Approval Inbox PWA).

---

## 4. Engineering, Security & Anti-Tautological Verification Checklist

| Category | Mandatory Standard in `adk-spec` |
| --- | --- |
| **Python 3.14 Language & Toolchain** | Target `Python 3.14` (`requires-python = ">=3.14,<3.15"`, `.python-version = 3.14`, `[tool.uv] exclude-newer = "P3D"`, `hatchling>=1.33.0`); omit `from __future__ import annotations` via native PEP 649/749 (`annotationlib`); use PEP 750 `t-strings` (`string.templatelib.Template`) for safe untrusted data wrapping & TUI escaping; validate via `make ci` (`ruff==0.17.6` with McCabe `<= 10` & `S607`, `pyrefly==1.5.0` with `direct-abstract-base-instantiation = "ignore"`, `import-linter 2.17`, `pytest 9.2.0` with `faulthandler_timeout = 300` & `asyncio_mode = "strict"`). |
| **Architecture & Boundaries** | Strict Hexagonal isolation (`adk_spec.domain` has zero `google.adk` / `google.genai` imports, enforced continuously by `import-linter 2.17`); flat `adk_spec/` package + separate `tui/` `uv` workspace member; every stage wrapped behind a `Protocol` port and frozen Pydantic `2.14.4` DTO (`ConfigDict(frozen=True, extra="forbid")`); `truststore>=0.10.5` injected before HTTP/LLM clients. |
| **Migration Governance** | Every pure/read-only Python candidate validates via guarded `StageRegistry` (`allow_shadow=True` cloned fan-out), `AgentEvaluator` + `ToolArgsMatcher`, and built-in ADK `efficiency_evaluators` (`token_usage_v1`, `inference_call_count_v1`, `invocation_duration_v1`). |
| **Spec & Anti-Tautological Verification** | EARS + RFC 2119 + 4-hash `#### Scenario:` (`<= 500` char cap); `@pytest.mark.spec` traceability + **Hypothesis `6.170.17`** PBT derived from EARS invariants + **`mutmut 3.8.1` (POSIX) / `cosmic-ray 8.9.0` (Windows)** mutation checks in `strict` `verify_converge`. |
| **Scoped Knowledge & Auto-Scaling RAG (Claude Projects Pattern)** | Curated `.spec/knowledge/` pack + selective `knowledge:` allowlist (`1 MiB` cap) pinned in `.spec/.knowledge-lock.json` via explicit manual `adk-spec knowledge sync`; 2-tier Direct Cache → pure-Python BM25/heading `spec_knowledge_search` (~10x capacity across Copilot/Gemini windows) + live Workbench Capacity Meter; transcript-isolated threads; human-gated `[↑ Promote to Knowledge]` (`ASI06`); `(app_name, project_id)` `isolated_memory` wall & Phase 4 `Can view`/`Can edit` RBAC. |
| **Parallelism & Isolation** | Independent active changes and parallel `[P]` tasks execute inside isolated `.worktrees/<change-id>` Git worktrees backed by `LocalEnvironment` (or `E2B`/`Daytona` in cloud). |
| **Stability & Concurrency** | `static_instruction` prefix splitting + `BuiltInPlanner` budgets + `FallbackModel` (429/503) + `ReflectAndRetry{Tool,Model}Plugin`; `RunConfig(max_llm_calls, ToolThreadPoolConfig, StreamingMode.SSE)`; `BufferedSessionService` with explicit `flush_session()` & `close()`. |
| **OWASP Agentic Security (`ASI01`/`02`/`05`/`06`) & Privacy** | Least-privilege `BaseToolset(tool_filter=...)` + path-normalized `PurePosixPath` `WritePolicyPlugin` blocking `Execute` + narrow `append_convergence_tasks`; `ModelArmorPlugin` (`after_tool_callback` screening); `ToolCallIntegrityPlugin` HMAC on agent tool checkpoints; human-approved-only `BaseMemoryService` ingestion; `TelemetryConfig(NO_CONTENT)`; `1 MiB` MCP cap + symlink denial + TUI ANSI sanitization. |
| **Accessibility & Transport UX** | Keyboard-first (`Cmd+K`, `j`/`k`, `a`/`e`/`r`), WCAG 2.2 AA contrast with textual `+`/`-`/`~` diff prefixes, virtualized >500-line diffs, `Last-Event-ID` SSE auto-reconnect with ETag/SHA-256 optimistic concurrency, and `ArtifactService` lazy-loading for large reports. |
| **Dual-Arm LLM Parity (Copilot + Gemini)** | Separate `settings.py` (fast, zero-import) from `models.py`; first-class `SPEC_PROVIDER=copilot\|gemini`; `LiteLlm("github_copilot/...")` with `disable_copilot_system_to_assistant = True`, `_skip_mcp_handler=True`, `_HideBearer` log filter, `adk-spec-login` 15-min OAuth flow, GHE `*.ghe.com` endpoints, and `truststore`; guard `BuiltInPlanner` / `ContextCacheConfig` / `ServiceTier.DEFERRED` / `ModelArmorPlugin` behind `provider == "gemini"`. |
| **Windows & macOS Cross-Platform Parity** | `.gitattributes` (`* text=auto eol=lf`) + LF-normalized SHA-256 fingerprints; reject Windows drives/UNC/DOS reserved names & `os.path.isjunction()`; `sys.stdout.reconfigure(encoding="utf-8", errors="replace")`; `%APPDATA%` vs XDG paths; `ignore_cleanup_errors=True` for Windows AV locks; full-PATH non-CWD binary resolution; `"mutmut>=3.8.1; sys_platform != 'win32'"` + `cosmic-ray>=8.9.0` / WSL; PowerShell `uv run` parity alongside `Makefile`, `.github/copilot-instructions.md`, and 3-OS CI (`windows-latest`, `macos-latest`, `ubuntu-latest`). |
