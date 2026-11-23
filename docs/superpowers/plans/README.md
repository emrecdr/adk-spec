# Plans and roadmap: where the project stands

Updated on 22 November 2026.

## The golden rule

The owner's, 22 November 2026: few subcommands, simple flows, and no user overwhelmed with detail. The measure is
**easy to understand**, not the fewest commands.

How it is applied in every phase below:

- A command exists where a person decides something. The tool's own work happens inside it.
- A new capability goes inside an existing command. No phase below adds a subcommand.
- A command prints what it wrote, what needs the person, and the next command. Detail goes in files.

## How to read this

- A **phase** is one plan in this folder. It is built test first, cleaned up (`/simplify`), reviewed
  (`/code-review`), committed and merged to `main`. No phase ends with uncommitted work.
- A **design** comes before a plan where a phase is large or changes what a person does. It lives in `../specs/`
  and needs the owner's approval. A **plan** names the exact files and tests and is written once its design is
  approved.
- A detailed plan is written for one phase at a time, just before it is built, because each phase so far has
  changed the next. A phase further out has its expected shape below, which its own design confirms or changes.
- No live model call is made without the owner's go-ahead in so many words.

## Done and in progress

| # | Phase | Plan file | What it delivered | State |
|---|---|---|---|---|
| 1 | Foundation | `2026-11-21-adk-spec-foundation.md` | The `.spec/` tree; parsers and renderers; the validator; `init`, `new`, `validate`, `status`, `rebase`, `approve`, `archive`. No model. | Done |
| 2 | Model stages | `2026-11-22-adk-spec-model-stages.md` | `propose` and `plan`, each stage behind a gate; the token ledger; both provider arms. | Done, confirmed live on Copilot |
| 3 | Check and verify | `2026-11-21-adk-spec-check-and-verify.md` | `check` and `verify`, each finding held to a quote code finds; recordings; the measurement script. | Done, measured live twice. The Gemini arm and a run on Windows are the owner's |
| 4 | Questions in code | `2026-11-21-adk-spec-questions-in-code.md` | A brief names its open points and code asks them: one model call fewer a round. | Built and merged. Its live proof waits for the owner's go-ahead |
| 5 | The simple flow | `2026-11-22-adk-spec-simple-flow.md` | A standard change in four commands, a lean one in three: `propose` writes the whole change, `approve` records bases and makes the check. Help in three groups, progress lines, a `next` line. | Built, cleaned up, reviewed and merged. Its live proof waits for the owner's go-ahead |
| 6 | Brownfield, part 1 | `2026-11-22-adk-spec-brownfield-context.md` | `propose` reads the code that matters before it plans, and writes `context.md`, every statement with a quote code found. Secrets scrubbed from every request; `[repository] exclude`. | Built, cleaned up, reviewed and merged. Measured live: `integration` 5/5, and one `propose` on adk-spec |
| 7 | Brownfield, part 2 | `2026-11-22-adk-spec-across-repositories.md` | A change names the repositories it spans (`--with`); one reading covers them, a model reviews it, `context.md` says what is unknown; `verify` judges the work in all of them. | Built, cleaned up, reviewed and merged. Measured live: `across` caught 5/5 |
| 8 | Brownfield, part 3 | `2026-11-22-adk-spec-init-profile.md` | `init` reads the code, writes `.spec/profile.md`, drafts rules already true of the code into the template constitution; every change's reading starts from the profile. | Built, cleaned up, reviewed and merged. Measured live: `profile` 3/5 and 5/5, then a fix |
| 9 | Tests as evidence | `2026-11-22-adk-spec-verify-tests.md` | `verify` runs the test command a person wrote in `.spec/config.toml`, in every repository of the change; a failing run blocks "verified" unless overridden. | Built, cleaned up, reviewed and merged. Measured live: `propose` to `verify`, the tests run and passed |
| 10 and 11 | Sizing by rule; revising by instruction | `2026-11-22-adk-spec-sizing-and-revising.md` | The sizing rule was removed by the owner after review: the model sizes every request. `propose "<instruction>" --id <id>` revises an open change, keeping its tier, its IDs by name and what the instruction does not reach, and says what it added, changed and dropped. | Built, cleaned up, reviewed and merged. Measured live: sized by rule, revised with its IDs kept |
| 12 | A lessons file | `2026-11-22-adk-spec-lessons.md` | `.spec/lessons.md`, shared through git and read by every drafting stage: a person's corrections, and a line adk-spec adds in code for each fault a gate sent back that the next try fixed. `approve` names a drafted file a person edited, once. No model call. | Built, cleaned up, reviewed and merged. Measured live: a lesson written and counted |
| 13 | The `strict` tier | `2026-11-22-adk-spec-strict-tier.md` | A design always owed; `propose` stops after the brief and specs for a person to read, and `plan` goes on; two different names approve; a warning blocks, with no override. What each tier demands is one table in the domain. | Built, cleaned up, reviewed and merged. Measured live: the stop, a design, two names |
| 15 | Research during planning | `2026-11-23-adk-spec-research-during-planning.md` | `propose` reads the code, and the project's installed libraries offline, before the brief; the brief asks only what the code cannot answer, in order of what depends on what, and "yes" takes a suggestion; rules from the skills the owner pointed to in the brief, specs, tasks and check. | Built, cleaned up, reviewed and merged; measured live, a fault the first run found fixed |
| 14 | Inside a coding assistant | `2026-11-22-adk-spec-mcp-server.md` | `adk-spec-mcp` serves six commands as MCP tools to a coding assistant (`propose`, revising too, `plan`, `check`, `verify`, `status`, `validate`), each run as the terminal runs it; approving and archiving stay the person's. | Built, cleaned up, reviewed and merged. Its live proof, in VS Code and in Claude Code, waits for the owner |

