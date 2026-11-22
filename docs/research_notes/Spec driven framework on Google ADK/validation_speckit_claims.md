# Validation of Spec Kit claims

Fact-check of the Spec Kit claims in two documents against the Spec Kit repository and docs site.
Scope is Spec Kit only; OpenSpec and Google ADK claims in the comparative report were not checked here.

## 1. What this was validated against

| Item | Value |
| --- | --- |
| Documents validated (frozen snapshot, 2026-11-20 23:16 CET) | `research_notes/02-speckit-research-notes.md` (all of it) and `reports/01-spec-frameworks-comparative-analysis.md` (Spec Kit claims only) |
| Repository clone | `github/spec-kit`, shallow clone, commit `a4d571229e164e440f8950cac034607bae7b7518` |
| Commit date | 2026-11-20 15:50:41 UTC (16:50:41 CET), "fix(extensions): describe extension list options accurately (#5496)" |
| Is that commit current? | Yes. The GitHub commits API returned the same hash as the head of `main` at validation time. |
| Version in the clone | `pyproject.toml:3` says `1.4.4.dev0` (development version after the 1.4.3 release) |
| Latest release | `v1.4.3`, published 2026-11-19 14:31 UTC (GitHub releases API); PyPI `specify-cli` latest is also `1.4.3`; `CHANGELOG.md:5` agrees |
| Distance from the release | 7 commits and 21 files after `v1.4.3` (GitHub compare API). None of the files the two documents cite changed in those commits. |
| Docs site | `https://github.github.io/spec-kit/` and five sub-pages returned HTTP 200; the text of `reference/agentic-sdd.html` matched the clone's `docs/reference/agentic-sdd.md` on the passages spot-checked |
| URLs used | `https://api.github.com/repos/github/spec-kit/releases`, `.../commits`, `.../compare/v1.4.3...a4d5712`, `https://pypi.org/pypi/specify-cli/json`, `https://github.github.io/spec-kit/` |

Method and limits:

- Everything was checked by reading files. No Spec Kit script, installer or test was run, so behaviour such as the MCP response cap and gate handling is confirmed from documentation and source code, not from execution.
- Evidence is given as a path relative to the clone root, with line numbers.
- 66 claims were checked: 43 from the research notes and 23 from the comparative report. The second set overlaps the first, because the report repeats the notes.

## 2. Overall reliability

### `02-speckit-research-notes.md`: mostly reliable on mechanics, unreliable on how strongly things are enforced

| Verdict | Count |
| --- | --- |
| CONFIRMED | 29 |
| PARTLY RIGHT | 13 |
| WRONG | 1 |
| OUTDATED | 0 |
| UNVERIFIABLE | 0 |
| Total | 43 |

- All 22 source files it lists exist, and the one direct quotation appears verbatim. Nothing was fabricated.
- File names, directory layouts, command order, template structure, numeric limits and the read/write rules of `analyze` and `converge` are accurate.
- The one flat error is the clarify taxonomy: it has 10 categories, not 7.
- The 13 partly right claims share one pattern: guidance, conventions and prompt text are described as if Spec Kit enforced them ("enforces", "authority model", "immutable", "strict-contract gates").

### `01-spec-frameworks-comparative-analysis.md` (Spec Kit claims): usable as a summary, not as a specification

| Verdict | Count |
| --- | --- |
| CONFIRMED | 13 |
| PARTLY RIGHT | 9 |
| WRONG | 1 |
| OUTDATED | 0 |
| UNVERIFIABLE | 0 |
| Total | 23 |

- The version (`v1.4.3`) is correct and current.
- It repeats the notes' errors (7 clarify categories, immutable constitution, authority model, "often gitignored").
- It adds three of its own: a citation to a file that does not contain the cited content, a "strict" preset that does not exist, and a classification of Spec Kit as "spec-anchored" that Spec Kit's own docs do not support.

## 3. Claims checked: research notes

Section numbers refer to the notes.

