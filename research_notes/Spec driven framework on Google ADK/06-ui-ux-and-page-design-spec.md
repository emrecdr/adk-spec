# `adk-spec` Workbench — UI / UX & Page Design Specification

This document defines the user experience, interaction architecture, protocol stack, visual design system, and detailed page layouts (Pages 0–9) for the **`adk-spec` Workbench**, replacing the traditional static "chat wall" with a spatial, artifact-first engineering studio backed by **Google ADK 2.0**, **FastAPI + SSE**, **AG-UI 1.0**, and **A2UI**.

---

## 1. Core UX Design Principles

1. **Break the "Chat Wall":** Conversational chat belongs in a collapsible side copilot rail; specifications, deltas, workflow DAGs, ambiguity matrices, task boards, and code diffs deserve spatial, structured panes.
2. **Anti-Approval-Fatigue HITL:** Bare *"Approve / Reject"* prompts invite rubber-stamping. Every review gate MUST surface **contextual side-by-side diffs**, risk badges, and **3-way action controls** (positioning **Reject / Revise** defensively adjacent to or prior to **Approve**):
   - **Revise with Feedback** (send Plannotator inline annotations or change notes back to the paused ADK loop)
   - **Edit Inline** (modify a requirement, scenario, or task directly before resuming)
   - **Approve & Resume** (sign off cleanly)
3. **Quit-Earliest Progressive Review Order (OpenSpec `reviewing-changes.md`):** Present change artifacts in sequential tabs: `1. Proposal (Why/Scope)` → `2. Spec Deltas` → `3. Design & Contracts` → `4. Tasks` so reviewers catch wrong scope at Step 1 before reading 200 lines of tasks.
4. **Execution Provenance Transparency:** Every finding, validation check, and artifact update displays an explicit provenance pill:
   - `[Python Deterministic]` · `[LLM Agent]` · `[Advisor Consulted]` · `[Human Approved]`
5. **Async-First Hibernation & Time-Travel Undo:** Long-running ADK workflows (`ResumabilityConfig(is_resumable=True)`) hibernate across hours or days inside a persistent **Review Inbox** (desktop + mobile PWA), while a **Time-Travel Rewind Scrubber** (`Runner.rewind_async`) lets users safely undo any bad agent turn.
6. **Scoped Knowledge Workspace & Transparent Context Scaling (Claude Projects Pattern):** Multiple parallel `explore` / `assess` / `change` session tabs share one persistent Constitution + `.spec/knowledge/` pack without cross-chat transcript bleed, monitor live token budget via a visible **Knowledge Capacity & Mode Meter** (`Direct Cache` vs. `Indexed RAG`), refresh external repo paths deterministically via an explicit manual **`[↻ Sync Knowledge]`** control, and promote vetted chat outputs back into durable truth via human-gated **`[↑ Promote to Knowledge]`** / **`[→ Seed Proposal]`** actions.

---

## 2. Multi-Surface Architecture & Resilient Transport Protocol

