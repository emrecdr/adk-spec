# adk-spec internal system map: underused data, manual friction and unfinished journeys

Scope: the adk-spec repository at branch `audit4` (HEAD 7320972), read only. Sources are the repository's own files,
cited as `path:line` relative to the repository root. No command that calls a model was run. Bug fixes, edge-case
guards, refactors and cosmetics are left out on purpose: every opportunity below is feature-level.

Constraints every opportunity must meet, from the project's own rules:

- No new subcommand; a capability goes inside an existing command; a command prints what it wrote, what needs the
  person, and the next command, and detail goes in files — [docs/superpowers/plans/README.md:5-14](docs/superpowers/plans/README.md#L5)
- Four layers (`domain` → `workspace` → `orchestration` → `interfaces`); `domain` does no I/O, `workspace` imports no
  network module, only `workspace/process.py` starts a program — [CLAUDE.md](CLAUDE.md) ("Architecture")
- A new field in `change.json` makes every older adk-spec refuse the file; the owner has rejected a feature on that
  ground before ("The tier recorded in an approval ... a new field makes every older adk-spec refuse the file") —
  [docs/superpowers/plans/README.md:423-424](docs/superpowers/plans/README.md#L423). The `model_blocking` field was
  added with a serializer that omits it when empty, so older versions still read most files —
  [adk_spec/domain/model.py:153-173](adk_spec/domain/model.py#L153)
- "No command from a change's files, a model's answer or a task's `verify:` line is run" (an anti-goal of phase 9) —
  [docs/superpowers/specs/2026-11-22-verify-tests-design.md:36-41](docs/superpowers/specs/2026-11-22-verify-tests-design.md#L36)

---

## 1. What are the tool's entry points, core workflows, data models and integrations?

### Takeaway
adk-spec is one argparse CLI with 13 subcommands (`cli.py`, 2,229 lines), a six-tool MCP server that runs the same
CLI in a subprocess, an Agent Skill file `init` writes, and an ADK web "watch" app. Four model-backed workflows
(propose, plan, check, verify) plus a code-reading sub-workflow (scout → survey → review). Everything is persisted as
Markdown under `.spec/` plus one `change.json` per change; reports and run recordings are write-only by design.

### Cited Findings

**Entry points**
- CLI subcommands: `init`, `new`, `validate`, `status`, `rebase`, `approve`, `archive`, `propose`, `plan`, `check`,
  `verify`, `smoke`, `models`, `login`, wired in `_parser()` — [adk_spec/interfaces/cli.py:177-276](adk_spec/interfaces/cli.py#L177).
  Exit codes: 0 done, 1 findings/refused, 2 usage, 3 engine, 130 interrupted — [cli.py:115-122](adk_spec/interfaces/cli.py#L115)
- The engine is never imported at module top: offline commands start without ADK — [cli.py:1-6](adk_spec/interfaces/cli.py#L1)
- `adk-spec-mcp`: six tools (`propose`, `plan`, `check`, `verify`, `status`, `validate`); each runs
  `python -P -m adk_spec` in its own process and returns the printed text; no tool approves, archives, overrides or
  names another repository — [adk_spec/interfaces/mcp_server.py:1-17, 133-204](adk_spec/interfaces/mcp_server.py#L133).
  The `status` and `validate` tools never pass `--json`, so the assistant receives human text — [mcp_server.py:189-202](adk_spec/interfaces/mcp_server.py#L189)
- Agent Skill `.claude/skills/adk-spec/SKILL.md`, written once by `init`, never over an existing one; it tells the
  assistant which commands it may run and to implement `tasks.md` ticking boxes — [adk_spec/workspace/skill.py:19-75](adk_spec/workspace/skill.py#L19)
- `adk_spec/agent.py` is the shape `adk web` loads, for watching a propose; writes nothing — [README.md:796-804](README.md#L796)

**Core workflows (who calls a model)**
- `propose`: triage (tier + capabilities, skipped with `--tier`) → code reading (scout/survey/review, up to 7 calls,
  held to half the remaining token ceiling) → brief + deltas, with up to 3 question rounds of 3 questions → design
  (where owed) → tasks; a strict change stops after brief + specs — [cli.py:967-985, 1773-1833, 1998-2082](adk_spec/interfaces/cli.py#L1998);
  [adk_spec/orchestration/plugins.py:119-132](adk_spec/orchestration/plugins.py#L119)
- `propose "<instruction>" --id <id>` revises an open change, keeping tier, IDs by name, `context.md` — [README.md:444-461](README.md#L444)
- `approve`: records bases where missing (`_based`), makes the check where none is current (model call), refuses on
  blockers, records approval with file fingerprints, base commit(s), names drafted files a person edited —
  [cli.py:689-735](adk_spec/interfaces/cli.py#L689)
- `check`: code findings + model findings, each model finding kept only where its quote is found — [cli.py:1435-1531](adk_spec/interfaces/cli.py#L1435)
- `verify`: runs the person's test command(s) in each repository, diffs the work since the approval's base commit(s),
  asks the model for one verdict per requirement, keeps a `met` only where a quoted line is in the diff —
  [cli.py:1581-1731](adk_spec/interfaces/cli.py#L1581); [adk_spec/domain/verify.py:101-133](adk_spec/domain/verify.py#L101)
- `archive`: merges deltas into living specs, all or none; refuses on a moved base (`delta.base-stale`) —
  [cli.py:795-826](adk_spec/interfaces/cli.py#L795); [adk_spec/domain/merge.py:31-51](adk_spec/domain/merge.py#L31)
- `init`: makes `.spec/`, writes the skill, reads the code (up to 7 calls) into `profile.md`, drafts rules into the
  constitution only while it is still the template — [cli.py:317-401](adk_spec/interfaces/cli.py#L317)

**Data models** ([adk_spec/domain/model.py](adk_spec/domain/model.py))
- `Spec` (capability, purpose, requirements, `retired` with the removing change's id) — [model.py:46-60](adk_spec/domain/model.py#L46)
- `Delta` (added / modified / removed) — [model.py:69-77](adk_spec/domain/model.py#L69)
- `Task` (id, done, parallel `[P]`, requirement IDs, description, `files`, `verify`) — [model.py:80-88](adk_spec/domain/model.py#L80)
- `Statement` (kind exists/touches/convention/risk, path, line, quote, note, `within`) — [model.py:106-121](adk_spec/domain/model.py#L106)
- `Approval` (by, at, file fingerprints, bases, override reason, `second` approver) — [model.py:139-150](adk_spec/domain/model.py#L139)
- `Checked` (at, files, blocking, model, model_blocking) — [model.py:153-173](adk_spec/domain/model.py#L153)
- `Verification` (at, base, diff fingerprint, verdicts `dict[str,str]`, override, model, other repos' bases, test
  outcomes) — [model.py:180-198](adk_spec/domain/model.py#L180)
- `ChangeState` (id, tier, status draft/approved/verified/archived, bases, approval, needs_design, check,
  verification, base_commit, repositories, base_commits, drafted fingerprints). No archived timestamp field —
  [model.py:201-229](adk_spec/domain/model.py#L201)
- The tier table `DEMANDS` (asks, checked, verified, design, read_first, approvers, warnings_block, override) —
  [adk_spec/domain/lifecycle.py:68-92](adk_spec/domain/lifecycle.py#L68); next step logic `next_step` —
  [lifecycle.py:448-482](adk_spec/domain/lifecycle.py#L448)

**Files on disk**
- `.spec/`: `config.toml`, `constitution.md`, `profile.md`, `lessons.md`, `specs/<cap>/spec.md`,
  `changes/<id>/{brief.md, specs/, design.md, tasks.md, context.md, reports/, change.json}`, `runs/` (git-ignored) —
  [CLAUDE.md](CLAUDE.md); [adk_spec/workspace/layout.py:40-52](adk_spec/workspace/layout.py#L40)
- Archived changes stay in `.spec/changes/<id>/` with `status: archived`; `archive` writes only the merged specs and the
  state — [cli.py:824](adk_spec/interfaces/cli.py#L824); [layout.py:189-197](adk_spec/workspace/layout.py#L189)
- Reports are "written whole each time, for a person to read, and never parsed back" — [adk_spec/domain/report_md.py:1-5](adk_spec/domain/report_md.py#L1)

**Integrations**
- Two model arms (GitHub Copilot through LiteLLM, Gemini) — [CLAUDE.md](CLAUDE.md)
- git (list, grep, diff, head, resolve) — [adk_spec/workspace/git.py:156-255](adk_spec/workspace/git.py#L156)
- Other repositories via `--with`, read through their own git list and exclusions, tests from their own config —
  [adk_spec/workspace/source.py:359-450](adk_spec/workspace/source.py#L359); [README.md:757-772](README.md#L757)
- Installed libraries read offline as `python:`/`node:` paths from `.venv`/`venv`/`node_modules` —
  [adk_spec/workspace/installed.py:24-28, 47-61](adk_spec/workspace/installed.py#L47)
- The project's own test command, run with no shell — [cli.py:1686-1702](adk_spec/interfaces/cli.py#L1686)
- CI: only `adk-spec validate --strict` is documented — [README.md:536-543](README.md#L536)
- No integration with GitHub pull requests, issue trackers, release tooling or a CI action for user repositories was
  found in the code (no `gh` call; `workspace` may import no network module).

### Inferences
- The tool is rich in recorded, quote-grounded data but its outputs end at Markdown reports and one-line `next`
  hints; almost nothing it records is read back by a later command except `change.json` fields used for gating.
- The MCP server and the Skill both hand an assistant prose; a structured (`--json`) path exists for `status` and
  `validate` only, and the MCP tools do not use it.

### Gaps
- `agent.py` and `graph.py` internals were skimmed, not read line by line; nothing in them suggested further data
  stores.

---

## 2. What data does the tool already hold that no command uses well?

### Takeaway
Seven stores are computed with care and then dropped or never read back: verify evidence per requirement, the task
list's `files`/`verify`/`[P]` metadata, verification verdicts after an `unmet`, `context.md` and `profile.md`
statements with their quotes and commits, lesson counts, run recordings and token ledgers, and the history held by
archived changes. The largest unclaimed value is a requirement-to-code map with a code-only drift signal, built
from evidence `verify` already grounds.

### Cited Findings

**(a) Verify evidence: computed, grounded, then thrown away**
- `grounded()` returns, per requirement, `evidence: tuple[(path, quote)]`, each quote proved present in the diff —
  [adk_spec/domain/verify.py:23-30, 101-133](adk_spec/domain/verify.py#L101)
- The `Verification` record keeps only `verdicts: dict[str, str]` (ID → met/unmet/unclear), not the evidence or the
  reason — [model.py:180-193](adk_spec/domain/model.py#L180); written at [cli.py:1639-1655](adk_spec/interfaces/cli.py#L1639)
- Evidence and reasons go only into `reports/verify.md` — [report_md.py:61-94](adk_spec/domain/report_md.py#L61) — which
  is never parsed back — [report_md.py:1-5](adk_spec/domain/report_md.py#L1)
- `archive` folds requirements into the living spec with no provenance and no evidence; only removals keep the change
  id (`Retired`) — [merge.py:36-48](adk_spec/domain/merge.py#L36)
- The owner's own original design wanted test-to-requirement binding (`@pytest.mark.spec("<capability>:<REQ-ID>")`) —
  [docs/reports/02-adk-spec-framework-architecture-and-roadmap.md:47](docs/reports/02-adk-spec-framework-architecture-and-roadmap.md#L47)
- The project's prior research concluded both parent tools "fail at the same point, the hand-back after
  implementation ... A hybrid needs the fold-back to be automatic or checked, plus a visible drift signal", and cites
  drift detection "treated as 'information, not a gate'" — [docs/research_notes/Spec driven framework on Google ADK/sdd_comparison_and_critique.md:90, 166](docs/research_notes/Spec%20driven%20framework%20on%20Google%20ADK/sdd_comparison_and_critique.md#L90)

**(b) Task metadata written, validated, never used**
- Grammar: `- [ ] T001 [P] [REQ-...] description`, with optional `files:` and `verify:` lines —
  [adk_spec/domain/tasks_md.py:1-6](adk_spec/domain/tasks_md.py#L1)
- The validator warns when a task has no `verify:` line — [adk_spec/domain/validate.py:270-274](adk_spec/domain/validate.py#L270)
- A repository-wide search finds `task.files`, `task.verify` and `task.parallel` read only by the converter and the
  renderer (convert.py:205-209, tasks_md.py:81-88) and the validator (validate.py:273): no command checks a task's
  files against the diff or runs its `verify` line (search run on the branch).
- Ticked boxes are used only to decide whether `plan` may redraft (`started`) — [cli.py:450-456](adk_spec/interfaces/cli.py#L450);
  [lifecycle.py:381-385](adk_spec/domain/lifecycle.py#L381). The verify stage is told "Judge what the diff shows, not
  which boxes of the tasks are ticked" — [adk_spec/orchestration/stages/verify.py:35](adk_spec/orchestration/stages/verify.py#L35)

**(c) Verdicts after an `unmet` do not steer the next step**
- After a verification that is not all `met` the change stays `approved` — [lifecycle.py:233-251](adk_spec/domain/lifecycle.py#L233)
- `_after_approval` reads only `tests_passed` from the verification; with tests passing it says the generic
  "implement tasks.md, then run `adk-spec verify <id>`" whatever the verdicts were — [lifecycle.py:422-445](adk_spec/domain/lifecycle.py#L422)
- The README's troubleshooting for `unmet`/`unclear` is "Implement what is missing ... and verify again" —
  [README.md:571](README.md#L571)

**(d) `context.md` and `profile.md`: quote-checked statements, never re-checked**
- Each statement keeps path, line, quote and the opening line of its block — [model.py:111-121](adk_spec/domain/model.py#L111);
  the file records when and at what commit each repository was read — [adk_spec/domain/context_md.py:42-91](adk_spec/domain/context_md.py#L42);
  the same renderer writes `profile.md` with the current commit — [cli.py:1361-1384](adk_spec/interfaces/cli.py#L1361)
- `context_md.py` offers `render_context`, `unknown_count` and `drafted_rules`; there is no parser that reads the
  statements back — [context_md.py:42-134](adk_spec/domain/context_md.py#L42)
- `context.md` is "no part of an approval" and is kept and read as it stands; to refresh it a person deletes it —
  [README.md:735-738](README.md#L735); `profile.md` is refreshed only by `init --refresh` —
  [cli.py:324-338](adk_spec/interfaces/cli.py#L324)
- The constitution receives drafted rules only while it is exactly the template, so `convention` statements found by
  every later reading never reach it — [layout.py:309-315](adk_spec/workspace/layout.py#L309); [cli.py:396-401](adk_spec/interfaces/cli.py#L396)

**(e) Lesson counts and check findings**
- adk-spec appends `- <stage>, \`<code>\` (<count>): <example>` under "Sent back by a gate" and increments the count
  each run the fault recurs — [adk_spec/domain/lessons_md.py:33, 42-56, 74-91](adk_spec/domain/lessons_md.py#L42)
- The count is stripped before a stage reads the file — [lessons_md.py:59-71](adk_spec/domain/lessons_md.py#L59) — and
  no command prints it
- Live measurement: "a lesson written by code after a real send-back, and counted when the fault came back, the lesson
  in the prompt not having prevented it" — [docs/superpowers/plans/README.md:321-323](docs/superpowers/plans/README.md#L321)
- Only drafting gates' send-backs become lessons ([CLAUDE.md](CLAUDE.md)); a blocking check finding that a person then
  fixed by editing is recorded only as a count in `Checked.blocking` and in `reports/check.md` —
  [lifecycle.py:194-211](adk_spec/domain/lifecycle.py#L194)

**(f) Run recordings and the token ledger**
- A recording keeps each call's stage, full instruction, the gate's send-back, the answer, tokens and seconds, and the
  pass's outcome — [adk_spec/workspace/runs.py:27-56](adk_spec/workspace/runs.py#L27); written for every model command —
  [cli.py:935-956](adk_spec/interfaces/cli.py#L935)
- Recordings are pruned to `[limits] keep_runs` (default 20) and git-ignored — [runs.py:69-83](adk_spec/workspace/runs.py#L69);
  [README.md:615](README.md#L615)
- The only reader of recordings is `scripts/measure.py` (`from adk_spec.workspace.runs import listed, read`); within
  the package `listed` is used only to prune — search on the branch; [scripts/measure.py](scripts/measure.py)
- The ledger counts calls and prompt/output/total tokens per stage — [adk_spec/orchestration/plugins.py:97-148](adk_spec/orchestration/plugins.py#L97);
  [adk_spec/orchestration/run.py:32-49](adk_spec/orchestration/run.py#L32) — and is printed once as a `tokens` line,
  then lost — [cli.py:959-964](adk_spec/interfaces/cli.py#L959)
- Live runs show the spread: one `propose` from 9,631 tokens / 15 s to 23,149 tokens / 321 s —
  [docs/measurements/2026-11-23-phase-15-live.md:51-52, 94-95](docs/measurements/2026-11-23-phase-15-live.md#L51)

**(g) Approvals, overrides and the history of archived changes**
- Each change records approver(s), times, any override reason for a check, any override reason for a verification,
  each repository's test outcome — [model.py:139-198](adk_spec/domain/model.py#L139)
- `status` rows carry only id, tier, status, actor and next phrase, also in `--json` — [cli.py:570-596](adk_spec/interfaces/cli.py#L570)
- Archived changes keep their brief, deltas, tasks, reports and `change.json`, so each requirement's ADDED / MODIFIED /
  REMOVED history across changes is on disk, but no command reads archived deltas: `taken()` skips archived changes
  ("history grows, and is not read") — [layout.py:231-245](adk_spec/workspace/layout.py#L231); `validate` skips them —
  [cli.py:553](adk_spec/interfaces/cli.py#L553)
- The person's answers to the brief's questions are folded into the brief draft — [cli.py:869-893, 2056-2082](adk_spec/interfaces/cli.py#L869) —
  and survive verbatim only inside git-ignored, pruned recordings. "A glossary and decision records under `.spec/`" was
  left for the owner to choose later — [docs/superpowers/specs/2026-11-23-research-during-planning-design.md:67-70](docs/superpowers/specs/2026-11-23-research-during-planning-design.md#L67)
- Triage's tier reason is printed (`sized standard: ...`) and not stored — [cli.py:2027-2030](adk_spec/interfaces/cli.py#L2027)

### Inferences
Opportunities, ranked by value against cost (my judgement), each with its fit:

1. **Requirement-to-code map, kept at archive, with a code-only drift signal (high value, medium cost).** Persist each
   `met` verdict's `(path, quote)` evidence when a change is verified (from `grounded()`, verify.py:101-133) and carry
   it into the record at `archive` (cli.py:795-826). Later, re-check each quote in the current file with the same
   `quoted_at` test the package already uses (domain/text.py) and report "REQ-AUTH-004: its evidence in
   src/auth/passkey.py is gone" as information, not a gate. Host commands: `status` (a group or one line) and
   `validate` (a WARNING code, so `--strict` can fail CI). No model. Design questions: where to store it without
   breaking older readers (a new file such as `reports/evidence.json` that no approval fingerprints, or a field
   omitted when empty as `model_blocking` is); whether the living spec grammar (`## Purpose`, `## Requirements`,
   `## Retired` only — domain/spec_md.py:3-7, 18) gains a section or the map lives beside it; scrubbing quotes before
   writing (secrets.scrub). This is the "checked reconciliation step ... plus a visible drift signal" the prior
   research named.
2. **Verify cross-checks the task list against the diff (high value, small cost, code only).** In `_verified`
   (cli.py:1613-1662) and `render_verify` (report_md.py:61-94): a ticked task whose `files:` none changed; files in
   the diff no task names; an `unmet`/`unclear` requirement whose tasks are all ticked (the clearest "agent ignored
   the spec" signal). Requirement-to-task links already exist in `Task.requirements`. Reports are not fingerprinted,
   so approvals are untouched.
3. **The next line names what is unmet (high value, small cost).** Extend `_after_approval` (lifecycle.py:422-445) to
   read `state.verification.verdicts`: "REQ-AUTH-005 unmet, REQ-AUTH-006 unclear: reports/verify.md says what is
   missing; then run `adk-spec verify <id>`". `status` and the MCP/Skill flow get it for free since both follow the
   step `status` names (skill.py:63-64).
4. **Context and profile freshness (medium value, small cost).** A parser for the statement lines `render_context`
   writes, then a quote re-check at `approve` (for `context.md`) and at `propose` start (for `profile.md`): "context.md:
   3 of 14 statements no longer hold; delete it and `plan` reads again" / "profile: 5 of 30 no longer hold; `init
   --refresh` reads again". At `verify`, `touches` statements whose files the diff never changed are a second scope
   check. No model.
5. **Constitution candidates from readings (medium value, small cost).** `convention` statements from each change's
   `context.md` that recur across changes are rule candidates; today rules are drafted only into a template
   constitution (layout.py:309-315). A non-invasive form: `init --refresh` lists candidate rules in its output or a
   report instead of writing into a constitution the person owns.
6. **Lessons that do not work, surfaced (medium value for tuning, small cost).** A lesson whose count keeps rising is
   evidence the prompt line is not preventing the fault (plans/README.md:321-323). Surface the top counts in one
   `validate` INFO line, or in the `lessons` line `approve` already prints. A blocking check finding a person fixed is
   also a correction and could be offered as a lesson line.
7. **Per-change cost and audit view (low to medium value).** Persisted call/token totals per change (from the ledger)
   and an audit list across changes (overrides, overridden failing tests, two-name approvals) in `status --all --json`.
   Recordings are pruned at 20 and local, so totals would have to be written into the change, with the
   `change.json` compatibility cost above.

### Gaps
- No measurement exists of how often verify evidence survives later commits, so the drift signal's noise rate is
  unknown; the quote test (`quoted_at`) tolerates whitespace in some way not examined here.
- Whether the owner wants anything stored beyond `change.json` and Markdown (e.g. a JSON sidecar) is an open design
  decision; no precedent file under `reports/` is JSON today.

---

## 3. Where does a person do manual work the tool could take over in one pass?

### Takeaway
Most remaining hand-work sits at the edges of the four-command flow: writing the test command, writing lessons after
`approve` names an edited draft, resolving a moved base by reading and rebasing, wiring CI, and moving the finished
change into a commit or pull request. Each can be absorbed by an existing command without a new subcommand; one
(the test command) must keep the person as the author because of the phase-9 anti-goal.

### Cited Findings
- **Test command by hand.** `verify` runs nothing until a person writes `[verify] test` in `.spec/config.toml`, and
  then prints `tests none named ...: set [verify] test in .spec/config.toml` — [adk_spec/workspace/config.py:20-22, 40-43](adk_spec/workspace/config.py#L20);
  [cli.py:1691-1694](adk_spec/interfaces/cli.py#L1691). Meanwhile `init`'s reading was designed to describe "how the
  project is built and tested" — [docs/superpowers/plans/README.md:207-208](docs/superpowers/plans/README.md#L207) — and
  the profile has a "How this repository does things" section — [context_md.py:23-28](adk_spec/domain/context_md.py#L23).
  Constraint: only a command the person wrote is run — [verify-tests-design.md:5-8, 36-41](docs/superpowers/specs/2026-11-22-verify-tests-design.md#L5)
- **Lessons by hand.** `approve` prints `lessons <files> edited since drafted: say what you corrected in one line in
  .spec/lessons.md` — [cli.py:726-733](adk_spec/interfaces/cli.py#L726). It knows only that the fingerprint changed;
  `drafted` stores fingerprints, not text — [model.py:227-229](adk_spec/domain/model.py#L227); [lifecycle.py:130-133](adk_spec/domain/lifecycle.py#L130)
- **Moved base by hand.** When another change archived first, `archive` stops with `delta.base-stale`; the person
  reads the current requirement, updates the delta, runs `rebase`, and approves again — [cli.py:814-823](adk_spec/interfaces/cli.py#L814);
  [README.md:573](README.md#L573). Bases are fingerprints only — [lifecycle.py:27-36](adk_spec/domain/lifecycle.py#L27) —
  but the change records the commit where its work began (`base_commit`) — [model.py:217-220](adk_spec/domain/model.py#L217)
- **Commit/PR by hand.** The flow ends with "Commit the change with the code it describes" — [README.md:379](README.md#L379)
- **Implementation prompt by hand.** The README gives a prompt to paste into the assistant — [README.md:344-347, 519](README.md#L344);
  the Skill covers this for assistants that load it — [skill.py:56-64](adk_spec/workspace/skill.py#L56)
- **CI by hand.** A person writes a CI job around `validate --strict` — [README.md:536-543](README.md#L536)
- **Second approver by hand.** A strict change needs two names, each recorded by running `approve` locally; the name
  "is a recorded claim, not an authentication" — [model.py:139-150](adk_spec/domain/model.py#L139); [README.md:433-436](README.md#L433)
- **Decided, not friction to re-open:** repositories are named with each change, not in config —
  [docs/superpowers/plans/README.md:188-190](docs/superpowers/plans/README.md#L188); a late-failing `propose` keeps
  nothing, deferred twice by the owner — [plans/README.md:412-415](docs/superpowers/plans/README.md#L412)

### Inferences
1. **`init` offers the test command it found, for the person to accept (small cost).** Where the reading quotes a test
   invocation (a `Makefile`, `pyproject.toml`, `package.json` script, CI file), `init` prints it as a suggestion and,
   on a terminal, asks once whether to write it into `[verify] test`; the person's "yes" keeps them the author, so the
   anti-goal holds. With `--no-input`/MCP it only prints the suggestion. Fit: `_init`/`_described` (cli.py:317-393),
   `workspace.config`. No extra model call if the reading already holds the statement.
2. **`approve` takes the lesson in the same pass (small cost).** On a terminal, after naming the edited drafts, ask
   one optional line ("what did you correct? empty skips") and append it under "From people" via `Workspace`'s
   lessons writer (layout.py:301-307 shows the write path for gate lessons). Optionally keep the drafted text (not
   only its fingerprint) under `reports/` so `approve` can show which lines changed; this needs no new `change.json`
   field. Golden-rule fit: approve is already the decision point.
3. **A moved base explained in place (medium cost).** When `archive` stops on `delta.base-stale`, show the old and new
   text of the requirement (living spec now vs. the spec at `base_commit`, read with `git show` through
   workspace/git.py) instead of asking the person to find it; or let `propose "<instruction>" --id <id>` re-draft the
   delta against the new living text, since revision already keeps IDs by name (README.md:444-461).
4. **CI wiring:** see the roadmap item in section 5; a documented copy-paste workflow plus `validate` codes would
   remove most hand-work without a new command.

### Gaps
- Whether `init`'s reading reliably states a test command was not measured; the live `profile` case checks error
  classes and test placement, not the test command — [docs/measurements/README.md:18](docs/measurements/README.md#L18).

---

## 4. Which end-to-end journeys stop short?

### Takeaway
The change lifecycle is complete inside `.spec/`, but every journey that leaves it stops: nothing turns a verified
change into a PR description, archived changes into release notes, an `unmet` verdict into the next fix, a living
requirement back into the code that implements it, overlapping open changes into an early warning, or one repository's
archive into the other repositories' record. Each can be closed in code alone, mostly inside `verify`, `archive`,
`status` and `validate`.

### Cited Findings
- **Verified → pull request.** `verify` writes `reports/verify.md` and the next line says `run adk-spec archive`;
  nothing assembles a PR body — [cli.py:1652-1662](adk_spec/interfaces/cli.py#L1652). The data a PR body needs is
  all present: brief title/why/what (`Brief`, model.py:96-103), requirement IDs, verdicts and evidence (section 2a),
  test outcomes (model.py:192-198), approvers and overrides (model.py:139-150).
- **Archived → release notes/changelog.** `archive` prints one line `archived <id>: folded into <caps>` —
  [cli.py:825](adk_spec/interfaces/cli.py#L825); no archived timestamp is recorded (model.py:201-229); `status --all
  --json` rows lack title, date and requirement IDs (cli.py:583).
- **Failing verify → next fix.** See section 2c. Also: an approved change's tasks cannot be redrafted by `plan` ("plan
  drafts no task for an approved change, whose new tasks you write in tasks.md or revise with propose --id") and any
  edit to `tasks.md` other than ticking voids the approval — [README.md:456-460](README.md#L456); [lifecycle.py:1-7, 53-65](adk_spec/domain/lifecycle.py#L1).
  The owner's original design had an `apply ↔ converge` loop that appended convergence tasks —
  [docs/reports/02-adk-spec-framework-architecture-and-roadmap.md:56-59](docs/reports/02-adk-spec-framework-architecture-and-roadmap.md#L56)
- **Living spec → code.** No map; evidence is dropped at archive (section 2a). Phase 9 was listed on the roadmap as
  mapping "results to requirement IDs" so a person could "see which requirements no test covers" —
  [docs/superpowers/plans/README.md:246-250](docs/superpowers/plans/README.md#L246) — but its design made "Mapping each
  test to a requirement ID" a non-goal — [verify-tests-design.md:31-34](docs/superpowers/specs/2026-11-22-verify-tests-design.md#L31).
  `git grep` is already wrapped — [git.py:212-221](adk_spec/workspace/git.py#L212)
- **After archive.** Nothing re-checks a living spec against later code; requirements are re-judged only inside a
  new change's `verify`.
- **Several open changes (team).** Requirement IDs are never handed out twice across open changes —
  [layout.py:231-236](adk_spec/workspace/layout.py#L231) — but two open changes that MODIFY or REMOVE the same
  requirement are found only when the second archives, as `delta.base-stale` — [merge.py:34-35](adk_spec/domain/merge.py#L34);
  [validate.py:24-75](adk_spec/domain/validate.py#L24) (the SEVERITY table of codes) lists no cross-change code. The project's research names
  OpenSpec's "parallel-change overwrite on archive" as a failure "delta-merge designs must handle (conflict detection
  at requirement level)" — [sdd_comparison_and_critique.md:92](docs/research_notes/Spec%20driven%20framework%20on%20Google%20ADK/sdd_comparison_and_critique.md#L92)
- **Across repositories.** `--with` repositories are read, approved (base commits) and verified (diff and tests) —
  [README.md:757-772](README.md#L757) — but the archive writes living specs only into the workspace that holds
  `.spec/` (cli.py:824); another repository that is itself an adk-spec project gets no record. A repository missing
  on a teammate's machine makes `verify` refuse ("the work cannot be judged on part of it") — [cli.py:1562-1578](adk_spec/interfaces/cli.py#L1562)
- **A bug path.** Tasks for a bug fix start with a failing test — [plans/README.md:352-354](docs/superpowers/plans/README.md#L352) —
  but there is no "unchanged behaviour" requirement shape; the project's research cites Kiro's Bugfix Spec with
  Current / Expected / Unchanged Behavior sections — [sdd_comparison_and_critique.md:162, 182-183](docs/research_notes/Spec%20driven%20framework%20on%20Google%20ADK/sdd_comparison_and_critique.md#L162)

### Inferences
1. **PR-ready summary when verified (medium-high value, small cost, code only).** When `verify` leaves the change
   `verified`, also write `reports/summary.md`: title, why, requirement IDs with verdict and one evidence line each,
   test outcomes, approvers, any override with its reason, other repositories and their base commits. Print one
   `wrote` line. No `gh` call is needed (and `workspace` may not import network code); the person or assistant pastes
   it. Optionally the Skill tells the assistant to use it as the PR body.
2. **Changelog at archive (medium value, small cost).** `archive` appends one entry per change to a file such as
   `.spec/changelog.md` (date, title, IDs added/modified/removed), written in the same `write_all` set as the specs
   (layout.py:189-197), which also gives the missing archive date without a `change.json` field.
3. **Requirement coverage by name (medium value, small cost).** At `verify`, `git grep` each requirement ID in tracked
   files (git.py:215-221) and list "REQ-AUTH-005: no file outside .spec names it"; the tasks stage could be told to
   name the ID in each test's name or docstring, closing phase 9's dropped promise without a pytest plugin.
4. **Overlap warning across open changes (medium-high value for teams, small cost).** In `status`, `approve` and
   `propose`, list requirements that another open change also MODIFIES or REMOVES, by reading the other changes'
   deltas (the `taken()` loop in layout.py:231-250 already walks them). Warn early; keep `archive`'s refusal as the
   guard.
5. **Living spec drift after archive:** the evidence map in section 2 inference 1.
6. **Across repositories:** at archive, name the other repositories and the requirements their code met (from the
   evidence paths' repository prefix), so a person can record them there; a full cross-repository archive needs the
   owner's decision on where the record lives.

### Gaps
- No team workflow (several people, several machines, PR review as approval) is described anywhere in the docs; how
  two approvers coordinate `change.json` through git is not specified.
- I found no statement of whether `archive` is expected to run on the feature branch before merge or on `main` after,
  which matters for where a summary or changelog entry lands.

---

## 5. Which items does the roadmap list as candidates or deferred, and what deeper design do they need?

### Takeaway
The roadmap names four candidates, in the owner's recommended order: a diff of MODIFIED requirements for the approver
(code only), `verify` judging the work against the constitution (measured first), a tier raised after the reading,
and `validate` codes for a voided approval and drifted work in CI. All four have their inputs already computed; the
design work is mostly about where they show, whether they block, and compatibility.

### Cited Findings
- The four candidates, verbatim order — [docs/superpowers/plans/README.md:458-461](docs/superpowers/plans/README.md#L458)
- Left for the owner from phase 15: "a second verify review against the repository's rules beside the requirements
  ...; task dependencies written in tasks.md ...; a glossary and decision records under .spec/ ...; every stage's
  instruction reworded as the wanted behaviour ..., measured live before and after" —
  [research-during-planning-design.md:67-70](docs/superpowers/specs/2026-11-23-research-during-planning-design.md#L67);
  [plans/README.md:357-361](docs/superpowers/plans/README.md#L357)
- Held out until the owner asks: living specs drafted from existing code — [plans/README.md:239-240](docs/superpowers/plans/README.md#L239);
  a capability-to-folder map with an accept step — [plans/README.md:235-236](docs/superpowers/plans/README.md#L235)
- Deferred with reasons (not to re-propose): a late-failing propose keeping its reading; MCP progress notifications;
  the tier recorded in an approval — [plans/README.md:412-424](docs/superpowers/plans/README.md#L412)
- **(1) MODIFIED diff inputs.** Until archive the living spec holds the old requirement and the delta the new one; both
  are loaded in every `_assessed` (cli.py:459-468); the validator already detects a modification that drops a
  scenario (`delta.drops-scenario`) and one that changes nothing (`delta.modified-unchanged`) — validate.py codes
  list. Reports under `reports/` are not fingerprinted (layout.py:47-48), so a diff written there touches no approval.
- **(2) Verify inputs.** The verify stage's sections are deltas, tasks, requirements to judge, diff and tests; no
  constitution — [stages/verify.py:47-57](adk_spec/orchestration/stages/verify.py#L47). The check stage already reads
  the constitution and has a `constitution` finding kind — [stages/check.py:37-44](adk_spec/orchestration/stages/check.py#L37);
  [adk_spec/domain/drafts.py:158-172](adk_spec/domain/drafts.py#L158). A labelled `constitution` case exists for the
  check — [docs/measurements/README.md:14](docs/measurements/README.md#L14). The constitution may run to 16,000
  characters before `validate` warns — [adk_spec/workspace/context.py:25](adk_spec/workspace/context.py#L25)
- **(3) Tier inputs.** The tier is fixed by triage before the reading and printed "before the reading spends" —
  [cli.py:2019-2030](adk_spec/interfaces/cli.py#L2019); the reading then produces `risk` statements and unknowns —
  [adk_spec/domain/drafts.py:227-279](adk_spec/domain/drafts.py#L227). A person's `--tier` is final and triage is
  skipped — [cli.py:976-982](adk_spec/interfaces/cli.py#L976). Phase 10's rule-based sizing was removed because a
  missed risk word sized a risky fix lean — [plans/README.md:284-287](docs/superpowers/plans/README.md#L284)
- **(4) CI inputs.** `Assessed` already computes `stale` (approval no longer covers files) and `drifted` (work changed
  since verified) — [cli.py:427-468](adk_spec/interfaces/cli.py#L427), [cli.py:482-494](adk_spec/interfaces/cli.py#L482) —
  but `validate` emits only `findings`, and calls `_assessed(..., drift=False)` — [cli.py:544-554](adk_spec/interfaces/cli.py#L544);
  `--json` already prints findings and `failed` — [cli.py:556-558](adk_spec/interfaces/cli.py#L556)

### Inferences
1. **MODIFIED diff (small cost, code only).** A pure `domain` function (difflib on the canonical requirement render,
   `spec_md.render_spec`) producing a per-requirement old/new view, written into `reports/check.md` or its own report
   and named in one `approve` line ("2 requirements modified: reports/... shows each"). Design points: also show
   REMOVED requirements' text; show the base-stale case at `archive` with the same renderer (section 3, inference 3);
   keep the terminal to one line, per the golden rule.
2. **Verify against the constitution (medium cost, model).** Add the rules section to the verify stage and a second
   list in `VerdictsDraft` for rule breaks, each quoting added diff lines and grounded by `lines_of_diff`
   (verify.py:37-65) as verdicts are. Decide whether a rule break blocks `verified` (perhaps on the tier whose
   warnings block, `DEMANDS.warnings_block`), extend `scripts/cases.py` with a diff that breaks a rule, and measure
   before and after, as the roadmap says. Cost: the constitution's characters on every `verify`.
3. **Tier raised after the reading (medium cost, model, live measurement).** Let the review stage (or the brief) return
   a raise with a reason that quotes a kept `risk` statement; only ever raise, never when the person gave `--tier`;
   say it in one line before the brief ("raised to strict: ..."). Raising changes `DEMANDS.asks`, `design`,
   `read_first` and `approvers`, so it must happen before `_rounds` (cli.py:2043). A schema field changes
   `drafts.py`; the gate needs a check that the quoted risk exists.
4. **`validate` codes for CI (small to medium cost, code only).** Emit `change.approval-void` for an approved or
   verified change whose `stale` is non-empty and `change.work-drifted` for a verified change whose diff moved
   (needs the base commit in the CI clone, so a shallow checkout must fetch history; other repositories are absent in
   CI and should be skipped with an INFO). As WARNINGs they fail `--strict`; the README's CI recipe and a sample
   workflow then cover a pull request that edited an approved change or changed verified work.
5. **Owner-deferred items in light of the above:** task dependencies (`tasks.md`) would let the next-step line name
   the next unblocked task; decision records would hold the Q&A that today survives only in recordings (section 2g);
   a capability-to-folder map would make the drift signal in section 2 able to say which capability a changed file
   belongs to, which the prior research names as the mechanism behind drift detection.

### Gaps
- No measurement exists yet of how often triage under-sizes a request that the reading then shows to be risky, which
  is the evidence item 3 would need.
- The CI behaviour of `base_commit` in a shallow clone, and of `_drifted` when the base is unreachable (it returns
  True on a `GitError` — cli.py:488-491), was not tested here; a CI code would need that settled.