| # | Claim (section) | Verdict | Evidence | Correction |
| --- | --- | --- | --- | --- |
| A1 | The 22 listed source files exist (header) | CONFIRMED | All 22 paths present in the clone | |
| A2 | Spec Kit is `specify-cli`, Python, installed with `uv` (§1) | CONFIRMED | `pyproject.toml:2,6`; `README.md:73,80` | |
| A3 | Entry points are separate, independent processes: core SDD, bug fixing, idea assessment (§1) | CONFIRMED | `README.md:34` ("independent entry points, not mandatory phases") | Bug and assess are bundled extensions that must be installed; only SDD is in core |
| A4 | Core order is constitution, specify, clarify, plan, checklist, tasks, analyze, implement, converge (§1) | CONFIRMED | `docs/reference/agentic-sdd.md:15` | Only specify is required before plan; clarify, checklist and analyze are optional (`agentic-sdd.md:5`). The README's minimal flow has six commands (`README.md:105-118`) |
| A5 | Terminal outcome is `Converged`, with `tasks.md` left byte-for-byte unchanged (§1, §4) | CONFIRMED | `templates/commands/converge.md:82-83,228-231`; `README.md:121` | |
| A6 | Bug process is `bug-assess`, `bug-fix`, `bug-test`, stored in `.specify/bugs/<slug>/`, verdict `verified`, `partial` or `failed` (§1) | PARTLY RIGHT | `extensions/bug/extension.yml:17-25`; `docs/reference/agentic-bugfix.md:3,51` | Path and verdicts are right. The command ids are `speckit.bug.assess`, `speckit.bug.fix`, `speckit.bug.test`. The names `bug-assess`, `bug-fix`, `bug-test` are the Spec Kit repository's own GitHub workflows, which do not use the bug extension (`docs/guides/agentic-sdlc.md:207-218`) |
| A7 | Assess process has five stages under `.specify/assessments/<slug>/`, verdict `go`, `needs-clarification` or `kill`; `go` hands `decision.md` to specify (§1) | PARTLY RIGHT | `extensions/assess/extension.yml:19-33`; `docs/reference/agentic-assessment.md:21-29,70-74,94-96` | Stages, path and verdicts are right. Command ids are `speckit.assess.<stage>`. The handoff is manual: the user may pass a handoff summary to specify. No hook or workflow step does it (`workflows/assess/workflow.yml:58-62`) |
| A8 | Spec Kit "explicitly separates three distinct authority layers" (regular automation, agent automation, human work) as an authority model (§1) | PARTLY RIGHT | `docs/guides/agentic-sdlc.md:1-11,31-54,289-302` | The three terms are real, but the page is a case study of how the Spec Kit project develops itself. It says the modes "are not an exhaustive taxonomy", that "a stage can combine them", and that the mix "is not a prescribed recipe". Nothing in the tool implements or enforces these layers. "Approve specs/plans" is not in the source text |
| A9 | Quotation: "Running an agent on GitHub Actions does not make its reasoning a deterministic script." (§1) | CONFIRMED | `docs/guides/agentic-sdlc.md:43-44` | |
| A10 | Constitution lives at `.specify/memory/constitution.md`, is created once per project, and carries `Version`, `Ratified`, `Last Amended` (§2) | CONFIRMED | `templates/constitution-template.md:49`; `templates/commands/constitution.md:77`; `README.md:105` | |
| A11 | Constitution holds MUST/SHOULD rules such as library-first, TDD, security, observability, simplicity (§2) | CONFIRMED | `templates/constitution-template.md:6-35` | These are examples inside HTML comments. The template is all placeholders; Spec Kit prescribes no principles |
| A12 | Every downstream command (specify, plan, analyze, converge) treats the constitution as "supreme authority" (§2) | PARTLY RIGHT | `templates/commands/analyze.md:60`; `converge.md:85-88`; `plan.md:64-72`; `specify.md:119` | Analyze and converge call it "non-negotiable". Plan runs a Constitution Check gate. Specify, clarify, tasks, checklist and implement only load it "if exists" as context. The phrase "supreme authority" is not in the repository |
| A13 | A violation of a constitution MUST is automatically `CRITICAL` in analyze and converge (§2) | CONFIRMED | `analyze.md:60,170`; `converge.md:176-177,223-224` | |
| A14 | Spec template has prioritized user stories (P1, P2, P3) with "Why this priority", "Independent Test", Given/When/Then scenarios, and an Edge Cases section (§2) | CONFIRMED | `templates/spec-template.md:26-37,71-79` | |
| A15 | Functional requirements are `FR-###` MUST statements with inline `[NEEDS CLARIFICATION: ...]` markers (§2) | CONFIRMED | `templates/spec-template.md:90-99` | The notes omit the limit: at most 3 markers per spec (`templates/commands/specify.md:132`) |
| A16 | Success criteria `SC-###` are "buildable", "measurable technical criteria", excluding business KPIs during analysis (§2) | PARTLY RIGHT | `templates/spec-template.md:108-118`; `analyze.md:116`; `converge.md:112-113` | The template asks for technology-agnostic outcomes and itself lists a business metric as `SC-004` ("Reduce support tickets ... by 50%"). Only analyze and converge filter such items out when mapping requirements to tasks |
| A17 | `spec.md` covers what and why, with no technology stack (§2) | CONFIRMED | `docs/reference/agentic-sdd.md:53`; `specify.md` "Quick Guidelines" | |
| A18 | Clarify scans a "7-category coverage taxonomy" (§2, §7) | WRONG | `templates/commands/clarify.md:75-123` | There are 10 categories. The notes list the first seven and drop "Terminology & Consistency" (line 113), "Completion Signals" (117) and "Misc / Placeholders" (121) |
| A19 | Clarify marks status Clear, Partial or Missing (§2) | CONFIRMED | `clarify.md:73` | Status is per category, not per item |
| A20 | Clarify asks at most 5 questions and writes the answers into `spec.md` (§2) | CONFIRMED | `clarify.md:2,129-130,178,182-198,233` | The limit is per run; the command can be re-run (`agentic-sdd.md:63`) |
| A21 | Plan declares Language/Version, Primary Dependencies, Storage, Testing, Target Platform, Performance Goals, Constraints, Scale/Scope and checks them against the constitution (§3) | CONFIRMED | `templates/plan-template.md:21-43`; `plan.md:68-72,164` | Also has "Project Type" (line 31) |
| A22 | Plan produces `plan.md`, `research.md`, `data-model.md`, `contracts/` (§3) | CONFIRMED | `templates/plan-template.md:50-56` | Also `quickstart.md` |
| A23 | Contract-driven development guide: contracts define inputs and outputs, validation, error semantics, interaction guarantees, versioning and deprecation (§3) | CONFIRMED | `docs/how-to/contract-driven-development.md:38-46` | |
| A24 | Spec Kit "enforces one authoritative owner per contract", and tasks "explicitly include" provider and consumer contract tests (§3) | PARTLY RIGHT | `contract-driven-development.md:14-16,55-64,94-95,114-115` | This is written guidance only. The page says it "does not introduce automatic contract synchronization" and that Spec Kit "does not publish or synchronize" contracts. Contract tests appear only if the user asks `/speckit.tasks` for them; tests are optional by default (`templates/commands/tasks.md:148`) |
| A25 | A "3-step escalation ladder": scoped execution, sub-agent delegation, spec-of-specs (§3) | PARTLY RIGHT | `docs/how-to/complex-features.md:18-69` | The guide lists four options; the third is "combine both" |
| A26 | `roadmap.md` columns (ID, Sub-feature, Intent, Scope boundary, Depends on, Status, Sub-spec), immutable `R#` ids, worktrees for parallel slices, links in both directions (§3) | CONFIRMED | `docs/how-to/spec-of-specs.md:36-37,62-73,93-105` | It is a hand-maintained Markdown convention: "there is no special tooling behind it" (lines 17-18, 47-48) |
| A27 | `tasks.md` phases: Setup, Foundational (blocks all stories), one phase per user story with the first marked MVP, final Polish (§3) | CONFIRMED | `templates/tasks-template.md:48,58-62,77,150` | |
| A28 | "Every task line" has an id (`T001`), optional `[P]`, a story label (`[US1]`) and a file path (§3) | PARTLY RIGHT | `templates/commands/tasks.md:155-180` | The story label is required only in user-story phases. Setup, Foundational and Polish tasks must not have one (lines 163-168) |
| A29 | Checklist gate: reviewer-owned, "unit tests for requirements"; implement reads the checkbox counts and must not change them (§4) | CONFIRMED | `templates/commands/checklist.md:9-11,32-37,147-148`; `templates/checklist-template.md:8,41`; `implement.md:57-58,81` | Two details are missing. `checklists/requirements.md` is a separate built-in checklist that specify creates and clarify rewrites. When items are unchecked, implement stops and asks; the user can answer "yes" and continue |
| A30 | Analyze: strictly read-only, covers constitution, spec, plan, data-model and tasks, 50-finding cap, six passes, four severities, `Entity.field` citation rule (§4) | CONFIRMED | `analyze.md:58,108-110,125,127-164,168-173` | Its output on CRITICAL findings is a recommendation; nothing blocks implement (`analyze.md:216`) |
| A31 | Converge: append-only, writes only a new `## Phase N: Convergence` section, runs after implement, never edits code, spec, plan or existing tasks (§4) | CONFIRMED | `converge.md:65-66,73-83,204-231`; `docs/reference/agentic-sdd.md:149-158` | |
| A32 | Presets are stackable and priority-ordered and replace templates or commands; `lean` reduces the flow to constitution, specify, plan, tasks, implement (§5) | CONFIRMED | `docs/presets/overview.md:3-7,48-59`; `presets/lean/preset.yml:15-45`; `presets/lean/README.md:3-21` | Presets also cover scripts and can prepend, append or wrap (`overview.md:84-96`). `lean` replaces five command prompts; it does not uninstall clarify, checklist, analyze or converge. The lean plan prompt drops the Constitution Check gate (`presets/lean/commands/speckit.plan.md`) |
| A33 | Extensions add commands and `before_*` / `after_*` hooks, registered in `.specify/extensions.yml` (§5) | CONFIRMED | `docs/extensions/overview.md:434-461`; `docs/extensions/api.md:708-760` | |
| A34 | `workflows/speckit/workflow.yml` chains commands, shell steps and resumable gates `review-spec` and `review-plan`, with verdict inputs and run ids (§5) | PARTLY RIGHT | `workflows/speckit/workflow.yml:43-80`; `docs/workflows/overview.md:27-65` | Gates, verdict inputs and run ids are right. The file has no shell steps. It chains only specify, plan, tasks and implement; constitution, clarify, checklist, analyze and converge are not in it. Shell steps exist as a step type (`docs/workflow-steps/types.md:11`) |
| A35 | Overlays use `insert_after`, `insert_before`, `replace`, `remove`, with lower-number-wins integer priority (§5) | CONFIRMED | `docs/workflows/overlays.md:9,56-71` | Default priority is 10. Overlays cannot change inputs or target steps added by other overlays (lines 173-181) |
| A36 | `specify mcp` is read-only over stdio, uses `FileHelper` to reject symlinks and junctions, caps responses at 1 MiB (`response_too_large`), limits pages to 1000 items, returns `code`, `message`, `details`, `retryable` (§5) | CONFIRMED | `docs/overview/mcp.md:3-5,11-13,20-21,33,73-79,85-90`; `src/specify_cli/artifacts/mcp_list.py:25,227-233` | The server is marked experimental. It exposes only version, artifact inventory and installed-workflow listing. The docs say the checks "do not provide an OS sandbox" |
| A37 | No unified living spec or delta model; specs are per feature and "often gitignored after delivery"; no built-in delta merge or automatic reconciliation (§6.1) | PARTLY RIGHT | `docs/how-to/evolving-specs.md:40-44`; `docs/how-to/persisting-specs.md:3-8,84-102,129-133` | No delta merge and no reconcile command: correct. "Often gitignored" is unsupported. The docs describe four persistence models, say "none is the default", and include a "living spec" model. Only Spec Kit's own repository ignores `specs/`. `specify init` ignores only `feature.json` and local extension config (`docs/overview/core.md:88`) |
| A38 | "High default ceremony" is a documented limitation of the full nine-command path (§6.2) | PARTLY RIGHT | `docs/reference/agentic-sdd.md:5`; `README.md:105-118` | None of the three cited sources states this. The nine-command path is not the default; three of the nine are optional. The nearest source text is in the lean preset README ("without the ceremony of the full templates") |
| A39 | Hooks depend on the LLM reading `.specify/extensions.yml`, filtering `enabled` and `condition`, and remembering to run mandatory hooks (§6.3) | PARTLY RIGHT | `clarify.md:23-54`; `docs/extensions/api.md:746-768` | Correct except for `condition`. The templates tell the model not to evaluate conditions and to skip any hook that has one. Hook `priority` is also ignored by the templates, and `auto_execute_hooks` is reserved and unused |
| A40 | "Immutable `constitution.md` authority" (§7) | PARTLY RIGHT | `spec-driven.md:276,380-398`; `templates/commands/constitution.md:2,99-103,127` | The philosophy page uses the word "immutable", but the command "creates or updates" the file, bumps its version by semantic-versioning rules and overwrites it. Operationally the constitution is amendable and versioned |
| A41 | Analyze and converge are pure LLM prompt runs (§7) | CONFIRMED | No analysis or convergence logic exists under `src/` or `scripts/`. The only script they call checks that files exist (`scripts/bash/check-prerequisites.sh:138-168`) | |
| A42 | Hooks are enforced through Markdown prompts, not runtime code (§7) | CONFIRMED | `src/specify_cli/extensions/__init__.py:6482-6487` ("The actual execution is delegated to the AI agent") | See omission 8 below: runtime events are a separate, script-executed mechanism |
| A43 | Spec Kit has no lightweight `config.yaml` that splits context, rules and guidance (§7) | CONFIRMED | No such file among the `.specify/` paths the docs reference (`init-options.json`, `extensions.yml`, `feature.json`, catalogs) | Project guidance lives in the constitution, preset layers and `.specify/templates/overrides/` |

