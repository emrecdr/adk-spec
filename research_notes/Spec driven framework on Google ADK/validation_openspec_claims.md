# Validation of OpenSpec claims

Fact-check of two documents against the OpenSpec primary sources. Only factual claims about OpenSpec were checked. The documents were not edited.

## 1. What was validated, and against what

**Files validated** (frozen snapshot taken 2026-11-20 23:16 CET):

| File | Scope |
| --- | --- |
| `research_notes/01-openspec-research-notes.md` (175 lines) | Whole file |
| `reports/01-spec-frameworks-comparative-analysis.md` (96 lines) | OpenSpec claims only. Spec Kit, ADK and industry-pattern claims were not checked. |

**Primary sources:**

| Source | Value |
| --- | --- |
| Clone of `Fission-AI/OpenSpec` | Commit `0c737dc1b543249b38b0f4716816fcf493d894dd`, dated 2026-11-19 22:15:20 +0000, "Version Packages (#2284)". Shallow clone (depth 1). |
| GitHub `main` at check time | Same commit (`https://api.github.com/repos/Fission-AI/OpenSpec/commits`). |
| Latest release | `v2.1.1`, published 2026-11-19T22:26:58Z (`https://api.github.com/repos/Fission-AI/OpenSpec/releases`). Previous: v2.1.0 (2026-11-17), v2.0.0 (2026-11-11), v1.17.0 (2026-11-09). |
| npm | `@fission-ai/openspec` latest = 2.1.1, `engines.node >=22.20.0` (`https://registry.npmjs.org/@fission-ai/openspec/latest`). |
| Website | `https://openspec.dev/` shows v2.1.1 and spells skills `/openspec-propose`; `https://openspec.dev/docs/upgrade-to-2`. |

**Method and limits:**

- The clone was read only (file reads, `grep`, `git log`). Nothing in it was run, so every statement about CLI behavior comes from reading source, tests and docs, not from executing the CLI.
- Paths below are relative to the clone root. `file:N` is a line number at the commit above.
- The clone has no history, so dates of older changes come from `CHANGELOG.md`.

## 2. Reliability verdicts

| File | Verdict | Confirmed | Wrong | Partly right | Outdated | Unverifiable | Total |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `01-openspec-research-notes.md` | Reliable on layout, file formats, schema and config contents. Not reliable on what is enforced by code, on version history, or on the parallel-merge bug. | 36 | 1 | 14 | 2 | 0 | 53 |
| `01-spec-frameworks-comparative-analysis.md` (OpenSpec claims) | Mostly reliable. Repeats the outdated merge-bug claim three times and overstates OpenSpec's quality gates. | 18 | 0 | 5 | 1 | 2 | 26 |

- **Notes:** every cited file exists, and the one direct quotation (N13) is accurate. The philosophy block is a paraphrase laid out like source text (N3). The errors are in interpretation: the notes read prompt-level instructions as enforced rules, and treat a stale planning document as a description of current behavior.
- **Report:** it inherits the notes' errors. Its OpenSpec column in the head-to-head table is otherwise accurate.

## 3. Errors that matter most for a framework design

1. **The "parallel delta data loss" bug is not current behavior.**
   - Both documents present it as an unresolved, silent failure.
   - The exact case they describe has been refused since 1.6.0: `openspec archive` aborts when the main spec holds a scenario the `MODIFIED` block lacks (`src/core/specs-apply.ts:564-569`, `CHANGELOG.md:960`, test at `test/core/archive.test.ts:3374`). `openspec validate` reports the same loss as an ERROR (`src/core/validation/validator.ts:802-812`, `CHANGELOG.md:693`).
   - `openspec-parallel-merge-plan.md` is stale. It cites `src/core/archive.ts:455-526` for `buildUpdatedSpec`; the function now lives at `src/core/specs-apply.ts:169`.
   - None of the plan's remedies exist in `src/` (no `meta.json`, no requirement fingerprints, no `change sync`, no diff3).
   - Residual risk, from reading the code: the guard compares scenario names only (`src/core/parsers/requirement-blocks.ts:687-717`). A stale `MODIFIED` block that keeps every scenario name still overwrites concurrent edits to the requirement text or to a scenario body. I did not run this.
