# Comparative Analysis: OpenSpec vs. GitHub Spec Kit & Synthesis for Google ADK 2.0

- **Companion reports:** [02-adk-spec-framework-architecture-and-roadmap.md](02-adk-spec-framework-architecture-and-roadmap.md) · [03-ui-ux-workbench-and-engineering-standards.md](03-ui-ux-workbench-and-engineering-standards.md)

## Executive Summary

**OpenSpec** (`Fission-AI/OpenSpec` `2.1.1`) and **GitHub Spec Kit** (`github/spec-kit` `v1.4.3`) converge on the same core premise—specifications should serve as the version-controlled source of truth between humans and AI agents—but solve different halves of the software engineering lifecycle:

- **OpenSpec** excels at **living system truth, brownfield delta iteration, and review ergonomics**. Its separation of canonical `specs/` from isolated `changes/`, explicit delta operators (`ADDED` / `MODIFIED` / `REMOVED` / `RENAMED`), declarative `schema.yaml` artifact DAG, quit-earliest review cadence (`docs/reviewing-changes.md`), `cli-view` dashboard invariants, and thorough removal/rename verification make it ideal for evolving real codebases continuously.
- **GitHub Spec Kit** excels at **engineering governance, requirements hygiene, and multi-stage quality gates**. Its immutable `constitution.md`, Human/Agent/Script authority separation (`docs/guides/agentic-sdlc.md`), 7-dimension `clarify` ambiguity scan, read-only 6-pass `analyze` audit, reviewer-owned `checklist` gate, vertical-slice `tasks.md` format, append-only `converge` loop, and composable presets/workflows/overlays deliver unmatched rigor for complex features.

Neither framework alone is complete. Both suffer from **prompt-fragile runtime enforcement**, "chat-wall" UX gaps, indirect prompt-injection exposure, and single-model cost/reliability assumptions, while OpenSpec documents an unresolved **parallel delta data-loss bug** (`openspec-parallel-merge-plan.md`) and Spec Kit lacks a unified living-spec / delta-merge model (`docs/how-to/evolving-specs.md`). Building a synthesized framework natively on **Python 3.14** + **Google ADK 2.0 (`google-adk` `2.15.0`)**—enriched with 2025–2026 industry patterns (**EARS** syntax, **executable specs + Hypothesis PBT + mutation testing**, **OWASP Agentic Security defenses**, **Git worktrees**, and **AG-UI / A2UI + React Flow** workbenches)—resolves these blind spots while enabling an **LLM-first → iterative Python migration** path.

---

## Broader 2025–2026 SDD Maturity Context

| SDD Maturity Level | Core Model | Representatives | Position of `adk-spec` |
| --- | --- | --- | --- |
| **Level 1: Spec-First** | Ad-hoc prompt PRD before coding; specs go stale immediately | Raw Cursor / Claude chats | Superseded |
| **Level 2: Spec-Anchored** | Living repo specs evolved alongside PRs & tasks | **OpenSpec**, **Spec Kit**, **AWS Kiro** | Core foundation (living `specs/` + deltas + EARS) |
| **Level 3: Spec-As-Source** | Specs compile into code & tests; code is derived output | **Tessl** | Selective Level 3 compilation (`contracts/`, Pydantic schemas, `@pytest.mark.spec` + Hypothesis PBT, `import-linter`, drift checks) |

Compared to **AWS Kiro** (famous for **EARS** requirement patterns), **BMAD** (role-separated agile personas), **Tessl** (executable guardrails), and **Claude Projects** (`9517075`, persistent Knowledge Packs, automatic Direct-to-RAG context scaling, selective manual sync, and isolated parallel threads), `adk-spec` adopts **EARS + RFC 2119 + 4-hash BDD scenarios**, adds a **2-tier Direct Cache → pure-Python `spec_knowledge_search` loader**, maps specialist roles onto **ADK `LlmAgent` modes (`chat`, `task`, `single_turn`)**, and isolates parallel work via **Git worktrees**.

---

## Head-to-Head Architectural Comparison

