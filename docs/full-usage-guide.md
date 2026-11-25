# `adk-spec` End-to-End Usage Guide & Full-Integration Playbook

**Status Legend:**
- **`[Built: Phases 1–13]`** — Implemented, reviewed and merged; every phase on the roadmap in [plans/README.md](superpowers/plans/README.md) is built. Brought up to date with the code on 22 November 2026.
- **`[Built: Phase 15]`** — Research during planning: `propose` reads the code and the project's installed libraries offline before the brief, which asks only what the code cannot answer, in order of what depends on what; `yes` takes a suggestion.
- **`[Built: Phase 14]`** — The second interface, decided by the owner on 22 November 2026 and built: `adk-spec-mcp`, an MCP server inside coding assistants.

> **Core Thesis:** **Models draft, explore, clarify, and judge; Python owns the files, requirement IDs, structural checks, SHA-256 approvals, secret/key guards, and atomic spec merge.** Every capability—whether you run `adk-spec` today or after Phase 13—keeps human decisions cleanly separated from deterministic guardrails.

For installation and current command syntax, see [README.md](../README.md). For research foundations and the roadmap, see [Spec driven framework on Google ADK.md](reports/Spec%20driven%20framework%20on%20Google%20ADK.md) and [plans/README.md](superpowers/plans/README.md).

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
                      └─ (Phase 8 [Built]: reads the code, writes profile.md, drafts rules already true of it)
                             │
                             ▼
  1. PROPOSE          adk-spec propose "<request>" [--with ../other-repo] [--tier lean|standard|strict]
     (Decision 1:     ├─ Triage: the model sizes the request (Phase 10's rules were removed by the owner)
      What to build?) │   └─ tier == none ──▶ exits cleanly (no change folder for trivial typos)
                      ├─ Explore Code first [Built P6–P7, P15]: Scout → Python Git Source (scrubbed, no keys) → Survey
                      │   └─ LLM Review checks quote attribution & names "## What is still unknown" → context.md
                      ├─ Clarify: <=3 open points/round, <=3 rounds, `=` takes suggestion (or --no-input)
                      ├─ Write Brief + EARS/BDD Delta Specs (with stable REQ-<CAP>-NNN IDs, reading lessons.md)
                      ├─ (Phase 13 [Built] strict: stops after brief.md and the specs; `plan` goes on)
                      └─ Plan: Design (when owed / always in strict) + Tasks (T### [P] [REQ-...] + files + verify)
                             │
                      (Human reads & edits .spec/changes/<id>/*; Phase 11 [Built]: `propose "..." --id <id>` revises)
                             ▼
  2. APPROVE          adk-spec approve <id> [--by <reviewer>] [--strict] [--override "<reason>"]
     (Decision 2:     ├─ Python auto-records missing spec base fingerprints + starts commit(s) across repos
      Agree on plan?) ├─ Code Checks (syntax, IDs, 100% req-to-task coverage) + LLM Check (quote-grounded findings)
                      └─ Records approver, timestamp & SHA-256 of files (strict: warnings block + a 2nd name)
                             │
                      (You / VS Code Copilot / Claude Code implements tasks & ticks `- [x]` boxes in tasks.md)
                             ▼
  3. VERIFY           adk-spec verify <id> [--base <ref>] [--override "<reason>"]   (standard & strict)
     (Decision 3:     ├─ Phase 9 [Built]: runs the test command in .spec/config.toml, in every repo; a failure blocks
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

| Capability / Workflow | How OpenSpec / Spec Kit / Kiro / Claude Projects Do It | Exact `adk-spec` Way (`[Built]`, with its phase) | What Python Enforces Beyond Prompt-Only Tools |
| --- | --- | --- | --- |
| **Living System Truth + Isolated Changes** | **OpenSpec** separates living `specs/` from `changes/` and folds them back during archive. | **`[Built: P1]`** `.spec/specs/<capability>/spec.md` holds canonical behavior; `.spec/changes/<id>/` holds active deltas (`ADDED`, `MODIFIED`, `REMOVED`). `adk-spec archive <id>` folds them atomically. | Assigns permanent **`REQ-<CAP>-<NNN>` IDs** (retired IDs are never reused) and checks LF-normalized **base SHA-256 fingerprints**—avoiding OpenSpec's name-keyed merge fragility while preventing silent overwrites. |
| **Project Principles / Constitution** | **Spec Kit** keeps `.specify/memory/constitution.md` checked by prompt instructions. | **`[Built: P1–P3]`** `.spec/constitution.md` loaded live by every stage. **`[Built: P8]`** `init` reads the code and drafts rules already true of it, each with its quoted evidence and marked as drafted, into the constitution while it is still the template. | Never copied or drifted inside per-change templates; constitution length is linted (`validate`), and `check` flags violations with exact quotes. |
| **Bounded Clarification Interview** | **Spec Kit** `/speckit.clarify` asks up to 5 questions interactively over a 10-category taxonomy. | **`[Built: P2, P4–P5]`** Built right into `propose`: asks `<= 3` open points per round (up to 3 rounds), each with a suggested answer (`=` accepts, empty leaves open). Pass `--no-input` for CI/non-interactive use. | Code enforces marker budgets (`<= 3` markers), extracts questions deterministically without an extra model call, and **blocks `plan` and `approve`** while any `[NEEDS CLARIFICATION]` marker remains unresolved. |
| **Brownfield Code Reading** | **OpenSpec** reads implementation/tests ad hoc in prompts; **Claude Projects** relies on uploaded/synced repo context. | **`[Built: P6–P7]`** Built into `propose` & `plan` (across `--with` multi-repo workspaces): Scout → Python Git Source → Survey → LLM Review writes `.spec/changes/<id>/context.md`. | Reads strictly via `git ls-files` + `git grep` (never outside repo, never symlinks/junctions, never `[repository] exclude`), strips private-key files, scrubs secrets, annotates enclosing code block (`within`), and **drops any statement whose quote is missing from the file**. |
| **Cross-Artifact Consistency Audit** | **Spec Kit** `/speckit.analyze` checks alignment across spec, plan, and tasks in chat. | **`[Built: P3, P5]`** Runs automatically inside `approve` (or standalone via `adk-spec check <id>` / `--no-model`). Writes `.spec/changes/<id>/reports/check.md`. | Deterministic Python verifies 100% requirement-to-task ID coverage (`coverage_of`) and valid structure; LLM findings without real file quotes are dropped; `--override` only waives findings you were already shown. |
| **Conditional Design & Task Slicing** | **OpenSpec** creates `design.md` only when risky/cross-cutting; **Spec Kit** breaks work into `T### [P]` tasks. | **`[Built: P1–P5]`** `design.md` generated only when cross-cutting, new dep, security/migration risk, or tech decision is owed (always in `strict`); test-first `tasks.md` with `T### [P] [REQ-...]` + `files` + `verify`. | Approval fingerprints `tasks.md` with **all `- [ ]` boxes cleared** (`_as_approved`), so coding agents ticking `- [x]` never break your approval—while any real text edit voids approval automatically. |
| **Right-Sized Workflow Tiers** | **Spec Kit** `lean` preset; **Kiro** bugfix vs. spec-first mode. | **`[Built: P5, P10, P13]`** `none`, `lean` (3 commands: `propose`, `approve`, `archive`), `standard` (4 commands + check + verify), `strict` (a stop after the brief and specs, a design always owed, warnings that block, two approvers). The model sizes each request; `--tier` names one by hand. | One table in the domain (`DEMANDS`) says what each tier asks, and every rule reads it: `lean` skips `check` and `verify`; `standard`/`strict` cannot archive without a non-drifted `verify`; `strict` refuses `approve --override` and the same name twice. |
| **Implementation Verification** | **OpenSpec** `/opsx:verify` & **Spec Kit** `/speckit.converge` review changes via chat prompts. | **`[Built: P3, P7, P9]`** `adk-spec verify <id>` runs the test command you wrote in `.spec/config.toml` in every repo of the change, then judges the diffs (`--base` supported), and writes `reports/verify.md`. | Code refuses to accept any `met` verdict unless the model quotes an **actual added line (or removed line for `REMOVED` requirements)** from the real working-tree diff. Missing or hallucinated quotes downgrade to `unclear`. |
| **Iterating Scope After Drafting** | **OpenSpec** update skill & mid-feature corrections. | **`[Built: P1, P5, P11]`** Edit any file by hand + `adk-spec plan <id>` / `adk-spec rebase <id>`, or `adk-spec propose "<instruction>" --id <id>`, which revises an open change's brief, deltas and tasks and lists the requirements it added, changed and dropped. | `approve` detects any edit automatically via file hashes; a revision keeps each requirement's ID by its name; `rebase` updates stale requirement bases; `plan` refuses to overwrite ticked tasks, or a design you wrote or edited, unless `--replace` is passed. |
| **Workspace Memory & Guardrails** | **Claude Projects** durable Project Memory / Knowledge Base across chats. | **`[Built: P1–P8, P12]`** `.spec/specs/`, `constitution.md`, editable `context.md`, `[repository] exclude`, the repository's `.spec/profile.md` (`P8`), and `.spec/lessons.md` (`P12`), shared through git, which every drafting stage reads. | Runs under `.spec/.gitignore` local run logs (`.spec/runs/`), fail-closed regex secret scrubbing across 40+ vendor/header/URL patterns (a pasted private key's whole body, footer or not), `ADK_CAPTURE_MESSAGE_CONTENT_IN_SPANS=false`, and OS-trusted TLS (`truststore`). |
| **Model Flexibility & Cost Control** | Typically locked to one IDE chat model without per-stage routing or token caps. | **`[Built: P2–P3]`** Dual-arm **GitHub Copilot** (`adk-spec login`, `models`) & **Gemini** (AI Studio / Vertex AI), per-stage `SPEC_<ROLE>_MODEL`, `SPEC_FALLBACK_MODEL` (408/429/5xx failover), and `[limits] max_tokens`. | `UsageLedger` counts exact per-stage tokens and **cuts off further LLM calls cleanly** once `[limits] max_tokens` is reached; `scripts/measure.py` benchmarks real fault-catch rate across models. |

---

## 3. Full Roadmap Snapshot

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
| **8** | Brownfield Part 3 (`init` Profile) | **Built**, measured live | `init`, `propose`, `plan` | `init` reads the code (saying so first; `--no-explore` skips, `--refresh` reads again), writes `.spec/profile.md`, and drafts rules already true of the code into the template constitution, with evidence; every reading starts from the profile |
| **9** | Tests as Evidence | **Built**, measured live | `verify` (via `.spec/config.toml`) | The test command you write as a list (`[verify] test`) runs in every repository of the change before the model judges; a failing run blocks "verified" unless `--override` |
| **10** | Triage by Rules | **Removed** by the owner | `propose` | Built and measured live, then removed on 22 November 2026: its list of risk words kept missing some, and a miss sized a risky fix lean, with no check and no verification, to save one sizing call. The model sizes every request |
| **11** | Revising by Instruction | **Built**, measured live | `propose "..." --id <id>` | Revises an open change in place: keeps its tier and each requirement's ID by name, lists what was added, changed and dropped, and makes an approved change a draft again where a file changed |
| **12** | Lessons File | **Built**, measured live | `propose`, `plan`, `approve` | `.spec/lessons.md`, shared through git: a person's corrections, and a line adk-spec adds in code for each fault a gate sent back that the next try fixed; `approve` names a drafted file you edited |
| **13** | Strict Tier | **Built**, measured live | `propose`, `plan`, `approve`, `new` | `strict`: a design always owed; `propose` stops after the brief and specs, and `plan` goes on; two different names approve; a warning of the check blocks, with no `--override` |

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

# 2. Initialize .spec/ in an existing repository [Built: P1, P8]
#    init says first that it reads the code with a model, then writes:
#      - .spec/profile.md: the stack, the commands, where things live, conventions and risks, each statement
#        with the code it quotes; every later reading starts from it
#      - rules already true of the code, drafted into .spec/constitution.md while it is the template, each marked
#        as drafted with its evidence, for you to keep, edit or delete
#    (--no-explore keeps init offline, with no model call; --refresh reads the code again later.)
adk-spec init
```

Edit `.spec/config.toml` to harden exclusions, set token limits, and register your test command `[Built]`:

```toml
[project]
default_tier = "standard"

[limits]
max_tokens = 80000
keep_runs = 20

[repository]
# Never listed, read, explored, or included in verify diffs on any OS:
exclude = ["vendor/**", "**/*.pem", "*.key", "config/production.yaml"]

# Phase 9 [Built]: only a test command you write here is ever run by verify: a list, run with no shell
[verify]
test = ["uv", "run", "pytest", "-q"]
timeout = 900
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
1. **Triage:** Picks `standard` (`--tier standard` skips triage `[Built]`).
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
4. **Brownfield Exploration & Review `[Built: P6–P7]`:** Reads tracked source files (`git grep` searches first, then folders, then files), rejects unquoted statements, attaches enclosing block signatures (`in: def start_session(...)`), and lets the `review` LLM flag any remaining unknowns in `.spec/changes/<id>/context.md`. *(Every reading starts from `.spec/profile.md` `[Built: P8]`.)*
5. **Plan `[Built]`:** Drafts `design.md` (when cross-cutting/security-sensitive, as passkeys are) and test-first `tasks.md`.
6. **Output `[Built]`:** Names exact files written, token usage, **what to read first** with line counts (`read      brief.md (42 lines, 3 assumptions) and design.md (58 lines) and context.md (1 unknown) first`, the assumptions those the brief made where it might have asked), and prints:
   `next      run adk-spec approve let-users-sign-in-with-a-passkey`

#### Step 2 — Review & Edit the Drafts (`brief.md`, `specs/`, `design.md`, `tasks.md`)
All files under `.spec/changes/let-users-sign-in-with-a-passkey/` are plain Markdown—edit any requirement, assumption, or task by hand before approving. (Or revise it by instruction `[Built: P11]`: `adk-spec propose "Use Redis for challenge storage" --id let-users-sign-in-with-a-passkey`.)

#### Step 3 — `approve` (Auto-base + Structural & Semantic Check + Freeze Approval)
```bash
adk-spec approve let-users-sign-in-with-a-passkey
```
What happens inside `approve` `[Built]`:
- Captures missing base SHA-256 fingerprints against `.spec/specs/` and records your starting Git commit (`base_commit`).
- Runs deterministic structural + 100% requirement-to-task checks AND the LLM consistency `check` (dropping any LLM finding that doesn't quote real file text), writing `reports/check.md`.
- Blocks cleanly if anything `ERROR`/blocking is found (never silently passing broken plans; you either fix the files or rerun with `--override "<reason>"` after seeing `reports/check.md`).
- Records `by`, `at`, and SHA-256 hashes of every change file in `change.json`. An approval of other files than the last
  one drops that verification: a change edited since is verified again. Approved again as it stands, a verified change
  stays verified, and its `reports/summary.md` names the new approval.
- Before you approve, read `reports/review.md` `[Built: P16]`: each requirement the change adds, whole; each it removes,
  with its reason and as the living spec holds it; each it modifies, as a diff against the living spec. Each command that writes a change and leaves it
  waiting on an approval writes the view again and names it on a `review` line, with the open changes that modify or
  remove the same requirements; a command refused, and `status`, write nothing. Once a change is approved, `approve`
  names those on a `note` line: whichever is archived second is stopped, to be reworked onto the first. A spec
  edited by hand is in the view once a command writes it again: `check --no-model` does, and calls no model. A new
  capability's view shows the purpose its living spec opens on.

#### Step 4 — Implement with Your Coding Agent (VS Code Copilot / Claude Code / Cursor)
Point your coding agent at `.spec/changes/let-users-sign-in-with-a-passkey/` (`brief.md`, `context.md`, `specs/`, `design.md`, `tasks.md`) and have it implement each task and tick boxes (`- [x] T001 ...`). **Ticking `- [x]` never voids approval** `[Built]`.

#### Step 5 — `verify` (Run Tests + Quote-Grounded Diff Verdict)
```bash
adk-spec verify let-users-sign-in-with-a-passkey
```
What happens inside `verify`:
- **Phase 9 `[Built]`:** Runs your `[verify] test` command (`uv run pytest -q`) first, says what it runs, and shows the model and the report the end of its output, scrubbed. A failing run blocks "verified" whatever the verdicts, unless `--override "<reason>"`.
- **Phase 3 & 6 `[Built]`:** Computes the real diff (tracked + untracked non-ignored files, minus `.spec/`, `[repository] exclude`, and private-key files), scrubs secret shapes, asks the LLM for per-requirement verdicts (`met`/`unmet`/`unclear`) with exact line quotes, and **downgrades any `met` whose quote isn't literally in the diff to `unclear`**.
- Writes `reports/verify.md`. Re-run `verify` as many times as you need while finishing code! Once all requirements read `met`, `next` says `run adk-spec archive ...`.
- **Phase 16 `[Built]`:** also writes, as one set with the record, the change's `evidence.md`: each quote a `met` verdict of
  a requirement the change adds or modifies was grounded on, one line each, a quote over a secret left out. Then
  `reports/summary.md`, Markdown to paste into the pull request, and, where a requirement is not shown met,
  `reports/remaining.md`: per requirement, what code found first (a task ticked yet unmet, files its tasks named that the
  work never touched), then the model's reason. The `next` line names the unmet requirements and the file.

#### Step 6 — `archive` (Fold Deltas into Canonical Living Truth)
```bash
adk-spec archive let-users-sign-in-with-a-passkey
```
- Confirms approval is still valid, diff hasn't drifted since `verify`, and no concurrent change modified the same requirement base SHA-256.
- Atomically merges `ADDED` / `MODIFIED` / `REMOVED` blocks into `.spec/specs/auth/spec.md` and marks the change `archived`.
- **Phase 16 `[Built]`:** in the same write, folds the change's evidence into `.spec/specs/auth/evidence.md` (a requirement
  it adds or modifies gets its lines, one it removes loses them) and puts an entry above the others in
  `.spec/changelog.md`; one with a code fence never closed is left, and the archive says the entry was not added,
  since where it goes is then a guess. Later, `validate` and `status` look for each kept quote in the code, in its
  file and then across its repository: a requirement none of whose quotes is found is noted as suspect (INFO, never a
  CI failure). Delete its lines in a reviewed commit, or verify a change that keeps it, to clear it.
- **Phase 17 `[Built]`:** `verify` prints one `note` where every line that proved a living requirement the change
  does not name is gone from the code, in files the work changed (a moved file by either name).
  `status`, and `propose` before it spends anything, say on one line how many of `.spec/profile.md`'s quotes are no
  longer in the code (a library's quote, or one git cannot look for, is not counted): `init --refresh` reads it
  again. A drafted task keeps `[P]` only where it names its files and none is a file of the task before or after it.
- `validate` is also a merge gate `[Built: P16]`: `change.approval-void` (an approved change edited since) and
  `change.work-drifted` (verified work that moved, where the tier owes a verification) are warnings that fail
  `--strict`; under GitHub Actions each finding is also an annotation on its line, and a summary goes on the run's page.

---

### Use Case 3: Cross-Repository Full-Stack Feature (Phases 7 and 9 `[Built]`)

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

### Use Case 4: Small Bug Fix (`lean` 3-Command Path) vs. Trivial Edit (`none`) (Phases 5 and 10 `[Built]`)

**Scenario A — Small focused bug fix inside one capability (`lean`):**
```bash
# The model sizes it, and may call a fix that touches security, money or data strict; --tier lean says it by hand:
adk-spec propose "Fix the crash when the export runs on an empty month."

# Fast 3-command loop (no design, no check, no verify owed):
adk-spec approve fix-the-crash-on-an-empty-month
# ... fix bug + add unit test ...
adk-spec archive fix-the-crash-on-an-empty-month
```

**Scenario B — Typo / comment / throwaway tweak (`none`):**
```bash
adk-spec propose "Fix typo in README install header."
# Output:
# no spec is owed: Cosmetic documentation edit with no behavioral change.
# Exits cleanly with no .spec/changes/ folder created!
```

---

### Use Case 5: Mid-Flight Scope Changes & Parallel Team Spec Conflicts (Phases 1 and 11 `[Built]`)

**Scenario A — Requirements change while implementing:**
- **Manual route `[Built]`:** Edit `.spec/changes/<id>/brief.md` or delta `spec.md`, then run `adk-spec plan <id>` (re-generates tasks only; add `--replace` if tasks were already ticked). Any edit voids the old approval, forcing a fresh `approve`.
- **Instruction route `[Built: P11]`:** Revise brief, delta specs, and tasks directly from natural language without adding another subcommand. Each requirement keeps its ID by its name, the output lists what was added, changed and dropped, a ticked task keeps `tasks.md`, and an approved change whose files changed is approved again:
  ```bash
  adk-spec propose "Also support 8-digit one-time backup codes when no authenticator is present." \
    --id let-users-sign-in-with-a-passkey
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

### Use Case 6: High-Risk / Compliance Feature — `strict` Tier (Phase 13 `[Built]`)

**Scenario:** Modifying payment ledger reconciliation, multi-tenant RBAC isolation, or PII encryption where mistakes are expensive.

```bash
# 1. Start in strict mode [Built: P13]:
adk-spec propose "Migrate billing webhooks to idempotent double-entry ledger." --tier strict
```

What `strict` adds on top of `standard` `[Built: P13]`:
1. **A stop for reading:** `propose` writes `brief.md` and the delta specs, then stops before exploration, design and tasks (`plan waits: a strict change is read first`). Read and edit them, or revise by instruction, then run the `plan` the line names.
2. **Mandatory `design.md`:** Always owed regardless of what the brief says; `plan` drafts it, and keeps one you wrote or edited unless `--replace`.
3. **Warnings block too:** A warning of the check, the model's or the code's, blocks the approval as an error does, and `approve --override` is refused: the finding is fixed. (`verify --override "<reason>"` is kept, as on standard.)
4. **Dual-Approver Accountability:** Requires **two different names**, compared without case, recorded in `change.json` before verify and archive can proceed; an edit between the two voids the first:
   ```bash
   adk-spec plan migrate-billing-webhooks
   adk-spec approve migrate-billing-webhooks --by alice
   adk-spec approve migrate-billing-webhooks --by bob
   # Implement, then verify (the tests run first) and archive:
   adk-spec verify migrate-billing-webhooks
   adk-spec archive migrate-billing-webhooks
   ```

---

### Use Case 7: Switching Providers, Lessons Feedback Loop, Visual Inspection & Benchmarking (Phases 2, 3, 6 and 12 `[Built]`)

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
- **Workspace self-improvement (`lessons`) `[Built: P12]`:**
  `.spec/lessons.md`, shared through git, is read by every drafting stage within 6,000 characters. Write a correction you made in one line under "From people"; adk-spec adds a line under "Sent back by a gate" each time a gate sent a draft back and the next try put it right, and counts it when it comes back, in code, with no model call. `approve` names a drafted file you edited, once, so that you can write down what you corrected.

---

## 5. End-State `.spec/` Directory Map & Command Cheat Sheet

### What Lives in `.spec/`

```text
.spec/
├── .gitignore                        # Ignores .lock [Built]
├── .lock                             # Writer lock: its process & machine; taken over where that process ended
├── config.toml                       # [project] default_tier, [limits], [repository] exclude, [verify] test
├── constitution.md                   # Short, versioned rules with reasons (rules drafted by init, P8)
├── profile.md                        # What the repository is and where things live, quoted [Built: P8]
├── lessons.md                        # People's corrections and what gates sent back, in git [Built: P12]
├── changelog.md                      # An entry per archived change, newest first [Built: P16]
├── runs/                             # Auto-gitignored *.json scrubbed stage recordings (keep_runs=20) [Built]
├── specs/
│   └── <capability>/
│       ├── spec.md                   # Living canonical truth (## Purpose, ## Requirements, ## Retired) [Built]
│       └── evidence.md               # The lines verify proved each requirement with, one a line [Built: P16]
└── changes/
    └── <change-id>/
        ├── change.json               # Tier, status, base hashes, approval hashes, commit(s), verify state [Built]
        ├── brief.md                  # Why, what changes, non-goals, capabilities, impact, assumptions [Built]
        ├── context.md                # Multi-repo quote-verified code notes & ## What is still unknown [Built P6–P7]
        ├── design.md                 # Context, goals, decisions, risks (when owed / always in strict) [Built]
        ├── tasks.md                  # Vertical T### [P] [REQ-...] checklist (`files` + `verify`) [Built]
        ├── specs/<cap>/spec.md       # Delta spec: ADDED / MODIFIED / REMOVED [Built]
        ├── evidence.md               # What its last verify proved, folded in at archive [Built: P16]
        └── reports/                  # check.md, verify.md; review.md, summary.md, remaining.md [Built: P16]
```

### Quick Command Reference (Grouped Like `adk-spec --help`)

| Group | Command | Purpose |
| --- | --- | --- |
| **Everyday** | `adk-spec init` | Initialize `.spec/`, read the code into `profile.md` and draft rules (`--no-explore`, `--refresh`) |
| | `adk-spec propose "<request>"` | Clarify + draft brief/deltas + explore code (with `--with` repos) + plan; with `--id` of an open change, revise it |
| | `adk-spec approve <id>` | Auto-base + run structural & LLM `check` + record SHA-256 approval & start commits |
| | `adk-spec verify <id>` | Run the tests + judge diffs across all repos with quote-grounded evidence |
| | `adk-spec archive <id>` | Fingerprint-guarded atomic merge into `.spec/specs/<cap>/spec.md` |
| | `adk-spec status [--all]` | Show open changes grouped by *Waiting on you* / *Ready to run* / *Done* |
| **Redo One Step** | `adk-spec plan <id>` | Explore (if no `context.md`) & re-draft `design.md` + `tasks.md`, keeping ticked tasks and an edited design unless `--replace` (`--with`) |
| | `adk-spec check <id>` | Re-run cross-artifact analysis (`--no-model` for pure-Python offline checks) |
| | `adk-spec rebase <id>` | Refresh stale requirement base fingerprints after concurrent archives |
| | `adk-spec validate [id]` | Offline lint of living specs and open changes (`--strict`, `--json`) |
| | `adk-spec new <id>` | Scaffold an empty hand-written change folder |
| **Assistant** | `adk-spec-mcp [--root]` | MCP server over stdio: `propose`, `plan`, `check`, `verify`, `status`, `validate` as tools; `approve`/`archive` stay in the terminal (see README) |
| **Setup** | `adk-spec login [--force]` | 15-minute GitHub Copilot OAuth device flow (`--force` re-authenticates) |
| | `adk-spec models [--json]` | Query active arm's live model catalog with zero model tokens spent |
| | `adk-spec smoke [--check]` | Offline config check (`--check`) or single schema-bound smoke call |

### Phase 15: research during planning (`[Built]`)

The owner decided on 23 November 2026, in grilling rounds, how a change is researched before it is planned. `propose` sizes the request alone (one owing no spec spends no reading), reads the code that matters for it, its installed libraries too (`python:httpx/_client.py`, `node:react/index.js`, read offline at the versions installed), and only then drafts the brief and the specs from what was kept and from `profile.md`, never asking you what those show. The brief's open points name what they wait on: a round asks only those answerable now, and `=` takes a suggestion, and `yes` takes one that is itself a yes. Rules taken from the skills the owner pointed to sit in the stages: the brief invents nothing and keeps an answer's numbers and negatives; scenarios are written so a run could show them false; tasks make the change easy first and start a bug fix with a failing test; the check finds a requirement that softens the brief. Company documentation and web search were set aside for now.

### Phase 14: inside a coding assistant (`[Built]`)

The owner decided on 22 November 2026 how `adk-spec` is used alongside the terminal: **inside coding assistants, as an MCP server**, and it is built. `adk-spec-mcp` serves `propose` (revising too), `plan`, `check`, `verify`, `status` and `validate` as tools to VS Code GitHub Copilot and Claude Code, each run as the terminal runs it, on adk-spec's own models, with the same files, checks and approvals; points a brief leaves open come back in the output for the assistant to put to you. Approving and archiving stay yours, in a terminal, and so does naming another repository: a change spanning several starts with `propose --with` in a terminal, and the tools keep them. The README shows the `.vscode/mcp.json` and `claude mcp add` setup. A standalone Web Workbench or TUI was not chosen.