2. **There are two merge implementations, and the documents describe only one.**
   - The CLI (`openspec archive`) does a deterministic whole-block replace with guards.
   - The default skill (`openspec-archive-change`) does not call the CLI archive. The agent merges the specs itself and moves the folder with `mv` (`skills/openspec-archive-change/SKILL.md:153`, `:188`).
   - The skill's merge has different semantics: it keeps scenarios the delta does not mention and treats `ADDED` on an existing requirement as an implicit `MODIFIED` (`skills/openspec-sync-specs/SKILL.md:120`, `:128`, `:255`).
3. **`validate --strict` and `verify` are not gates in the default workflow.**
   - No planning or apply skill tells the agent to run `openspec validate <change>`. Only the sync path runs `openspec validate --specs` on main specs (`skills/openspec-sync-specs/SKILL.md:179`).
   - `verify` is outside the default `core` profile (`src/core/profiles.ts:14`), is advisory (`skills/openspec-verify-change/SKILL.md:72`) and "does **not** block archiving" (`docs/reviewing-changes.md:119`).
   - Incomplete tasks warn but do not block archive (`docs-lab/reference/cli.md:1093`; `skills/openspec-archive-change/SKILL.md:216`).
4. **Most "strict structural rules" are warnings.**
   - WARNING, failing only under `--strict`: the 500-character limit, a missing SHALL/MUST, a scenario without WHEN/GIVEN or THEN, a brief Purpose (`validator.ts:321-340`, `:863-887`, `:1158-1163`, `:1062-1064`).
   - ERROR in normal mode: an ADDED or MODIFIED requirement with no scenario, a change with zero deltas and no `skip_specs`, duplicates and cross-section conflicts, a delta file outside a capability folder, a dropped scenario (`validator.ts:343`, `:379`, `:569`, `:199-207`, `:808`).
   - In a main spec, a requirement with no scenario is only a WARNING (`validator.ts:884-890`).
5. **Two format rules the notes state as requirements are not enforced.**
   - `REMOVED` needs only requirement names. Reason and Migration are schema guidance (`schemas/spec-driven/schema.yaml:99`); the validator checks names only (`validator.ts:404-413`).
   - `SHOULD` is not accepted as a normative keyword. The validator matches `SHALL|MUST` only (`src/core/parsers/requirement-text.ts:52-54`), and the schema says "avoid should/may" (`schema.yaml:104`).
6. **The artifact graph advises; it does not gate.**
   - An artifact is complete when its file exists; the content is not read (`src/core/artifact-graph/state.ts:14-36`, `docs-lab/reference/schemas/schema-yaml.md:91`).
   - Asking for a blocked artifact returns instructions with a warning to "proceed with caution" (`src/commands/workflow/instructions.ts:243`).
   - `design.md` is optional only through its prose instruction, which the skill interprets (`skills/openspec-propose/SKILL.md:133-137`).
7. **OPSX was introduced in 1.0.0, not 2.x** (`CHANGELOG.md:1154-1160`). Version 2.0 removed the `/opsx:*` command files and made skills the only delivery, in `.agents/skills/` (`CHANGELOG.md:84-91`).

## 4. Claims checked: `01-openspec-research-notes.md`

