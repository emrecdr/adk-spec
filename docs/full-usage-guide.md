# `adk-spec` End-to-End Usage Guide & Full-Integration Playbook

**Status Legend:**
- **`[Built: Phases 1–7]`** — Already implemented and verified in the codebase (including Phase 7 on `across-repositories`).
- **`[Planned: Phases 8–13]`** — Defined on the active roadmap in [plans/README.md](superpowers/plans/README.md); exact flags and file schemas will be finalized in each phase's design spec before implementation.
- **`[Open Decision]`** — Future second interface surface (embedding inside an IDE coding assistant vs. a Web Workbench / TUI), pending owner confirmation.

> **Core Thesis:** **Models draft, explore, clarify, and judge; Python owns the files, requirement IDs, structural checks, SHA-256 approvals, secret/key guards, and atomic spec merge.** Every capability—whether you run `adk-spec` today or after Phase 13—keeps human decisions cleanly separated from deterministic guardrails.

For installation and current command syntax, see [README.md](../README.md). For research foundations and the roadmap, see [Spec driven framework on Google ADK.md](../reports/Spec%20driven%20framework%20on%20Google%20ADK.md) and [plans/README.md](superpowers/plans/README.md).

---

## 1. Plan Goal & End-State Usage Model

### The Golden Rule: One Command per Human Decision

OpenSpec started with a sprawling multi-command workflow before simplifying, and Spec Kit requires orchestrating up to nine slash prompts by hand. `adk-spec` is designed around one rule ([plans/README.md](superpowers/plans/README.md)):

- **A command exists only where a person decides something.** Everything the tool can do deterministically or across chained stages happens *inside* that command.
- **No command sprawl across phases.** Phases 8 through 13 make existing commands smarter (`init` profiles your repo, `propose` revises open changes and reads lessons, `verify` runs tests before judging, `approve` supports two approvers in `strict`), rather than adding new subcommands you have to memorize.
- **Keep terminals quiet; put detail in files.** Commands print progress while running, what files were written, what needs your attention first, and a single `next` line telling you what to run next. Full specs, findings, diffs, and recordings live under `.spec/`.

### Division of Labor: `adk-spec` vs. Your Coding Agent

`adk-spec` is **not** a code-editing loop—it is the **specification, planning, and verification harness** beside whatever coding assistant you use (GitHub Copilot in VS Code, Claude Code, Cursor, or your own edits):

1. **`adk-spec` owns intent, evidence, and truth:** clarifies ambiguity, reads relevant repos safely, drafts specs/designs/tasks, checks cross-file consistency, freezes approved baselines with SHA-256 hashes, judges diffs + tests against each requirement, and merges approved deltas into `.spec/specs/`.
2. **Your coding agent owns writing application code:** reads the approved `.spec/changes/<id>/` (`brief.md`, `context.md`, delta specs, `design.md`, `tasks.md`), implements each vertical slice test-first, and ticks `- [x] T###` boxes (without voiding approval).

### Full Integrated Lifecycle Flow (All Phases Combined)

```text
  [Once per Repo]     adk-spec init
                      └─ (Phase 8 [Planned]: reads repo, drafts constitution.md & capability map with evidence)
                             │
                             ▼
  1. PROPOSE          adk-spec propose "<request>" [--with ../other-repo] [--tier lean|standard|strict]
     (Decision 1:     ├─ Triage (Phase 10 [Planned]: deterministic rules first, LLM on edge cases)
      What to build?) │   └─ tier == none ──▶ exits cleanly (no change folder for trivial typos)
                      ├─ Clarify: <=3 open points/round, <=3 rounds, `=` takes suggestion (or --no-input)
                      ├─ (Phase 13 [Planned] strict: pauses after brief.md before drafting specs/tasks)
                      ├─ Write Brief + EARS/BDD Delta Specs (with stable REQ-<CAP>-NNN IDs & Lessons [P12])
                      ├─ Explore Code [Built P6–P7]: Scout → Python Git Source (scrubbed, no keys) → Survey
                      │   └─ LLM Review checks quote attribution & names "## What is still unknown" → context.md
                      └─ Plan: Design (when owed / always in strict) + Tasks (T### [P] [REQ-...] + files + verify)
                             │
                      (Human reads & edits .spec/changes/<id>/*; Phase 11 [Planned]: `propose --id <id> "..."` revises)
                             ▼
  2. APPROVE          adk-spec approve <id> [--by <reviewer>] [--strict] [--override "<reason>"]
     (Decision 2:     ├─ Python auto-records missing spec base fingerprints + starts commit(s) across repos
      Agree on plan?) ├─ Code Checks (syntax, IDs, 100% req-to-task coverage) + LLM Check (quote-grounded findings)
                      └─ Records approver, timestamp & SHA-256 of files (strict [P13]: 0 criticals + 2nd approver)
                             │
                      (You / VS Code Copilot / Claude Code implements tasks & ticks `- [x]` boxes in tasks.md)
                             ▼
  3. VERIFY           adk-spec verify <id> [--base <ref>] [--override "<reason>"]   (standard & strict)
     (Decision 3:     ├─ Phase 9 [Planned]: runs configured project test command + maps test results to REQ-IDs
      Is it built?)   ├─ Reads working-tree diff across ALL repos in the change (excluding private-key files)
                      └─ LLM judges met/unmet/unclear; Python keeps `met` ONLY where a diff line quote matches!
                             │
                             ▼
  4. ARCHIVE          adk-spec archive <id>
     (Decision 4:     ├─ Verifies approval, no file drift, non-drifted diff, and live spec base SHA-256 match
      Make record?)   └─ Atomic write: folds ADDED / MODIFIED / REMOVED deltas into .spec/specs/<cap>/spec.md
```