## 4. Claims checked: comparative report (Spec Kit only)

| # | Claim (location) | Verdict | Evidence | Correction |
| --- | --- | --- | --- | --- |
| B1 | Spec Kit version is `v1.4.3` (summary, table header) | CONFIRMED | GitHub releases API: `v1.4.3`, 2026-11-19; PyPI `1.4.3`; `CHANGELOG.md:5` | |
| B2 | "Immutable `constitution.md`"; "immutable project axioms" (summary, harvested 1) | PARTLY RIGHT | Same as A40 | Treat as amendable and versioned |
| B3 | "Human/Agent/Script authority separation" is a Spec Kit feature (summary, table, harvested 1) | PARTLY RIGHT | Same as A8 | It is a description of the project's own practice, not a mechanism |
| B4 | Clarify is a "7-dimension" scan (summary, table, harvested 2) | WRONG | `templates/commands/clarify.md:75-123` | 10 categories. The Clear/Partial/Missing statuses and the 5-question limit in the same cells are correct |
| B5 | Read-only six-pass analyze, reviewer-owned checklist, append-only converge, phased `tasks.md` with `T###`, `[P]`, `[US#]` (summary, table, harvested 3 and 4) | CONFIRMED | Same as A27, A29, A30, A31 | |
| B6 | Core philosophy "structured engineering rigor, constitution-governed quality gates", cited to `docs/overview/core.md` (table) | PARTLY RIGHT | `docs/overview/core.md:1-3` | Citation error. That file is the CLI reference for `init`, `check`, `version` and `mcp`. The philosophy is in `docs/how-to/sdd.md` and `spec-driven.md`. The README frames Spec Kit as a toolkit of processes you can customize or replace (`README.md:34`) |
| B7 | Python CLI `specify-cli` via `uv` or `pipx`, plus integrations, presets, bundles (table) | CONFIRMED | `pyproject.toml:2`; `docs/install/uv.md`, `docs/install/pipx.md`; `bundles/` | |
| B8 | Layout is "feature-scoped `.specify/`" plus `specs/###-feature-name/`, "often gitignored after delivery" (table) | PARTLY RIGHT | `templates/commands/specify.md:86-106`; `docs/how-to/persisting-specs.md:3-8,129-133` | `.specify/` is project-scoped. Feature directories are `specs/<prefix>-<short-name>/`, where the prefix is a 3-digit number or a timestamp. "Often gitignored" is unsupported (see A37) |
| B9 | "Greenfield-strong"; manual reconciliation for evolving specs (table) | PARTLY RIGHT | `docs/how-to/evolving-specs.md:40-44`; `docs/how-to/existing-projects.md:1-5` | Manual reconciliation is correct. "Greenfield-strong" is the report's judgement; Spec Kit documents adoption in existing projects and ships bug fixing for existing code |
| B10 | Core SDD plus YAML `workflow.yml` plus overlays (table) | CONFIRMED | `workflows/speckit/workflow.yml`; `docs/workflows/overlays.md` | |
| B11 | Multi-process: core SDD, `assess` (go / needs-clarification / kill), `bug` (verified / partial / failed) (table) | CONFIRMED | Same as A3, A6, A7 | |
| B12 | Versioned `.specify/memory/constitution.md` with MUST/SHOULD rules as the governing authority (table) | CONFIRMED | Same as A10, A13 | Repository wording is "non-negotiable" |
| B13 | Resumable workflow gates `review-spec`, `review-plan`, plus command handoffs (table) | CONFIRMED | `workflows/speckit/workflow.yml:50-68`; `handoffs:` front matter in `templates/commands/{constitution,specify,clarify,plan,tasks}.md:3` | |
| B14 | Stackable presets (for example `lean`), extensions, overlays with `insert_after`, `replace`, `remove` (table) | CONFIRMED | Same as A32, A33, A35 | |
| B15 | Scale: scoped implement, sub-agents, shallow `roadmap.md`, `contracts/` (table) | CONFIRMED | Same as A25, A26 | Conventions only. Monorepo support (`docs/how-to/monorepo.md`, `SPECIFY_INIT_DIR`) is not mentioned |
| B16 | Machine contract is a read-only experimental `specify mcp` with symlink and junction checks and a 1 MiB cap (table) | CONFIRMED | Same as A36 | The CLI also has JSON contracts the report omits: `specify artifact list --json`, `specify version --json`, `specify workflow status --json` |
| B17 | Failure modes: no built-in delta merge; hooks and write boundaries enforced through prompts (table) | CONFIRMED | Same as A37, A41, A42 | |
| B18 | Spec Kit "lacks a unified living-spec / delta-merge model", cited to `docs/how-to/evolving-specs.md` (summary) | PARTLY RIGHT | `evolving-specs.md:40-44`; `persisting-specs.md:84-102` | No delta merge: correct. A "living spec" model is documented as one of four team conventions |
| B19 | Spec Kit is "Level 2: Spec-Anchored", with living repository specs (maturity table) | PARTLY RIGHT | `docs/how-to/persisting-specs.md:24-39,104-133,155` | Spec Kit says the persistence model "is a team convention, not a CLI setting". Its own repository uses the constitution-only model, which the page calls "a spec-first lifecycle choice" |
| B20 | Dedicated assess and bugfix pipelines, cited to `extensions/assess/extension.yml` and the two how-to pages (harvested 5) | CONFIRMED | `extensions/assess/extension.yml`; `bundles/{assess,bugfix}/bundle.yml` | |
| B21 | "Stackable presets (`lean` vs. strict)" (harvested 6) | PARTLY RIGHT | `presets/catalog.json` (entries: `lean`, `constitution-sync`) | There is no "strict" preset. The contrast is `lean` versus the core defaults |
| B22 | Spec Kit relies on prompt-only enforcement for analyze's read-only rule, checklist ownership and hooks (blind-spot table) | CONFIRMED | Same as A29, A30, A42 | Workflow gates and step ordering are enforced by the workflow engine, not by prompts |
| B23 | Spec Kit shares the blind spots of single-model assumptions and parallel working-tree collisions (summary, blind-spot table) | PARTLY RIGHT | `docs/workflow-steps/types.md:163-232`; `docs/overview/core.md:84`; `docs/how-to/spec-of-specs.md:36-37` | Workflow steps accept a per-step `integration`, `model`, `reasoning_effort` and `context_size`. The docs prescribe separate worktrees and `SPECIFY_FEATURE_NO_PERSIST` for concurrent agents. There is no automatic model fallback |