| Dimension | OpenSpec (`Fission-AI/OpenSpec` `2.1.1`) | GitHub Spec Kit (`github/spec-kit` `v1.4.3`) |
| --- | --- | --- |
| **Core Philosophy** | Fluid, iterative, brownfield-first; *actions, not phase gates* (`docs/concepts.md`) | Structured engineering rigor, constitution-governed quality gates (`docs/overview/core.md`) |
| **Runtime & Ecosystem** | TypeScript / Node.js CLI (`@fission-ai/openspec`) + 30+ tool skill adapters | Python CLI (`specify-cli` via `uv`/`pipx`) + agent integrations, presets, bundles |
| **Repository Layout** | Living `openspec/specs/<cap>/spec.md` + isolated `openspec/changes/<id>/` + `archive/` | Feature-scoped `.specify/` + `specs/###-feature-name/` (often gitignored after delivery) |
| **Brownfield vs. Greenfield** | **Brownfield-native:** explicit `ADDED`/`MODIFIED`/`REMOVED`/`RENAMED` deltas + `skip_specs: true` | **Greenfield-strong:** full feature specs per directory; manual reconciliation for evolving specs |
| **Workflow & Authority Model** | Declarative `schema.yaml` DAG (`ArtifactGraph`: `proposal → specs & design → tasks`) | Core SDD + YAML `workflow.yml` + `overlays` + explicit Human/Agent/Regular Automation boundary (`agentic-sdlc.md`) |
| **Process Scope** | Single SDD + `explore` + `onboard` | Multi-process: Core SDD + `assess` (`go`/`needs-clarification`/`kill`) + `bug` (`verified`/`partial`/`failed`) |
| **Governance & Config** | `config.yaml` cleanly splits `context`, `rules.<artifact>`, and `operations.*.guidance` | Versioned `.specify/memory/constitution.md` (`MUST`/`SHOULD` invariants = supreme authority) |
| **Ambiguity Resolution** | Ad-hoc via `openspec-explore` and `Open Questions` in `design.md` | Structured `/speckit.clarify` 7-dimension taxonomy (`Clear`/`Partial`/`Missing`, ≤ 5 targeted questions) |
| **Task Structure** | Grouped checkboxes (`- [ ] 1.1 ...`) with inline verification criteria | Phased (`Setup → Foundational → US1..USn → Polish`) with `T001`, `[P]` parallel, `[US1]` story tags |
| **Quality Gates** | `openspec validate --strict` + `verify-change` (checks `REMOVED` via `git log` & `RENAMED` invariance) | Three distinct gates: reviewer `checklist` + read-only 6-pass `analyze` + append-only `converge` loop |
| **Review UX & Dashboards** | Quit-earliest reading order (`reviewing-changes.md`); `cli-view` dashboard invariants (`0/0` guard, ANSI sanitization) | Resumable CLI workflow gates (`review-spec`, `review-plan`) + command handoffs |
| **Customization** | Custom `schema.yaml` + templates + `core`/expanded profiles | Stackable priority-ordered `presets` (e.g., `lean`) + `extensions` + `overlays` (`insert_after`, `replace`, `remove`) |
| **Multi-Repo / Scale** | **Stores (beta):** standalone Git planning repo (`--store <id>`) shared across repos | **Escalation ladder + Spec-of-Specs:** scoped `implement` → sub-agents → shallow `roadmap.md` (`R1..Rn`) + `contracts/` |
| **Machine Contract** | Standardized `--json` envelopes, exit codes (`0`/`1`/`130`), diagnostic code catalog (`docs/agent-contract.md`) | Read-only experimental `specify mcp` over stdio with `FileHelper` symlink/junction checks and `1 MiB` response cap |
| **Documented Failure Modes** | `buildUpdatedSpec` replace-only block substitution silently drops concurrent scenarios (`openspec-parallel-merge-plan.md`) | No built-in delta merge/reconciliation; extension hooks and write boundaries enforced via LLM Markdown prompts |

---

## Best Parts Harvested from Each Framework

### Harvested from OpenSpec