## The plan being followed now

None: phases 1 to 14 are done, phase 10's rule since removed. What is left is the owner's, below.

## How a change flows

| | Before phase 5 | Now |
|---|---|---|
| Once for a repository | `init` | `init`, which reads the code into `profile.md` and drafts rules already true of it |
| One standard change | `propose`, `plan`, `check`, `approve`, `verify`, `archive` | `propose`, `approve`, `verify`, `archive`: `propose` reads every repository the change names, and `verify` runs your tests first |
| One lean change | `propose`, `plan`, `approve`, `archive` | `propose`, `approve`, `archive` |
| One strict change | none | `propose`, which stops after the brief and specs, then `plan`, `approve` by two names, `verify`, `archive` |
| Changing an open change | edit its files, then `plan` | the same, or `propose "<instruction>" --id <id>` |

## Roadmap: the phases to come

The order is a recommendation, changed on 22 November 2026 after the golden rule and the research on it
(`docs/research_notes/Simple command flows in spec tools/`): the simple flow now comes first, so that reading the code
is built once, in its final place inside `propose`.

Each phase says what features it adds and what a person can do once it is finished.

### Phase 5. The simple flow

**Goal.** One standard change takes four commands, one for each decision a person makes.

**Features it adds.**

- **`propose` writes the whole change**: brief, specs, the design where one is owed, and tasks, in one pass.
- **`approve` does its own preparation**: it records what the change is written against and runs the check where
  none is current. It stops on anything blocking.
- **A `next` line from every command**, `approve` and `archive` included.
- **Help in three groups**: the everyday commands first, then "to redo one step", then "setup".
- **Progress while a command runs**: one line a stage.
- **What to read first**: `propose` ends by naming the brief and the design, with their lengths.

**By the end of this phase, you can:**

- Take a change from a request to the record with four commands:

  ```
  adk-spec propose "Let users sign in with a passkey."
  adk-spec approve sign-in-with-a-passkey
  adk-spec verify sign-in-with-a-passkey
  adk-spec archive sign-in-with-a-passkey
  ```

- Never have to remember `plan`, `check`, `rebase` or `validate`, and still run any of them to redo one step.
- See what a command is doing while it works, and what to do when it ends.