---

## 2. What You Can Do Similar to Other Spec Kits (and Where `adk-spec` Goes Further)

If you have used **OpenSpec**, **GitHub Spec Kit**, **AWS Kiro**, or **Claude Projects**, here is how every familiar capability translates to `adk-spec`:

| Capability / Workflow | How OpenSpec / Spec Kit / Kiro / Claude Projects Do It | Exact `adk-spec` Way (`[Built]` vs. `[Planned]`) | What Python Enforces Beyond Prompt-Only Tools |
| --- | --- | --- | --- |
| **Living System Truth + Isolated Changes** | **OpenSpec** separates living `specs/` from `changes/` and folds them back during archive. | **`[Built: P1]`** `.spec/specs/<capability>/spec.md` holds canonical behavior; `.spec/changes/<id>/` holds active deltas (`ADDED`, `MODIFIED`, `REMOVED`). `adk-spec archive <id>` folds them atomically. | Assigns permanent **`REQ-<CAP>-<NNN>` IDs** (retired IDs are never reused) and checks LF-normalized **base SHA-256 fingerprints**—avoiding OpenSpec's name-keyed merge fragility while preventing silent overwrites. |
| **Project Principles / Constitution** | **Spec Kit** keeps `.specify/memory/constitution.md` checked by prompt instructions. | **`[Built: P1–P3]`** `.spec/constitution.md` loaded live by every stage. **`[Planned: P8]`** `init` scans existing repo docs/CI and drafts evidence-backed rules for you to accept/edit. | Never copied or drifted inside per-change templates; constitution length is linted (`validate`), and `check` flags violations with exact quotes. |
| **Bounded Clarification Interview** | **Spec Kit** `/speckit.clarify` asks up to 5 questions interactively over a 10-category taxonomy. | **`[Built: P2, P4–P5]`** Built right into `propose`: asks `<= 3` open points per round (up to 3 rounds), each with a suggested answer (`=` accepts, empty leaves open). Pass `--no-input` for CI/non-interactive use. | Code enforces marker budgets (`<= 3` markers), extracts questions deterministically without an extra model call, and **blocks `plan` and `approve`** while any `[NEEDS CLARIFICATION]` marker remains unresolved. |
| **Brownfield Code Reading** | **OpenSpec** reads implementation/tests ad hoc in prompts; **Claude Projects** relies on uploaded/synced repo context. | **`[Built: P6–P7]`** Built into `propose` & `plan` (across `--with` multi-repo workspaces): Scout → Python Git Source → Survey → LLM Review writes `.spec/changes/<id>/context.md`. | Reads strictly via `git ls-files` + `git grep` (never outside repo, never symlinks/junctions, never `[repository] exclude`), strips private-key files, scrubs secrets, annotates enclosing code block (`within`), and **drops any statement whose quote is missing from the file**. |
| **Cross-Artifact Consistency Audit** | **Spec Kit** `/speckit.analyze` checks alignment across spec, plan, and tasks in chat. | **`[Built: P3, P5]`** Runs automatically inside `approve` (or standalone via `adk-spec check <id>` / `--no-model`). Writes `.spec/changes/<id>/reports/check.md`. | Deterministic Python verifies 100% requirement-to-task ID coverage (`coverage_of`) and valid structure; LLM findings without real file quotes are dropped; `--override` only waives findings you were already shown. |
| **Conditional Design & Task Slicing** | **OpenSpec** creates `design.md` only when risky/cross-cutting; **Spec Kit** breaks work into `T### [P]` tasks. | **`[Built: P1–P5]`** `design.md` generated only when cross-cutting, new dep, security/migration risk, or tech decision is owed (always in `strict`); test-first `tasks.md` with `T### [P] [REQ-...]` + `files` + `verify`. | Approval fingerprints `tasks.md` with **all `- [ ]` boxes cleared** (`_as_approved`), so coding agents ticking `- [x]` never break your approval—while any real text edit voids approval automatically. |
| **Right-Sized Workflow Tiers** | **Spec Kit** `lean` preset; **Kiro** bugfix vs. spec-first mode. | **`[Built: P5]`** `none`, `lean` (3 commands: `propose`, `approve`, `archive`), `standard` (4 commands + check + verify). **`[Planned: P10 & P13]`** Rule-based triage (`P10`) + `strict` tier (`P13`: pause after brief, mandatory design, 0 criticals, 2nd approver). | Enforced in code via `ChangeState.tier` (`lean` skips `verify`; `standard`/`strict` cannot archive without non-drifted `verify`; invalid `--tier strict` refused cleanly until Phase 13 lands). |
| **Implementation Verification** | **OpenSpec** `/opsx:verify` & **Spec Kit** `/speckit.converge` review changes via chat prompts. | **`[Built: P3, P7]`** `adk-spec verify <id>` inspects diffs across every repo in the change (`--base` supported) and writes `reports/verify.md`. **`[Planned: P9]`** Runs project tests before model judgement. | Code refuses to accept any `met` verdict unless the model quotes an **actual added line (or removed line for `REMOVED` requirements)** from the real working-tree diff. Missing or hallucinated quotes downgrade to `unclear`. |
| **Iterating Scope After Drafting** | **OpenSpec** update skill & mid-feature corrections. | **`[Built: P1, P5]`** Edit any file by hand + `adk-spec plan <id>` / `adk-spec rebase <id>`. **`[Planned: P11]`** `adk-spec propose --id <id> "<instruction>"` revises open brief, deltas, and tasks conversationally. | `approve` detects any edit automatically via file hashes; `rebase` updates stale requirement bases; `plan` refuses to overwrite ticked tasks unless `--replace` is passed. |
| **Workspace Memory & Guardrails** | **Claude Projects** durable Project Memory / Knowledge Base across chats. | **`[Built: P1–P6]`** `.spec/specs/`, `constitution.md`, editable `context.md`, `[repository] exclude`. **`[Planned: P8, P12]`** Repo profile/capability map (`P8`) + capped `.spec/lessons` (`P12`) capturing past gate corrections. | Runs under `.spec/.gitignore` local run logs (`.spec/runs/`), fail-closed regex secret scrubbing across 40+ vendor/header/URL patterns, `ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=false`, and OS-trusted TLS (`truststore`). |
| **Model Flexibility & Cost Control** | Typically locked to one IDE chat model without per-stage routing or token caps. | **`[Built: P2–P3]`** Dual-arm **GitHub Copilot** (`adk-spec login`, `models`) & **Gemini** (AI Studio / Vertex AI), per-stage `SPEC_<ROLE>_MODEL`, `SPEC_FALLBACK_MODEL` (408/429/5xx failover), and `[limits] max_tokens`. | `UsageLedger` counts exact per-stage tokens and **cuts off further LLM calls cleanly** once `[limits] max_tokens` is reached; `scripts/measure.py` benchmarks real fault-catch rate across models. |