| # | Claim (section) | Verdict | Evidence | Correction |
| --- | --- | --- | --- | --- |
| N1 | Header: the listed source files exist in the repo | CONFIRMED | All cited paths exist at the commit, including `docs/stores-beta/user-guide.md`, `openspec/specs/cli-view/spec.md`, `openspec-parallel-merge-plan.md` | See omission 7.1: `docs/` is the legacy docs tree. |
| N2 | §1: TypeScript/Node.js package `@fission-ai/openspec` | CONFIRMED | `package.json:2-3`, `:59-61` | A standalone install that runs without Node.js also ships (`README.md:197`; `docs-lab/reference/cli.md`, "openspec install"). |
| N3 | §1: five-line philosophy block | PARTLY RIGHT | `docs/concepts.md:7-14` lists four principles; `README.md:29-33` adds "scalable from personal projects to enterprises" | The text after each dash is the author's paraphrase, not source text. "multi-repo team Stores" is not in the source line. |
| N4 | §1: dependencies are enablers; downstream unlocks once upstream exists | CONFIRMED | `docs/opsx.md:52-53`, `docs/concepts.md:458`, `src/core/artifact-graph/state.ts:14-36` | "Exists" means the file exists. See error 6. |
| N5 | §2: directory tree (`config.yaml`, `specs/<capability-path>/spec.md`, `changes/<id>/…`, `changes/archive/`) | CONFIRMED | `docs/concepts.md:55-64`, `:190-198`; `schemas/spec-driven/schema.yaml:6`, `:51`, `:165`, `:200` | |
| N6 | §2: `.openspec.yaml` holds a schema override and optional `skip_specs: true` | CONFIRMED | `src/core/change-metadata/schema.ts:24-62` | Also `created`, `goal`, `affected_areas`, `initiative`, `retire_capabilities`. |
| N7 | §2: `proposal.md` = Why, What Changes, New/Modified Capabilities, Impact; `design.md` = decisions, trade-offs, migration plan | CONFIRMED | `schemas/spec-driven/templates/proposal.md:3-32`; `schema.yaml:177-184` | The design template has four headings only (`templates/design.md:3-19`). Migration Plan and Open Questions appear only in the instruction. |
| N8 | §2: archive entry is an "immutable completed record after delta sync" | PARTLY RIGHT | Path format: `skills/openspec-archive-change/SKILL.md:112`, `:188`; `docs/concepts.md:549` | Nothing states or enforces immutability. Archive can also run without a sync ("Archive without syncing", `SKILL.md:132-138`; CLI `--skip-specs`). |
| N9 | §2: Stores are standalone Git planning repos, registered once per machine, with `.openspec-store/store.yaml` | CONFIRMED | `docs/stores-beta/user-guide.md:23-35`, `:3` (beta) | |
| N10 | §2: store rule 1, OpenSpec never clones, pulls or pushes | CONFIRMED | `docs/stores-beta/user-guide.md:47-48`, `:419` | |
| N11 | §2: store rule 2, declarations change visibility only; commands act on `--store <id>` | PARTLY RIGHT | Wording: `user-guide.md:49-51`. `planningHome.root`: `docs/agent-contract.md:61` | A `store:` line in `openspec/config.yaml` and the global `defaultStore` also redirect commands (`user-guide.md:134`, `:156`; `docs/agent-contract.md:30-36`). |
| N12 | §3: specs use RFC 2119 keywords `MUST`, `SHALL`, `SHOULD` | PARTLY RIGHT | `docs/concepts.md:120` lists SHOULD | Schema and validator accept SHALL/MUST only (`schema.yaml:104`, `src/core/parsers/requirement-text.ts:52-54`). A SHOULD-only requirement is a WARNING. |
| N13 | §3: boundary heuristic quote | CONFIRMED | `schema.yaml:71-72`; `docs/concepts.md:152-153` | |
| N14 | §3: requirement description limited to 500 characters for ADDED and main specs; `--strict` fails above it | CONFIRMED | `schema.yaml:109`; `src/core/validation/constants.ts:11`; `validator.ts:334-340`, `:878-883`, `:1062-1064` | 2.1.1 also warns when a MODIFIED block grows past the limit (`validator.ts:789-801`, `CHANGELOG.md:23`). |
| N15 | §3: scenarios need exactly four hashes with WHEN/GIVEN and THEN; three hashes or bullets "fail silently in the parser" | PARTLY RIGHT | `schema.yaml:105-108`; `requirement-text.ts:31` | Not silent: a delta requirement left with no level-4 child is an ERROR (`validator.ts:343`, `:379`). Missing WHEN/THEN is a WARNING (`validator.ts:1158-1163`). Any `####` child counts as a scenario, labeled or not. |
| N16 | §3: new-capability delta starts with `## Purpose` (50+ chars); existing-capability deltas must omit it "so archive doesn't overwrite or generate `TBD` placeholders" | PARTLY RIGHT | `schema.yaml:111-119`; `templates/spec.md:3-4`; `constants.ts:7` | The rationale is wrong. For an existing capability the delta Purpose is ignored with a warning (`specs-apply.ts:381-399`). The TBD placeholder appears when a new capability has no Purpose (`constants.ts:20-21`). |
| N17 | §3: delta files live at `changes/<id>/specs/<capability-path>/spec.md` with four operators | CONFIRMED | `schema.yaml:96-100`; `validator.ts:199-207` | |
| N18 | §3: `## ADDED Requirements` adds requirements and scenarios | CONFIRMED | `schema.yaml:97`; `specs-apply.ts:580-606` | Archive fails if the name exists with different content. |
| N19 | §3: `MODIFIED` needs the whole requirement block; partial content "drops uncopied scenarios on archive" | PARTLY RIGHT | Rule: `schema.yaml:127-134` | The parenthetical is outdated. Archive and validate now refuse a block that omits a current scenario (`specs-apply.ts:564-569`, `validator.ts:802-812`). |
| N20 | §3: `REMOVED` "must include" Reason and Migration | PARTLY RIGHT | Guidance: `schema.yaml:99` | Not enforced. See error 5. |
| N21 | §3: `RENAMED` uses `FROM:`/`TO:` and changes the header only | CONFIRMED | `schema.yaml:100`; `specs-apply.ts:461-520` | Unpaired FROM/TO lines are an ERROR (`validator.ts:244-249`). |
| N22 | §3: zero-delta change rejected unless `.openspec.yaml` sets `skip_specs: true` | CONFIRMED | `validator.ts:527-571`; `schema.yaml:36-42`; `constants.ts:37-43` | The marker plus any file under `specs/` is itself an ERROR (`validator.ts:559-561`). |
| N23 | §4: "OpenSpec 2.x replaced hardcoded TypeScript workflow prompts with OPSX" | WRONG | `CHANGELOG.md:1154-1160` ("OpenSpec 1.0 — The OPSX Release"); `docs/opsx.md:13-20`; `CHANGELOG.md:84-91` | OPSX arrived in 1.0.0. 2.0 made skills the only delivery and removed `/opsx:*` command files. |
| N24 | §4: schema defines `proposal` → `specs` and `design` → `tasks` requiring both; `apply` requires `tasks`, tracks `tasks.md` | CONFIRMED | `schema.yaml:48`, `:161-162`, `:196-197`, `:264-270` | |
| N25 | §4: `relativePathSchema` validates `generates`, `template`, `tracks`; rejects absolute paths, drive letters, `..`, null bytes | CONFIRMED | `src/core/artifact-graph/types.ts:4-22`, `:31`, `:33`, `:43` | |
| N26 | §4: Kahn's sort with ties broken by declaration order, formerly alphabetical | CONFIRMED | `src/core/artifact-graph/graph.ts:20-38`, `:92-139` | |
| N27 | §4: schema precedence is CLI flag, change metadata, project config, default | CONFIRMED | `docs/opsx.md:110-114`; `docs/customization.md:152-159`; `src/utils/change-metadata.ts:248-296` | A second lookup chooses the schema directory: project, user, package (`src/core/artifact-graph/resolver.ts:133-138`). |
| N28 | §4: `context` is injected into all artifacts and operations; never overrides CLI paths or user choices | CONFIRMED | `docs/customization.md:95`, `:119-126`; `src/core/project-config.ts:41-46` | Capped at 50 KB (`project-config.ts:256`). |
| N29 | §4: `rules.<artifact_id>` is injected for the matching artifact only; `instructions specs` constrains main specs during merge | CONFIRMED | `docs/customization.md:96`, `:139-141`; `project-config.ts:48-55` | |
| N30 | §4: `operations.{apply,archive}.guidance` is advisory, fetched at execution time, separate from rules | CONFIRMED | `docs/customization.md:100-129`; `project-config.ts:57-64` | |
| N31 | §4: `core` profile = propose, explore, apply, update, sync, archive | CONFIRMED | `src/core/profiles.ts:14`; `docs/opsx.md:68` | |
| N32 | §4: expanded profile adds new, continue, ff, verify, bulk-archive, onboard | CONFIRMED | `profiles.ts:19-32`; `docs/reviewing-changes.md:121` | In code the profiles are `core` and `custom` (`src/core/global-config.ts:11`). "Expanded" is documentation wording. |
| N33 | §5.1: only `x`/`X` counts as done; `[~]`, `[-]`, `[]` are incomplete | CONFIRMED | `src/utils/task-progress.ts:55`, `:134`; `schema.yaml:210-214` | The rule is in the CLI task parser, not the verify skill. |
| N34 | §5.1: `REMOVED` check reads the baseline, recovers it from `git log -p` / `git show` when already synced, and treats an empty baseline as not verified | CONFIRMED | `skills/openspec-verify-change/SKILL.md:103-111` | |
| N35 | §5.1: `RENAMED` check verifies the TO behavior against the baseline without requiring renamed code symbols | CONFIRMED | `skills/openspec-verify-change/SKILL.md:112-120` | |
| N36 | §5.1: verification is "rigorous" and "unusually strong" | PARTLY RIGHT | `SKILL.md:72`, `:210`; `docs/reviewing-changes.md:119` | It is an LLM procedure using keyword search, advisory, optional, and non-blocking. `git log` recovers spec text, not code evidence. |
| N37 | §5.2: `artifactPaths.specs.existingOutputPaths` is the only delta-spec source | CONFIRMED | `skills/openspec-archive-change/SKILL.md:116-119`; `docs/customization.md:133-137` | Skill contract, not CLI code. |
| N38 | §5.2: task counts come from `openspec list --json`; no inference when the lookup fails | CONFIRMED | `skills/openspec-archive-change/SKILL.md:88-100` | |
| N39 | §5.2: fetches `openspec instructions specs` before the merge and aborts on failure; bulk archive fetches all first | CONFIRMED | `skills/openspec-archive-change/SKILL.md:145-151`; `docs/customization.md:139-146` | |
| N40 | §5.2: moves the change to `changes/archive/YYYY-MM-DD-<change-id>/` | CONFIRMED | `skills/openspec-archive-change/SKILL.md:112`, `:188` | |
| N41 | §5.3: all agent-facing commands expose `--json` envelopes with exit codes 0/1/130 and a diagnostic code catalog | PARTLY RIGHT | `docs/agent-contract.md:98-105`, `:107-137` | Not uniform. `schemas --json` is a bare array, `templates` has no root or status keys, key casing is split, and 130 applies only to `store` prompts in human mode (`agent-contract.md:93`, `:96`, `:139-150`). |
| N42 | §5.4: two review moments, after `propose` and after `apply` via `verify` | CONFIRMED | `docs/reviewing-changes.md:9-19` | |
| N43 | §5.4: quit-earliest reading order proposal, specs, design, tasks | CONFIRMED | `docs/reviewing-changes.md:23-33` | The source poses three questions; `design.md` is "only for bigger changes" and has none. |
| N44 | §5.4: dashboard summary metrics and active-change sorting | CONFIRMED | `openspec/specs/cli-view/spec.md:27-34`, `:44-48`; `src/core/view.ts:138-145` | |
| N45 | §5.4: artifact chips, `tasks.total > 0` completed filter, terminal control character replacement | CONFIRMED | `cli-view/spec.md:54-59`, `:73-77`, `:81-99`; `view.ts:113-116`, `:220-221` | |
| N46 | §6: the plan documents a bug in the merger at `src/core/archive.ts` and `src/core/parsers/requirement-blocks.ts` | PARTLY RIGHT | `openspec-parallel-merge-plan.md:4-5`, `:16` | The document exists and says this, but its code references are stale. `buildUpdatedSpec` is at `src/core/specs-apply.ts:169`. |
| N47 | §6: root cause, whole-block replace with no stored base version | CONFIRMED | `specs-apply.ts:451-456`, `:577`; plan `:16-17` | Still the mechanism, now behind a guard. |
| N48 | §6: second archive "silently" deletes the first change's scenario "with zero conflict warning" | OUTDATED | `specs-apply.ts:564-569`; `CHANGELOG.md:960`; `test/core/archive.test.ts:3374` | See error 1. |
| N49 | §6: remediation phases 0–3 are "not yet fully shipped" | PARTLY RIGHT | Plan text: `openspec-parallel-merge-plan.md:30-79` | None of the planned mechanisms is in `src/`. A different, narrower guard shipped instead. |
| N50 | §7: "Replace-only delta merge silently drops concurrent scenario edits" | OUTDATED | Same as N48 | Dropped scenarios are refused. See error 1 for the residual risk. |
| N51 | §7: the 500-character and `####` rules "rely heavily on prompt adherence unless parsed" | PARTLY RIGHT | `validator.ts:334-343` | Both are parsed and checked by `openspec validate`. They go unchecked only when nobody runs it (error 3). |
| N52 | §7: "Most enforcement (sync, checklist, git recovery) lives in Markdown skill instructions rather than runtime code" | PARTLY RIGHT | Skills: `skills/openspec-sync-specs/SKILL.md`, `openspec-verify-change/SKILL.md` | True for sync, verify and the skill-driven archive. The CLI enforces validation and the archive merge in code (`validator.ts`, `specs-apply.ts`, `src/core/archive.ts`). |
| N53 | §7: no constitution file, no `clarify`/`analyze`/`converge`, no `[P]` or `[US#]` task markers | CONFIRMED | No match for "constitution" in `src`, `schemas`, `skills`, `docs`; 12 skills in `skills/`; `templates/tasks.md` | |