1. **Living `specs/` Truth + Isolated `changes/` + Timestamped `archive/`** (`docs/concepts.md`): Eliminates feature-directory drift and keeps parallel active changes isolated without context collision.
2. **Explicit Delta Operators & `skip_specs: true`** (`schemas/spec-driven/schema.yaml`): `ADDED` / `MODIFIED` / `REMOVED` (`Reason` + `Migration`) / `RENAMED` (`FROM:` / `TO:`) keep brownfield context surgical; `skip_specs: true` prevents agents from inventing fake requirements during pure refactors.
3. **Behavior-Only Boundary & Strict Scenario Grammar** (`schemas/spec-driven/schema.yaml`): RFC 2119 (`MUST`/`SHALL`) + 4-hash `#### Scenario:` (`GIVEN`/`WHEN`/`THEN`) + `<= 500` char requirement cap keeps specs testable and free of implementation leakage.
4. **Declarative Artifact DAG + 3-Way Config Split** (`src/core/artifact-graph/graph.ts`, `docs/customization.md`): Declaration-order tie-breaking (`proposal → specs → design → tasks`) and strict separation of global `context`, per-artifact `rules`, and advisory `operations.*.guidance`.
5. **Deep Verification for Removals & Renames** (`skills/openspec-verify-change/SKILL.md`): Never trusting empty baselines and explicitly checking `git log` to prove `REMOVED` code paths are truly gone and `RENAMED` behaviors survived intact.
6. **Review Ergonomics, `cli-view` Invariants, `Stores`, & `--json` Contract** (`docs/reviewing-changes.md`, `openspec/specs/cli-view/spec.md`, `docs/stores-beta/user-guide.md`, `docs/agent-contract.md`): Quit-earliest review progression, strict `tasks.total > 0` completion filter, ANSI sanitization, and multi-repo Stores.

### Harvested from GitHub Spec Kit

1. **Versioned Project `constitution.md` + Authority Boundaries** (`templates/constitution-template.md`, `docs/guides/agentic-sdlc.md`): Establishes immutable project axioms (`MUST`/`SHOULD`) where violations escalate as `CRITICAL`, alongside clear separation of deterministic scripts, LLM agents, and human approvals.
2. **7-Dimension `clarify` Ambiguity Scan (≤ 5 Questions)** (`templates/commands/clarify.md`): Prevents silent guessing across Functional Scope, Data Model, UX, NFRs, Integrations, Edge Cases, and Constraints.
3. **Three Separated Quality Gates (`checklist`, `analyze`, `converge`)** (`templates/commands/{analyze,converge}.md`, `docs/reference/agentic-sdd.md`): Reviewer-owned `checklist`, strictly read-only 6-pass `analyze` (strict `Entity.field` coverage rules), and strictly append-only `converge` (`## Phase N: Convergence` or byte-for-byte unchanged `Converged`).
4. **Execution-Ready `tasks.md`** (`templates/tasks-template.md`): `Setup → Foundational → Vertical User Stories (MVP first) → Polish` with `T###`, `[P]` parallelism, and `[US#]` traceability.
5. **Multi-Process Entry Points + Escalation Ladder (`contracts/`, `roadmap.md`)** (`extensions/assess/extension.yml`, `docs/how-to/{contract-driven-development,spec-of-specs}.md`): Dedicated `assess` and `bugfix` pipelines plus explicit external interface contracts and shallow `roadmap.md` epic decomposition.
6. **Stackable Presets (`lean` vs. strict), Workflow Overlays, & MCP Security Hardening** (`presets/lean/preset.yml`, `docs/workflows/overlays.md`, `docs/overview/mcp.md`).

---

## Shared Blind Spots Solved by Google ADK 2.0 + Modern Industry Stack