---

## 3. Full Roadmap Snapshot (Built vs. Planned)

Every phase from [plans/README.md](superpowers/plans/README.md) contributes to the unified workflow below:

| Phase | Name | Current State | Primary Command(s) Enhanced | What It Gives You |
| --- | --- | --- | --- | --- |
| **1** | Foundation | **Built** | `init`, `new`, `validate`, `status`, `rebase`, `approve`, `archive` | `.spec/` file tree, `REQ-<CAP>-NNN` IDs, SHA-256 approvals, atomic ID-keyed delta merge, LF cross-platform safety |
| **2** | Model Stages | **Built** | `propose`, `plan`, `login`, `models`, `smoke` | Dual-arm Copilot + Gemini runtime, `SPEC_<ROLE>_MODEL`, fallback, token ledger, gate retries |
| **3** | Check & Verify | **Built** | `check`, `verify`, `approve` | Quote-grounded semantic consistency checks, diff-grounded requirement verdicts, `.spec/runs/` recordings, `scripts/measure.py` |
| **4** | Questions in Code | **Built** | `propose` | Model lists open points inside `BriefDraft`; Python runs interactive Q&A saving 1 LLM call/round |
| **5** | The Simple Flow | **Built** | `propose`, `approve`, `verify`, `archive`, `--help` | 4-command everyday workflow, `propose` writes full change, `approve` auto-bases & auto-checks, `next` lines, quiet/scannable output |
| **6** | Brownfield Part 1 | **Built** | `propose`, `plan`, `check`, `verify` | Multi-round safe `git` exploration → quote-verified `context.md`, fail-closed secret scrubbing, auto private-key omission, `[repository] exclude` |
| **7** | Brownfield Part 2 (Multi-Repo) | **Built** (`across-repositories`) | `propose`, `plan`, `approve`, `verify` | `--with PATH`/`NAME=PATH` across N repos, search-first round order, block context (`in: ...`), LLM `review` + `"## What is still unknown"`, cross-repo `verify` |
| **8** | Brownfield Part 3 (`init` Profile) | Planned | `init`, `propose` | `init` scans repo docs/CI to propose repo stack profile, evidence-backed `constitution.md`, and capability-to-folder map (with refresh/skip flags) |
| **9** | Tests as Evidence | Planned | `verify` (via `.spec/config.toml`) | User-configured test command runs automatically before LLM diff judgement and maps pass/fail results directly to `REQ-*` IDs |
| **10** | Triage by Rules | Planned | `propose` | Fast deterministic sizing rules route obvious small/medium requests to `none` or `lean` with zero triage LLM call |
| **11** | Revising by Instruction | Planned | `propose --id <id> "..."` | One-line conversational revisions to brief, delta specs, and tasks of an open change without manual rewrites |
| **12** | Lessons File | Planned | `propose`, `plan`, `approve` | Capped `.spec/` lessons file records past gate rejections & human corrections so future drafts stop repeating the same mistakes |
| **13** | Strict Tier | Planned | `propose`, `approve`, `new` | Risk-triggered `strict` mode: pauses after `brief.md` before full draft, mandatory `design.md`, 0 criticals allowed, requires 2nd approver |

