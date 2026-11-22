# OpenSpec (`Fission-AI/OpenSpec`) — Deep Research Notes

- **Sources verified:** [`Fission-AI/OpenSpec`](https://github.com/Fission-AI/OpenSpec) (`main` branch: `README.md`, `docs/concepts.md`, `docs/opsx.md`, `docs/customization.md`, `docs/agent-contract.md`, `docs/reviewing-changes.md`, `docs/stores-beta/user-guide.md`, `schemas/spec-driven/schema.yaml`, `schemas/spec-driven/templates/*`, `openspec/specs/cli-view/spec.md`, `src/core/artifact-graph/{graph.ts,types.ts}`, `skills/openspec-{verify-change,archive-change,sync-specs}/SKILL.md`, `openspec-parallel-merge-plan.md`), plus [openspec.dev](https://openspec.dev/).

---

## 1. Core Philosophy & Design Thesis

OpenSpec is a TypeScript/Node.js (`@fission-ai/openspec`) spec-driven development (SDD) framework designed around **brownfield iteration** and **low-friction human–AI alignment**:

```text
fluid not rigid         — actions, not waterfall phase gates; edit any artifact anytime
iterative not waterfall — learn as you build and refine specs continuously
easy not complex        — lightweight Markdown + minimal setup overhead
brownfield-first        — model deltas against existing behavior, not full rewrites
scalable                — personal single-repo projects up to multi-repo team Stores
```

Rather than locking engineers into linear phase gates, OpenSpec models **dependencies as enablers**: once an upstream artifact exists, downstream artifacts unlock, while upstream artifacts can still be updated mid-flight.

---

## 2. Directory & Living-Truth Architecture

OpenSpec cleanly separates **what is true today** from **what is proposed in-flight** and **what is archived for history**:

```text
openspec/
├── config.yaml                      # Default schema, project context, per-artifact rules, operation guidance
├── specs/                           # Living source of truth (current system behavior)
│   └── <capability-path>/
│       └── spec.md                  # Domain-organized (e.g., auth/, identity/user-auth/, payments/)
└── changes/                         # Parallel-safe isolated change workspaces
    ├── <change-id>/
    │   ├── .openspec.yaml           # Change metadata (schema override, optional skip_specs: true)
    │   ├── proposal.md              # Why, What Changes, New/Modified Capabilities, Impact
    │   ├── specs/<capability>/spec.md  # Delta spec (ADDED / MODIFIED / REMOVED / RENAMED)
    │   ├── design.md                # How: technical decisions, trade-offs, migration plan
    │   └── tasks.md                 # Tracked checkbox implementation checklist (- [ ] 1.1 ...)
    └── archive/
        └── YYYY-MM-DD-<change-id>/  # Immutable completed record after delta sync
```

### Multi-Repo Planning via Stores (Beta)

For changes spanning multiple repositories or platform teams owning shared contracts (`docs/stores-beta/user-guide.md`), OpenSpec supports **Stores**—standalone Git planning repositories registered once locally:

```text
team-plans/
├── .openspec-store/store.yaml       # Store identity ("I am team-plans")
└── openspec/
    ├── specs/
    └── changes/
```

Two explicit design rules govern Stores:
1. **A store is just a Git repo** — OpenSpec never silently clones, pulls, or pushes; teams commit and review it via standard Git workflows.
2. **Declarations, not hidden machinery** — code repos may declare relationships to stores, changing visibility/diagnostics, while commands act cleanly on `--store <id>` (resolving `planningHome.root`).

---

## 3. Specification Format & Delta Operators

### Observable Behavior Contract

From `schemas/spec-driven/schema.yaml` and `docs/concepts.md`:
- Specs define **externally observable behavior** using RFC 2119 keywords (`MUST`, `SHALL`, `SHOULD`) and testable scenarios.
- **Boundary heuristic:** *"If the implementation can change without changing externally visible behavior, it likely does not belong in the spec."* Internal class names, framework choices, and file layouts belong in `design.md` or `tasks.md`.
- **Strict structural rules enforced by `openspec validate` (`--strict`):**
  - Requirements use `### Requirement: <name>` with description capped at `<= 500` characters for `ADDED` / main specs (`--strict` fails above 500 chars; one behavior per requirement).
  - Scenarios **MUST** use exactly four hashes (`#### Scenario: <name>`) with `WHEN`/`GIVEN` and `THEN` bullets (three hashes or plain bullets fail silently in the parser).
  - Every new capability delta starts with `## Purpose` (`50+` chars); deltas modifying existing capabilities **must omit** `## Purpose` so archive doesn't overwrite or generate `TBD` placeholders.

### Delta Spec Operators

Delta files in `openspec/changes/<change-id>/specs/<capability-path>/spec.md` support four explicit mutation blocks:
1. `## ADDED Requirements` — introduces new requirements and scenarios.
2. `## MODIFIED Requirements` — updates an existing requirement; requires copying the **entire** existing requirement block (`### Requirement:` + all `#### Scenario:` clauses) and editing it in place (partial content drops uncopied scenarios on archive).
3. `## REMOVED Requirements` — deprecates/removes existing behavior; must include `**Reason**` and `**Migration**` notes.
4. `## RENAMED Requirements` — renames a requirement header via `FROM:` / `TO:` without altering behavior.

### Zero-Delta Escape Hatch (`skip_specs: true`)

`openspec validate` rejects a change with zero spec deltas unless `.openspec.yaml` explicitly sets `skip_specs: true` (reserved for pure refactors, tooling, or documentation). This prevents agents from inventing fake behavioral requirements merely to appease validation.

---

## 4. OPSX Artifact DAG (`schema.yaml`, `ArtifactGraph`, `config.yaml`)

OpenSpec 2.x replaced hardcoded TypeScript workflow prompts with **OPSX**—a declarative, customizable schema engine:

- **Schema definition (`schemas/spec-driven/schema.yaml`):** Defines `artifacts:` (`proposal` → `specs` & `design` in parallel after `proposal` → `tasks` requiring `[specs, design]`) and `apply:` (`requires: [tasks]`, `tracks: tasks.md`).
- **Path safety (`src/core/artifact-graph/types.ts`):** `relativePathSchema` validates `generates`, `template`, and `tracks` with Zod, rejecting absolute paths, Windows drive letters, `..` traversal, and null bytes.
- **Deterministic tie-breaking (`src/core/artifact-graph/graph.ts`):** `ArtifactGraph` uses Kahn's topological sort and breaks ties by **schema declaration order** (`proposal` → `specs` → `design` → `tasks`) rather than alphabetical sorting (which previously sorted `design` ahead of `specs`).
- **Schema resolution precedence (highest to lowest):**
  1. CLI flag (`--schema <name>`)
  2. Change metadata (`.openspec.yaml`)
  3. Project config (`openspec/config.yaml`)
  4. Default (`spec-driven`)

### Three-Way Prompt Configuration Separation (`openspec/config.yaml`)

| Config Field | Scope | Semantics |
| --- | --- | --- |
| `context` | Injected into **all** artifacts & ops | Required prompt-level project facts (tech stack, conventions, constraints). Never overrides CLI-controlled paths or explicit user choices. |
| `rules.<artifact_id>` | Injected **only** for matching artifact | Content constraints (e.g., `proposal`: include rollback plan; `specs`: reference existing patterns). `instructions specs` constrains main specs during merge. |
| `operations.{apply,archive}.guidance` | Fetched dynamically at execution time | Optional additive advice for conducting `apply` or `archive`; strictly separate from artifact `rules` and never treated as enforceable gates. |

### Workflow Profiles

- **Default (`core`) profile:** `propose`, `explore`, `apply`, `update`, `sync`, `archive`.
- **Expanded profile:** adds `new`, `continue`, `ff` (fast-forward all planning artifacts), `verify`, `bulk-archive`, `onboard`.

---

## 5. Verification, Archival, Machine Contract & Review UX

### 5.1 Rigorous Verification (`openspec-verify-change`)

Beyond checking task checkboxes (`x`/`X` only; `[~]`, `[-]`, `[]` count as incomplete) and `ADDED`/`MODIFIED` implementation + test scenario coverage, OpenSpec has an unusually strong verification spec for **removals and renames**:
- **`REMOVED` requirements:** Must verify the baseline behavior is actually absent from the codebase (ignoring matches in `openspec/` docs or migration code). If the main spec was already synced, it recovers the pre-removal baseline from `git -C "<planningHome.root>" log -p` / `git show <commit>^:...`. An empty or title-only baseline is treated as *not verified*—never silently marked passing.
- **`RENAMED` requirements:** Verifies `TO` behavior remains implemented against the baseline (`FROM` or `TO` if already synced) without forcing developers to rename internal code symbols or filenames.

### 5.2 Safe Archive & Sync Contract (`openspec-archive-change`, `openspec-sync-specs`)

- Uses `artifactPaths.specs.existingOutputPaths` from `openspec status --json` strictly as the delta-spec source (never inferring deltas from `proposal.md` or `design.md`).
- Counts tracked tasks strictly across schema-resolved task files (`openspec list --json`), refusing to infer completion when `tasks.md` is missing or JSON validation fails.
- Fetches `openspec instructions specs --change <name> --json` prior to semantic merge and aborts before any spec write or move if the lookup fails (for `bulk-archive`, fetches all snapshots before the first write).
- Moves the change folder to `openspec/changes/archive/YYYY-MM-DD-<change-id>/`.

### 5.3 Machine-Readable Agent Contract (`docs/agent-contract.md`)

- All agent-facing commands expose `--json` envelopes with standardized exit codes (`0` success/health findings, `1` failure or validation fail, `130` cancelled interactive prompt) and an explicit diagnostic code catalog (`no_openspec_root`, `unknown_store`, `archive_validation_failed`, etc.).

### 5.4 Review Ergonomics & Dashboard Spec (`docs/reviewing-changes.md`, `openspec/specs/cli-view/spec.md`)

OpenSpec also codifies high-leverage human review and dashboard UI principles:
- **Two high-leverage review moments:** (1) immediately after `propose` (before any code is written, where fixing a wrong turn is nearly free) and (2) after `apply` via `verify`.
- **Quit-earliest progressive reading order:** Reviewers inspect artifacts in sequence so bad scope is caught immediately:
  1. `proposal.md` — *Is this the right problem and scope?* (stop immediately if wrong)
  2. `specs/*/spec.md` — *Is "done" defined observably and what scenarios are missing?* (heart of the review)
  3. `design.md` — *Is the technical approach sound?* (only for bigger changes)
  4. `tasks.md` — *Does every task trace to a requirement with no scope creep?*
- **Dashboard (`openspec view` / `cli-view`) specification invariants:**
  - **Summary metrics:** total specs & requirements, draft changes, active changes in progress, completed changes, and overall task progress percentage.
  - **Deterministic active sorting:** active changes sorted ascending by completion % (0% items first, missing progress treated as 0%, alphabetical change-ID tie-breaker).
  - **Decoupled artifact chips vs. task progress:** display schema name and dependency-ordered artifact status chips (`✓` done, `→` ready, blank blocked, `(skipped)` skipped) without altering task-progress percentages (e.g., an existing `tasks.md` artifact is `✓` even when checkboxes are 0% complete).
  - **Strict completed filter:** only classify changes as completed when `tasks.total > 0 AND tasks.completed === tasks.total` (explicitly preventing empty `0/0` changes from falsely appearing complete).
  - **Display security hygiene:** replace terminal control characters in schema names, artifact IDs, and error strings with inert text before rendering.

---

## 6. Documented Failure Mode: Parallel Delta Data Loss

OpenSpec's own `openspec-parallel-merge-plan.md` documents a critical structural bug in its TypeScript merger (`src/core/archive.ts` & `src/core/parsers/requirement-blocks.ts`):

- **Root Cause:** `buildUpdatedSpec` performs replace-only hash-map substitution of entire `### Requirement:` blocks without storing the base version or merging scenarios.
- **Failure Scenario:** Change A adds Scenario X to `Requirement: Auth` and archives first. Change B (started from the pre-A spec) adds Scenario Y to `Requirement: Auth` and archives second. `buildUpdatedSpec` overwrites the whole block with Change B's copy, **silently deleting Scenario X** with zero conflict warning.
- **OpenSpec's Proposed Remediation (Not Yet Fully Shipped):**
  - *Phase 0:* Persist SHA-256 base requirement fingerprints + raw base text in change metadata (`meta.json`) and abort archive on stale base hashes.
  - *Phase 1:* Add a `change sync` / rebase command performing 3-way `diff3` per requirement with Git-style conflict markers.
  - *Phase 2–3:* Nested scenario-level deltas and AST/CRDT spec IR with stable requirement IDs.

---

## 7. OpenSpec Strengths & Gaps Summary

| Dimension | Strengths to Adopt | Gaps / Weaknesses to Fix |
| --- | --- | --- |
| **Spec Model** | Living `specs/` truth + isolated `changes/` + `archive/` + `skip_specs: true` | Replace-only delta merge silently drops concurrent scenario edits |
| **Format** | RFC 2119 + 4-hash `#### Scenario:` (`GIVEN/WHEN/THEN`) + observable-behavior boundary | `<= 500` char and `####` rules rely heavily on prompt adherence unless parsed |
| **Config & DAG** | `schema.yaml` declarative `ArtifactGraph`; clean 3-way split (`context` / `rules` / `guidance`) | No immutable project-wide `constitution.md` authority |
| **Quality Gates** | Exceptional `REMOVED`/`RENAMED` baseline & `git log` verification | No `clarify` ambiguity taxonomy; no read-only cross-artifact `analyze`; no automated `converge` loop |
| **UX & Execution** | Fluid actions-not-phases; `explore` zero-stakes mode; quit-earliest review; `cli-view` invariants; `--json` contract | `tasks.md` lacks `[P]` parallelism, `[US#]` vertical slices, and phase checkpoints |
| **Scale** | Cross-repo `Stores` (beta) for multi-repo planning | Most enforcement (sync, checklist, git recovery) lives in Markdown skill instructions (`SKILL.md`) rather than runtime code |