## 5. Errors that matter most for a framework design

1. **Clarify has 10 categories, not 7.** A design that copies the seven listed ones loses terminology consistency, completion signals (testable acceptance criteria) and the placeholder and vague-adjective scan (`clarify.md:113-123`).
2. **The constitution is amendable, not immutable.** `/speckit.constitution` updates it with semantic-version bumps and a Sync Impact Report. A design needs an amendment path and a version field, not a frozen file.
3. **The "authority model" is not a Spec Kit mechanism.** It is three descriptive terms from a case study that says it is "not a prescribed recipe". A design that wants this separation has to build it; there is nothing to port.
4. **The quality gates are optional and advisory.** Clarify, checklist and analyze are "quality gates you add". Analyze only recommends fixing CRITICAL findings, and implement proceeds past unchecked checklists if the user says yes. The bundled `speckit` workflow runs none of them, and not converge either.
5. **Constitution authority is uneven across commands.** Only plan (a gate), analyze and converge (severity rules) act on it. Specify, clarify, tasks, checklist and implement load it as optional context.
6. **Contracts, roadmap and escalation are documentation conventions.** Nothing validates ownership, pins versions, generates contract tests or maintains `roadmap.md`.
7. **Specs are not "often gitignored".** Persistence is an explicit team choice among four documented models, one of which is a living spec. The claim generalizes from Spec Kit's own repository.
8. **Hook conditions are skipped, not evaluated.** A hook with a `condition` is never surfaced by the current command templates, and hook `priority` is ignored.
9. **Story labels are not on every task.** `[US#]` is required in story phases and forbidden in Setup, Foundational and Polish. A parser that requires it everywhere will reject valid files.