---

## 4. Example End-to-End Use Cases (Full Integrated Experience)

> **Windows Note:** Set `PYTHONUTF8=1` in your user environment on Windows (and `UV_PYTHON_ARCH=x86_64` on Windows ARM64 for LiteLLM compatibility). All commands below run identically on Windows PowerShell and macOS/Linux zsh.

---

### Use Case 1: Adopting `adk-spec` in an Existing Repository (`init`, Phases 1 + 6 + 8 + 9)

**Scenario:** You join or maintain an existing FastAPI + React repository (`200+` files) and want `adk-spec` to respect existing architecture, keep secrets out, cap token spend, and run your test suite during verification.

```bash
# 1. Authenticate once (Copilot arm) and inspect available models [Built]
adk-spec login
adk-spec models

# 2. Initialize .spec/ in an existing repository [Built in P1; Enhanced in P8 Planned]
#    Phase 8 [Planned] scans README, CI config, and repo layout to propose:
#      - short repo stack & build/test profile (with quoted evidence)
#      - starter .spec/constitution.md rules for you to accept, edit, or drop
#      - starter capability-to-folder map (e.g. `auth -> src/auth/`) so future `propose` runs start directly there
#    (Add --no-profile or skip prompt to keep init purely offline with no LLM call.)
adk-spec init
```

Edit `.spec/config.toml` to harden exclusions `[Built]`, set token limits `[Built]`, and register your test command `[Planned: P9]`:

```toml
[project]
default_tier = "standard"

[limits]
max_tokens = 30000
keep_runs = 20

[repository]
# Never listed, read, explored, or included in verify diffs on any OS:
exclude = ["vendor/**", "**/*.pem", "*.key", "config/production.yaml"]

# Phase 9 [Planned]: only a test command you explicitly write here is ever run by verify
[verify]
test_command = "uv run pytest -q"
```