**Not yet, at the end of this phase.** `propose` still does not read your code.

**From the research.** OpenSpec cut its default from ten commands to four because "new users feel overwhelmed".
Kiro and BMAD both added a one-pass path in 2026. Spec Kit only ever grew, and its own newsletters name ceremony
and verbose output as its most-cited concerns. What users call heavy is mostly how much they must read, so this
phase also shows and measures the lengths of what it writes.

**Depends on.** Nothing unbuilt. **Size.** Medium: the work is in some forty tests that pin today's steps.

**State.** Done, on 22 November 2026. One thing differs from the design: where a question is left unanswered,
`propose` writes the brief and the specs and drafts no plan on a guess; the person settles the point and runs
`plan`. Its live proof, one standard change through the four commands, waits for the owner's go-ahead.

### Phase 6. Brownfield, part 1: the plan rests on your code

**Goal.** A design and a task list for a new feature rest on what the repository's code is, not on file names.

**Features it adds.**

- **`propose` reads the code that matters for the change** before it drafts the design and the tasks. No command of
  its own. `plan` does the same for a change that has no context yet.
- **`context.md`** in the change's folder, in four sections: what exists, where the change plugs in, conventions
  to follow, risks. Every statement names a file and a line and quotes the code.
- **Checked statements**: one whose quote is not in the file it names is left out and counted.
- **Safe reading**: only files git tracks or would track; no symbolic link; nothing git ignores.
- **`[repository] exclude`**: paths that are never read, listed or sent, by any command.
- **Secret scrubbing in every command**: known secret shapes are removed from every model request and from the
  recordings.
- **`--no-explore`** on `propose` and `plan`, to skip the reading.

**By the end of this phase, you can:**

- Run `propose` in an existing repository and get a design and tasks that name the functions and files that exist
  and follow the conventions the code already keeps.
- Open `context.md` and see, for each statement, the file, the line and the quoted code.
- Name paths that are never to leave the machine.
- Know that a key or a password of a known shape, in a tracked file, is not sent to the provider.

**Not yet, at the end of this phase.** The brief and the specs do not read the code; no profile of the whole
repository; no spec for behaviour that already exists.

**How it works.** The model points and Python reads, as the owner chose. A scout stage names files, folders and
search words; code checks every path against git's own list and reads within fixed caps; a survey stage writes
statements, each with a quote; code keeps only those whose quote is in the file.

**Where it sits, and why.** After the brief and the specs are written, before the design and the tasks. The scout
then knows the change that was agreed, with the answers to its questions; a request that owes no spec and a change
with a question left open read nothing; and a reading that fails leaves a written change and a plan drafted
without it.

**From the research.** OpenSpec's `propose` has read "relevant implementation, nearby tests, configuration, and
documentation" before drafting since its version 1.12.0. It keeps no record of what it read and checks none of
it; the checked quotes are what this phase adds.

**Cost to a person.** It becomes the largest part of `propose`: up to four model calls and some 30,000 tokens at
the caps, far less in a small repository. `[limits] max_tokens` holds it and `--no-explore` skips it.

**Design.** `../specs/2026-11-22-brownfield-feature-context-design.md`.

**Depends on.** Phase 5. **Size.** About eight tasks.

**State.** Done, on 22 November 2026. Its reviews found and fixed real leaks, among them a private key's body shown
by a range of lines, and lines of a key shown by a diff of a change next to it; the plan's "What changed" section
lists them. Measured live: the `integration` case 5/5, and one `propose` on adk-spec itself. A note on the key gap,
which the reference project shares, is in `../../notes/`.

### Phase 7. Brownfield, part 2: context across repositories, checked by a model

New on the roadmap on 22 November 2026, from the owner: "we will work mostly on brownfields, and in many cases more
than 1 repo is involved in building new features, so gathering context is very imprortant part of the process, so
llm model should be checking results".

**Goal.** The context a plan rests on covers every repository the feature spans, and a model says whether it is
enough and what is still unknown.