## 6. Material omissions

1. **Almost the whole SDD pipeline is prompt text.** The CLI has no code for specify, clarify, plan, tasks, analyze, implement or converge. Its command groups are `init`, `check`, `version`, `mcp`, `self`, `extension`, `integration`, `event`, `preset`, `artifact`, `bundle` and `workflow`. Helper scripts only resolve paths and templates and check that `plan.md`, `spec.md` and `tasks.md` exist. In specify, even creating the feature directory is done by the model (`specify.md:100-106`).
2. **The workflow engine is the one place with code-enforced orchestration.** It has 14 step types (command, prompt, shell, github, init, slot, gate, if, switch, while, do-while, fan-out, fan-in, workflow), persisted run state, and six run states (`docs/workflow-steps/types.md:9-22`; `docs/workflows/cli.md:108`).
3. **Specify has its own validation loop.** It creates `checklists/requirements.md`, allows at most 3 `[NEEDS CLARIFICATION]` markers, asks up to 3 questions, and retries validation up to 3 times (`specify.md:132,150,200`). Clarify later rewrites that checklist (`clarify.md:210-227`).
4. **Clarify mechanics.** One question at a time, each either 2 to 5 options or an answer of 5 words or fewer, with a recommended answer; answers are logged under `## Clarifications` / `### Session YYYY-MM-DD` and saved after each one (`clarify.md:129-198`).
5. **Converge mechanics.** Four gap types (`missing`, `partial`, `contradicts`, `unrequested`); checked boxes are not treated as evidence; no git or diff is used (`converge.md:68-69,147-163`).
6. **Active feature state.** The current feature is recorded in `.specify/feature.json`, with environment overrides. Git branches are optional and come from the `git` extension, which is not installed by default (`docs/overview/core.md:25,81-86`).
7. **Tests are optional by default.** Task generation adds test tasks only on request (`templates/commands/tasks.md:148`), even though the philosophy page describes test-first as non-negotiable. `spec-driven.md` also describes "Nine Articles" and "Phase -1" gates that are not in the current plan template.
8. **Extension runtime events.** Separate from hooks, extensions can bind scripts to agent lifecycle events (`session_start`, `pre_tool_use`, `post_tool_use`, `user_prompt_submit`, `stop`, `session_end`). These run scripts directly, not prompts (`docs/extensions/api.md:793-817`). This is Spec Kit's existing non-prompt enforcement path, and neither document mentions it.
9. **Integration layer.** There are 43 integration packages under `src/specify_cli/integrations/`. Commands are rendered per agent at install time as command files or skills, and the invocation syntax differs by agent (`/speckit.plan`, `/speckit-plan`, `$speckit-plan`) (`docs/reference/agentic-sdd.md:12`; `docs/presets/overview.md:61-65`).
10. **Template resolution stack.** Project overrides, then presets, then extensions, then core, each resolved per file, with `replace`, `prepend`, `append` and `wrap` strategies (`docs/presets/overview.md:48-96`).
11. **Bundles and catalogs.** Bundles package extensions, presets, workflows and steps. Community catalogs are explicitly not audited (`README.md:65`).
12. **Plan details.** The Constitution Check is evaluated twice (before research and after design), and justified violations go in a Complexity Tracking table (`templates/plan-template.md:39-43,106-113`).