## 5. Claims checked: `01-spec-frameworks-comparative-analysis.md` (OpenSpec only)

| # | Claim (section) | Verdict | Evidence | Correction |
| --- | --- | --- | --- | --- |
| R1 | Summary and table header: OpenSpec version `2.1.1` | CONFIRMED | `package.json:3`; release v2.1.1; npm latest | |
| R2 | Summary: strengths list (specs/changes split, four delta operators, schema DAG, review cadence, dashboard invariants, removal/rename verification) | CONFIRMED | See N5, N17, N24, N43–N45, N34–N35 | |
| R3 | Summary, "Documented Failure Modes" row and blind-spot table: an unresolved parallel delta data-loss bug in `buildUpdatedSpec` (stated three times) | OUTDATED | See N48 | See error 1. |
| R4 | Summary and blind-spot table: OpenSpec suffers from "prompt-fragile runtime enforcement" | PARTLY RIGHT | See N52 | True for skills. The CLI's validation and archive merge are code. The examples given (`analyze`, `checklist`, hooks) are Spec Kit features. |
| R5 | Summary: OpenSpec has "chat-wall" UX gaps, prompt-injection exposure, single-model assumptions | UNVERIFIABLE | `SECURITY.md` (threat model) and `README.md` (model advice) are the nearest sources | Evaluative. No OpenSpec source states or refutes it. |
| R6 | Maturity table: OpenSpec is "Level 2: Spec-Anchored" | UNVERIFIABLE | Not an OpenSpec term | Third-party taxonomy. |
| R7 | Table, Core Philosophy: fluid, iterative, brownfield-first; "actions, not phase gates" (`docs/concepts.md`) | CONFIRMED | `docs/concepts.md:10-13`; `docs/opsx.md:52` | "Actions, not phases" is in `docs/opsx.md`, not `concepts.md`. |
| R8 | Table, Runtime: TypeScript/Node.js CLI plus "30+ tool skill adapters" | CONFIRMED | `README.md:153`, `:183` | Since 2.0 there is one shared skill copy in `.agents/skills/`, not a per-tool adapter (`CHANGELOG.md:91`). |
| R9 | Table, Repository Layout | CONFIRMED | See N5 | |
| R10 | Table, Brownfield: four delta operators plus `skip_specs: true` | CONFIRMED | See N17, N22 | |
| R11 | Table, Workflow: declarative `schema.yaml` DAG | CONFIRMED | See N24, N26 | See error 6. |
| R12 | Table, Process Scope: "Single SDD + `explore` + `onboard`" | PARTLY RIGHT | `schemas/` holds only `spec-driven` | Custom and forked schemas define other processes (`docs/customization.md:163-199`, `:413-417`). There are 12 workflows, not 3. |
| R13 | Table, Governance: `config.yaml` splits context, rules, guidance | CONFIRMED | See N28–N30 | |
| R14 | Table, Ambiguity: ad hoc through `openspec-explore` and Open Questions in `design.md` | CONFIRMED | `schema.yaml:183-188`, `:206-208`; `skills/openspec-explore/SKILL.md` | The schema tells the agent to resolve spec-affecting questions with the user before writing tasks. |
| R15 | Table, Task Structure: grouped checkboxes with inline verification | CONFIRMED | `schema.yaml:216-230`; `templates/tasks.md` | |
| R16 | Table, Quality Gates: `openspec validate --strict` plus `verify-change` (REMOVED via `git log`) | PARTLY RIGHT | See N36 | Neither is a gate in the default workflow. See error 3. |
| R17 | Table, Review UX: reading order; `0/0` guard; "ANSI sanitization" | CONFIRMED | See N43, N45 | The spec says "terminal control characters". |
| R18 | Table, Customization: custom `schema.yaml`, templates, `core`/expanded profiles | CONFIRMED | See N27, N31, N32; `docs/customization.md:163-199` | |
| R19 | Table, Multi-Repo: Stores (beta), `--store <id>` | CONFIRMED | See N9–N11 | |
| R20 | Table, Machine Contract: standardized `--json` envelopes, exit codes 0/1/130, code catalog | PARTLY RIGHT | See N41 | |
| R21 | Harvest 1: living `specs/`, isolated `changes/`, dated `archive/`, no collision between parallel changes | CONFIRMED | `docs/concepts.md:46-50`, `:549` | Isolation holds only "as long as they modify different requirements" (`docs/concepts.md:404`). |
| R22 | Harvest 2: delta operators with Reason/Migration and FROM/TO; `skip_specs` | CONFIRMED | `schema.yaml:36-42`, `:96-100` | See N20. |
| R23 | Harvest 3: MUST/SHALL, four-hash scenarios, 500-character limit | CONFIRMED | `schema.yaml:104-109` | See error 4 for severities. |
| R24 | Harvest 4: declaration-order tie-breaking; three-way config split | CONFIRMED | See N26, N28–N30 | |
| R25 | Harvest 5: verification checks `git log` "to prove `REMOVED` code paths are truly gone" | PARTLY RIGHT | `skills/openspec-verify-change/SKILL.md:105-108` | `git log` recovers the removed requirement's text from spec history. The evidence that code is gone is an LLM codebase search. |
| R26 | Harvest 6: review order, `tasks.total > 0` filter, sanitization, Stores, `--json` | CONFIRMED | See N43, N45, N9 | See N41. |