**Features it adds** (a recommendation, settled in the phase's design).

- **Other repositories named with each change**: `propose "..." --with ../api --with ../web`. Each is read through
  its own git list with the same rules as the first: no link, nothing ignored, its own exclusions, secrets scrubbed,
  no file that holds a key.
- **One reading across them**: the scout sees each repository's files under its name, and a statement names the
  repository, the file and the line.
- **A model's verdict on the reading**: once the rounds end, a stage reads the brief, the specs and what was kept,
  and says what is established and what is still unknown. The unknowns go into `context.md`, where the person and
  the planning stages both see them, and may send the reading one round further.

**By the end of this phase, you can:** plan a feature that changes an API and the web app that calls it, from one
workspace, and read in `context.md` what was found in each and what nobody could establish.

- **`verify` across repositories**: approval records where each repository's work began, and `verify` judges the
  work in all of them.

**Decided by the owner, 22 November 2026.** adk-spec reads every named repository and a model reviews the reading;
`verify` covers every repository in this phase; an unknown is said, and `propose` does not stop on it. The
repositories are named with each change, not in a project's config.

**Design.** `../specs/2026-11-22-brownfield-across-repositories-design.md`.

**Depends on.** Phase 6. **Size.** Medium to large.

**State.** Done, on 22 November 2026: built, cleaned up, reviewed and merged. Its reviews found and fixed real faults,
among them git trusting every repository it ran in; the plan's "What changed" section lists them. The first live
reading, of adk-spec's own code, came before it and shaped it. Its own live proof, the `across` case, caught the planted
file in the other repository in 5 runs of 5.

### Phase 8. Brownfield, part 3: `init` describes the repository

**Goal.** adk-spec knows a repository before the first change.

**Features it adds.**

- **`init` reads an existing repository** and writes a short profile under `.spec/`: stack, layout, how the project
  is built and tested, each statement with a quote. It says before it starts that it will call a model, and takes a
  flag to skip.
- **A drafted constitution**: rules that are already true of the code, each with its evidence, for the person to
  accept, change or drop.
- **A capability-to-folder map**, proposed and written only when the person accepts it.
- **`propose` starting from the map**: a capability's own folders are read first, with no model call spent on
  finding them.
- **A flag on `init` to refresh** the profile later.

**By the end of this phase, you can:**

- Adopt adk-spec in an existing repository with one command, and have it describe that repository back to you with
  its evidence.
- Accept, edit or reject each proposed rule and each folder mapping.
- Get briefs and plans that use your stack and your conventions without having written them down first.

**From the research.** Neither parent project does this. Spec Kit's guide for an existing project says to write
only principles "already true for the repository", from the README, the architecture decisions, the contribution
guide and the CI configuration: those are what `init` reads first. OpenSpec's position is "You write specs only for
what you're about to change", so this phase writes a profile and rules, and no spec of the existing system.

**Depends on.** Phase 7. **Size.** Medium to large.

**Decided by the owner, 22 November 2026.** `init` reads the code with a model and says so first, `--no-explore`
skipping it; rules already true of the code are drafted into `constitution.md` while it is the empty template, each
with its evidence and marked as drafted.

**State.** Done, on 22 November 2026: built, cleaned up, reviewed and merged. A capability-to-folder map with an
accept step was left out: the profile names where things live, and is the person's to edit. Measured live: `init`
on a copy of adk-spec, and the `profile` case, 3/5 and then, after a fix to the reading's instruction, 5/5.

**To decide then.** Whether living specs are ever drafted from existing code. It is an open request in both
projects' trackers and the part most likely to be wrong; it stays out until the owner asks for it.

### Phase 9. Tests as evidence, inside `verify`

**Goal.** A verdict rests on the project's own tests as well as on the diff.

**Features it adds.** A test command in `.spec/config.toml`, written by the person. `verify` runs it before a model
judges, maps results to requirement IDs, and shows them in `reports/verify.md`.

**By the end of this phase, you can:** have `verify` say "met" because a named test passes and "unmet" because one
fails; see which requirements no test covers.

**From the research.** A step that only advises gets skipped: OpenSpec's `verify` cannot block its archive. Ours is
a gate already and stays one, and the tests run inside it, with no new command.

**Depends on.** Nothing unbuilt. **Size.** Large, and security-sensitive: it is the first phase in which adk-spec
runs a command of the project's. Only a command the person wrote is ever run.

**Decided by the owner, 22 November 2026.** The command is one a person writes in `.spec/config.toml`, run by every
`verify` before the model judges, and another repository's from its own config; a failing run blocks "verified",
`--override` with a reason being the way through.

**State.** Done, on 22 November 2026: built, cleaned up, reviewed and merged. Its reviews made the run itself safe:
judged by its own exit, its whole tree stopped when it ends or is interrupted, its output a rolling window, withheld
where it names a private key. Measured live: one change from `propose` to `verify`, its tests run and passed, which
showed adk-spec's own virtual environment leaking into the run, since fixed.

### Phase 10. Triage by rules

**Goal.** Most requests are sized (lean, standard, none) with no model call.

**Features it adds.** Rules that size a request from what can be measured in it; a model asked only where they do
not decide.

**By the end of this phase, you can:** run `propose` and have the first model call go straight to the work.

**From the research.** Fixed ceremony for small changes is the second most-named complaint, and "spec mode for
features, a lighter path for fixes" is what users praise. This phase makes the lighter path the default for what
is small. **Size.** Small.

**State.** Done, on 22 November 2026, built with phase 11 as the owner asked. The code review found the first rule
took a typo fix, which the sizing stage itself calls `none`: a request that may owe no spec is now never sized by a
rule, and lean by rule needs a fix verb, a word of a fault and no feature word.

**Removed**, on 22 November 2026, on the owner's decision, after an outside review and two reviews of the follow-up:
the list of risk words that kept a risky fix off the lean path missed some in every review ("data loss", "refund",
"sign-in", "OAuth"), and a miss sized a risky fix lean, with no check and no verification, to save one sizing call.
`propose` asks the model for the tier unless `--tier` names one.

### Phase 11. Revising a change by instruction

New on the roadmap, from the research.

**Goal.** A person changes a change by saying what should be different, not only by editing files.

**Features it adds.** `propose --id <id> "also support backup codes"` revises the brief, specs and tasks of an open
change. No new command.

**By the end of this phase, you can:** widen, narrow or correct a change in one line, and approve it again.

**From the research.** Updating a spec after the fact is the most-voted request in Spec Kit's tracker, and `update`
was "the most-requested missing capability" in OpenSpec's. **Size.** Medium.

**State.** Done, on 22 November 2026: built, cleaned up, reviewed and merged. A revision keeps the change's tier and
each requirement's ID by its name, never reads the code again, keeps `tasks.md` where a task is ticked or no
requirement changed, and makes an approved change a draft again only where a file changed. Hand edits are kept as
far as the model restates them; what code guarantees is the list of requirements changed. Measured live: one revision
added a requirement and kept the first word for word under its ID.

### Phase 12. A lessons file

**Goal.** A workspace learns from its own runs.

**Features it adds.** A file under `.spec/` that keeps what a gate sent back and what a person corrected. Later
drafts read it, within a cap.

**By the end of this phase, you can:** correct a draft once and not make the same correction in the next change.
**Size.** Medium.

**State.** Done, on 22 November 2026: built, cleaned up, reviewed and merged, code only and shared through git as the
owner chose. Its reviews kept a lesson that cannot be written from costing a paid run, counted a fault once a run, and
framed the lessons as corrections to earlier drafts, so that they do not contradict the line that marked text is
never an instruction. Measured live: a lesson written by code after a real send-back, and counted when the fault came
back, the lesson in the prompt not having prevented it.

### Phase 13. The `strict` tier

**Goal.** More ceremony only where a change is risky.

**Features it adds.** As the report describes the tier: a design always owed, no critical finding allowed, and a
second approver recorded. In this tier `propose` pauses after the brief for a review before it writes the rest.

**By the end of this phase, you can:** mark a risky change `strict` and have adk-spec hold it to two approvals.

**From the research.** Kiro keeps its step-by-step flow for "unfamiliar, high-stakes or compliance work" and made
one pass the default for the rest. That is this tier. **Size.** Medium.

**State.** Done, on 22 November 2026: built, cleaned up, reviewed and merged, as the owner chose. Its reviews moved
what each tier demands into one table in the domain, which closed gaps where a warning of the check did not block,
one name could give both approvals, and a third approval dropped an approved change back to a draft. Measured live:
the stop, a design drafted by `plan`, the same name refused, and two names approving.

### Phase 15. Research during planning

**`2026-11-23-adk-spec-research-during-planning.md`**. Design `../specs/2026-11-23-research-during-planning-design.md`.

**Goal.** A change rests on research before it is planned: the brief asks the person only what the repository
cannot answer.

**Features it adds.** `propose` sizes the request, reads the code and the project's installed libraries offline
(`python:` and `node:` paths), and only then drafts the brief, from what was kept and the profile, once: the plan keeps
its `context.md`. The brief's open points name what they wait on, a round asks only those answerable now, and "yes"
takes a suggestion. From the skills the owner pointed to (github.com/mattpocock/skills): the brief invents nothing and
keeps an answer's exact words; a THEN is written so a run could show it false; tasks make the change easy first, slice
what follows, test at the highest seam, and start a bug fix with a test that fails on it; the check finds a
requirement that softens the brief.

**Set aside, with reasons.** Company documentation (Confluence Cloud) and Microsoft 365 Copilot's reach into it: the
models adk-spec calls are GitHub Copilot's, whose connectors run in its clients, and Microsoft 365 is another product
needing an app registration. Web search: one arm only, or a third party's key fed words from company work. From the
skills, for the owner to choose later: a second verify review against the repository's rules, task dependencies in
`tasks.md`, a glossary and decision records, and stage instructions reworded positively, measured before and after.

**State.** Built, cleaned up, reviewed and merged on 23 November 2026, and measured live the same day
(`../../measurements/2026-11-23-phase-15-live.md`): the first run failed at the deltas, the brief naming three
capabilities where triage named one; the brief now starts from triage's, and the second run wrote the change. Not
yet seen live: a standard change's question rounds, and a scout opening an installed library.

### Phase 14. adk-spec inside a coding assistant

The owner's choice, on 22 November 2026, of the second way to use adk-spec.

**Goal.** A person drafts, checks and verifies a change from inside the coding assistant they already use, GitHub
Copilot in VS Code or Claude Code.

**Features it adds.** `adk-spec-mcp`, an MCP server over stdio, whose tools run six of the commands as the terminal
runs them, asking no question, on adk-spec's own models: `propose` (revising an open change too), `plan`, `check`,
`verify`, `status`, `validate`. `approve`, `archive` and `--override` are no tools: they record a person's decision,
and the server's instructions tell the assistant so. `cli.py` is not split: each tool runs `python -m adk_spec` in a
process of its own.

**By the end of this phase, you can:** ask your coding assistant to propose a change, read its brief and specs in the
editor, implement the tasks with the same assistant, and verify the work, approving and archiving in the editor's
terminal.

**From the research.** Both parent projects live inside coding assistants, and the outside review of 22 November
2026 named it the biggest gain in daily use on Windows. **Size.** Small, as the owner chose it thin.

**State.** Done, on 22 November 2026: built, cleaned up, reviewed and merged, as the owner chose. Its live proof, the
server in VS Code with Copilot and in Claude Code, waits for the owner. The `mcp` package it brought may also let
Copilot's GPT models answer through LiteLLM, which one live call should show before it is claimed.

### Not planned unless a measurement asks for it

The contradiction pass of `check` moved to code. The two measurements so far show it is the least steady stage,
and a step moves to code only where its output is a function of its input with no judgement.

## Decided, and next

- **The third audit, 23 November 2026**: a read-only audit's findings, each checked by an independent verifier that
  tried to disprove it, then fixed test first on the branch `audit3-fixes`, as recommended. Fixed: exclude patterns
  read as `.gitignore` reads them (`secrets/` at any depth, a folder with all it holds); `verify`'s tests given no
  variable adk-spec's own `.env` set; open points printed with their suggestions under `--no-input`; a lock that
  could not be written removed; one unreadable `change.json` stopping no other change; the reading held to half of
  what is left of a token ceiling, and the README's example ceiling raised from 30,000 to 80,000; the tier said
  before the reading; a refusal counting as the check did; every next line naming its command; the editor's tools
  told how to implement, each parameter described; a capability with no living spec named as new to the stages, the
  cause of the send-back met most; keys in a large or non-UTF-8 file withheld from a diff; a Gemini answer cut at its
  limit not asked again; the chat given triage's capabilities; `new` under the lock; a file on disk before it
  replaces the old one; a folder listed once while it does not change; no node package walked past the cap. The
  README is a usage guide, at the owner's request. Refuted: statements dropped for a wrong path were invented quotes.
  Deferred, with their reasons:
  - **A propose that fails late keeps nothing** (the reading and the answers are lost). Keeping a half-written change
    reverses the rule that a change is written whole or not at all, and makes `validate` fail for the workspace. The
    owner decided on 23 November 2026, as recommended, to keep it deferred. The most common late failure, a delta with
    no purpose, is fixed at its cause.
  - **An Agent Skill beside the MCP server.** Built, on the owner's decision of 23 November 2026: `init` writes
    `.claude/skills/adk-spec/SKILL.md`, which Copilot and Claude Code read, once and never over one that is there
    (`docs/superpowers/specs/2026-11-24-agent-skill-design.md`). Cleaned up and code-reviewed: the skill leaves
    `--with` to the person as the server does, a skill that cannot be written is one line and never a failed `init`,
    and git's listings leave it out as they leave out `.spec/`.
  - **Progress notifications from the MCP tools.** Neither VS Code nor Claude Code times a local server out at 60 s,
    and Claude Code is reported to send no progress token, so a heartbeat would be cosmetic in VS Code alone.
  - **The tier recorded in an approval.** It catches only an accidental edit of `change.json`, which a hand edit could
    already forge, and a new field makes every older adk-spec refuse the file.
- **A second way to use adk-spec, beside the terminal**: decided on 22 November 2026, as recommended. It is an MCP
  server for coding assistants, phase 14 above.
- **A change file written by a newer adk-spec**: decided on 22 November 2026, as recommended. An older adk-spec keeps
  refusing it, since ignoring the fields it does not know would drop them when it saves, but says why: the file was
  written by a newer adk-spec, and upgrading reads it.

## The owner's, outside any phase

- A smoke run on the Gemini arm. It needs a `GOOGLE_API_KEY`.
- The gate on a Windows machine. The CI workflow has a Windows job, and the repository has no remote.
- A Windows job object, to stop what a passing test run leaves running there; until then it runs on, and only a run
  past its time, or interrupted, is stopped on Windows. It waits for a Windows machine to test it on.
- Two items of the outside audit of 22 November 2026, deferred with their reasons. Untracked files diffed in Python
  rather than one `git` process each: faster on Windows, but the diff's text would change, and every change verified
  before it would read as drifted unless the text matched git's byte for byte; a Windows run should first show the
  cost. LiteLLM's private names in `login.py` and `catalog.py` replaced: ADK 2.14.1 holds LiteLLM below 1.106.3
  itself, so no upgrade follows, and a new login flow needs a live login to prove.
- Plan 4's live proof: one `propose` and a 25-call measurement, on a go-ahead.
- Plan 5's live proof: one standard change through the four commands, on a go-ahead. `approve` calls a model
  now, on a standard change whose check is not current.
- Every live model call: each needs a go-ahead in so many words.