Review `.spec/constitution.md` (`[Built]`, keep concise under 16,000 chars so every stage reads crisp rules):

```markdown
# Constitution
Version: 1

## Technology and versions
- Backend uses Python 3.14, FastAPI, Pydantic v2, and pytest (`pyproject.toml:L4`). Reason: matches runtime & CI.

## Coding standards
- Every endpoint change MUST include integration tests and explicit error schemas (`docs/CONTRIBUTING.md:L18`).
```

---

### Use Case 2: Everyday Standard Feature — The 4-Command Flow (Phases 1–6 + 9)

**Scenario:** Add WebAuthn/passkey sign-in to your backend service (`standard` tier).

#### Step 1 — `propose` (Clarify intent + read codebase + draft change)
```bash
adk-spec propose "Let users sign in with a passkey alongside existing password login."
```
What happens inside `propose`:
1. **Triage:** Picks `standard` (`--tier standard` skips triage `[Built]`; Phase 10 `[Planned]` uses fast Python rules when obvious).
2. **Brief & Interactive Clarification `[Built]`:** If the request has open questions (up to 3 per round, max 3 rounds), `adk-spec` asks interactively:
   ```text
   The brief leaves 2 points open. A line answers. `=` takes the suggestion.
   An empty line leaves the point open.
   1. Should enterprise SSO accounts be allowed to register passkeys?
      suggested: Allow passkeys as an optional second method unless SSO-enforced.
   > =
   2. How long should WebAuthn challenge nonces remain valid?
      suggested: Expire challenge nonces after 5 minutes.
   > 3 minutes, single-use
   ```
3. **Delta Specs `[Built]`:** Creates/updates capability specs with stable IDs (e.g., `REQ-AUTH-004: Passkey Sign-In`) and `GIVEN`/`WHEN`/`THEN` scenarios.
4. **Brownfield Exploration & Review `[Built: P6–P7]`:** Reads tracked source files (`git grep` searches first, then folders, then files), rejects unquoted statements, attaches enclosing block signatures (`in: def start_session(...)`), and lets the `review` LLM flag any remaining unknowns in `.spec/changes/<id>/context.md`. *(Phase 8 `[Planned]` jumps straight to mapped `src/auth/` folders.)*
5. **Plan `[Built]`:** Drafts `design.md` (when cross-cutting/security-sensitive, as passkeys are) and test-first `tasks.md`.
6. **Output `[Built]`:** Names exact files written, token usage, **what to read first** with line counts (`read      brief.md (42 lines) and design.md (58 lines) and context.md (1 unknown) first`), and prints:
   `next      run adk-spec approve let-users-sign-in-with-a-passkey`

#### Step 2 — Review & Edit the Drafts (`brief.md`, `specs/`, `design.md`, `tasks.md`)
All files under `.spec/changes/let-users-sign-in-with-a-passkey/` are plain Markdown—edit any requirement, assumption, or task by hand before approving. (Or in Phase 11 `[Planned]`, run `adk-spec propose --id let-users-sign-in-with-a-passkey "Use Redis for challenge storage"`.)