## 6. Emphasis that would mislead a designer

- **Skill behavior reads as engine behavior.** Notes §5.1 and §5.2 describe contracts written in `SKILL.md` files. An LLM follows them; no code enforces them. Notes §7 says so in one table cell, but the sections themselves do not.
- **`validate --strict` reads as the normal bar.** It is an opt-in flag on a command the default skills never invoke.
- **The DAG reads as an engine that locks and unlocks.** It reports state from file existence and orders recommendations.

## 7. Material omissions

1. **`docs/` is the legacy documentation tree.**
   - The published site is built from `docs-lab/` (`docs-lab/README.md:3-6`, `website/docs.sync.config.mjs`).
   - Legacy pages still describe 1.x: `/opsx:*` commands, `.claude/skills/`, the `delivery` setting.
   - `docs/concepts.md:240-254` shows a proposal with Intent/Scope/Approach, which contradicts the shipped template (Why / What Changes / Capabilities / Impact).
2. **CLI versus skills.**
   - The CLI has no `propose`, `apply`, `verify`, `sync` or `explore` command.
   - Code: `new change`, `status`, `list`, `view`, `show`, `instructions`, `validate`, `archive`, `schema …`, `store …` (`docs-lab/reference/cli.md:7-58`).
   - Twelve skills carry the workflow and call that CLI for state and prompts (`skills/`).