```text
┌─────────────────────────── Client Surfaces ──────────────────────────────┐
│  1. Web Workbench (React/Next.js + @xyflow/react + Plannotator + A2UI)   │
│  2. Mobile Approval Inbox PWA (High-density async triage + deep links)   │
│  3. Built-in Dev Debugger (`adk web`) for Day-1 trace/event inspection   │
│  4. Terminal Dashboard (`adk-spec view` Rich TUI + sanitized text)       │
│  5. IDE Coding Agents via MCP (`to_mcp_server`)                          │
└──────────────────────────┬──────────────────────────┬────────────────────┘
                           │ AG-UI 1.0 (SSE + Last-   │ REST JSON + ETag
                           │ Event-ID Reconnect)      │ Concurrency
                           ▼                          ▼
┌──────────────────────────────────────────────────────────────────────────┐
│   FastAPI ASGI Host (`get_fast_api_app(agents_dir=..., web=False)`)      │
│   + `ag_ui_adk` (`ADKAgent`) + `/api/spec/*` Read-Only Index & Rewind     │
└──────────────────────────────────┬───────────────────────────────────────┘
                                   ▼
┌──────────────────────────────────────────────────────────────────────────┐
│  Google ADK 2.0 `App` (`StreamingMode.SSE`, `ResumabilityConfig`,        │
│  `WritePolicyPlugin`, `ToolCallIntegrityPlugin`, `ModelArmorPlugin`)     │
└──────────────────────────────────────────────────────────────────────────┘
```

### Resilient SSE Auto-Reconnect & Multi-Reviewer Concurrency

- **Typed SSE Envelopes:** Every streamed ADK event carries `event_id` (monotonic sequence), `run_id`, `invocation_id`, `node_id`, and `timestamp`.
- **`Last-Event-ID` Cursor Recovery:** Frontend SSE hooks reconnect automatically using exponential backoff + jitter and send `Last-Event-ID` so missed deltas replay cleanly without duplicate graph renders. If disconnected, active nodes freeze gracefully under a non-blocking `"Stream interrupted — resyncing state..."` banner.
- **Optimistic Concurrency (ETag / SHA-256):** Inline edits in Pages 2, 3, and 8 validate the file's SHA-256/ETag before saving so two reviewers never silently overwrite each other.

### A2UI Trusted Component Catalog (Declarative Generative UI)

Agents emit declarative **A2UI** JSON payloads mapped strictly to vetted host components (zero arbitrary HTML/JS execution):
- `SpecDeltaDiffCard`, `ClarifyQuestionCard`, `AnalysisFindingList`, `ReviewGateCard`, `ToolConfirmationModal`, `ConvergenceSummaryCard`, `AgentDAGNode` (React Flow composite node).

---

## 3. Global Application Shell & Navigation

```text
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│ [adk-spec]  Repo: my-app ▾  Store: local ▾  Change: add-oauth-pkce ▾  [Profile: STANDARD ▾]      │
│  🔍 Cmd+K Search...  [📚 42% Direct]  [↻ Sync (2)]  [⏪ Rewind]  [🔔 Inbox (2)]  [● SSE Synced]  │
├───────────────┬──────────────────────────────────────────────────────────────────────────────────┤
│ 🚀 Onboard    │  (Page 0 — shown when repo has no `.spec/` root)                                 │
│ 🏠 Overview   │                                                                                  │
│ 📝 Change IDE │                                                                                  │
│ 🔔 Reviews (2)│                                ACTIVE PAGE CANVAS                                │
│ ❓ Clarify    │                                                                                  │
│ 🛡️ Analyze    │                                                                                  │
│ ⚙️ Execution  │                                                                                  │
│ 📚 Specs/Map  │                                                                                  │
│ 🔀 Sync/Merge │                                                                                  │
│ 📊 Eval/Ops   │                                                                                  │
└───────────────┴──────────────────────────────────────────────────────────────────────────────────┘
```

*(Shell telemetry pills dynamically reflect knowledge scaling: `[📚 42% Direct]` when injected directly into cached prefix context, automatically transitioning to `[📚 RAG Mode]` above budget with `[↻ Sync (N)]` highlighting manually stale allowlisted repo files.)*

---

## 4. Detailed Page Designs & Wireframes (Pages 0–9)

### Page 0: First-Run Onboarding & Constitution Wizard
- **Trigger:** Shown automatically when a workspace lacks `.spec/` (never initializes silently as a side effect—matches OpenSpec's project check rule).
- **Primary user jobs:** Bootstrap `.spec/` in < 60 seconds without manual boilerplate.
- **Flow:** (1) Read-only repo scan detects language/framework/test runner (`Python 3.14`, `uv`, `pytest`, `FastAPI`), (2) drafts starter `.spec/constitution.md` (`MUST`/`SHOULD` principles) + `.spec/config.yaml` (`context` + `knowledge:` + `rules`), (3) user selects default ceremony profile (`lean` | `standard` | `strict`), (4) `[Initialize .spec/ & Start First Change]` button writes files safely and opens Page 2 or Page 4.

### Page 1: Project Overview & Spec Health Dashboard
- **Primary user jobs:** Monitor overall spec health, resume active changes, spot spec drift, and track LLM → Python migration ROI.
- **UX invariants (from OpenSpec `cli-view`):**
  - Summary KPI strip: Living Specs & Requirements | Draft Changes | Active Changes | Completed Changes (`tasks.total > 0 AND completed === total`, never `0/0`) | Spec Test Coverage %.
  - **Active Changes Table:** Sorted ascending by completion % (`0%` first, alphabetical tie-breaker), displaying decoupled DAG chips (`✓` done, `→` ready, `·` blocked, `(skipped)`).
  - **Drift, Integrity & ROI Panels:** Constitution version, stale base fingerprint alerts, Model Armor block count, and cumulative token savings.

```text
+-------------------------------------------------------------------------------------------------+
| OVERVIEW DASHBOARD                                                           [+ New Change]     |
+---------------------+---------------------+---------------------+-------------------------------+
| Living Specs: 14    | Active Changes: 3   | Spec Test Cov: 84%  | Python Offload: 35% (Wave 1)  |
| Reqs: 68 | Scen: 142| Pending Reviews: 2  | Drift Alerts: 1 ⚠   | Token Savings: -41% vs Phase1 |
+---------------------+---------------------+---------------------+-------------------------------+
| ACTIVE CHANGES (sorted asc by task %)                                                           |
| Change ID           Profile   DAG Status (P · S · D · T)          Tasks       Next Action       |
| ----------------------------------------------------------------------------------------------- |
| fix-token-refresh   lean      [✓ Prop] [✓ Spec] [→ Des] [· Task]   0/6  (0%)  [Open Design ->]  |
| add-oauth-pkce      standard  [✓ Prop] [✓ Spec] [✓ Des] [✓ Task]   4/12 (33%) [Review Gate 🔔]  |
| migrate-billing-v2  strict    [✓ Prop] [✓ Spec] [✓ Des] [✓ Task]  11/14 (79%) [Converge Loop]   |
+-------------------------------------------------------------------------------------------------+
```

### Page 2: Active Change Workbench (3-Pane Split IDE + Spatial DAG + Plannotator)
- **Primary user jobs:** Author, inspect, annotate, and iterate fluidly across `proposal.md`, delta `specs/`, `contracts/`, `design.md`, and `tasks.md` while keeping exploratory side threads isolated from implementation runs.
- **Layout:**
  - **Left Rail (20%):** Visual Artifact DAG (`proposal → specs & design → tasks`), `skip_specs` badge, file tree, Base Fingerprint freshness (`OK` vs `Stale`), and compact **Project Knowledge Pack** meter (`Direct Cache 42%` vs. `Indexed RAG` pill).
  - **Center Canvas (50%):**
    - Toggle between **Document Editor (Rendered EARS / Raw Markdown / Side-by-Side Diff)** and **Spatial Workflow DAG (`@xyflow/react`)** showing live ADK node execution (`idle`, `streaming`, `waiting_approval`, `completed`), token burn badges, animated conditional edges, and inline **Time-Travel Rewind** points (`⏪ Rewind before this turn`).
    - **Plannotator-Style Inline Annotations:** Highlight any line, EARS sentence, or Mermaid diagram block to attach an AST/line-range anchored comment (`"Add expired verifier scenario"`). Queued annotations bundle cleanly into the next ADK turn payload.
  - **Right Copilot & Node Timeline (30%):** Transcript-isolated parallel session tabs (`explore` · `clarify` · `change`) sharing only the workspace Knowledge Pack + live SSE invocation trace + `ModelConsultTool` advisor callouts. Every vetted exploratory artifact card carries human-gated **`[↑ Promote to Knowledge]`** (writes `.spec/knowledge/<slug>.md` via diff preview) and **`[→ Seed Proposal]`** actions.

```text
+--------------------+---------------------------------------------+------------------------------+
| ARTIFACT DAG       | [1.Proposal] [2.Delta Specs*] [🕸 DAG View] | COORDINATOR & LIVE TRACE     |
|                    | Mode: [Rendered+Annotate | Raw | Diff]      |                              |
| ✓ proposal.md      | ------------------------------------------- | ▶ Workflow: sdd_standard     |
| ● specs/auth/      | ## MODIFIED Requirements                    |   ✓ load_project_context     |
|   spec.md (delta)  | ### Requirement: PKCE Token Exchange [REQ-9]|   ✓ propose_agent (task)     |
| ✓ contracts/       | WHEN an OAuth client exchanges a code,      |   ● specify_agent (streaming)|
| ✓ design.md        | the AuthService SHALL verify SHA-256 PKCE.  |     └ Advisor Consult (1/2)  |
| → tasks.md         |  💬 [Line 14 Annotation - @emrec]:          | ---------------------------- |
| 🔒 checklists/     |  │ "Specify 400 error JSON code here."      | Pending Annotations (1):     |
|                    |  └ [Apply Patch to Next Turn]               | • specs/auth/spec.md:L14     |
| Fingerprint: OK    | #### Scenario: Invalid code_verifier        | [Send Turn with Annotations] |
+--------------------+---------------------------------------------+------------------------------+
```

### Page 3: HITL Review Gate, Async Review Inbox & Mobile Approval PWA
- **Primary user jobs:** Clear paused ADK workflow gates (`RequestInput` and `ToolConfirmation`) asynchronously on desktop or mobile without approval fatigue.
- **Desktop Layout:**
  - Left queue lists paused invocations (`interrupt_id`, change, risk tier, elapsed wait time, gate type).
  - Right canvas locks to the **4-Step Quit-Earliest Progressive Stepper** (`1. Proposal → 2. Delta Specs → 3. Design & Contracts → 4. Tasks`) with side-by-side red/green diffs, Plannotator inline comment support, and constitution check status.
  - Bottom sticky action bar places **defensive actions cleanly**: `[↩ Revise with Feedback]` | `[✎ Edit Delta Inline]` | `[✓ Approve & Resume]`. Destructive `ToolConfirmation` drawers display exact args + HMAC `ToolCallIntegrityPlugin` verification shield.
- **Mobile Approval Inbox PWA (`<768px`):**
  - High-density swipe/tap card stack summarizing *What Changed*, *Why*, *Risk Tier*, and expandable line diff, plus deep-link (`Open in Desktop React Flow DAG`) into the exact highlighted graph node.

### Page 4: Clarify & Discovery Studio
- **Primary user jobs:** Resolve `[NEEDS CLARIFICATION]` markers across the 7-dimension ambiguity taxonomy before planning/coding.
- **Layout:** Top 7-dimension coverage matrix (`Clear` / `Partial` / `Missing` pills), stack of `<= 5` interactive `ClarifyQuestionCard`s with rationale & impact trade-offs, and a live right-hand diff preview of exact EARS/Scenario patches before resuming `ClarifyAgent`.

### Page 5: Analysis & Requirements Checklist Console
- **Primary user jobs:** Inspect read-only 6-pass `analyze` audits (`CRITICAL`/`HIGH`/`MEDIUM`/`LOW`), verify executable spec coverage, and manage reviewer-owned checklists.
- **Layout:** Explicit `🔒 WritePolicyPlugin Active: Read-Only Mode` banner; severity/pass filterable findings table (max 50 high-signal) with provenance badges (`[Python Lint]` / `[LLM Semantic]`); **Traceability Matrix** tab (`REQ-ID` ↔ `Entity.field` ↔ `Task T###` ↔ `Hypothesis PBT` / `@pytest.mark.spec` status); and Reviewer Checklist panel locked against agent edits.

### Page 6: Execution & Convergence Monitor (`apply` ↔ `converge`)
- **Primary user jobs:** Monitor vertical-slice tasks, `[P]` parallel workers in isolated `.worktrees/<change-id>`, live test/mutation runs, and convergence loops.
- **Layout:** Toggle between **Vertical-Slice Swimlanes** (`Setup → Foundational → US1..USn → Polish → Phase N: Convergence`) and **Live React Flow Worker Graph**; `[P]` worker cards showing Git worktree path, streaming `pytest` + `mutmut` survivor counts, and retry attempts (`1/3`); Convergence drawer highlighting appended tasks or **`✅ Converged (tasks.md byte-for-byte unchanged)`**.

### Page 7: Living Specs, Knowledge Pack, Contracts & Roadmaps Explorer
- **Primary user jobs:** Browse `.spec/specs/` canonical truth, curate and manually sync the scoped **Project Knowledge Pack** (`.spec/knowledge/` + allowlisted repo files), inspect `contracts/` OpenAPI/Pydantic agreements (including A2A federated Store sources), and navigate epic `roadmap.md` dependency DAGs (`R1..Rn`).
- **Project Knowledge Pack & RBAC Controls (Claude Projects Pattern):**
  - **"Configure Included Files" Picker + Token Budget Bar:** Add/remove selective repo globs (`1 MiB` file cap, skipping lockfiles/build outputs) with per-file token usage, total capacity progress bar (`Direct Cache` vs. automatic `Indexed RAG Mode`), and stale-file count badge + explicit **`[↻ Sync Now]`** button refreshing `.spec/.knowledge-lock.json`.
  - **Isolation & Team Roles:** Per-project **`isolated_memory`** switch (`Strict` defaults ON to block cross-project memory spillover) and Phase 4 workspace role badges (**`Can view`**: inspect + run isolated chats vs. **`Can edit`**: modify constitution, knowledge allowlist & archive approvals; sharing resets on archive).

### Page 8: 3-Way Delta Conflict Resolver & Archive Studio
- **Primary user jobs:** Merge parallel changes into `.spec/specs/` without data loss (`Base SHA-256` | `Live Main Spec` | `Incoming Delta` 3-pane diff3 viewer), optional *"Propose Clean Merge (ConflictResolverAgent)"* button, and pre-archive validation + `ToolConfirmation` modal.

### Page 9: ADK Observability, Eval & Migration Console
- **Primary user jobs:** Govern the **LLM → Python migration** via objective telemetry.
- **Layout:** Strangler-Fig `StageRegistry` matrix (`llm | shadow | hybrid | python`, `shadow` diff parity %, `AgentEvaluator` accuracy, built-in `token_usage_v1` / `inference_call_count_v1` / `invocation_duration_v1` savings, one-click `[Promote to Python]` gated by `>= 99%` parity), `ModelConsultObservabilityPlugin` & `FallbackModel` stats, and **`Privacy Shield: TelemetryConfig(NO_CONTENT)`** status badge.

---

## 5. UX Polish, Accessibility & Terminal Hygiene Standards

- **Keyboard-first navigation:** `Cmd+K` command palette, `j`/`k` item triage, `a` / `e` / `r` review actions (guarded against accidental key-repeat submits).
- **Accessibility (WCAG 2.2 AA):** Semantic regions, high-contrast colorblind-safe diffs (`+`/`-`/`~` textual markers alongside color), focus-trapped `ToolConfirmation` modals, and `aria-live="polite"` SSE progress announcements.
- **Large diff performance:** Virtualized diff panes (>500 lines) and `ArtifactService` lazy-loaded evidence drawers (>64KB).
- **TUI (`adk-spec view`) hygiene:** Escape/strip all ANSI/VT control sequences from user/schema/error text before terminal rendering; support clean `--json` for CI scripts.

---

## 6. Visual Design System & Token Specification

| Token Group | Specification |
| --- | --- |
| **Themes** | Dark-first IDE palette (`#0B0F17` canvas, `#121826` elevated pane, `#1F2937` hairline borders) + accessible Light mode |
| **Severity Tokens** | `CRITICAL` (`#EF4444` crimson), `HIGH` (`#F59E0B` amber), `MEDIUM` (`#38BDF8` sky), `LOW` (`#94A3B8` slate) |
| **Provenance Pills** | `[Python]` (`#10B981` emerald), `[LLM]` (`#8B5CF6` violet), `[Advisor]` (`#6366F1` indigo), `[Human]` (`#14B8A6` teal) |
| **Typography** | UI prose: `Inter` / `Geist` (`14px` base, `1.5` line-height); Code, EARS IDs, diffs & hashes: `JetBrains Mono` (`13px`, tabular nums) |
| **Spacing & Radii** | Strict `4px` spacing grid (`4/8/12/16/24/32px`); `8px` card radii, `6px` badges, `12px` modals |
| **Responsive Breakpoints** | `>= 1440px`: 3-pane Change IDE; `1024–1439px`: 2-pane + collapsible Copilot drawer; `< 768px`: Mobile Approval Inbox PWA |
