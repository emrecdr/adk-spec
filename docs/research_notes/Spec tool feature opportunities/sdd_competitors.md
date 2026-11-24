# Spec-driven development tools, November 2026: standout capabilities and the gaps a local spec CLI could fill

Reading notes for the report writer:

- Research date: 24 November 2026. Every capability carries a source URL. Dates are release or page-update dates as
  the source states them.
- How sources were read. GitHub repositories (OpenSpec, Spec Kit, BMAD-METHOD, GSD Core, Superpowers) were read
  through the public GitHub API: release notes and doc files are verbatim. Web docs (kiro.dev, docs.tessl.io,
  docs.traycer.ai, Augment/Intent pages) were read through a page reader that summarises. Quotes from those are as
  the reader returned them and were not character-checked.
- Labels: [docs] = the vendor's own documentation or release notes; [marketing] = a vendor landing page or a claim
  with no documentation behind it; [snippet] = seen only in a search-result summary, page not opened; [third party]
  = someone other than the vendor.
- Earlier local research not redone here: `docs/research_notes/Simple command flows in spec tools/` (command flows of
  OpenSpec, Spec Kit, Kiro, BMAD, 22 November 2026) and `docs/research_notes/Spec driven framework on Google ADK/`
  (internals and critique, 20 November 2026). This round looks at what goes beyond parity.