| Shared Blind Spot in OpenSpec & Spec Kit | How Native Google ADK 2.0 (`v2.15.0`) + Modern Patterns Solve It |
| --- | --- |
| **Prompt-only enforcement** (asking LLMs in Markdown not to edit files in `analyze`, not to flip `checklist` boxes, or to run hooks) | **Least-Privilege `tool_filter` + Hardened `WritePolicyPlugin`:** Strips mutating tools at `BaseToolset` declaration and enforces normalized `PurePosixPath` + `Execute` locks in `before_tool_callback`. |
| **Indirect prompt injection & OWASP `ASI01`/`ASI02`/`ASI05`/`ASI06`** | **`ModelArmorPlugin` + Sandboxed `EnvironmentToolset` + Memory Quarantine:** Screens `after_tool_callback` outputs against prompt injection, runs untrusted builds in `E2B`/`Daytona`, and indexes only human-approved archived specs into `BaseMemoryService`. |
| **Parallel delta silent data loss** (OpenSpec's replace-only `buildUpdatedSpec`) | **Fingerprint-Guarded 3-Way Merge Engine:** Captures SHA-256 requirement baselines in `.change.yaml`, runs deterministic diff3 merge in `@node`, and invokes `ConflictResolverAgent` + `ToolConfirmation` only on genuine collisions. |
| **Ambiguous prose & shallow/tautological AI tests + architectural drift** | **EARS + `@pytest.mark.spec` + `Hypothesis` PBT + `mutmut` + `import-linter`:** Converts EARS invariants into property tests, catches weak assertions via mutation testing in `converge`, and locks Hexagonal/constitutional layer boundaries mechanically. |
| **Parallel agent working-tree collisions** | **Git Worktree Isolation + `parallel_worker=True`:** Dedicated `.worktrees/<change-id>` workspaces prevent branch/index races across concurrent agents. |
| **Monolithic model cost, rate limits & flakiness** | **`static_instruction` + `BuiltInPlanner` + `FallbackModel` + `ModelConsultTool` + `ServiceTier.DEFERRED`:** Maximizes Gemini prefix cache hits, tunes per-stage thinking budgets, auto-fails over 429/503s, and offloads batch CI drift runs to deferred capacity. |
| **Telemetry privacy leaks & tampered HITL state** | **`TelemetryConfig(NO_CONTENT)` + `ToolCallIntegrityPlugin`:** Disables ADK's default prompt-to-span capture (`ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=True`) and HMAC-SHA256 stamps stored agent tool calls across HITL pauses. |
| **Chat-wall UX fatigue & irreversible bad turns** | **AG-UI + A2UI + React Flow DAG + Plannotator + `Runner.rewind_async`:** Replaces raw chat dumps with spatial DAGs, inline AST-anchored review comments, `Last-Event-ID` SSE reconnect, Mobile Approval Inbox PWA, and time-travel session rewind. |
| **Irreconciled cross-team silos** | **`to_a2a` / `RemoteA2aAgent` + `Stores`:** Publishes platform living specs and contracts over A2A JSON-RPC + Agent Cards without monorepo lock-in. |
| **No objective verification when replacing prompts with code** | **Guarded `StageRegistry` + `AgentEvaluator` + Built-In `efficiency_evaluators` + `ToolArgsMatcher`:** Proves output parity via `shadow` mode on pure stages and gates cutovers on `token_usage_v1` / `inference_call_count_v1` / `invocation_duration_v1` gains. |

---

## Granular Research Notes

- [01-openspec-research-notes.md](../research_notes/Spec%20driven%20framework%20on%20Google%20ADK/01-openspec-research-notes.md) — OpenSpec architecture, OPSX DAG, delta rules, Stores, verification/archive contracts, review UX & `cli-view`, parallel merge failure analysis.
- [02-speckit-research-notes.md](../research_notes/Spec%20driven%20framework%20on%20Google%20ADK/02-speckit-research-notes.md) — Spec Kit constitution, Human/Agent/Script authority, multi-process workflows, clarify/analyze/converge contracts, presets/overlays, contracts, spec-of-specs, and MCP hardening.
- [03-google-adk-v2-best-practices.md](../research_notes/Spec%20driven%20framework%20on%20Google%20ADK/03-google-adk-v2-best-practices.md) — Verified ADK `v2.15.0` imports, 10 workflow validation rules, `@node`/`JoinNode` gotchas, `static_instruction`, `BuiltInPlanner`, `EnvironmentToolset` + `tool_filter`, `ModelArmorPlugin`, `Runner.rewind_async`, built-in `efficiency_evaluators`, `ToolArgsMatcher`, and `to_a2a`.
- [04-validation-audit-and-improvement-options.md](../research_notes/Spec%20driven%20framework%20on%20Google%20ADK/04-validation-audit-and-improvement-options.md) — Six-pass validation audit log (including red-team code fixes, Python 3.14/`uv`, Copilot+Gemini/Windows parity & Claude Projects benchmark) + 24 architectural, security, verification, coding, context-scaling, and UX improvements.
- [05-modern-sdd-standards-and-architecture-patterns.md](../research_notes/Spec%20driven%20framework%20on%20Google%20ADK/05-modern-sdd-standards-and-architecture-patterns.md) — SDD Maturity Spectrum, Claude Projects + Kiro/BMAD/Tessl synthesis, EARS + BDD grammar, executable traceability, 7 context-engineering pillars (including 2-tier auto-scaling RAG & pinned sync), Hexagonal + guarded Strangler-Fig architecture, Git worktrees, `Hypothesis` + `mutmut`/`cosmic-ray` + `import-linter`, Windows/macOS parity, and OWASP Agentic Security posture.
- [06-ui-ux-and-page-design-spec.md](../research_notes/Spec%20driven%20framework%20on%20Google%20ADK/06-ui-ux-and-page-design-spec.md) — Complete 10-view (Pages 0–9) AG-UI/A2UI Workbench, React Flow DAG, Plannotator inline annotations, Mobile Approval Inbox PWA, Time-Travel Rewind scrubber, design tokens, and TUI spec.
