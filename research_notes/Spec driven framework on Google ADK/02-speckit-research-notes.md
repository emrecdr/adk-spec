# GitHub Spec Kit (`github/spec-kit`) — Deep Research Notes

- **Sources verified:** [`github/spec-kit`](https://github.com/github/spec-kit) (`main` branch: `README.md`, `docs/overview/{core,mcp}.md`, `docs/reference/agentic-sdd.md`, `docs/workflows/{overview,overlays}.md`, `docs/presets/overview.md`, `docs/extensions/overview.md`, `docs/guides/agentic-sdlc.md`, `docs/how-to/{evolving-specs,contract-driven-development,spec-of-specs}.md`, `templates/{constitution,spec,plan,tasks}-template.md`, `templates/commands/{clarify,analyze,converge}.md`, `workflows/speckit/workflow.yml`, `presets/lean/preset.yml`, `extensions/assess/extension.yml`), plus [github.github.io/spec-kit](https://github.github.io/spec-kit/).

---

## 1. Core Philosophy & Multi-Process Architecture

GitHub Spec Kit (`specify-cli`, Python/`uv`) frames Spec-Driven Development as an engineering discipline with explicit governance, structured artifact pipelines, and composable process packs.

Crucially, Spec Kit recognizes that **not every engineering activity is a greenfield feature**. It separates entry points into independent processes:

| Process | Lifecycle Stages | Terminal Outcomes / Verdicts |
| --- | --- | --- |
| **Core SDD** | `constitution` → `specify` → `clarify` → `plan` → `checklist` → `tasks` → `analyze` → `implement` ↔ `converge` | `Converged` (byte-for-byte unchanged `tasks.md`) |
| **Bug Fixing (`bug` ext.)** | `bug-assess` → `bug-fix` → `bug-test` (stored in `.specify/bugs/<slug>/`) | `verified` \| `partial` \| `failed` |
| **Idea Assessment (`assess` ext.)** | `assess-intake` → `assess-research` → `assess-define` → `assess-shape` → `assess-decide` (`.specify/assessments/<slug>/`) | `go` (hands `decision.md` to `specify`) \| `needs-clarification` \| `kill` |

### Human vs. Agent vs. Regular Automation Authority Model (`docs/guides/agentic-sdlc.md`)

Spec Kit explicitly separates three distinct authority layers across the SDLC so AI automation never blurs accountability:
1. **Regular Automation (Deterministic Scripts/CI):** Rule-based checks, builds, linters, and publishers—never interpret intent or pick designs.
2. **Agent Automation (LLM Workflows):** Interpret context, draft assessments/specs, propose code, and generate reports. Spec Kit warns explicitly: *"Running an agent on GitHub Actions does not make its reasoning a deterministic script."*
3. **Human Work (Decision Authority):** Frame intent, resolve trade-offs, initiate workflows, approve specs/plans, and decide what merges.

---

## 2. Project Governance & Requirements Rigor

### The Constitution (`.specify/memory/constitution.md`)

Established once per project and versioned (`Version | Ratified | Last Amended`), the constitution encodes non-negotiable engineering axioms (`MUST`/`SHOULD`)—such as library-first boundaries, TDD mandates, security constraints, observability standards, and simplicity/YAGNI rules.
- Every downstream command (`specify`, `plan`, `analyze`, `converge`) treats the constitution as **supreme authority**.
- A violation of a constitutional `MUST` rule is automatically graded `CRITICAL` during analysis and convergence.

### Feature Spec Structure (`templates/spec-template.md`)

Spec Kit focuses `spec.md` strictly on *What* and *Why* (product behavior, zero stack assumptions) with strong structural conventions:
1. **Prioritized, Independently Testable User Stories (`P1`, `P2`, `P3`):** Each story defines *Why this priority*, *Independent Test* (viable MVP slice), and `Given`/`When`/`Then` Acceptance Scenarios.
2. **Edge Cases:** Boundary conditions and error scenarios explicitly surfaced early.
3. **Functional Requirements (`FR-###`):** Numbered `MUST` statements with explicit inline ambiguity markers (`[NEEDS CLARIFICATION: ...]`).
4. **Buildable Success Criteria (`SC-###`):** Measurable technical criteria—explicitly excluding post-launch business KPIs (e.g., *"reduce support tickets by 50%"*) during analysis so implementation tasks stay actionable.

### Structured Ambiguity Interrogation (`templates/commands/clarify.md`)

Before technical planning, `/speckit.clarify` audits `spec.md` across a **7-category coverage taxonomy**, internally scoring every item `Clear`, `Partial`, or `Missing`:
1. Functional Scope & Behavior (goals, explicit out-of-scope, personas)
2. Domain & Data Model (entities, identity/uniqueness, state transitions, scale)
3. Interaction & UX Flow (critical journeys, empty/loading/error states, a11y/l10n)
4. Non-Functional Quality Attributes (latency/throughput, scalability, reliability, observability, security/privacy, compliance)
5. Integration & External Dependencies (external APIs, failure modes, formats, versioning)
6. Edge Cases & Failure Handling (negative cases, rate limiting, concurrent edit conflicts)
7. Constraints & Tradeoffs (stack constraints, explicit compromises)

It asks **at most 5 high-impact targeted clarification questions** and encodes the user's answers directly back into `spec.md`.

---

## 3. Execution Blueprinting, Contracts & Spec-of-Specs

### Technical Blueprint (`plan.md`, `research.md`, `data-model.md`, `contracts/`)

`/speckit.plan` separates technical execution from product intent by declaring `Language/Version`, `Primary Dependencies`, `Storage`, `Testing`, `Target Platform`, `Performance Goals`, `Constraints`, and `Scale/Scope`—checking all choices against the Constitution before decomposing work.

### Contract-Driven Development (`docs/how-to/contract-driven-development.md`)

For external interfaces (APIs, events, libraries, CLIs, shared files), Spec Kit introduces an explicit **contract layer** between behavioral specs and internal design:
- Defines accepted inputs/outputs, validation rules, error semantics, **interaction guarantees** (idempotency, ordering, retries, timeouts), versioning, and deprecation policy.
- Enforces **one authoritative owner** per contract (same repo: direct reference; cross-repo: pinned immutable version/digest, read-only for consumers).
- Tasks explicitly include both provider and consumer contract tests (including negative cases).

### Complex Feature Escalation Ladder & Spec-of-Specs (`docs/how-to/spec-of-specs.md`)

Spec Kit warns against premature decomposition overhead and prescribes a 3-step escalation ladder for large features:
1. **Scoped execution:** Limit `/speckit.implement` invocations to one phase/story at a time.
2. **Sub-agent delegation:** Delegate bounded slices within the same spec.
3. **Spec-of-Specs (`roadmap.md`):** Use only when even a single phase exceeds the context window. Run one shallow decomposition pass producing a durable `roadmap.md` with columns:
   - `ID` (`R1`, `R2`, `R3` — immutable traceability anchors) | `Sub-feature` | `Intent` | `Scope boundary` (`in / deferred`) | `Depends on` | `Status` (`planned · in-progress · done`) | `Sub-spec` path.
   - Run independent slices concurrently using separate **Git worktrees** and link each sub-spec bidirectionally back to its `R#` ID.

### Vertically Sliced, Parallel-Annotated Tasks (`templates/tasks-template.md`)

`tasks.md` organizes implementation into phased, independently verifiable slices:
- **Phase 1: Setup** (shared project skeleton)
- **Phase 2: Foundational** (blocking prerequisites—no user story starts until complete)
- **Phase 3..N: User Story 1 (`[US1]` 🎯 MVP), User Story 2 (`[US2]`), ...** (optional test-first block + models/services/endpoints + story checkpoint)
- **Final Phase: Polish** (cross-cutting hardening)
- Every task line carries a stable ID (`T001`), optional parallel marker (`[P]`), story label (`[US1]`), and concrete file path.

---

## 4. Three Strict-Contract Quality Gates

Spec Kit cleanly separates quality verification into three distinct tools with **non-overlapping write permissions**:

| Gate | Write Contract | Core Responsibility |
| --- | --- | --- |
| **`checklist`** | **Reviewer-owned** (implementer read-only) | "Unit tests for requirements"—verifies spec completeness, clarity, and edge-case coverage. `/speckit.implement` reads `[x]`/`[ ]` counts as a gate, warns on unchecked items, and **must never** silently flip checkboxes. |
| **`analyze`** | **Strictly read-only** (zero file writes) | Cross-artifact audit (`constitution`, `spec`, `plan`, `data-model`, `tasks`). Caps output at **50 high-signal findings** across **6 detection passes** (Duplication, Ambiguity, Underspecification, Constitution Alignment, Coverage Gaps including strict `data-model.md` + `Entity.field` citations, Inconsistency) graded `CRITICAL` / `HIGH` / `MEDIUM` / `LOW`. |
| **`converge`** | **Strictly append-only** (writes only new `## Phase N: Convergence` items to `tasks.md`) | Runs after `implement`. Never edits code, `spec.md`, `plan.md`, or existing tasks. Leaves `tasks.md` **byte-for-byte unchanged** if satisfied (`Converged`), or appends traceable remediation tasks so `implement ↔ converge` repeats until converged. |

---

## 5. Composable Customization, Workflows, Overlays & MCP Guardrails

- **Presets (`presets/lean/preset.yml`, etc.):** Stackable, priority-ordered overrides that replace templates or commands (e.g., the `lean` preset strips Spec Kit down to `constitution → specify → plan → tasks → implement` for rapid iteration without forking core).
- **Extensions & Hooks (`extensions/`):** Add commands, skills, and `before_*` / `after_*` lifecycle hooks via `.specify/extensions.yml`.
- **Declarative Workflows & Overlays (`workflows/speckit/workflow.yml`, `docs/workflows/overlays.md`):**
  - `workflow.yml` chains commands, shell steps, and **resumable human review gates** (`review-spec`, `review-plan`) backed by verdict inputs (`speckit_review_spec_verdict=approve|reject`) and persisted run IDs.
  - **Overlays** customize installed workflows non-destructively using `insert_after`, `insert_before`, `replace`, and `remove` edits with **lower-wins** integer `priority` precedence.
- **Hardened MCP Server Patterns (`docs/overview/mcp.md`):**
  - Read-only local surface (`specify mcp` over stdio) using `FileHelper` to reject symlinks/junctions at read boundaries, capping responses at `1 MiB` (`response_too_large`), bounding pages at `<= 1000` items, and returning sanitized structured errors (`code`, `message`, `details`, `retryable`).

---

## 6. Documented Limitations

From `docs/how-to/evolving-specs.md`, `templates/commands/clarify.md`, and `README.md`:
1. **No Unified Living Spec / Delta Model:** Specs are organized per feature (`specs/###-feature-name/`, often gitignored after delivery). Core has no built-in delta merge (`ADDED`/`MODIFIED`/`REMOVED`) into a canonical system truth or automatic cross-artifact reconciliation.
2. **High Default Ceremony:** Full path (`constitution → specify → clarify → plan → checklist → tasks → analyze → implement → converge`) creates heavy Markdown overhead for minor brownfield edits unless overridden via `lean` preset.
3. **Prompt-Fragile Extension Hooks:** Pre-execution hook blocks in command templates rely on the LLM reading `.specify/extensions.yml`, filtering `enabled`/`condition` rules in natural language, and remembering to execute mandatory hooks before proceeding.

---

## 7. Spec Kit Strengths & Gaps Summary

| Dimension | Strengths to Adopt | Gaps / Weaknesses to Fix |
| --- | --- | --- |
| **Governance** | Immutable `constitution.md` authority + `CRITICAL` enforcement; clear Human/Agent/Script boundary | No lightweight `config.yaml` operation guidance split |
| **Requirements** | 7-dimension `clarify` taxonomy (≤ 5 Qs); `[NEEDS CLARIFICATION]`; `contracts/`; escalation ladder & `roadmap.md` | Feature-directory fragmentation; no living canonical `specs/` + delta merge |
| **Planning & Tasks** | Vertical user-story slices (`[US#]`), `[P]` parallel markers, Setup/Foundational phases, checkpoints | Overweight for tiny changes unless a `lean` profile is selected |
| **Quality Gates** | Distinct read-only `analyze` (6 passes), reviewer-owned `checklist`, append-only `converge` loop | `analyze` & `converge` are pure LLM prompt runs (expensive/non-deterministic for structural checks) |
| **Extensibility & Safety** | Stackable `Presets`, non-destructive `Overlays` (`insert_after`/`replace`/`remove`), MCP `1 MiB`/symlink hardening, multi-process (`assess`, `bugfix`) | Hooks enforced via Markdown prompts rather than runtime code |