- What the local CLI already has was checked in its source and roadmap, so gaps are not reported for things it
  already does. Examples: an approval voided by any edit, a "drifted" state when the work changes after
  verification that blocks archive (`adk_spec/domain/lifecycle.py`), a recommended-features list already in
  `docs/superpowers/plans/README.md` ("a diff of what each MODIFIED requirement changes … `verify` judging the work
  against the constitution … a tier raised after the reading … `validate` codes for a voided approval and drifted
  work in CI").
- The scope ran past the usual tool budget because the brief named eight tools. Augment Intent's primary docs could
  not be reached (see its Gaps).

## 1. OpenSpec: what is new since 2.0 (stores, cross-repo planning, show --diff, explore, validate --strict, dashboards)?

### Takeaway
OpenSpec 2.0 (11 Nov 2026), 2.1 (17 Nov) and 2.1.1 (19 Nov) changed packaging, not workflow: skills only, a shared
`.agents/skills/` folder, global installs, offline skill install. The standout capabilities are older 1.x features
that are now mature: stores and worksets for planning across repositories (beta), `show --diff` for per-requirement
delta diffs, a `validate --strict` that keeps gaining checks that protect archive, an `openspec view` dashboard, and
a report-only verify skill.

### Cited Findings
- **2.0.0 (2026-11-11).** Skills move to `.agents/skills/`; tools that do not read it (Claude Code, Kiro) get links;
  `/opsx:*` slash commands are removed ("`/opsx:propose` becomes `/openspec-propose`"); `openspec update` removes
  older generated files but keeps and lists edited ones; Amazon Q support removed. "The OpenSpec workflows themselves
  haven't changed." [docs] — [OpenSpec v2.0.0](https://github.com/Fission-AI/OpenSpec/releases/tag/v2.0.0)
- **2.1.0 (2026-11-17).** Global skills through Vercel's `skills` installer; `openspec update` asks once whether a
  repo keeps project skills or switches to global and records the choice in `openspec/config.yaml`; in CI or from an
  agent there is no question. [docs] — [OpenSpec v2.1.0](https://github.com/Fission-AI/OpenSpec/releases/tag/v2.1.0)
- **2.1.1 (2026-11-19).** Skills install from the CLI package itself (no Git or network). "Archive won't
  half-finish": if the archive folder exists, archive stops before touching any main spec. `validate --strict` now
  warns when a MODIFIED requirement grows past 500 characters and accepts YAML frontmatter on a delta spec. [docs] —
  [OpenSpec v2.1.1](https://github.com/Fission-AI/OpenSpec/releases/tag/v2.1.1)
- **Validate checks added in late 1.x.** A scenario with no WHEN/GIVEN or no THEN step warns, and `--strict` fails
  on it (1.16.0, 2026-10-30). A requirement under an unknown delta section such as `## DEPRECATED Requirements` now
  fails validate and is refused by archive, where it was dropped with a warning before (1.16.1, 2026-11-07). Warnings
  for text in a delta that archive would not carry into the main spec, such as prose before the first requirement
  (1.14.2, 2026-10-15). A requirement over 500 characters is a strict failure (1.14.1, 2026-10-06). Unknown keys in
  `.openspec.yaml` are named and fail `--strict` (1.14.0, 2026-09-30). [docs] —
  [v1.16.0](https://github.com/Fission-AI/OpenSpec/releases/tag/v1.16.0);
  [v1.16.1](https://github.com/Fission-AI/OpenSpec/releases/tag/v1.16.1);
  [v1.14.2](https://github.com/Fission-AI/OpenSpec/releases/tag/v1.14.2);
  [v1.14.1](https://github.com/Fission-AI/OpenSpec/releases/tag/v1.14.1);
  [v1.14.0](https://github.com/Fission-AI/OpenSpec/releases/tag/v1.14.0)
- **`validate --report findings` and `--archived`.** A findings-only report, also as JSON, can be run over archived
  changes (`openspec validate --archived --report findings --json`). [docs] —
  [OpenSpec CLI reference](https://github.com/Fission-AI/OpenSpec/blob/main/docs-lab/reference/cli.md)
- **`openspec show <change> --diff`.** Prints the proposal, then a "Specifications Changed (diffs)" section. ADDED
  requirements show their full text; REMOVED ones keep their Reason and Migration; a MODIFIED one gets a diff against
  the main spec. "If a MODIFIED header matches only after folding case or whitespace, the output includes both the
  diff and a warning that archive matching is exact." With `--json --diff`, a MODIFIED delta gains a `diff` string,
  a `warning` string, or both. [docs] —
  [OpenSpec CLI reference](https://github.com/Fission-AI/OpenSpec/blob/main/docs-lab/reference/cli.md)
- **`show --json` names requirements and scenarios** (1.14.0), "so JSON readers can cite a requirement without
  parsing the markdown." [docs] — [v1.14.0](https://github.com/Fission-AI/OpenSpec/releases/tag/v1.14.0)
- **Stores (beta): one planning repo, many code repos.** "A store moves that folder into a repository of its own,
  and several code repos can share it." Use cases: a frontend and a backend repo with "a single home" for one
  feature's plan; Android, iOS and web repos sharing one behaviour spec ("one spec serves all three"). Setup:
  `openspec store setup`, push the store, teammates `openspec store register <path>`. Three setups: repo-local,
  store-only (a `store: team-plans` line in `openspec/config.yaml`), store-optional (`--store` per command). A fixed
  resolution order picks where artifacts go (`--store` flag, then the project's own `openspec/`, then the `store:`
  line, then `defaultStore`), and "OpenSpec never picks a store by name on its own". [docs] —
  [Stores (beta)](https://github.com/Fission-AI/OpenSpec/blob/main/docs-lab/multi-repo/stores.md)
- **Store-aware fixes.** Store-backed apply can edit the declaring project (1.14.0); when no root is found, the error
  names the store whose id matches the repo's `origin` (1.16.0). [docs] —
  [v1.14.0](https://github.com/Fission-AI/OpenSpec/releases/tag/v1.14.0);
  [v1.16.0](https://github.com/Fission-AI/OpenSpec/releases/tag/v1.16.0)
- **Worksets (beta).** A named list of folders saved on one machine. `openspec workset open` writes a
  `.code-workspace` file and opens VS Code or Cursor on it, so "the agent can grep the store's specs and the repo's
  code in one session". Claude Code and Codex are "temporarily disabled as workset openers". [docs] —
  [Worksets (beta)](https://github.com/Fission-AI/OpenSpec/blob/main/docs-lab/multi-repo/worksets.md)
- **`openspec view` dashboard.** One screen, groups changes by task progress (Draft, Active with a progress bar,
  Completed), and since 1.14.0 shows each change's schema and which artifacts are done, ready, blocked or skipped.
  `list --archived` and a separate archived section were added in 1.14.0. [docs] —
  [CLI reference](https://github.com/Fission-AI/OpenSpec/blob/main/docs-lab/reference/cli.md);
  [v1.14.0](https://github.com/Fission-AI/OpenSpec/releases/tag/v1.14.0)
- **Explore skill.** "Think through an idea before it becomes a change proposal." It creates nothing by default,
  captures a proposal or updates one on request, "Never code". [docs] —
  [Skills reference](https://github.com/Fission-AI/OpenSpec/blob/main/docs-lab/reference/skills.md)
- **Verify skill (optional).** Report only: "a scorecard for Completeness, Correctness, and Coherence, then CRITICAL,
  WARNING, and SUGGESTION issues … and a final archive-readiness assessment. It changes nothing and does not
  archive." [docs] — [Skills reference](https://github.com/Fission-AI/OpenSpec/blob/main/docs-lab/reference/skills.md)
- **Verify hardening.** It no longer reports skipped checks as passing; removed requirements pass "once the behavior
  is gone" (1.13.2, 2026-09-23). It reads a REMOVED requirement's original text from the main spec before searching
  the code, and reports it as not verified when the text cannot be recovered (1.14.2). [docs] —
  [v1.13.2](https://github.com/Fission-AI/OpenSpec/releases/tag/v1.13.2);
  [v1.14.2](https://github.com/Fission-AI/OpenSpec/releases/tag/v1.14.2)
- **Bulk archive** syncs deltas first, and "When two change proposals touch the same spec it checks the codebase and
  syncs implemented deltas oldest first." [docs] —
  [Skills reference](https://github.com/Fission-AI/OpenSpec/blob/main/docs-lab/reference/skills.md)
- **Evidence for verification is left to the team.** The review guide asks for a record per scenario (Scenario,
  Check, Result, Tested version) and says "A checked task or an agent's summary alone does not prove the test
  passed." It also says "Archiving does not enforce these checks." [docs] —
  [Review the plan](https://github.com/Fission-AI/OpenSpec/blob/main/docs-lab/guides/review-the-plan.md)
- **Task guidance.** Each task group carries its own tests and doc updates "instead of deferring them to a final
  group" (1.13.2). Apply checks the exact checkbox by `sourcePath` and `line` (1.14.0). [docs] —
  [v1.13.2](https://github.com/Fission-AI/OpenSpec/releases/tag/v1.13.2);
  [v1.14.0](https://github.com/Fission-AI/OpenSpec/releases/tag/v1.14.0)
- `openspec update --dry-run [--json]` reports every file an update would add, change or delete (1.15.0,
  2026-10-24). [docs] — [v1.15.0](https://github.com/Fission-AI/OpenSpec/releases/tag/v1.15.0)

### Inferences
- OpenSpec's lead is in code-checked spec hygiene (validate rules that guard archive) and in the reviewer's view of a
  change (`show --diff`). Its verification stays a model's report with no evidence enforced, and its own guide says
  so.
- A store is the opposite of the local CLI's design. In a store, the plan lives in its own repo and code repos point
  at it. In the local CLI, a change in one repo names the other repos it spans. Stores answer the case of "one
  behaviour spec, several client repos", which per-repo living specs do not.

### Gaps
- When stores, `show --diff` and explore were first released: not established. The release notes read (1.13.2 to
  2.1.1) only show fixes to them.
- The guides for teams, reviewing the plan and workflow runs are still headings-only drafts (`docs-lab/guides/teams.md`,
  `workflow-runs.md`), so OpenSpec's recommended team and PR conventions are not documented in the current tree.

## 2. GitHub Spec Kit: converge, checklist, analyze, extensions, presets, workflows with review gates, MCP server?

### Takeaway
Spec Kit 1.4.x (1.4.4 on 2026-11-23) has the widest automation surface: append-only `converge`, which turns
unbuilt work into traceable tasks; `checklist` as "unit tests for requirements"; read-only `analyze`; resumable YAML
workflows with human review gates that can be answered without a TTY; mandatory and optional extension hooks before
each command; and a large, unreviewed community catalog. Its MCP server is experimental and read-only: it serves
inventory, not the workflow.

### Cited Findings
- **Converge.** "Assess the current codebase against the feature's spec, plan, and tasks, then append any remaining
  unbuilt work as new tasks to tasks.md." "APPEND-ONLY, NEVER REWRITE": its only write is a new
  `## Phase N: Convergence` section; it must not modify `spec.md` or `plan.md`, renumber tasks, or touch code. When
  everything is met it leaves `tasks.md` "byte-for-byte unchanged". "This is **not** a diff tool": it assesses the
  present code, "no git, no branch comparison, no history". Each finding records "a stable id, the `source-ref` it
  traces to, the `gap-type`, a severity"; "completion claims are not evidence". A constitution MUST violation is the
  highest severity. [docs] —
  [converge.md](https://github.com/github/spec-kit/blob/main/templates/commands/converge.md)
- **The delivery loop now ends in converge.** "specify -> plan -> tasks -> implement -> converge"; repeat implement
  and converge "until the agreed feature is complete". Converge "does not rewrite artifacts to accept code as a
  replacement for documented intent." "Core has no dedicated command that automatically reconciles differences among
  `spec.md`, `plan.md`, and `tasks.md`." [docs] —
  [Evolving specs](https://github.com/github/spec-kit/blob/main/docs/how-to/evolving-specs.md)
- **Checklist: "Unit Tests for English".** Checklists "validate the quality, clarity, and completeness of
  requirements", not the implementation. Examples: "Is 'prominent display' quantified with specific
  sizing/positioning?", "Does the spec define what happens when logo image fails to load?" Items get `CHK###` IDs and
  are reviewer-owned: the command "MUST NOT mark generated items `[x]`." [docs] —
  [checklist.md](https://github.com/github/spec-kit/blob/main/templates/commands/checklist.md)
- **Analyze.** "STRICTLY READ-ONLY" cross-artifact analysis of spec, plan and tasks. It builds a requirements
  inventory keyed by `FR-###`/`SC-###`, maps tasks to requirements, and runs detection passes for duplication and
  ambiguity, among others. Constitution conflicts "are automatically CRITICAL". Since 1.4.2 (2026-11-17) it also
  checks "constrained-field task citations" against `data-model.md` (exact `Entity.field` constraints). [docs] —
  [analyze.md](https://github.com/github/spec-kit/blob/main/templates/commands/analyze.md);
  [v1.4.2 "cite canonical field constraints and analyze drift"](https://github.com/github/spec-kit/releases/tag/v1.4.2)
- **Extension hooks on every command.** Each command reads `.specify/extensions.yml` for `hooks.before_<command>`.
  Optional hooks are offered; a mandatory hook (`optional: false`) must be executed and awaited. Unreadable YAML must
  be reported, not skipped silently. [docs] —
  [converge.md](https://github.com/github/spec-kit/blob/main/templates/commands/converge.md);
  [v1.4.1 "list the converge hook events"](https://github.com/github/spec-kit/releases/tag/v1.4.1)
- **Workflows with review gates.** YAML definitions "chain agent commands, prompts, shell tasks, control flow, and
  human review gates into repeatable, resumable runs". The bundled `speckit` workflow runs specify, plan, tasks and
  implement "with review gates after specification and planning"; a gate prompts on a TTY "otherwise it pauses". A
  verdict can be passed without a TTY: `specify workflow resume <run_id> --input speckit_review_spec_verdict=approve`.
  "Approving the specification does not approve the plan review." Runs have IDs and persisted state; completed steps
  are replayed without re-executing. Bundled workflows: `speckit`, `bugfix`, `assess`. Overlays can insert, replace or
  remove steps. [docs] — [Workflows](https://github.com/github/spec-kit/blob/main/docs/workflows/overview.md)
- Workflow features in recent releases: per-step reasoning effort and context size (1.3.3, 2026-11-09);
  project-installed pipe functions (1.4.0, 2026-11-10). [docs] —
  [v1.3.3](https://github.com/github/spec-kit/releases/tag/v1.3.3);
  [v1.4.0](https://github.com/github/spec-kit/releases/tag/v1.4.0)
- **MCP server (`specify mcp`), experimental.** stdio only. Tools: `specify_version`, `specify_artifact_list`,
  `specify_artifact_info`, `specify_workflow_list`, plus generic tools that accept only `version`. "All are
  read-only, local-only (no network access)". "The server does not expose mutations, installation or update
  operations, workflow execution, confirmations, or access tiers." Errors carry `code`, `message`, `details`,
  `retryable`. [docs] — [MCP Server](https://github.com/github/spec-kit/blob/main/docs/overview/mcp.md)
- **Presets.** Bounded Markdown section replacement (1.4.3, 2026-11-19); a searchable community preset directory
  (1.4.3); governance presets keep shipping (Autonomous Run Governance, Intake Review Governance, Model Routing
  Governance). [docs] — [v1.4.3](https://github.com/github/spec-kit/releases/tag/v1.4.3);
  [v1.4.2](https://github.com/github/spec-kit/releases/tag/v1.4.2)
- **Version provenance in generated skills** (1.4.2). [docs] —
  [v1.4.2](https://github.com/github/spec-kit/releases/tag/v1.4.2)
- **Community extension catalog.** "Maintainers only verify that catalog entries are complete and correctly formatted
  — they do not review, audit, endorse, or support the extension code itself." Entries relevant here:
  - CI Guard: "verify specs exist, check drift, and block merges on gaps".
  - DocGuard: "drift validation, traceability, safe archival, SARIF/JUnit, MCP, GitHub Actions".
  - BDD: "Convert specs to Gherkin scenarios … verify acceptance test coverage".
  - EARS Requirements Syntax: author, lint and convert requirements.
  - Golden Demo: "Deterministic behavioral drift oracle … CI/CD gatekeeper".
  - Axi: renders a feature's Markdown "in a local browser review surface for human annotation".
  - Fleet Orchestrator: "human-in-the-loop gates".
  - Multi-Repo Workspace Orchestration (added 1.4.1).
  - Several Jira, Linear, Azure DevOps and GitHub Projects sync extensions, some "idempotent, drift-aware,
    fail-closed".

  [docs, community] —
  [Community extensions](https://github.com/github/spec-kit/blob/main/docs/community/extensions.md);
  [v1.4.1](https://github.com/github/spec-kit/releases/tag/v1.4.1)

### Inferences
- Converge and analyze together give Spec Kit two halves of what the local CLI does in `check` and `verify`. The
  difference is the output. Spec Kit's output is **work for the coding assistant** (appended, traceable tasks).
  The local CLI's output is a **verdict for a person**. Converge's model-judged gaps are not quote-checked.
- The review gate with a verdict input passed on the command line is close to the local `approve`, but Spec Kit does
  not fingerprint what was approved.
- The catalog's number of entries is not evidence of quality: the maintainers say they review form only.
- The MCP server does less than the local CLI's six tools. Spec Kit has nothing to learn from here.

### Gaps
- Whether converge's appended tasks have been measured to converge (the number of loops) was not found.
- No primary source states how many people use workflows or the extension catalog.

## 3. AWS Kiro: specs (requirements-first, design-first, bugfix), steering, hooks, Markdown review, property-based testing, Autopilot, run-all-tasks?

### Takeaway
Kiro's standout capabilities are:
- property-based tests derived from EARS requirements, traceable to the requirement and its task, with shrinking
  (IDE only);
- bugfix specs that write down unchanged behaviour as a regression guard;
- Analyze Requirements, a whole-set check for ambiguity, conflict and missing edge cases;
- run-all-tasks in dependency waves;
- Markdown Review, with comments on exact passages;
- hooks on spec task start and end;
- three autonomy modes with per-file accept or reject.

### Cited Findings
- **Spec types.** Feature Specs in two variants, Requirements-First and Design-First. Bugfix Specs. Quick Spec, which
  "generates all three artifacts without approval gates". Files: `requirements.md` (or `bugfix.md`), `design.md`,
  `tasks.md`. [docs] — [Kiro Specs](https://kiro.dev/docs/specs/)
- **Run all tasks.** "Kiro builds a dependency graph and groups independent tasks into waves", run concurrently within
  a wave and in sequence across waves. Task status updates live. Available in the IDE, CLI and Web. [docs] —
  [Kiro Specs](https://kiro.dev/docs/specs/)
- **Markdown Review.** A floating Review button on requirements, design, bugfix or behaviour documents, where "you can
  comment on exact passages and send them to Kiro together". [docs] —
  [Kiro Specs](https://kiro.dev/docs/specs/) (links /docs/ide/editor/markdown-review/)
- **Property-based testing ("correctness"), IDE only.** Properties are extracted from EARS requirements ("EARS maps
  really well" to properties), after Kiro decides which requirements "can be logically tested". Test cases are
  generated in the design phase and run in the execution phase, with "hundreds or thousands" of random inputs per
  property. Shrinking reduces a failing input to the smallest that still fails. A failure can lead to a fix of "the
  spec, implementation, or test itself". Hovering a property shows "its connection to the original requirement and
  its linked task". The page names its own limits: evidence, "not proof"; weak properties can pass; requirements on
  external services may need mocks or examples. Page updated 2026-08-04. [docs] —
  [Correctness](https://kiro.dev/docs/specs/correctness/)
- **Bugfix specs.** `bugfix.md` has three sections:
  - Current Behavior: WHEN … THEN the system [incorrect behavior].
  - Expected Behavior: WHEN … THEN the system SHALL ….
  - Unchanged Behavior (Regression Prevention): WHEN … THEN the system SHALL CONTINUE TO ….

  The design finds the root cause and defines properties that show the bug exists, that the fix works, and that
  unchanged behaviour still holds. Tasks include PBTs for reproduction, fix and regressions. Page updated
  2026-08-04. [docs] — [Bugfix Specs](https://kiro.dev/docs/specs/bugfix-specs/)
- **Analyze Requirements.** A pre-design review of the whole requirement set. It looks for logical inconsistencies
  ("collectively impossible"), ambiguities ("large files", "fast response times"), conflicting constraints, unstated
  assumptions and missing edge cases. Findings arrive as questions with suggested fixes that update
  `requirements.md`, and a re-run re-checks the affected requirements. Feature specs only: IDE 1.4.215+ refuses
  bugfix specs. Page updated 2026-11-17. The page does not say whether it uses formal reasoning or an LLM. [docs] —
  [Analyze Requirements](https://kiro.dev/docs/specs/analyze-requirements/)
- **Hooks.** Triggers include File Create, Save and Delete ("respond only to changes made by the agent"), Prompt
  Submit, Agent Stop, Session Start and End, Pre and Post Compaction, Pre Tool Use (can block, and can rewrite the
  input from IDE 1.4.236 and CLI 3.4.0), Permission Request (can allow or deny, "cannot override a policy `deny`"),
  Post Tool Use, and the spec triggers **Pre Task Execution** ("before a spec task begins") and **Post Task
  Execution** ("for tests, linting, or documentation"). Page updated 2026-11-18. [docs] —
  [Hook types](https://kiro.dev/docs/hooks/types/); [Kiro changelog, IDE 1.4.236, 2026-11-18](https://kiro.dev/changelog/)
- **Autonomy modes and review (Kiro for VS Code 1.5.0, 2026-11-19).** Autopilot, Supervised and "Approve for me".
  "Accept or reject each file, or restore a checkpoint." Spec sessions in the sidebar, per-task CodeLens, and a
  workspace `.kiro` folder holding steering, hooks, skills, Powers and MCP. [docs] —
  [Kiro changelog](https://kiro.dev/changelog/)
- **Crew Conductor mode (0.13.0, 2026-11-19).** It "Plans from your goal, checks each worker's new work as the crew
  runs, and re-plans only the item that went wrong." [docs, read through a summary] —
  [Kiro changelog](https://kiro.dev/changelog/)
- **CLI surface.** Feature, bugfix and quick specs, parallel task execution and Analyze Requirements are in the CLI;
  correctness (PBT) is not. [docs] — [Kiro Specs](https://kiro.dev/docs/specs/)

### Inferences
- Kiro's PBT is a genuine differentiator for traceability from a requirement to an executable check. It costs a lot:
  it needs EARS, a design phase and the IDE. The idea that transfers to a tool that writes no code is smaller:
  **test obligations per scenario**, which the coding assistant writes and `verify` checks for.
- The "Unchanged Behavior" section is a cheap, high-value idea for bug fixes. It turns "don't break X" into
  requirements that a verifier can judge against the diff.
- Analyze Requirements overlaps with what the local `check` and the brief's questions already do. Its distinct parts
  are the whole-set view (requirements "collectively impossible") and edge-case prompts.

### Gaps
- No page read documents steering in detail (inclusion modes, file layout); only the `.kiro` folder holding steering
  is cited.
- Whether Kiro keeps specs in sync with code after implementation ("refresh" or "update tasks") is not covered by
  the pages read.
- Whether Analyze Requirements uses automated (formal) reasoning: not stated on the current page.

## 4. Tessl: verifiers, change verify in CI, drift audits, skills registry?

### Takeaway
Tessl has moved from "spec-as-source" to a platform for managing agent skills (registry, governance, evals,
observability). Its standout capability for this question is `tessl change verify`. A repository keeps verifier rules
as JSON; an LLM judge applies each rule to the files in a PR's diff; the result is a CI gate with GitHub annotations,
a machine-readable report with stable rule IDs, the lines a failed check refers to, and a budget on judge calls.
"Drift" in Tessl means skill copies drifting across an organisation, not code drifting from specs.

### Cited Findings
- **Platform.** Six components: registry and package manager (install, version and roll back skills and plugins);
  governance (scoring against standards, Snyk security scoring, RBAC, audit trail); evals ("running agents on real
  tasks with and without" a skill); observability; Context and Findings (drift, overlap and unmanaged copies across
  connected SCM accounts); and the Tessl Agent (open beta). The overview mentions no spec-driven or spec-as-source
  workflow. [docs] — [Tessl docs](https://docs.tessl.io/)
- **Verifier format.** A JSON file (for example `verifiers/actionable-errors.json`) with `name`, `instruction`,
  `relevant_when` (an observable trait that makes a target applicable), `context` (the problem, why it matters,
  legitimate exceptions), `scope`/`scope_reason`, and a `checklist` of named rules. Groups are declared in
  `tessl.json` with a path, a `level` (`error` fails the build, `warn` is advisory) and include/exclude globs.
  [docs] — [Verify agent changes in CI](https://docs.tessl.io/codifying-and-enforcing/verify-agent-changes-in-ci)
- **How it runs.** The selected source is sent to "Tessl's LLM judge". By default only files in the PR diff are
  judged.
  - Commands: `tessl change verify lint <file>`; `--dry-run --all --show-files` (shows the matched files with no
    judge calls); `--all --sample 5`; `--base "origin/$BASE_REF" --github --max-calls 200` (the CI gate;
    `--max-calls` stops before judging if the planned scope exceeds it); `--recursive` for monorepos;
    `--changed-verifiers-scope all`.
  - A Tessl Reviewer GitHub App runs on PR open or new commits, or on an `@tessl-verify` comment.
  - Guidance on editing verifiers: an agent may propose a correction, but must explain the counterexample and flag a
    change to the underlying requirement "as a policy change".

  [docs] — [Verify agent changes in CI](https://docs.tessl.io/codifying-and-enforcing/verify-agent-changes-in-ci)
- **CLI changelog (2026).**
  - 0.100.0 (Aug 26): `--report-json <path>` for CI; verifiers "carry a stable `id` in the report".
  - 0.107.0 (Sep 9) and 0.110.0 (Sep 23): the default judge model changes, and `--model` is added.
  - 0.114.0 (Oct 9): `change verify` runs without a Tessl login when `TESSL_LLM_BASE_URL` and `TESSL_LLM_API_KEY` are
    set, and "reports the lines a failed check refers to, including in GitHub annotations".
  - 0.117.0 (Oct 21): `tessl verify` during an uncommitted merge "measures only the branch's own changes".
  - 0.120.0 (Nov 17): `--level`; changed verifiers check only changed files by default; `tessl plugin import`
    converts a Claude Code plugin.
  - 0.105.0 (Sep 3): eval runs print a "Lift:" line.
  - 0.113.0 (Oct 1): `tessl code review --pr` supports GitLab.

  [docs, read through a summary; entries after 0.91.0 partly truncated] —
  [Tessl CLI changelog](https://docs.tessl.io/changelog-cli)

### Inferences
- `change verify` is the clearest example of a spec-like rule set judged per diff in CI. It shares the local CLI's
  premise (a model judges code against written rules). Tessl adds CI ergonomics that the local CLI lacks: diff-scoped
  selection, a dry run with no model call, a call budget, stable rule IDs in a JSON report, line-anchored PR
  annotations, and running against a team's own LLM endpoint.
- Nothing found says Tessl's judge must quote the code it relies on, or that code checks a quote. The local CLI's
  code-checked quotes remain a differentiator.

### Gaps
- The Verifiers overview page and the Tessl Agent pages were not read. Whether "spec-as-source" survives anywhere in
  Tessl's current product was not established. No page linked from the overview covers it.
- The changelog entries between 0.91.0 and 0.100.0 were partly truncated in the reader.

## 5. BMAD-METHOD, GSD, Traycer, Augment Intent and others: verification, traceability, review and handoff workflows?

### Takeaway
The other frameworks compete on **evidence-based review loops**:
- BMAD: every review finding gets a verdict and evidence; a "verification-gap" reviewer asks whether any test would
  fail if the behaviour broke; it checks that the test for each matrix row actually ran and passed; configurable
  review layers can call another model.
- GSD: verification reports go stale by content fingerprint; human UAT walkthroughs feed automatic gap-closure
  plans; PR bodies are assembled from requirement IDs and the verification status.
- Traycer: requirement changes propagate through every artifact; batch review against the plan, which stops when
  the product has drifted.

Augment Intent's "living spec" could not be confirmed from primary docs.

### Cited Findings
- **BMAD 6.11.0 (2026-08-10).**
  - Quick Dev becomes `bmad-build`, the one Phase 4 loop (`bmad-sprint-planning → bmad-build → bmad-code-review`).
  - Core cut from fourteen skills to eight.
  - "Skills stop guessing and start reading evidence": `bmad-retrospective` "requires a source reference on every
    finding".
  - **Verification-gap reviewer**: "asking 'if this behavior broke, would any test fail?' rather than 'is this
    wrong?', reporting untested behavior changes instead of bugs".
  - **Configurable review layers**: `[[workflow.review_layers]]` can add, replace or disable a reviewer, "including
    swapping in an external tool over bash and therefore a different model".
  - **Intent Alignment Auditor**: fed "the verbatim invocation intent alongside the diff".
  - **Matrix test coverage audited**: every row of a spec's I/O and Edge-Case Matrix needs a covering test "that
    actually executed and passed: one that exists but was never registered, filtered in, or enabled counts as
    missing".
  - A deterministic script core for sprint planning (`scripts/sprint_plan.py`, JSON-only output, drift checks).
  - **Inspectable content-addressed snapshots**: a `manifest.json` of the renderer and source hashes for "exactly what
    ran".
  - "Commits match the reviewed diff".
  - Intent-gap halts save the attempted change as a patch.
  - `bmad-check-implementation-readiness` folded into sprint planning as a PASS/CONCERNS/FAIL gate.
  - The adversarial reviewer "drops its persona for a method": "A/B piloting on Claude and Codex showed the 'cynical,
    jaded reviewer' framing made no difference to residual-bug hit rate."

  [docs] — [BMAD v6.11.0](https://github.com/bmad-code-org/BMAD-METHOD/releases/tag/v6.11.0)
- **BMAD 6.12.0 (2026-09-04).** "Build decides how much ceremony a change needs after investigating it, not before.
  Simple changes now get a two-section spec and finish in one session." "Review triage logs a verdict and evidence for
  every finding, so nothing gets dropped silently." 6.12.2 (2026-10-11): the installer notes v7 "is available for
  preview". [docs] — [BMAD v6.12.0](https://github.com/bmad-code-org/BMAD-METHOD/releases/tag/v6.12.0);
  [BMAD v6.12.2](https://github.com/bmad-code-org/BMAD-METHOD/releases/tag/v6.12.2)
- **BMAD 6.10.0 (2026-07-03).** `bmad-loop` for unattended dev loops. The Edge Case Hunter's "named-set
  generalization pass" catches diffs that special-case some members of an enum or flag set, with a "measured
  catch-rate improvement of 50% to 100% on a real regression, at a 19% token cost" [vendor claim]. [docs] —
  [BMAD v6.10.0](https://github.com/bmad-code-org/BMAD-METHOD/releases/tag/v6.10.0)
- **GSD Core.** It describes itself as "A light-weight meta-prompting, context engineering, and spec-driven
  development system". Each milestone repeats a phase loop in which plans run "in parallel waves; each executor starts
  with a clean 200k-token context". [docs] — [GSD Core README](https://github.com/open-gsd/gsd-core)
- **GSD verification goes stale by fingerprint.** The verifier "records a digest of every input its verdict covers —
  the phase's `PLAN.md`/`SUMMARY.md` files, mapped requirements, and implementation files in the change set"; any
  change flips `passed` to `stale`, and the report is "re-checked, not cached" by every completion gate. [docs] —
  [Verify and ship](https://github.com/open-gsd/gsd-core/blob/main/docs/how-to/verify-and-ship.md); fix for
  `gaps_found` reports going stale in [GSD v1.23.0](https://github.com/open-gsd/gsd-core/releases/tag/v1.23.0)
- **GSD UAT, then automatic gap closure.** `/gsd-verify-work` walks the user through deliverables taken from
  `SUMMARY.md`, one checkpoint at a time. Severity is inferred from the user's words ("crashes" → blocker). Progress is
  saved in `UAT.md` and can be resumed. On failures it spawns parallel debug agents, a planner in gap-closure mode and
  a plan checker (up to three iterations), then suggests `/gsd-execute-phase 1 --gaps-only`. [docs] —
  [Verify and ship](https://github.com/open-gsd/gsd-core/blob/main/docs/how-to/verify-and-ship.md)
- **GSD handoff to review.** `/gsd-ship` runs preflight checks (verification status, clean tree, `gh` auth) and builds
  the PR body from the phase goal, plan summaries, "Requirements addressed (REQ-IDs)", the verification status and key
  decisions. `/gsd-pr-branch` makes a branch "with only code changes" (no planning commits). `/gsd-audit-milestone`
  checks that all requirements shipped. [docs] —
  [Verify and ship](https://github.com/open-gsd/gsd-core/blob/main/docs/how-to/verify-and-ship.md)
- **GSD 1.23.0 (2026-11-23).**
  - "Deep verification before UAT": an agent enumerates interaction-level behaviours from the plan, summary and
    changed files, runs each one it can through a browser MCP server, and leaves the user only judgement items.
  - Unattended plan-review convergence with external reviewer lanes, ending in a `CONVERGENCE_STATUS`
    (`converged`, `open_conflicts`, `stalled`, `max_cycles`).
  - `/gsd-plan-phase` "validates each `<automated>` command without running it".
  - Requirement IDs shared by plans in one parallel wave are marked complete after the wave merges.
  - A TDD gate reads RED and GREEN commit evidence.

  [docs] — [GSD v1.23.0](https://github.com/open-gsd/gsd-core/releases/tag/v1.23.0)
- **GSD 1.22.0 (2026-11-19).** A plan can declare `executor_runtime` (run by another runtime's CLI in a worktree,
  completed in 1.23.0). [docs] — [GSD v1.22.0](https://github.com/open-gsd/gsd-core/releases/tag/v1.22.0)
- **Traycer is now a desktop app.** An "open-source desktop app for running AI coding agents in parallel, with shared
  plans and code review". The user brings their own agents (Claude Code, Codex, Cursor); each agent can have its own
  worktree. The IDE extension, which had Plan, Phases, Epic, Review, YOLO modes and a "Verification" feature
  ("Checking implementations against the plan and turning issues into review comments for agents"), is retired.
  [docs] — [Traycer docs](https://docs.traycer.ai/index.md);
  [Traycer docs index](https://docs.traycer.ai/llms.txt)
- **Traycer's artifact workflow** (built-in skills):
  - `traycer-revise-requirements` "propagates a requirement change through product, technical, and ticket
    artifacts".
  - `traycer-artifact-critique` writes a review artifact that pressure-tests a plan.
  - `traycer-ticket-breakdown` produces tickets with dependencies.
  - `traycer-execute` batches tickets by dependency, one child agent per ticket, and "reviews each batch against the
    plan". Passing tickets are marked done, small problems get a fix-up ticket, and "Product drift stops the run and
    returns to you".
  - `traycer-changeset-walkthrough` writes "a spec explaining what changed and the review order".
  - `traycer-autobuild` "asks you to approve the spec, rubric, and verification method".
  - `traycer-debate` debates a decision across several perspectives and models.

  [docs] — [Artifact workflow](https://docs.traycer.ai/concepts/artifact-workflow.md)
- **Augment Intent.**
  - [snippet] Augment's search-indexed copy says: "When an agent completes work, the spec updates to reflect reality.
    When requirements change, updates propagate to all active agents"; "A Coordinator agent breaks down your spec
    into tasks, and delegates to Implementors that can run in waves"; "A Verifier agent checks the results against
    the spec"; public beta using regular Augment credits. —
    [augmentcode.com/intent (search result)](https://www.augmentcode.com/intent)
  - The live URL now 308-redirects to intentapp.dev. That page names a Developer agent that "plan[s] and delegate[s]
    work", a verifier checking against a "Definition of Done", "Living Spec, aligned work", and isolated workspaces.
    It names no publisher and no beta or GA label. [marketing] — [intentapp.dev](https://intentapp.dev/)
  - The docs page docs.augmentcode.com/intent returned 404, and the docs index does not mention Intent. —
    [Augment docs](https://docs.augmentcode.com/intent/overview)
- **Superpowers** (obra/superpowers, about 326k stars). It is a methodology built from skills (brainstorming, writing
  plans, subagent-driven development). 7.0.2 (2026-11-03) tuned brainstorming with a blind-graded result: "filler
  questions dropped from 41 with 7.0.1 to 23" and "nothing got built before approval" [vendor's own measurement].
  [docs] — [Superpowers v7.0.2](https://github.com/obra/superpowers/releases/tag/v7.0.2)
- **Third-party comparisons of late 2026 are thin.** The most recent found, from a testing-tools vendor, covers only
  Spec Kit, OpenSpec, Kiro and BMAD "as of early November 2026". [snippet, third party] —
  [TestMu AI](https://www.testmuai.com/blog/spec-driven-development-tools/)

### Inferences
- These tools converge on the same pattern. The model's verdict counts only with evidence: BMAD's source reference
  on every finding, GSD's fingerprinted reports, Spec Kit's "completion claims are not evidence". None of them checks
  in code that a quoted passage exists. The local CLI's `quoted_at` rule is stronger than anything found.
- What they have that the local CLI lacks is mostly **handoff after the verdict**: gap-closure tasks (GSD, Spec Kit,
  Traycer), a PR body or walkthrough (GSD, Traycer), and test-execution evidence per requirement (BMAD, Kiro).
- Augment's "the spec updates to reflect reality" is the opposite of Spec Kit's explicit rule, which refuses to let
  code replace documented intent. Without primary docs, treat it as a marketing claim.

### Gaps
- Augment Intent: no reachable primary documentation, and who publishes intentapp.dev was not confirmed. The roles
  "Investigate Agent" and "reviewer agent for divergence" appear only in third-party or Product Hunt posts, not
  opened.
- Traycer's current desktop changelog and how its batch review judges a ticket were not read. Its artifact-workflow
  page "does not detail what the batch review checks".
- Other tools sometimes listed as spec-driven (cc-sdd, Agent OS, Taskmaster, Spec Workflow MCP, JetBrains Junie's
  planning) were not researched for lack of budget.
- BMAD v7 (in preview since October 2026) was not read.

## 6. Which capabilities are genuine differentiators, and which are hype?

### Takeaway
Genuine differentiators either change what a person can trust or cut what they must read:
- Tessl's diff-scoped CI verify with stable IDs and line annotations;
- Spec Kit's append-only converge;
- OpenSpec's `show --diff` and archive-guarding validate rules;
- GSD's fingerprint staleness and requirement-ID PR bodies;
- BMAD's test-executed coverage audit and verification-gap lens;
- Kiro's unchanged-behaviour bugfix section and requirement-traceable PBT (heavy, IDE only).

Hype, or unproven: self-updating "living specs", large unreviewed extension catalogs, reviewer personas, a read-only
inventory MCP server, and multi-agent "crews" sold as verification.

### Cited Findings
- **Genuine: code-enforced or evidence-bound checks.**
  - OpenSpec turned silent drops into failures (an unknown delta section now fails validate and archive). —
    [v1.16.1](https://github.com/Fission-AI/OpenSpec/releases/tag/v1.16.1)
  - GSD's verdict is "re-checked, not cached". —
    [Verify and ship](https://github.com/open-gsd/gsd-core/blob/main/docs/how-to/verify-and-ship.md)
  - BMAD counts a test that never executed as missing. —
    [BMAD v6.11.0](https://github.com/bmad-code-org/BMAD-METHOD/releases/tag/v6.11.0)
  - Tessl reports the lines a failed check refers to. —
    [Tessl CLI changelog](https://docs.tessl.io/changelog-cli)
- **Genuine but costly: Kiro's PBT.** The vendor itself says "evidence of correctness, not proof", and it is IDE only.
  — [Correctness](https://kiro.dev/docs/specs/correctness/)
- **Hype check, personas.** BMAD measured that the "cynical, jaded reviewer" persona "made no difference to
  residual-bug hit rate", while "requiring at least ten concrete findings and asking what is missing did" [vendor's
  own A/B]. — [BMAD v6.11.0](https://github.com/bmad-code-org/BMAD-METHOD/releases/tag/v6.11.0)
- **Hype check, catalogs.** Spec Kit's maintainers "do not review, audit, endorse, or support the extension code".
  The same is said of workflows: "Catalog listing and install permission are not evidence of code review or safety."
  — [Community extensions](https://github.com/github/spec-kit/blob/main/docs/community/extensions.md);
  [Workflows](https://github.com/github/spec-kit/blob/main/docs/workflows/overview.md)
- **Hype check, living specs that follow code.** Augment's claim is marketing only (see question 5). Spec Kit's
  documented position is the reverse: converge "does not rewrite artifacts to accept code as a replacement for
  documented intent". — [augmentcode.com/intent (search result)](https://www.augmentcode.com/intent);
  [Evolving specs](https://github.com/github/spec-kit/blob/main/docs/how-to/evolving-specs.md)
- **Hype check, MCP.** Spec Kit's server is experimental and exposes "no mutations … workflow execution,
  confirmations". — [MCP Server](https://github.com/github/spec-kit/blob/main/docs/overview/mcp.md)
- **Limited: worksets.** An editor window of several folders, with terminal agents "temporarily disabled". —
  [Worksets](https://github.com/Fission-AI/OpenSpec/blob/main/docs-lab/multi-repo/worksets.md)
- **Unclear: Kiro Analyze Requirements.** Its method is undocumented on the current page. —
  [Analyze Requirements](https://kiro.dev/docs/specs/analyze-requirements/)

### Inferences
- A capability is worth copying when its output is checkable by code or by a person in seconds: a diff, an ID, a
  fingerprint, a pass/fail with a line number. It is doubtful when it rests on more agents or more model prose.
- The local CLI's distinguishing properties (quotes checked by code, approvals as fingerprints, secrets scrubbed,
  never editing code) are absent from every competitor read. The gaps below should keep them intact.

### Gaps
- No independent measurement compares the verification quality of these tools. Every number above is a vendor's own.

## 7. Which capability gaps are most promising for the local CLI?

### Takeaway
Ranked by benefit against cost, within the owner's golden rule (no new subcommands, little on screen), the strongest
candidates are:
1. A per-requirement delta diff for the approver (OpenSpec `show --diff`).
2. CI-ready verify output: diff-scoped, a dry run, a call budget, stable IDs, annotations (Tessl).
3. Unmet requirements written out as traceable remediation tasks for the coding assistant (Spec Kit converge, GSD
   gap closure).
4. Test-execution evidence per requirement or scenario (BMAD, Kiro).
5. An "unchanged behaviour" section for bug fixes (Kiro).
6. A review summary for the PR, written to `reports/` (GSD, Traycer).
7. Cheap code-only spec lints (OpenSpec).

Stores, hooks, workflow engines, tracker sync and PBT generation cost more than they return for this tool.

### Cited Findings
Sources for each candidate are in the sections above. The key ones:
- OpenSpec: [`show --diff`](https://github.com/Fission-AI/OpenSpec/blob/main/docs-lab/reference/cli.md) and its
  archive-guarding [validate warnings](https://github.com/Fission-AI/OpenSpec/releases/tag/v1.14.2).
- Tessl: [CI verify](https://docs.tessl.io/codifying-and-enforcing/verify-agent-changes-in-ci) and
  [its changelog](https://docs.tessl.io/changelog-cli).
- Spec Kit: [converge](https://github.com/github/spec-kit/blob/main/templates/commands/converge.md).
- GSD: [verify-and-ship](https://github.com/open-gsd/gsd-core/blob/main/docs/how-to/verify-and-ship.md).
- BMAD: [6.11.0](https://github.com/bmad-code-org/BMAD-METHOD/releases/tag/v6.11.0).
- Kiro: [bugfix specs](https://kiro.dev/docs/specs/bugfix-specs/) and
  [correctness](https://kiro.dev/docs/specs/correctness/).
- Traycer: [artifact workflow](https://docs.traycer.ai/concepts/artifact-workflow.md).

### Inferences
Each candidate below gives what it is, the evidence for it, how it could fit the local CLI, who benefits, and the
size and risk.

1. **Per-requirement delta diff for the approver.**
   - What: when `approve` runs, or in `status <id>`, show each MODIFIED requirement as a diff against the living
     spec, and warn when a header matches only after folding case or whitespace.
   - Evidence: OpenSpec `show --diff`.
   - Fit: code only, no model; the roadmap already ranks it first.
   - Who benefits: the approver, who reads a diff instead of two documents.
   - Size: small. Risk: low.
2. **Verify made for CI.**
   - What: flags on existing commands, no new command.
     - `verify --dry-run` lists the requirements and files that would be judged, and the number of model calls,
       without calling a model. This also serves the owner's no-live-call rule.
     - A call budget that refuses before judging.
     - Diff-scoped judging against `--base <ref>`.
     - A JSON report with stable requirement IDs, plus GitHub annotations or SARIF pointing at the quoted lines.
       Quotes are already code-checked, so their line numbers are known.
   - Evidence: Tessl `change verify` (`--dry-run`, `--max-calls`, `--report-json` with stable IDs, line annotations,
     `--base`); Spec Kit community CI Guard and DocGuard (SARIF/JUnit).
   - Fit: the roadmap's "`validate` codes for a voided approval and drifted work in CI" is the code-only half of
     this.
   - Who benefits: teams that gate merges.
   - Size: medium. Risk: low, if the annotations come from code-checked quotes only.
3. **Remediation tasks from a failing verify.**
   - What: each requirement judged unmet becomes an appended task citing its requirement ID and the quoted
     evidence. Nothing else in the file is rewritten, and a converged run leaves the file byte-identical.
   - Evidence: Spec Kit converge (append-only, "byte-for-byte unchanged" when converged, findings traced by
     `source-ref`); GSD gap-closure plans; Traycer fix-up tickets.
   - Fit: this gives the coding assistant its next work in a form it already reads.
   - Caution: an edit to `tasks.md` voids the approval under the local rule. Either append to a reports file that
     the Agent Skill points the assistant at, or exempt an appended "Convergence" section from the fingerprint, as
     ticking a box already is. The owner should decide.
   - Size: small to medium.
4. **Test-execution evidence per requirement.**
   - What: map each scenario to the tests that cover it, by name or by a test ID the tasks require. Read the test
     runner's report (for example JUnit XML) so that code, not the model, confirms each test **ran and passed**.
     Then add a "verification gap" lens: which changed behaviour has no test that would fail.
   - Evidence: BMAD (a test "that exists but was never registered, filtered in, or enabled counts as missing"; "if
     this behavior broke, would any test fail?"); Kiro (property ↔ requirement ↔ task traceability); OpenSpec's guide
     ("A checked task or an agent's summary alone does not prove the test passed").
   - Fit: it extends phase 9 (tests as evidence).
   - Size: medium. The value is high, because it moves part of the verdict from the model to code.
5. **Bug-fix shape: current, expected and unchanged behaviour.**
   - What: for a fix, the brief or delta carries "unchanged behaviour" requirements (WHEN … SHALL CONTINUE TO …),
     and `verify` judges the diff against them like any requirement.
   - Evidence: Kiro bugfix specs.
   - Fit: a grammar addition, with no new command.
   - Who benefits: anyone fixing bugs on the lean path, where regressions hide.
   - Size: small to medium.
6. **A review summary for the PR.**
   - What: `verify` also writes a short Markdown summary to `reports/`: the change's goal, the requirements
     addressed by ID, the verdict per requirement with its quoted evidence, the approvals and their fingerprints,
     and a suggested review order (brief → spec delta → code). The person pastes it into the PR. Nothing extra is
     printed on screen.
   - Evidence: GSD `/gsd-ship` PR body (REQ-IDs, verification status); Traycer changeset walkthrough ("what changed
     and the review order"); OpenSpec team convention (review the proposal, then the spec delta, then the code; in a
     doc comment of the teams skeleton).
   - Size: small.
7. **Cheap spec lints in `validate --strict`, code only.**
   - What, where not already present:
     - a scenario without a WHEN or a THEN;
     - an over-long requirement;
     - an unknown delta section;
     - text in a delta that archive would drop;
     - an unknown key in `change.json` (already refused).
   - Evidence: OpenSpec 1.14 to 2.1.1.
   - Size: small. Each closes a silent loss at archive.
8. **Constitution as rules judged in verify, with scope and severity.**
   - What: the roadmap's second candidate. The Tessl verifier format suggests the shape: each rule with a
     `relevant_when`, globs and an error or warn level, so a rule is judged only on the files it applies to.
     Spec Kit treats a constitution MUST violation as CRITICAL in analyze and converge.
   - Size: medium. It needs measurement first, as the roadmap says.
9. **A second-opinion judge on the other provider arm** (optional; config, not a command).
   - What: re-judge disputed or failed requirements with the other model (Copilot or Gemini). A finding is kept only
     where its quote checks.
   - Evidence: BMAD review layers that swap in "a different model"; GSD cross-AI review lanes; Traycer debate.
   - Cost: double the model calls on the hard cases. Measure before building.

Not recommended now (cost greater than benefit, or against the golden rule):
- OpenSpec-style stores and worksets: a new topology and new commands. The local CLI already spans repositories.
- Spec Kit-style YAML workflows and extension hooks: an engine and an extension surface. `approve` is already the
  gate.
- Jira, Linear and GitHub Projects sync: community territory, and it needs network credentials.
- Generating property-based tests: this would write test code, which is outside the tool's rule. The useful part is
  in candidates 4 and 5.
- Self-updating living specs: contradicts approval-by-fingerprint and the "intent over code" rule.
- Interactive UAT walkthroughs: GSD's is good, but it adds a conversational step. A cheaper partial answer is
  for the verify report to list scenarios that have no automated evidence as "needs a person's check".

Already at parity, no work needed:
- staleness of approvals and of verified work (GSD's fingerprint idea; the local CLI already blocks archive on
  drifted work);
- a dashboard (`status`);
- revising a change by instruction (Traycer `revise-requirements`);
- MCP tools (the local server does more than Spec Kit's).

### Gaps
- No competitor publishes how often its verify finds real defects, so the ranking rests on mechanism and cost, not on
  measured yield.
- Whether line-anchored annotations can be produced for every quote depends on how the local verify records quote
  positions. This was not checked in the source.
- How the approval fingerprint should treat appended remediation tasks (candidate 3) is a design decision for the
  owner. No competitor has fingerprinted approvals to compare with.