#### Step 3 — `approve` (Auto-base + Structural & Semantic Check + Freeze Approval)
```bash
adk-spec approve let-users-sign-in-with-a-passkey
```
What happens inside `approve` `[Built]`:
- Captures missing base SHA-256 fingerprints against `.spec/specs/` and records your starting Git commit (`base_commit`).
- Runs deterministic structural + 100% requirement-to-task checks AND the LLM consistency `check` (dropping any LLM finding that doesn't quote real file text), writing `reports/check.md`.
- Blocks cleanly if anything `ERROR`/blocking is found (never silently passing broken plans; you either fix the files or rerun with `--override "<reason>"` after seeing `reports/check.md`).
- Records `by`, `at`, and SHA-256 hashes of every change file in `change.json`.

#### Step 4 — Implement with Your Coding Agent (VS Code Copilot / Claude Code / Cursor)
Point your coding agent at `.spec/changes/let-users-sign-in-with-a-passkey/` (`brief.md`, `context.md`, `specs/`, `design.md`, `tasks.md`) and have it implement each task and tick boxes (`- [x] T001 ...`). **Ticking `- [x]` never voids approval** `[Built]`.

#### Step 5 — `verify` (Run Tests + Quote-Grounded Diff Verdict)
```bash
adk-spec verify let-users-sign-in-with-a-passkey
```
What happens inside `verify`:
- **Phase 9 `[Planned]`:** Runs your configured `[verify] test_command` (`uv run pytest -q`) and correlates passing/failing test evidence with `REQ-AUTH-004`.
- **Phase 3 & 6 `[Built]`:** Computes the real diff (tracked + untracked non-ignored files, minus `.spec/`, `[repository] exclude`, and private-key files), scrubs secret shapes, asks the LLM for per-requirement verdicts (`met`/`unmet`/`unclear`) with exact line quotes, and **downgrades any `met` whose quote isn't literally in the diff to `unclear`**.
- Writes `reports/verify.md`. Re-run `verify` as many times as you need while finishing code! Once all requirements read `met`, `next` says `run adk-spec archive ...`.

#### Step 6 — `archive` (Fold Deltas into Canonical Living Truth)
```bash
adk-spec archive let-users-sign-in-with-a-passkey
```
- Confirms approval is still valid, diff hasn't drifted since `verify`, and no concurrent change modified the same requirement base SHA-256.
- Atomically merges `ADDED` / `MODIFIED` / `REMOVED` blocks into `.spec/specs/auth/spec.md` and marks the change `archived`.

---

### Use Case 3: Cross-Repository Full-Stack Feature (Phase 7 `[Built]` on `across-repositories` + Phase 9 `[Planned]`)

**Scenario:** You are working inside your `platform-gateway` checkout and need to add an authenticated billing export endpoint (`../billing-api`), consume it in the frontend (`../web-app`), and enforce gateway auth in the current repo.

```bash
# 1. Propose across all 3 repositories from one workspace [Built: P7]
adk-spec propose "Add CSV billing export button for org admins." \
  --with ../billing-api \
  --with web=../web-app

# 2. Forgot a mobile repo before approving? Attach it during plan [Built: P7]:
adk-spec plan add-csv-billing-export --with ../mobile-app
```

What `adk-spec` does across repos `[Built: P7]`:
- Inspects each repo using **its own `git ls-files`, `.gitignore`, and its own `.spec/config.toml` `[repository] exclude`** (never reading symlinks, junctions, or private-key files in any repo).
- Formats findings uniformly (`billing-api/src/routes/export.py:42`, `web/src/pages/Billing.tsx:88`) with enclosing block headers (`in: async def export_invoices(...)`) and lists any cross-repo gaps under `## What is still unknown` in `context.md` (plus the exact commit SHA each repo was read at).
- When you run `adk-spec approve add-csv-billing-export`, Python records the starting commit (`base_commits`) in **every repository** simultaneously.
- Implement changes in your gateway, `billing-api`, and `web-app` repos via Copilot/IDE, then run:
  ```bash
  # Inspects working-tree diffs across gateway + billing-api + web-app together:
  adk-spec verify add-csv-billing-export
  # Or pass a custom base commit for one linked repo if added late:
  adk-spec verify add-csv-billing-export --base billing-api=main

  # Fold specs into living truth once verified:
  adk-spec archive add-csv-billing-export
  ```

---

### Use Case 4: Small Bug Fix (`lean` 3-Command Path) vs. Trivial Edit (`none`) (Phases 5 `[Built]` & 10 `[Planned]`)

**Scenario A — Small focused bug fix inside one capability (`lean`):**
```bash
# Phase 10 [Planned] rule-based triage detects small scoped fix with 0 triage LLM tokens,
# or pass --tier lean explicitly [Built]:
adk-spec propose "Fix off-by-one expiry check on JWT refresh grace window." --tier lean

# Fast 3-command loop (no design, no check, no verify owed):
adk-spec approve fix-jwt-refresh-grace
# ... fix bug + add unit test ...
adk-spec archive fix-jwt-refresh-grace
```

**Scenario B — Typo / comment / throwaway tweak (`none`):**
```bash
adk-spec propose "Fix typo in README install header."
# Output:
# no spec is owed: Cosmetic documentation edit with no behavioral change.
# Exits cleanly with no .spec/changes/ folder created!
```

---

### Use Case 5: Mid-Flight Scope Changes & Parallel Team Spec Conflicts (Phases 1 `[Built]` & 11 `[Planned]`)

**Scenario A — Requirements change while implementing:**
- **Manual route `[Built]`:** Edit `.spec/changes/<id>/brief.md` or delta `spec.md`, then run `adk-spec plan <id>` (re-generates tasks only; add `--replace` if tasks were already ticked). Any edit voids the old approval, forcing a fresh `approve`.
- **Instruction route `[Planned: P11]`:** Revise brief, delta specs, and tasks directly from natural language without adding another subcommand:
  ```bash
  adk-spec propose --id let-users-sign-in-with-a-passkey \
    "Also support 8-digit one-time backup codes when no authenticator is present."
  ```

**Scenario B — Teammate archived a conflicting change first (`rebase`) `[Built: P1]`:**
1. You try `adk-spec archive add-oauth-pkce`.
2. Python detects `delta.base-stale`: `REQ-AUTH-002` in `.spec/specs/auth/spec.md` moved after you based your delta on it—and **refuses to write anything** (zero silent data loss).
3. Inspect the updated `REQ-AUTH-002`, reconcile your delta in `changes/add-oauth-pkce/specs/auth/spec.md`, then run:
   ```bash
   adk-spec rebase add-oauth-pkce
   adk-spec approve add-oauth-pkce
   adk-spec verify add-oauth-pkce
   adk-spec archive add-oauth-pkce
   ```

---

### Use Case 6: High-Risk / Compliance Feature — `strict` Tier (Phase 13 `[Planned]`)

**Scenario:** Modifying payment ledger reconciliation, multi-tenant RBAC isolation, or PII encryption where mistakes are expensive.

```bash
# 1. Start in strict mode [Planned: P13]:
adk-spec propose "Migrate billing webhooks to idempotent double-entry ledger." --tier strict
```

What `strict` adds on top of `standard` `[Planned: P13]`:
1. **Brief Alignment Pause:** `propose` pauses after drafting/clarifying `brief.md` so a human confirms scope before spending tokens on delta specs, exploration, design, and tasks.
2. **Mandatory `design.md`:** Always drafted regardless of size heuristics.
3. **Zero Blocking Findings Allowed:** Strict `check` and `validate` tolerates no critical/blocking shortcuts.
4. **Dual-Approver Accountability:** Requires **two distinct approvers** recorded in `change.json` before implementation/verify/archive can proceed:
   ```bash
   adk-spec approve migrate-billing-webhooks --by alice
   adk-spec approve migrate-billing-webhooks --by bob
   # Implement + run Phase 9 tests + verify + archive:
   adk-spec verify migrate-billing-webhooks
   adk-spec archive migrate-billing-webhooks
   ```

---

### Use Case 7: Switching Providers, Lessons Feedback Loop, Visual Inspection & Benchmarking (Phases 2, 3, 6 `[Built]` & 12 `[Planned]`)

- **Switching Copilot ↔ Gemini per team or per stage `[Built: P2]`:**
  In `.env` (read strictly from the `adk-spec` checkout directory, never poisoned by target repos):
  ```dotenv
  # Default GitHub Copilot arm (with fast fallback)
  SPEC_PROVIDER=copilot
  SPEC_MODEL=gpt-4.1
  SPEC_FALLBACK_MODEL=gpt-4o
  # Optional cheaper/stricter override for one stage:
  SPEC_VERIFY_MODEL=gpt-4o

  # Or switch whole pipeline to Google Gemini (AI Studio or Vertex AI):
  # SPEC_PROVIDER=gemini
  # SPEC_MODEL=gemini-3.8-flash
  # GOOGLE_API_KEY=...
  ```
- **Checking readiness & costs before spending `[Built]`:**
  ```bash
  adk-spec status                  # Grouped queue: Waiting on you / Ready to run / Done
  adk-spec smoke --check           # Zero-cost offline readiness validation
  adk-spec validate --strict       # Offline lint of all specs + open changes (CI-ready with --json)
  ```
- **Visual trace debugging in ADK's UI `[Built]`:**
  Run from inside any repo holding `.spec/`:
  ```bash
  uv run --project /path/to/adk_spec adk web --no_use_local_storage /path/to/adk_spec
  ```
  Choose `adk_spec`, type a feature request to watch every `Workflow` node transition live in ADK's event timeline (without touching `.spec/` files or saving unredacted `.adk/session.db` traces on disk).
- **Measuring prompt/model accuracy before & after changes `[Built: P3, P6–P7]`:**
  ```bash
  uv run python -m scripts.measure --runs 5 --out docs/measurements/latest.md
  uv run python scripts/dump_instructions.py
  ```
- **Workspace self-improvement (`lessons`) `[Planned: P12]`:**
  Whenever a human overrides/fixes a recurring `check` finding or edits recurring draft mistakes across changes, Phase 12 records concise rules into a capped `.spec/` lessons file—automatically feeding future `propose` and `plan` drafts so you never make the same correction twice.

---

## 5. End-State `.spec/` Directory Map & Command Cheat Sheet

### What Lives in `.spec/`

```text
.spec/
├── .gitignore                        # Ignores .lock [Built]
├── .lock                             # Exclusive writer lock during mutating commands [Built]
├── config.toml                       # [project] default_tier, [limits], [repository] exclude (+ [verify] P9)
├── constitution.md                   # Short, versioned rules with reasons (auto-drafted in init P8)
├── profile.md / capabilities         # Repo stack summary & capability->folder map [Planned: P8]
├── lessons.md                        # Capped workspace lessons from gate feedback/fixes [Planned: P12]
├── runs/                             # Auto-gitignored *.json scrubbed stage recordings (keep_runs=20) [Built]
├── specs/
│   └── <capability>/
│       └── spec.md                   # Living canonical truth (## Purpose, ## Requirements, ## Retired) [Built]
└── changes/
    └── <change-id>/
        ├── change.json               # Tier, status, base hashes, approval hashes, commit(s), verify state [Built]
        ├── brief.md                  # Why, what changes, non-goals, capabilities, impact, assumptions [Built]
        ├── context.md                # Multi-repo quote-verified code notes & ## What is still unknown [Built P6–P7]
        ├── design.md                 # Context, goals, decisions, risks (when owed / always in strict) [Built]
        ├── tasks.md                  # Vertical T### [P] [REQ-...] checklist (`files` + `verify`) [Built]
        ├── specs/<cap>/spec.md       # Delta spec: ADDED / MODIFIED / REMOVED [Built]
        └── reports/                  # check.md and verify.md [Built]
```

### Quick Command Reference (Grouped Like `adk-spec --help`)

| Group | Command | Purpose |
| --- | --- | --- |
| **Everyday** | `adk-spec init` | Initialize `.spec/` (`[Planned P8]`: auto-profile repo + propose constitution & map) |
| | `adk-spec propose "<request>"` | Clarify + draft brief/deltas + explore code (with `--with` repos) + plan (`[P11]`: `--id <id>` revises) |
| | `adk-spec approve <id>` | Auto-base + run structural & LLM `check` + record SHA-256 approval & start commits |
| | `adk-spec verify <id>` | Run tests (`[P9]`) + judge diffs across all repos with quote-grounded evidence |
| | `adk-spec archive <id>` | Fingerprint-guarded atomic merge into `.spec/specs/<cap>/spec.md` |
| | `adk-spec status [--all]` | Show open changes grouped by *Waiting on you* / *Ready to run* / *Done* |
| **Redo One Step** | `adk-spec plan <id>` | Re-explore (if no `context.md`) & re-draft `design.md` + `tasks.md` (`--replace`, `--with`) |
| | `adk-spec check <id>` | Re-run cross-artifact analysis (`--no-model` for pure-Python offline checks) |
| | `adk-spec rebase <id>` | Refresh stale requirement base fingerprints after concurrent archives |
| | `adk-spec validate [id]` | Offline lint of living specs and open changes (`--strict`, `--json`) |
| | `adk-spec new <id>` | Scaffold an empty hand-written change folder |
| **Setup** | `adk-spec login [--force]` | 15-minute GitHub Copilot OAuth device flow (`--force` re-authenticates) |
| | `adk-spec models [--json]` | Query active arm's live model catalog with zero model tokens spent |
| | `adk-spec smoke [--check]` | Offline config check (`--check`) or single schema-bound smoke call |

### Open Future Direction (`[Open Decision]` in `plans/README.md`)

One architectural question intentionally remains open for after Phases 7–9 are proven live: **how you want to invoke `adk-spec` alongside the terminal**—either directly inside coding assistants (such as exposing `.spec/` tools and workflows to VS Code GitHub Copilot / Claude Code via MCP + skills so you stay inside your editor's model lineup) or via a standalone Web Workbench / Rich TUI ([02-adk-spec-framework-architecture-and-roadmap.md](../reports/02-adk-spec-framework-architecture-and-roadmap.md)).
