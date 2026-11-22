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
| 6 | Brownfield, part 1 | `2026-11-22-adk-spec-brownfield-context.md` | `propose` reads the code that matters before it plans, and writes `context.md`, every statement with a quote code found. Secrets scrubbed from every request; `[repository] exclude`. | Built, cleaned up, reviewed and merged. Its live proof waits for the owner's go-ahead |

## The plan being followed now

**`2026-11-22-adk-spec-across-repositories.md`**, phase 7: context across repositories, checked by a model.

## How a change flows

| | Before phase 5 | Now | After phases 7 and 8 |
|---|---|---|---|
| Once for a repository | `init` | `init` | `init`, which also describes the repository back to you |
| One standard change | `propose`, `plan`, `check`, `approve`, `verify`, `archive` | `propose`, `approve`, `verify`, `archive`, with `propose` reading your code first | the same four, reading every repository the feature spans |
| One lean change | `propose`, `plan`, `approve`, `archive` | `propose`, `approve`, `archive` | the same three |

## Roadmap: the phases to come

The order is a recommendation, changed on 22 November 2026 after the golden rule and the research on it
(`research_notes/Simple command flows in spec tools/`): the simple flow now comes first, so that reading the code
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
lists them. Its live proof, the `integration` case and one reading of a real repository, waits for the owner's
go-ahead. A note on the key gap, which the reference project shares, is in `../../notes/`.

### Phase 7. Brownfield, part 2: context across repositories, checked by a model

New on the roadmap on 22 November 2026, from the owner: "we will work mostly on brownfields, and in many cases more
than 1 repo is involved in building new features, so gathering context is very imprortant part of the process, so
llm model should be checking results".

**Goal.** The context a plan rests on covers every repository the feature spans, and a model says whether it is
enough and what is still unknown.

**Features it adds** (a recommendation, settled in the phase's design).

- **Other repositories named once**, in `.spec/config.toml`, each read through its own git list with the same rules
  as the first: no link, nothing ignored, its own exclusions, secrets scrubbed, no file that holds a key.
- **One reading across them**: the scout sees each repository's files under its name, and a statement names the
  repository, the file and the line.
- **A model's verdict on the reading**: once the rounds end, a stage reads the brief, the specs and what was kept,
  and says what is established and what is still unknown. The unknowns go into `context.md`, where the person and
  the planning stages both see them, and may send the reading one round further.
- **Room as a setting**: rounds and characters a round in `.spec/config.toml`, for a large feature.

**By the end of this phase, you can:** plan a feature that changes an API and the web app that calls it, from one
workspace, and read in `context.md` what was found in each and what nobody could establish.

- **`verify` across repositories**: approval records where each repository's work began, and `verify` judges the
  work in all of them.

**Decided by the owner, 22 November 2026.** adk-spec reads every named repository and a model reviews the reading;
`verify` covers every repository in this phase; an unknown is said, and `propose` does not stop on it.

**Design.** `../specs/2026-11-22-brownfield-across-repositories-design.md`.

**Depends on.** Phase 6. **Size.** Medium to large.

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

### Phase 10. Triage by rules

**Goal.** Most requests are sized (lean, standard, none) with no model call.

**Features it adds.** Rules that size a request from what can be measured in it; a model asked only where they do
not decide.

**By the end of this phase, you can:** run `propose` and have the first model call go straight to the work.

**From the research.** Fixed ceremony for small changes is the second most-named complaint, and "spec mode for
features, a lighter path for fixes" is what users praise. This phase makes the lighter path the default for what
is small. **Size.** Small.

### Phase 11. Revising a change by instruction

New on the roadmap, from the research.

**Goal.** A person changes a change by saying what should be different, not only by editing files.

**Features it adds.** `propose --id <id> "also support backup codes"` revises the brief, specs and tasks of an open
change. No new command.

**By the end of this phase, you can:** widen, narrow or correct a change in one line, and approve it again.

**From the research.** Updating a spec after the fact is the most-voted request in Spec Kit's tracker, and `update`
was "the most-requested missing capability" in OpenSpec's. **Size.** Medium.

### Phase 12. A lessons file

**Goal.** A workspace learns from its own runs.

**Features it adds.** A file under `.spec/` that keeps what a gate sent back and what a person corrected. Later
drafts read it, within a cap.

**By the end of this phase, you can:** correct a draft once and not make the same correction in the next change.
**Size.** Medium.

### Phase 13. The `strict` tier

**Goal.** More ceremony only where a change is risky.

**Features it adds.** As the report describes the tier: a design always owed, no critical finding allowed, and a
second approver recorded. In this tier `propose` pauses after the brief for a review before it writes the rest.

**By the end of this phase, you can:** mark a risky change `strict` and have adk-spec hold it to two approvals.

**From the research.** Kiro keeps its step-by-step flow for "unfamiliar, high-stakes or compliance work" and made
one pass the default for the rest. That is this tier. **Size.** Medium.

### Not planned unless a measurement asks for it

The contradiction pass of `check` moved to code. The two measurements so far show it is the least steady stage,
and a step moves to code only where its output is a function of its input with no judgement.

## To decide

- **A second way to use adk-spec, beside the terminal.** Asked of the owner on 22 November 2026 and not yet
  answered. The research suggests use from inside a coding assistant, where both parent projects live, over a web
  workbench.

## The owner's, outside any phase

- A smoke run on the Gemini arm. It needs a `GOOGLE_API_KEY`.
- The gate on a Windows machine. The CI workflow has a Windows job, and the repository has no remote.
- Plan 4's live proof: one `propose` and a 25-call measurement, on a go-ahead.
- Plan 5's live proof: one standard change through the four commands, on a go-ahead. `approve` calls a model
  now, on a standard change whose check is not current.
- Every live model call: each needs a go-ahead in so many words.
