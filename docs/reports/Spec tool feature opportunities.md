# Put adk-spec's grounded evidence to work

The highest-value additions to adk-spec are not new stages or commands. They reuse evidence the tool already computes and then discards. **Ranked first is suspect requirements.** When a change is archived, adk-spec would keep each `met` verdict's code-checked quote, and `status` and `validate` would re-check those quotes against the current code. A living requirement whose implementing lines have gone is then flagged with no model call. Traceability tools have long marked a requirement-to-requirement link "suspect" when the parent changes; this moves that practice onto the link between a requirement and its code, which none of the tools studied does. Next come three cheap upgrades:

- a per-requirement review view for the approver (the roadmap's own first candidate);
- a `verify` that hands unmet requirements back as the coding assistant's next work, as Spec Kit's converge and GSD's gap closure do;
- a merge gate that reads the committed record through GitHub annotations instead of re-running a model.

Four more cover hand-off documents, tests as per-requirement evidence, rules and decisions judged in `verify`, and assistant integration as structured data. **None of the eight adds a subcommand, a `change.json` field or a model call.** Six touch no model prompt at all. Only options 6 and 7 need a live measurement before they are built. The market context explains the ranking. Every spec-driven tool studied in November 2026 now insists that a verdict carry evidence, but none documents checking that evidence in code. Their real lead is in what happens after the verdict: the hand-off to a fix, a reviewer, a pull request or CI. adk-spec already holds the stronger evidence, and these options carry it across those hand-offs.

Code references are relative to the repository root, at branch `audit4` (HEAD 7320972). The research date is 24 November 2026.

## Seven stores of checked evidence end in write-only files

The internal map found **seven stores of data that adk-spec computes with care and then drops or never reads back**. The most valuable is the evidence `verify` grounds:

- **Verify evidence.** `grounded()` returns, for each requirement, the `(path, quote)` pairs that code has proved present in the diff (`adk_spec/domain/verify.py:101-133`). The `Verification` record then keeps only `verdicts`, a map from ID to met, unmet or unclear (`adk_spec/domain/model.py:180-198`). The evidence survives only in `reports/verify.md`, which the renderer says is "never parsed back" (`adk_spec/domain/report_md.py:1-5`). `archive` folds requirements into the living spec with no provenance (`adk_spec/domain/merge.py:36-48`).
- **Task metadata.** The task list's `files:`, `verify:` and `[P]` metadata is rendered and validated (`adk_spec/domain/tasks_md.py:81-88`, `adk_spec/domain/validate.py:270-274`), but no command compares it with the diff.
- **Verdicts after a failure.** After an `unmet` verdict, the next step is the same generic "implement tasks.md, then run `adk-spec verify <id>`" whatever the verdicts said (`adk_spec/domain/lifecycle.py:422-445`).
- **Readings.** The statements in `context.md` and `profile.md` are quote-checked once and never again.
- **Lessons.** Lesson counts are stripped before a stage reads `lessons.md`, and no command prints them.
- **Recordings.** Run recordings are pruned at 20, and only `scripts/measure.py` reads them.
- **History.** Archived deltas are never read; `taken()` skips them (`adk_spec/workspace/layout.py:231-245`).

Every journey that leaves `.spec/` stops short. Nothing turns a verified change into a pull-request description, archived changes into a changelog, an `unmet` verdict into the next fix, or a living requirement back into the code that implements it. Two open changes that modify the same requirement are found only when the second one archives, as `delta.base-stale`. The project's prior research named this failure in the parent tools. Both "fail at the same point, the hand-back after implementation", and a hybrid "needs the fold-back to be automatic or checked, plus a visible drift signal" (`docs/research_notes/Spec driven framework on Google ADK/sdd_comparison_and_critique.md:90`). Phase 9 was put on the roadmap to map test "results to requirement IDs" (`docs/superpowers/plans/README.md:246-250`), but its design then made that mapping a non-goal (`docs/superpowers/specs/2026-11-22-verify-tests-design.md:31-34`).

Every option below is held to four rules:

- **The golden rule:** a capability goes inside an existing command, and a command prints what it wrote, what needs the person and the next command (`docs/superpowers/plans/README.md:5-14`).
- **The layers:** four of them (`domain` → `workspace` → `orchestration` → `interfaces`), and the workspace layer imports no network code.
- **The phase-9 anti-goal:** no command from a change's files, from a model's answer or from a task's `verify:` line is ever run.
- **Compatibility:** a new `change.json` field makes every older adk-spec refuse the file. The owner rejected recording the tier in an approval on exactly that ground (`docs/superpowers/plans/README.md:423-424`). `config.toml` refuses unknown keys in the same way (`adk_spec/workspace/config.py:1-2`).

Two facts in the source make compatible designs cheap. First, an approval fingerprints only `brief.md`, `design.md`, `tasks.md` and the delta specs (`adk_spec/workspace/layout.py:381-386`). Anything under `reports/`, and any new file in the change folder, is outside every approval. Second, capabilities are found by the folders that hold a `spec.md` (`adk_spec/workspace/layout.py:159-166`). A sidecar file beside a living spec is therefore invisible to older versions.

## Rivals demand evidence, but none checks it in code

By November 2026 the spec-driven field has converged on the idea that **a model's verdict counts only with evidence**:

- BMAD 6.11 "requires a source reference on every finding". Its verification-gap reviewer asks "if this behavior broke, would any test fail?" ([BMAD v6.11.0](https://github.com/bmad-code-org/BMAD-METHOD/releases/tag/v6.11.0)).
- GSD's verifier records a digest of every input. Any change flips `passed` to `stale`, and the report is "re-checked, not cached" ([GSD verify and ship](https://github.com/open-gsd/gsd-core/blob/main/docs/how-to/verify-and-ship.md)).
- Spec Kit's converge states that "completion claims are not evidence" ([Spec Kit converge](https://github.com/github/spec-kit/blob/main/templates/commands/converge.md)).
- OpenSpec's own guide concedes that "A checked task or an agent's summary alone does not prove the test passed" and that "Archiving does not enforce these checks" ([OpenSpec review guide](https://github.com/Fission-AI/OpenSpec/blob/main/docs-lab/guides/review-the-plan.md)).

**None of these tools, and none of the AI code reviewers studied (Copilot, CodeRabbit, Qodo, Greptile), documents a check in code that a quoted passage exists.** adk-spec's `quoted_at` rule remains stronger than anything found.

Where the rivals lead is **after the verdict**:

- **Converge.** Spec Kit appends unbuilt work as traceable tasks and leaves `tasks.md` "byte-for-byte unchanged" when the feature is complete ([Spec Kit converge](https://github.com/github/spec-kit/blob/main/templates/commands/converge.md)).
- **PR bodies.** GSD's `/gsd-ship` builds the body from "Requirements addressed (REQ-IDs)" and the verification status ([GSD](https://github.com/open-gsd/gsd-core/blob/main/docs/how-to/verify-and-ship.md)).
- **Batch review.** Traycer's batch review gives small problems a fix-up ticket and stops the run on product drift ([Traycer artifact workflow](https://docs.traycer.ai/concepts/artifact-workflow.md)).
- **CI ergonomics.** Tessl's `change verify` brings a dry run, a call budget, stable rule IDs in a JSON report, and GitHub annotations on "the lines a failed check refers to" ([Tessl changelog](https://docs.tessl.io/changelog-cli)).
- **A reviewer's diff.** OpenSpec's `show --diff` shows the approver each MODIFIED requirement as a diff ([OpenSpec CLI reference](https://github.com/Fission-AI/OpenSpec/blob/main/docs-lab/reference/cli.md)).

The traceability tools show a different gap. Doorstop reports a link as suspect "when the fingerprint of a parent item changes" ([Doorstop validation](https://doorstop.readthedocs.io/en/v2.0/cli/validation/)). Jama raises suspect links on upstream field edits ([Jama suspect links](https://help.jamasoftware.com/en/manage-content/coverage-and-traceability/relationships/clear-suspect-links.html)). PTC's suspect traces are marked automatically and cleared by a person after review ([PTC Windchill RV&S](https://support.ptc.com/help/windchillrvs/r13.2.0.0/en/IntegrityHelp/int-user/client_docs_managing_suspect_trace_relationships.html)). Yet Doorstop does not notice edits to the content of referenced source or test files; a feature discussion proposes hashing them (search summary, [doorstop issue #564](https://github.com/doorstop-dev/doorstop/issues/564)). Jama's triggers are field edits. **No tool studied marks a requirement suspect when the code behind it changes**, and adk-spec holds exactly the data needed to do it.

Two cautions shape the ranking. Every quantitative claim from these vendors is the vendor's own, and no competitor publishes how often its verify finds real defects. The ranking therefore rests on mechanism, on how many independent sources point the same way, and on cost, not on measured yield. Some highly visible features are hype. Augment Intent's spec that "updates to reflect reality" could not be traced to any primary documentation ([Augment Intent, search result](https://www.augmentcode.com/intent)). BMAD's own A/B test found that a reviewer persona "made no difference to residual-bug hit rate" ([BMAD v6.11.0](https://github.com/bmad-code-org/BMAD-METHOD/releases/tag/v6.11.0)).

## Eight ranked options, none needing a new command

| Rank | Option | Type | Commands that do more | Model prompts touched | Live measurement first | Effort | Sources that converge |
|---|---|---|---|---|---|---|---|
| 1 | Suspect requirements from kept verify evidence | `Feature Upgrade` | verify, archive, status, validate | None | No (an offline noise check) | Medium | Internal (evidence dropped), Doorstop, Jama and PTC suspect links, Doorstop's code-content gap, GSD staleness, prior research's drift signal |
| 2 | Per-requirement review view for the approver | `Feature Upgrade` | approve, check, archive, status | None | No | Small | Roadmap #1, OpenSpec `show --diff` and bulk archive, StrictDoc and req-cli diffs, SLSA v1.2 review rule |
| 3 | Unmet verdicts become the assistant's next work | `Feature Upgrade` | verify, status | None | No | Small to medium | Internal (generic next step, unused task metadata), Spec Kit converge, GSD gap closure, Traycer fix-ups, OpenSpec review guide |
| 4 | A merge gate that reads the committed record | `Feature Upgrade` | validate | None | No | Small to medium | Roadmap #4, Tessl `change verify`, GitHub workflow commands, rulesets and SARIF, GitLab code quality, Conftest |
| 5 | A pull-request summary and a requirement changelog | `New Feature` | verify, archive | None | No | Small | Internal (stopped journeys), GSD ship, Traycer walkthrough, StrictDoc changelog, sphinx-needs history |
| 6 | Tests that ran, mapped to requirements | `Feature Upgrade` | verify, init, propose and plan (tasks) | The tasks stage | Yes, for the tasks instruction | Medium | Internal (phase-9 promise), BMAD matrix audit, Kiro traceability, JUnit XML, OpenSpec guide, Qodo |
| 7 | Rules and design decisions judged in verify | `Feature Upgrade` | verify, plan (design) | The verify and design stages | Yes | Medium | Roadmap #2, Tessl verifiers, Spec Kit analyze and converge, MADR Confirmation, BMAD intent auditor |
| 8 | Structured MCP results and a cross-client Skill | `Feature Upgrade` | adk-spec-mcp, init, check, verify | None | No | Small to medium | Internal (MCP returns text only), MCP 2026-07-28, Agent Skills, AGENTS.md, Spec Kit's MCP server |

The roadmap's four candidates map onto this list as follows (`docs/superpowers/plans/README.md:458-461`):

- The MODIFIED-requirement diff is the core of option 2.
- `verify` against the constitution is option 7.
- `validate` codes for a voided approval and drifted work are the core of option 4.
- The tier raised after the reading is held back (see the next section) until a measurement shows that triage under-sizes requests.

### 1. Keep verify's evidence and flag suspect requirements

**Title & Type.** Suspect requirements from kept verify evidence. `Feature Upgrade` of `verify`, `archive`, `status` and `validate`.

**Evidence & Inspiration.** In the codebase, `grounded()` proves each quote present in the diff (`adk_spec/domain/verify.py:101-133`). Then `Verification` keeps only the verdicts (`adk_spec/domain/model.py:180-198`), and `archive` merges with no provenance (`adk_spec/domain/merge.py:36-48`). After archive, nothing re-checks a living requirement against later code.

Traceability practice supplies the mechanism. Doorstop marks a link suspect on a parent fingerprint change and clears it with `doorstop clear` ([Doorstop validation](https://doorstop.readthedocs.io/en/v2.0/cli/validation/)). Jama and PTC flag downstream items for a person to clear after review ([Jama](https://help.jamasoftware.com/en/manage-content/coverage-and-traceability/relationships/clear-suspect-links.html); [PTC](https://support.ptc.com/help/windchillrvs/r13.2.0.0/en/IntegrityHelp/int-user/client_docs_managing_suspect_trace_relationships.html)). The industry-standards research reduces suspect links to "a requirement ID plus a content hash". None of these tools tracks code content ([doorstop #564](https://github.com/doorstop-dev/doorstop/issues/564), search summary).

GSD applies the same staleness idea at report level ([GSD](https://github.com/open-gsd/gsd-core/blob/main/docs/how-to/verify-and-ship.md)). adk-spec already has staleness too, as `drifted` work for an open change, but it loses it at archive. The prior research asked for exactly this "visible drift signal", treated as "information, not a gate" (`sdd_comparison_and_critique.md:90, 166`).

**Core Value.** The living spec becomes a requirement-to-code map that stays honest after archive. `status` can say, for example, "auth: 2 of 14 requirements suspect, their evidence is gone from src/auth/passkey.py", and count the requirements that have no evidence on record. That count is the coverage view docs-as-code tools such as sphinx-needs provide ([sphinx-needs](https://sphinx-needs.readthedocs.io/en/latest/)).

Different people benefit:

- **Maintainers** learn which requirements a refactor may have broken, without a model call.
- **Auditors** get provenance: which change, which commit and which lines met each requirement.
- **The next `propose`** that touches the capability can name its suspect requirements.

The kept evidence also feeds options 4, 5 and 6, which turns several later options into renderers over one store.

**Codebase Fit.**

- **Domain.**
  - A new grammar module, `adk_spec/domain/evidence_md.py`. It renders and parses back lines of requirement ID, path, quote, change ID and commit, in the project's render-and-parse-back style.
  - A pure `suspect()` function that re-finds each quote in the current file text with `quoted_at` (`adk_spec/domain/text.py:51`). That function already returns the line where a quote starts, so a surviving quote is re-anchored to its current line.
  - A `spec.evidence-gone` code in `SEVERITY` (`adk_spec/domain/validate.py:24-67`).
- **Workspace.**
  - `verify` writes `changes/<id>/evidence.md`, which is outside the approval set.
  - `archive` folds the final verification's evidence into `.spec/specs/<capability>/evidence.md`, in the same all-or-none write as the merged specs. Older adk-spec ignores that sidecar, because it finds capabilities by their `spec.md` alone.
  - A quote missing from its file is searched for across tracked files with the existing `git grep` wrapper (`adk_spec/workspace/git.py:212-221`), so a moved function reads as moved, not gone.
  - Quotes pass through `secrets.scrub` before they are written.
- **Interfaces.** `status` prints one line per affected capability, and `validate` emits findings with a path and line.
- **Clearing.** A suspect clears when a later change verifies that requirement, whose fresh evidence replaces the line, or when a person deletes the line in a reviewed commit. That is Doorstop's `clear` without a command.
- **One checker for every reading.** The same re-checker extends to the `context.md` statements at `approve` and to `profile.md` at the start of `propose`. It would tell the person to delete `context.md`, or to run `init --refresh`.

**Impact vs. Effort.** High impact, medium effort: one grammar, one pure checker, one validate code, one archive write and one status line. It needs no model call and no live model measurement. Its noise rate is unknown, though. An offline replay should decide whether `spec.evidence-gone` is a WARNING, which fails `--strict`, or only INFO: take quotes from verified changes and check them against later commits of a real repository. `quoted_at` already treats every run of whitespace as one space, which absorbs reformatting. Evidence for a requirement that a later change retires must be dropped at that archive.

### 2. Show the approver what each requirement changes, and who else is changing it

**Title & Type.** Per-requirement review view for the approver. `Feature Upgrade` of `approve` and `check`, and of `archive`'s stop on a moved base.

**Evidence & Inspiration.** In the codebase, the living spec holds the old requirement and the delta holds the new one until archive, and both are already loaded together (`adk_spec/interfaces/cli.py:459-468`). Even so, the approver reads two documents. Two open changes that modify or remove the same requirement are found only at the second archive, as `delta.base-stale` (`adk_spec/domain/merge.py:34-35`). The person then finds and reads the moved text by hand (`adk_spec/interfaces/cli.py:814-823`). The prior research names OpenSpec's "parallel-change overwrite on archive" as a failure that "delta-merge designs must handle (conflict detection at requirement level)" (`sdd_comparison_and_critique.md:92`).

Competitors and standards point the same way:

- OpenSpec's `show --diff` prints ADDED requirements whole, REMOVED ones with their Reason and Migration, and each MODIFIED one as a diff against the main spec ([OpenSpec CLI reference](https://github.com/Fission-AI/OpenSpec/blob/main/docs-lab/reference/cli.md)).
- OpenSpec's bulk archive checks the codebase "When two change proposals touch the same spec" ([OpenSpec skills](https://github.com/Fission-AI/OpenSpec/blob/main/docs-lab/reference/skills.md)).
- StrictDoc compares requirement trees at two git revisions ([StrictDoc release notes](https://strictdoc.readthedocs.io/en/stable/strictdoc_04_release_notes.html)), as does req-cli's `diff` ([req-cli](https://docs.rs/crate/req-cli/0.1.0/source/src/commands/diff.rs)).
- SLSA v1.2's Source track says reviewers must see a clear representation of what accepting a change would do, and that an approval applies to the final revision ([SLSA v1.2 source requirements](https://slsa.dev/spec/v1.2/source-requirements)).

**Core Value.** Approving becomes reading one diff per changed requirement rather than reconstructing it from two files. A team learns at approval time, not at archive, that another open change also modifies or removes the same requirement. A `delta.base-stale` stop shows what moved instead of sending the person to look for it. Approvers benefit, including the second approver a strict change needs, and so do teams that run several open changes at once.

**Codebase Fit.**

- **Domain.** A pure `adk_spec/domain/review_md.py`. It makes a `difflib` unified diff of each MODIFIED requirement's canonical render (`spec_md`) against the living one, shows REMOVED and ADDED requirements whole, and lists the overlaps.
- **Workspace.** Overlaps are gathered by the loop that already walks the open changes' deltas to hand out IDs (`taken()`, `adk_spec/workspace/layout.py:231-250`). The view is written to `reports/review.md`, outside every approval. At archive's base-stale stop, the old text comes from git at the change's `base_commit` through `workspace/git.py`, where `.spec/` is committed.
- **Interfaces.** `approve` and `check` print one line, for example "2 requirements modified, 1 also modified by open change X: reports/review.md". `status` folds an overlap into its next phrase.

**Impact vs. Effort.** High value per unit of cost. The effort is small: no model, no field and no measurement. It is the roadmap's first candidate, widened with the overlap warning and the base-stale explanation, which share its renderer. The risk is negligible, since the output is a report outside every approval, and the terminal shows a single line.

### 3. Turn unmet verdicts into the assistant's next work

**Title & Type.** Unmet verdicts become the next work. `Feature Upgrade` of `verify` and of the next step that `status` names.

**Evidence & Inspiration.** In the codebase, a change whose verification is not all `met` stays `approved`. `_after_approval` reads only `tests_passed` and prints the same generic step whatever the verdicts said (`adk_spec/domain/lifecycle.py:422-445`). The README's advice is "Implement what is missing ... and verify again" (`README.md:571`). A task's `files:` metadata is never compared with the diff. Any edit to `tasks.md` other than ticking a box voids the approval, and `plan` drafts no tasks for an approved change (`README.md:456-460`). The owner's original design had an apply-and-converge loop that appended convergence tasks (`docs/reports/02-adk-spec-framework-architecture-and-roadmap.md:56-59`).

Competitors close this loop:

- Spec Kit's converge appends remaining work as a `## Phase N: Convergence` section. It is "APPEND-ONLY, NEVER REWRITE", gives each finding a stable ID and the `source-ref` it traces to, and leaves the file untouched when the work is complete ([converge](https://github.com/github/spec-kit/blob/main/templates/commands/converge.md)). Spec Kit's delivery loop now ends in converge ([Evolving specs](https://github.com/github/spec-kit/blob/main/docs/how-to/evolving-specs.md)).
- GSD sends failures to a gap-closure planner ([GSD](https://github.com/open-gsd/gsd-core/blob/main/docs/how-to/verify-and-ship.md)).
- Traycer files fix-up tickets after reviewing each batch against the plan ([Traycer](https://docs.traycer.ai/concepts/artifact-workflow.md)).

**Core Value.** This closes the hand-back the prior research named as both parent tools' failure. One failing `verify` would produce a list the coding assistant can act on. It would hold:

- each unmet or unclear requirement, with the model's reason;
- the tasks linked to that requirement;
- the files those tasks named that the diff never touched;
- every ticked task whose requirement is unmet, which is the clearest sign of an agent ignoring the spec.

The next-step line names the list. The Skill and the MCP tools follow the step `status` names (`adk_spec/workspace/skill.py:63-64`), so an assistant loops back without a person writing a prompt. Solo developers driving assistants benefit most, and reviewers stop receiving "done" claims that the verdicts contradict.

**Codebase Fit.**

- **Domain.**
  - `_after_approval` reads `state.verification.verdicts`, which `change.json` already holds, so no field is added. It names the IDs, for example "REQ-AUTH-005 unmet: work from reports/remaining.md, then run `adk-spec verify <id>`".
  - A pure `adk_spec/domain/remaining.py` crosses the verdicts with `Task.requirements`, `Task.files`, the ticked state and the diff's paths (`parts_of_diff`).
- **Workspace.** `reports/remaining.md` is rewritten whole on each `verify` and removed once every requirement is met, mirroring converge's untouched file when the work is complete.
- **Interfaces.** `verify` prints one `wrote` line.
- **Approval.** `tasks.md` is never touched, so the approval holds. The owner could instead allow an appended Convergence section that the fingerprint ignores, as `_as_approved` already lets ticks pass.
- **Anti-goal.** No task's `verify:` line is run.
- **Reach.** The Skill is written once and never over an existing copy, so new Skill text reaches only new installs. The next-step line reaches everyone.

**Impact vs. Effort.** High value for small-to-medium effort. There is no new model call, because the reasons come from the verdict call that already runs, and no live measurement is needed to build it. Running the labelled `half-done` case would show whether the reasons are specific enough to act on. One risk is that the model's reason for an unmet verdict is prose that code has not grounded. The report should label it as such and list the code-derived items (untouched files, ticked but unmet) first.

### 4. Gate merges on the committed record, with annotations

**Title & Type.** A merge gate that reads the committed record. `Feature Upgrade` of `validate`.

**Evidence & Inspiration.** In the codebase, `Assessed` already computes `stale` (an approval no longer covers the files) and `drifted` (the work changed since it was verified) (`adk_spec/interfaces/cli.py:427-494`). Yet `validate` emits only structural findings and calls `_assessed(..., drift=False)` (`adk_spec/interfaces/cli.py:544-554`). The documented CI recipe is `validate --strict` alone (`README.md:536-543`). The package holds no SARIF, annotation or job-summary output. This is the roadmap's fourth candidate.

Competitors:

- Tessl's `change verify` runs as a CI gate with a dry run that makes no judge calls, a `--max-calls` budget, `--report-json` with stable verifier IDs, and annotations on failed lines ([Tessl CI verify](https://docs.tessl.io/codifying-and-enforcing/verify-agent-changes-in-ci); [Tessl changelog](https://docs.tessl.io/changelog-cli)).
- Spec Kit's community lists CI Guard ("block merges on gaps") and DocGuard (SARIF and JUnit output) ([Spec Kit extensions](https://github.com/github/spec-kit/blob/main/docs/community/extensions.md)).

Standards:

- Any workflow step can write `::error file=…,line=…::` annotations and append Markdown to `$GITHUB_STEP_SUMMARY` ([GitHub workflow commands](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-commands)). A step may show 10 warning and 10 error annotations, so the job summary must carry the full list ([GitHub check runs](https://docs.github.com/en/rest/checks/runs)).
- Rulesets make a status check required ([GitHub rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets)).
- SARIF 2.1.0 deduplicates across runs by `partialFingerprints` and a stable `ruleId`, and shows alerts only on changed lines ([GitHub SARIF support](https://docs.github.com/en/code-security/code-scanning/integrating-with-code-scanning/sarif-support-for-code-scanning)).
- GitLab's code-quality JSON takes the same fields ([GitLab Code Quality](https://docs.gitlab.com/ci/testing/code_quality/)).
- Conftest separates warn and fail exit codes ([Conftest options](https://www.conftest.dev/options/)).

**Core Value.** A team can make "every change in this pull request is approved as it stands, and no verified work has drifted" a required status check. Findings are annotated on the exact `.spec/` line, with a short summary on the run page. It needs no GitHub App, no bot, no model call and no token in CI. Maintainers and reviewers who merge benefit. adk-spec gains the spec-level equivalent of GitHub's "dismiss stale approvals on push".

**Codebase Fit.**

- **Domain.**
  - Three new `SEVERITY` codes: `change.approval-void` and `change.work-drifted` as WARNINGs, so `--strict` fails on them, plus option 1's `spec.evidence-gone`.
  - A pure `adk_spec/domain/ci_md.py` that renders escaped workflow-command lines and a summary from `Finding`. `Finding` already carries a path and a line (`adk_spec/domain/model.py:124-129`).
- **Interfaces.**
  - `validate` assesses drift where git history is present.
  - When `GITHUB_ACTIONS=true`, it prints annotations and appends the summary to the file the runner names. That is a plain file write with no network.
  - The README gains a sample workflow with `fetch-depth: 0`.
  - Repositories named with `--with` that are absent in CI produce INFO, not a failure.
  - Messages pass `secrets.scrub`, because annotations leave the machine.
- **Later.** SARIF (`ruleId` as the finding code, a fingerprint from code, path and quote) and GitLab JSON can follow from the same finding model.
- **No live calls.** The gate never runs `verify`. It checks the record `verify` committed (the diff fingerprint and base commit), which keeps the no-live-call rule.

**Impact vs. Effort.** High value for teams, for small-to-medium effort, with no model and no measurement. One code decision is required first: `_drifted` returns true on a `GitError` (`adk_spec/interfaces/cli.py:488-491`), so a shallow clone would read as drifted. That case must become INFO. Annotations should ship before SARIF, because whether code scanning works on private repositories without GitHub Advanced Security was not verified.

### 5. Hand off a pull-request summary and a requirement changelog

**Title & Type.** A pull-request summary at verify and a requirement changelog at archive. `New Feature`, hosted in `verify` and `archive`.

**Evidence & Inspiration.** In the codebase, `verify` ends with "run adk-spec archive" (`adk_spec/interfaces/cli.py:1652-1662`). Nothing assembles a pull-request body, although every input is recorded: the brief's title and why, the requirement IDs, the verdicts and evidence, the test outcomes, the approvers and any override with its reason. The README's flow ends with "Commit the change with the code it describes" (`README.md:379`). `archive` prints one line and records no date.

Competitors and adjacent tools:

- GSD's `/gsd-ship` builds the PR body from the goal, "Requirements addressed (REQ-IDs)", the verification status and key decisions ([GSD](https://github.com/open-gsd/gsd-core/blob/main/docs/how-to/verify-and-ship.md)).
- Traycer writes "a spec explaining what changed and the review order" ([Traycer](https://docs.traycer.ai/concepts/artifact-workflow.md)).
- StrictDoc's Changelog compares requirement trees between revisions ([StrictDoc](https://strictdoc.readthedocs.io/en/stable/strictdoc_04_release_notes.html)), and sphinx-needs builds a history from versioned `needs.json` exports kept in git ([sphinx-needs builders](https://sphinx-needs.readthedocs.io/en/latest/builders.html)).
- CodeRabbit's Addressed, Not addressed and Unclear scale for pull requests matches adk-spec's met, unmet and unclear ([CodeRabbit PR validation](https://docs.coderabbit.ai/issues/pr-validation)).

**Core Value.** A verified change leaves adk-spec as a ready pull-request description. It holds the goal, each requirement ID with its verdict and one line-anchored quote, the test outcomes, the approvers, any override with its reason, the other repositories at their base commits, and a review order (brief, then deltas, then code). Each archive adds a requirement-level entry to a changelog: the date, the change, and the IDs added, modified or removed. Reviewers see intent and proof without opening `.spec/`. Release notes can draw on requirement-level history. The archive date is recorded without a `change.json` field.

**Codebase Fit.**

- **Domain.** Pure renderers `summary_md.py` and `changelog_md.py`. The changelog is parsed back, so a new entry can be prepended safely.
- **Workspace.** `reports/summary.md` is written when a verification leaves the change `verified`. `.spec/changelog.md` is written in the same all-or-none write as the archived specs (`adk_spec/workspace/layout.py:189-197`).
- **Interfaces.** One `wrote` line each. The Skill and the MCP `verify` tool tell the assistant to use the summary as the PR body.
- **No GitHub call.** There is no `gh` call: the workspace layer imports no network code, and the person or assistant pastes the text.
- **With option 1.** Evidence lines carry current line numbers.

**Impact vs. Effort.** Medium-to-high value for small effort, with no model and no measurement. Two questions remain open. Does `archive` run on the feature branch or on `main`? That decides where the changelog entry lands. And a single changelog file produces small, real merge conflicts between teammates.

### 6. Map the tests that ran to the requirements they cover

**Title & Type.** Tests that ran, mapped to requirements. `Feature Upgrade` of `verify`, with `init` and the tasks stage.

**Evidence & Inspiration.** In the codebase, `verify` runs the person's command and records one outcome per repository (`adk_spec/domain/model.py:192-198`). Phase 9 promised that a person could "see which requirements no test covers" (`docs/superpowers/plans/README.md:246-250`), but its design dropped that as a non-goal (`docs/superpowers/specs/2026-11-22-verify-tests-design.md:31-34`). The owner's original design bound tests with `@pytest.mark.spec("<capability>:<REQ-ID>")` (`docs/reports/02-adk-spec-framework-architecture-and-roadmap.md:47`). `verify` runs no tests at all until a person writes `[verify] test` (`adk_spec/workspace/config.py:20-22`), although `init`'s reading was designed to describe how the project is tested (`docs/superpowers/plans/README.md:207-208`).

Competitors:

- BMAD 6.11 requires a covering test for every matrix row "that actually executed and passed: one that exists but was never registered, filtered in, or enabled counts as missing" ([BMAD v6.11.0](https://github.com/bmad-code-org/BMAD-METHOD/releases/tag/v6.11.0)).
- Kiro links each property to its requirement and task ([Kiro correctness](https://kiro.dev/docs/specs/correctness/)).
- OpenSpec's guide says a checked task does not prove a test passed ([OpenSpec review guide](https://github.com/Fission-AI/OpenSpec/blob/main/docs-lab/guides/review-the-plan.md)).
- Qodo's "PR Code Verified" grade marks code that meets a ticket "but requires additional manual testing" ([PR-Agent ticket context](https://raw.githubusercontent.com/qodo-ai/pr-agent/main/docs/docs/core-abilities/fetching_ticket_context.md)).

Standards:

- JUnit XML has no official specification, but its common subset carries per-test `properties`, which pytest and Playwright both write ([testmoapp/junitxml](https://github.com/testmoapp/junitxml)).
- sphinx-test-reports links test results to specification objects ([sphinx-test-reports](https://sphinx-test-reports.readthedocs.io/en/latest/)).
- OpenFastTrace shows whether planned requirements were implemented ([OpenFastTrace](https://github.com/itsallcode/openfasttrace)).

**Core Value.** Part of the verdict moves from the model to code. For each requirement, the report lists:

- the tests that name it, and whether they ran and passed;
- any `met` verdict whose tests failed or were skipped, flagged;
- the requirements no test names, as "needs a person's check".

The strict-tier approver and the reviewer get proof that is not prose. The "the agent says the tests pass" failure is closed.

**Codebase Fit.**

- **Workspace.** After the run, `adk_spec/workspace/tests.py` reads a JUnit XML file whose path comes from the person's own command words, such as `--junitxml=PATH`. This avoids a new config key, which would make older versions refuse `config.toml`. The XML is parsed with external entities refused, and the output is scrubbed.
- **Domain.** A pure `adk_spec/domain/coverage.py` maps test cases to IDs, by the ID in the test name or by a `requirement` property. The results go into `reports/verify.md`, never into `change.json`.
- **A first level without JUnit.** `git grep` each requirement ID across tracked files (`adk_spec/workspace/git.py:212-221`) and list "no file outside .spec names REQ-X".
- **Orchestration.** The tasks stage is told to name each requirement ID in its test's name.
- **Init.** Where its reading quotes a test invocation, `init` prints it and, on a terminal, asks once whether to write it into `[verify] test`. The person's "yes" keeps them the author, as the phase-9 anti-goal requires.

**Impact vs. Effort.** High value for medium effort. The owner must first reverse phase 9's non-goal. The tasks-stage instruction change needs a live measurement of whether drafted tasks reliably name IDs. The `git grep` level can ship without one. JUnit dialects vary, so the parser should accept the common subset only.

### 7. Judge the work against the rules and the design's decisions

**Title & Type.** Rules and design decisions judged in verify. `Feature Upgrade` of `verify` and of the design stage.

**Evidence & Inspiration.** In the codebase, the verify stage's sections are the deltas, the tasks, the requirements, the diff and the tests, with no constitution (`adk_spec/orchestration/stages/verify.py:47-57`). The check stage already reads the constitution and has a `constitution` finding kind (`adk_spec/orchestration/stages/check.py:37-44`), and the labelled `constitution` case exists for `check` alone (`docs/measurements/README.md`). `design.md` records decisions, but nothing confirms that the code follows them. No module of the package names `AGENTS.md`, `CLAUDE.md` or `copilot-instructions.md`. This is the roadmap's second candidate, "measured first".

Competitors:

- Tessl's verifiers give each rule an `instruction`, a `relevant_when`, a scope, a `checklist`, and an error or warn level, judged per diff with stable IDs ([Tessl CI verify](https://docs.tessl.io/codifying-and-enforcing/verify-agent-changes-in-ci)).
- Spec Kit's analyze makes constitution conflicts "automatically CRITICAL" ([Spec Kit analyze](https://github.com/github/spec-kit/blob/main/templates/commands/analyze.md)).
- BMAD's Intent Alignment Auditor reads "the verbatim invocation intent alongside the diff" ([BMAD v6.11.0](https://github.com/bmad-code-org/BMAD-METHOD/releases/tag/v6.11.0)).

Adjacent tools and standards:

- Copilot code review reads `copilot-instructions.md` and `AGENTS.md` ([GitHub Copilot code review](https://docs.github.com/en/copilot/concepts/agents/code-review)).
- CodeRabbit "automatically detects and applies" `CLAUDE.md` and similar files ([CodeRabbit learnings](https://docs.coderabbit.ai/knowledge-base/learnings)).
- MADR's optional Confirmation section says how "compliance with the ADR can/will be confirmed" ([MADR](https://adr.github.io/madr/)).

**Core Value.** `verify` answers a reviewer's second question. It already asks whether the work does what the spec says. It would also ask whether the work does it the way this repository and this design said it would. Each rule break quotes an added diff line that code finds. Decisions in `design.md` gain a one-line Confirmation that `verify` judges like a requirement. Tech leads and strict-tier approvers benefit, and option 3's next-work list gains rule breaks as items.

**Codebase Fit.**

- **Orchestration.** A rules section in `stages/verify.py`, capped through `workspace/context.py`. The design stage asks for a Confirmation line for each decision.
- **Domain.** `VerdictsDraft` (`adk_spec/domain/drafts.py`) gains a list of rule breaks, each grounded by `lines_of_diff` as verdicts are (`adk_spec/domain/verify.py:37-65`).
- **Blocking.** A break blocks `verified` only where `DEMANDS.warnings_block` holds (strict), and is reported elsewhere. The rule is read from the table, not from a tier test. No `change.json` field is needed, because a blocked strict change simply stays `approved`.
- **Measurement.** `scripts/cases.py` gains a diff that breaks a rule.
- **Later.** Scoping each rule to globs, after Tessl's `relevant_when`. `init` could also cite rules from an existing `AGENTS.md` or `CLAUDE.md` when it drafts a constitution.

**Impact vs. Effort.** Medium-to-high value for medium effort. It adds up to 16,000 characters of constitution to every `verify` (`adk_spec/workspace/context.py:25`). It needs a live measurement before and after, as the roadmap says, because a longer prompt could degrade the requirement verdicts that the `half-done` case measures.

### 8. Return structured results to assistants, and reach more of them

**Title & Type.** Structured MCP results and a cross-client Skill. `Feature Upgrade` of `adk-spec-mcp` and `init`.

**Evidence & Inspiration.** In the codebase, the six MCP tools return printed text. Their `status` and `validate` tools never pass `--json` (`adk_spec/interfaces/mcp_server.py:189-202`). `propose`, `plan`, `check` and `verify` have no `--json` at all. The Skill is written only to `.claude/skills/adk-spec/SKILL.md` (`adk_spec/workspace/skill.py:17`).

Standards:

- MCP 2026-07-28 lets `outputSchema` use any JSON Schema 2020-12 keyword and `structuredContent` hold any JSON value. It deprecates Sampling, Roots and Logging ([MCP 2026-07-28 changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog)).
- Tools are the most widely supported MCP primitive. In the community client table they work in 28 of 39 clients, including every coding assistant listed; resources work in 11 and tasks in 2 ([mcp-client-capabilities](https://cdn.jsdelivr.net/npm/mcp-client-capabilities@0.0.14/README.md)).
- `.agents/skills/` "has emerged as a widely-adopted convention for cross-client skill sharing" ([Agent Skills client guide](https://agentskills.io/client-implementation/adding-skills-support)). Copilot reads `.github/skills`, `.claude/skills` and `.agents/skills` ([GitHub agent skills](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills)).
- Codex, Cursor, OpenCode, Gemini CLI and Antigravity scan `.agents/skills/`, while Claude Code does not (secondary source, [yage.ai](https://yage.ai/share/agent-skills-harness-portability-en-20260720.html)).
- `AGENTS.md` is used by more than 60,000 projects ([agents.md](https://agents.md/)).

Competitors: OpenSpec 2.0 moved its skills to `.agents/skills/` ([OpenSpec v2.0.0](https://github.com/Fission-AI/OpenSpec/releases/tag/v2.0.0)). Spec Kit's MCP server is still experimental and offers a read-only inventory ([Spec Kit MCP](https://github.com/github/spec-kit/blob/main/docs/overview/mcp.md)), so adk-spec's server is already ahead.

**Core Value.** An assistant acts on fields instead of parsing prose: verdicts per requirement, findings with a path and line, the next step, and the files written. The Skill also reaches Codex, Cursor, OpenCode and Gemini CLI users, which matters for a tool that ships a Gemini arm. Read-only resources let an assistant open a living spec or a report by URI. Every assistant-driven user benefits, and fewer misread outputs send an assistant to the wrong step.

**Codebase Fit.**

- **Interfaces.**
  - A `--json` flag on `check` and `verify`, and a compact result for `propose` and `plan`, built from the records the reports already use.
  - `mcp_server.py` runs each tool with `--json` and returns `structuredContent` under a declared `outputSchema`, keeping the text for older clients.
  - Read-only resources for living specs, change files and reports.
  - As now, no tool approves, archives, overrides or names another repository.
- **Workspace.** `skill.py` also writes `.agents/skills/adk-spec/SKILL.md`, never over an existing one. A three-to-five-line `AGENTS.md` pointer is printed as a suggestion rather than written into a file the person owns.

**Impact vs. Effort.** Medium value for small-to-medium effort, with no model and no measurement. Two things remain open: the Python MCP SDK's support for the 2026-07-28 revision, and whether Claude Code adopts `.agents/skills/`. Keep both copies until it does. MCP progress notifications stay deferred, as the owner decided.

## Sixteen ideas set aside, and why

The table records what was weighed and rejected or deferred. The common reasons are the golden rule, the compatibility rule, the no-network workspace, the rule that adk-spec never writes application code, hype, or features already at parity.

| Considered | Why it was set aside |
|---|---|
| Tier raised after the reading (roadmap's third candidate; BMAD 6.12 decides ceremony "after investigating it, not before", [BMAD v6.12.0](https://github.com/bmad-code-org/BMAD-METHOD/releases/tag/v6.12.0)) | Deferred, not rejected. No measurement shows how often triage under-sizes a request that the reading finds risky. Raising the tier mid-run changes the questions, the design and the approvers. Build it after a live measurement. |
| Bug-fix specs with current, expected and unchanged behaviour ([Kiro bugfix specs](https://kiro.dev/docs/specs/bugfix-specs/)) | A new delta heading makes every older adk-spec refuse the file under the strict grammar. `verify`'s rule that `met` needs an added line does not fit unchanged behaviour. The living spec already holds that behaviour, the regression proof arrives through option 6's tests, and a model's regression check over untouched requirements needs measuring first. |
| Remembered dismissals and learned suppression ([Greptile](https://www.greptile.com/docs/how-greptile-works/memory-and-learning), [CodeRabbit](https://docs.coderabbit.ai/knowledge-base/learnings)) | Nothing measures how often findings repeat. Keeping dismissals needs a `change.json` field or unreviewed lessons. Learning from reactions needs a pull-request surface the local tool lacks. |
| A second-opinion judge on the other provider arm (BMAD review layers, GSD lanes, Traycer debate) | It doubles the model calls on hard cases, and the only evidence of its yield is the vendors' own. Measure before building. |
| OpenSpec stores and worksets ([Stores](https://github.com/Fission-AI/OpenSpec/blob/main/docs-lab/multi-repo/stores.md)) | A new topology with new commands. `--with` already spans repositories, and worksets have terminal agents "temporarily disabled". |
| Spec Kit YAML workflows, extension hooks and catalogs ([Workflows](https://github.com/github/spec-kit/blob/main/docs/workflows/overview.md)) | An engine and an extension surface, against the golden rule; `approve` is already the gate. The catalog's maintainers "do not review, audit, endorse, or support the extension code". |
| Jira, Linear or GitHub Projects sync; hosted PR bots; Check Runs buttons | Network credentials the workspace layer may not import. Check runs require a GitHub App, and a bot means live model calls in CI. |
| Property-based test generation ([Kiro correctness](https://kiro.dev/docs/specs/correctness/)) | It writes test code, which adk-spec never does, and at Kiro it is IDE-only. Its traceable part is option 6. |
| Self-updating living specs (Augment Intent) | A marketing claim with no primary documentation that could be reached. It contradicts approval by fingerprint, and Spec Kit's documented rule refuses to let code replace intent ([Evolving specs](https://github.com/github/spec-kit/blob/main/docs/how-to/evolving-specs.md)). |
| An interactive UAT walkthrough (GSD) | A conversational step against one-pass flows. Option 6's "needs a person's check" list covers its cheap part. |
| EARS conformance and ISO/IEC/IEEE 29148 smell lints ([EARS](https://alistairmavin.com/ears/)) | Already near parity: `validate` flags a missing SHALL, a scenario without WHEN/THEN, and a statement over 500 characters, which is OpenSpec's limit. Smell detection reached 59% precision in the best-known study ([arXiv:1611.08847](https://arxiv.org/abs/1611.08847)), so more of it would be noise. |
| ReqIF export, dashboards and static sites, a `needs.json`-style export | ReqIF exchange is fragile across vendors, and the matching OMG issue is still open ([REQIF13-8](https://issues.omg.org/issues/REQIF13-8)). `status` is already the dashboard. A JSON export waits until someone asks for one. |
| OpenTelemetry GenAI traces; a persisted token ledger | The conventions are still at "Development" status and broke names on 21 November 2026 ([semconv-genai CHANGELOG](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/CHANGELOG.md)). Per-change totals would need a `change.json` field. |
| An in-toto approval attestation ([SLSA v1.2](https://slsa.dev/spec/v1.2/source-requirements), [actions/attest](https://github.com/actions/attest)) | Cheap to write unsigned, but signing belongs in CI and no regulated user has asked for it. It could follow option 4 as a documented recipe. |
| MADR decision records archived under `docs/decisions` ([MADR](https://adr.github.io/madr/)) | Writing outside `.spec/` is a product decision the owner has deferred. MADR's checkable part, Confirmation, is in option 7. |
| Reviewer personas and multi-agent "crews" | BMAD's own A/B test found that the persona "made no difference to residual-bug hit rate" ([BMAD v6.11.0](https://github.com/bmad-code-org/BMAD-METHOD/releases/tag/v6.11.0)). |

## What a measurement or the owner must settle

Most open questions are design calls the owner can make in an afternoon. Three need data. The suspect signal's noise rate decides whether option 1 can fail CI. The tasks-stage measurement decides whether option 6 goes beyond a `git grep` count. The verify measurement decides whether option 7's rules help or crowd out the requirement verdicts.

| Question | Settled by | Options |
|---|---|---|
| How often does a verified quote survive later reformatting, renames and refactors? Should `spec.evidence-gone` fail `--strict`? | An offline replay over a repository's history, with no model; then the owner | 1, 4 |
| Does kept evidence live in a sidecar beside `spec.md` (compatible with older versions) or in the archived change? | The owner | 1, 5 |
| Does remediation stay outside `tasks.md`, leaving the approval untouched, or go into an appended Convergence section that the fingerprint ignores? | The owner | 3 |
| A shallow CI clone reads as drifted, because `_drifted` returns true on a `GitError` (`adk_spec/interfaces/cli.py:488-491`). Does SARIF upload work on private repositories without GitHub Advanced Security? | A code decision, and a check of GitHub's plans | 4 |
| Does `archive` run on the feature branch or on `main`, which decides where summaries and changelog entries land? How do two approvers and several open changes coordinate through git, which no document describes? | The owner | 2, 4, 5 |
| Should phase 9's non-goal of mapping tests to requirement IDs be reversed? Do drafted tasks reliably put the IDs in test names? | The owner; a live measurement | 6 |
| Does a rules section in `verify` degrade the requirement verdicts, and what does it cost per run? | A live measurement on `scripts/cases.py`, with a new rule-breaking case | 7 |
| How often does triage under-size a request that the reading shows to be risky? | A live measurement | Tier raise (deferred) |
| Does the Python MCP SDK support MCP 2026-07-28, and will Claude Code read `.agents/skills/`? | An upstream check | 8 |

## Conclusion

Spec-driven tools are converging on evidence, and that changes where adk-spec's lead can grow. Its lead is not more model judgement. It is the only tool found whose evidence is checked in code. Today that evidence lives for one command run. The options here make it outlast the change that produced it: it becomes a requirement-to-code link that can go stale visibly, a pull-request body, a CI annotation, and a list of the next work. That is a new category for a local spec tool: a living spec that warns when its own proof decays, which neither the requirements-management incumbents nor the AI-era spec tools offer.

The order of building matters as much as the ranking. Options 2 and 3 are self-contained and can ship first. Option 1's evidence store is the substrate that turns options 4, 5 and 6 largely into renderers, so it should precede them. Options 6 and 7 wait on measurements. One finding cuts across all eight. The project's hardest constraint turned out to be compatibility, not architecture: `change.json` and `config.toml` both refuse what they do not know, so every compatible design had to hide in unfingerprinted reports or in sidecar files. That pattern is worth adopting deliberately, as a stated rule for additive files, before the next feature has to rediscover it.