3. **The CLI merge rules** (`src/core/specs-apply.ts`):
   - Operations apply in the order RENAMED, REMOVED, MODIFIED, ADDED (`:461`).
   - A requirement is identified by its header name, case-sensitive, with near-miss detection for case and spacing.
   - A new main spec accepts ADDED only (`:411`).
   - A delta already applied to the main spec is a no-op, so early sync is supported.
   - Only requirement blocks are carried into the main spec; other delta text is left behind with a warning.
4. **Capability retirement.** `retire_capabilities: true` in `.openspec.yaml` lets archive delete a main spec whose last requirement is removed (`src/core/change-metadata/schema.ts:55-61`).
5. **`openspec instructions` is the prompt-assembly API.** It returns `context`, `rules`, `template`, `instruction`, `dependencies` and `unlocks` per artifact. `status --json` reports each artifact as done, skipped, ready or blocked (`docs/agent-contract.md:61-71`).
6. **Schema details.**
   - Templates are given to the agent as the output format; they are not copied into the change (`docs-lab/reference/schemas/schema-yaml.md:112`).
   - Misspelled schema fields are ignored without a report (`schema-yaml.md:227`).
   - `openspec schema init`, `fork`, `validate` and `which` exist and are marked experimental (`docs-lab/reference/cli.md:38`).
7. **Root selection.** Commands resolve their root as `--store`, then the nearest `openspec/`, then a `store:` pointer, then the global `defaultStore` (`docs/stores-beta/user-guide.md:392-407`). `references:` gives read-only upstream specs; worksets are personal and never committed.
8. **Sync is a separate step from archive.** `openspec-sync-specs` merges deltas into main specs while the change stays active.
