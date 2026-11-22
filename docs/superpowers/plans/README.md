# Plans and roadmap: where the project stands

Updated on 22 November 2026.

## How to read this

- A **phase** is one plan in this folder. It is built test first, then cleaned up (`/simplify`), reviewed
  (`/code-review`), committed and merged to `main`. No phase ends with uncommitted work.
- A **design** comes before a plan where a phase is large or changes what a person does. It lives in `../specs/`
  and needs the owner's approval. A **plan** names the exact files, interfaces and tests, and is written once its
  design is approved.
- A detailed plan is written for one phase at a time, just before it is built. Each phase so far has changed the
  next: the live measurement after plan 3 found a fault that reshaped plan 4. So a phase further out has its
  **expected shape** below, and that shape is confirmed or changed by its own design when its turn comes.
- No live model call is made without the owner's go-ahead in so many words. Every phase ends with a task that
  holds its live steps.

## Done and in progress

| # | Phase | Plan file | What it delivered | State |
|---|---|---|---|---|
| 1 | Foundation | `2026-11-21-adk-spec-foundation.md` | The `.spec/` tree; parsers and renderers for briefs, specs, deltas and tasks; the validator; `init`, `new`, `validate`, `status`, `rebase`, `approve`, `archive`. No model. | Done |
| 2 | Model stages | `2026-11-22-adk-spec-model-stages.md` | `propose` (triage, brief, questions, deltas) and `plan` (design, tasks), each stage behind a gate; the token ledger; both provider arms; `smoke`, `models`, `login`. | Done, confirmed live on Copilot |
| 3 | Check and verify | `2026-11-21-adk-spec-check-and-verify.md` | `check` and `verify`, each finding and verdict held to a quote code finds; recordings of every run; the labelled set and the measurement script; the chat shape for ADK's own interface. | Done, measured live twice. The Gemini arm and a run on Windows are the owner's |
| 4 | Questions in code | `2026-11-21-adk-spec-questions-in-code.md` | A brief names its open points with a suggested answer and code asks them: one model call fewer a round. A malformed marker is a validator error. | Tasks 1 to 3 done and merged. Task 4, the live proof, waits for the owner's go-ahead |
| 5 | Brownfield, part 1 | not written yet | See the roadmap below. | **In design.** `../specs/2026-11-22-brownfield-feature-context-design.md` waits for the owner's approval |

## The plan being followed now

Phase 5 has a design and no plan yet. Until it has one, the last plan worked from is
`2026-11-21-adk-spec-questions-in-code.md`.

## How a change flows, today and after the next two phases

| Step | Today | After phase 5 | After phase 6 |
|---|---|---|---|
| Once for a repository | `init`, and a constitution written by hand | the same | `init`, then a survey that writes a repository profile, proposes which folders belong to which capability, and drafts a constitution from what is already true |
| Start a change | `propose "..."` | the same | the same, with the profile behind the brief |
| Read the code | not done: `plan` sees file paths only | `explore <id>` writes `context.md`, every statement with a checked quote | the same, starting from the capability's own folders |
| Plan | `plan <id>` | `plan <id>`, drafted from `context.md` | the same |
| Then | `check`, `approve`, implement, `verify`, `archive` | the same | the same |

## Roadmap: the phases to come

The owner chose phases 5 and 6 and their order on 22 November 2026. The order after them is a recommendation; it
follows the research report (`reports/Spec driven framework on Google ADK.md`, its migration table) and plan 3's
"What this plan leaves".

Each phase below says what features it adds and what a person can do once it is finished. Phase 5 has a design;
phases 6 to 11 give their expected shape, which each one's own design confirms or changes.

### Phase 5. Brownfield, part 1: context for one feature

**Goal.** A design and a task list for a new feature rest on what the repository's code is, not on file names.

**Features it adds.**

- **`adk-spec explore <id>`**: a new command, run between `propose` and `plan`, that reads the code that matters
  for one change.
- **`context.md`**: a new file in the change's folder, in four sections: what exists, where the change plugs in,
  conventions to follow, risks. Every statement names a file and a line and quotes the code.
- **Checked statements**: a statement whose quote is not in the file it names is left out and counted. Nothing
  invented reaches a later stage.
- **`plan` drafting from the context**: the design and tasks stages read `context.md`.
- **Safe reading**: only files git tracks or would track; no symbolic link; no file git ignores.
- **`[explore] exclude`**: a setting for paths that must never be read.
- **Secret scrubbing in every command**: known secret shapes are removed from every model request, `verify`'s diff
  included, and from the recordings.
- **`status` naming the step**: `explore` is shown as the next step for a draft with a brief and no context.
- **A measurement case**: a small repository with one planted integration point and one decoy.

**By the end of this phase, you can:**

- Start a feature in an existing repository and have adk-spec read the relevant code for it:

  ```
  adk-spec propose "Let users sign in with a passkey."
  adk-spec explore sign-in-with-a-passkey
  adk-spec plan sign-in-with-a-passkey
  ```

- Open `context.md` and see, for each statement, the file, the line and the quoted code, then correct or delete
  any of it before a design is drafted from it.
- Get a design and a task list that name the functions and files that exist and follow the conventions the code
  already keeps.
- Name folders that are never to leave the machine, and know they are not read.
- Know that a key or a password of a known shape, in a tracked file, is not sent to the provider by any command.
- See what an exploration cost on its `tokens` line, and hold it with `[limits] max_tokens`.

**Not yet, at the end of this phase.** `propose` does not read code before it writes the brief. There is no profile
of the whole repository and no map of folders to capabilities. No spec is written for behaviour that already
exists.

**How it works.** The model points and Python reads. A scout stage names files, folders and search words. Code
checks every path against git's own list, reads within fixed caps, and runs each search as a fixed string. A survey
stage writes statements, each with a quote, and code keeps only those whose quote is in the file. The survey may
ask to look again, a fixed number of times. In a repository past 300 files the scout is shown folders and not
files, so it first asks for a folder's listing or for a search.

**Expected tasks.** The plan fixes them once the design is approved.

1. Secret scrubbing, ported from `adk_review`: first in every app's roster, failing closed, for every command.
2. Reading source safely: paths from git's list only, no symbolic link, text only, the caps, line ranges, the
   exclusions, a folder's listing, and a fixed-string search.
3. Statements as data: their schema, grounding by quote with the code `check` and `verify` use, and `context.md`.
4. The scout and survey stages, the loop between them, their gates, and the `explore` command with its recording
   and its tokens line.
5. `plan` reading `context.md`: the design and tasks stages gain one section each.
6. `status`, the README, and the labelled case for the measurement script.
7. Live, on the owner's go-ahead: that case several times, and one real repository read by hand.

**Depends on.** Nothing unbuilt. **Size.** About seven tasks.

**Cost to a person.** The most expensive command: three or four model calls and up to some 20,000 tokens for one
exploration, where a `propose` and a `plan` together spend 3,000 to 10,000.

**Risks.** A real model quoting loosely, so that true statements are left out. A scout that names the wrong files
in a large repository. Scrubbing that changes what other commands send. Each has a test or a live measurement.

**Open.** The owner's approval of the design.

### Phase 6. Brownfield, part 2: a baseline of the repository

**Goal.** adk-spec knows a repository before the first change: its stack, its structure, its conventions, and which
folders belong to which capability.

**Features it adds.**

- **A one-time survey command**, run after `init` on an existing repository.
- **A repository profile** under `.spec/`: languages and frameworks with their versions, the layout, how the
  project is built and tested, each statement with a quote from a manifest, a README or the code.
- **A capability-to-folder map**, proposed by the survey and written to the config only when the person accepts it.
- **A drafted constitution**: rules that are already true of the code, each with its evidence, for the person to
  accept, change or drop. Spec Kit's own advice for an existing project is to write only such rules.
- **`explore` starting from the map**: for a change that touches a capability, that capability's folders are read
  first, with no model call spent on finding them.
- **Every drafting stage reading the profile**, the brief included.

**By the end of this phase, you can:**

- Adopt adk-spec in an existing repository with two commands, and have it describe that repository back to you,
  with its evidence.
- Accept, edit or reject each proposed rule and each folder mapping, one at a time.
- Get briefs and plans that use your stack and your conventions without your having written them down first.
- Explore a change faster and for fewer tokens, because the first files come from the map.

**Not yet, at the end of this phase.** No spec for behaviour that already exists; no check that code and specs
still agree.

**How it works.** The reading, grounding and scrubbing of phase 5, pointed at the repository as a whole and at its
manifests first.

**Depends on.** Phase 5. **Size.** Medium to large.

**Risks.** A wrong map misleads every later run, so nothing is written to the config without the person.

**To decide then.**

- Whether `propose` explores before it writes the brief. Phase 5's measurement shows whether a request alone finds
  the right files.
- Whether living specs are drafted from existing code. It is the most requested feature of Spec Kit and the part
  most likely to be wrong; it stays out until the owner asks for it.
- A drift check between living specs and code, the report's sixth migration step, which needs the map.

### Phase 7. Tests as evidence for `verify`

**Goal.** A verdict rests on the project's own tests as well as on the diff.

**Features it adds.**

- **A test command in `.spec/config.toml`**, written by the person.
- **`verify` running it** before a model judges, with a timeout.
- **Results mapped to requirements**: which tests speak for which requirement ID, and whether they pass.
- **Evidence in the report**: `reports/verify.md` shows the tests beside the quoted lines of the diff.

**By the end of this phase, you can:**

- Have `verify` say "met" for a requirement because a named test passes, and "unmet" because one fails, with no
  model's opinion needed for either.
- See, for each requirement, the tests that cover it, and which requirements no test covers.
- Archive a change knowing its requirements were checked by running code, not only by reading a diff.

**How it works.** Code runs the configured command as an argument list and never through a shell, with no provider
token in its environment. It maps results to requirement IDs. The model judges only what the evidence leaves open.

**Depends on.** Nothing unbuilt. **Size.** Large.

**Risks.** It is the first phase in which adk-spec runs a command of the project's: a process left running, most of
all on Windows, and a command that should not have been run at all. Only a command the person wrote is ever run; a
model never chooses one.

### Phase 8. Triage by rules

**Goal.** Most requests are sized (lean, standard, none) with no model call.

**Features it adds.** Rules that size a request from what can be measured in it, and a model asked only where the
rules do not decide. `propose` says which rule sized the request.

**By the end of this phase, you can:** run `propose` without `--tier` and, for most requests, have the first model
call go straight to the brief: faster, and one call cheaper.

**How it works.** The rules are drawn from the recordings of real runs and proven by replaying recorded triage
answers against them.

**Size.** Small.

### Phase 9. The contradiction pass of `check` in code

**Goal.** What code can decide about two files that disagree is decided by code.

**Features it adds.** Code checks for the kinds of disagreement that need no reading, reported by `check` and by
`check --no-model`.

**By the end of this phase, you can:** catch a share of contradictions for free and the same way every run, where
today a model catches them in some runs and not in others.

**Depends on.** More measurement, and it may not happen. The two measurements so far show this pass is the least
steady of all: caught in 2 runs of 3, then in 1 of 3. A step moves to code only where its output is a function of
its input with no judgement, and this one may not be.

**Size.** Medium.

### Phase 10. A lessons file

**Goal.** A workspace learns from its own runs.

**Features it adds.** A file under `.spec/` that keeps what a gate sent back and what a person corrected in a
draft. Later drafts read it, within a cap. The person can edit it.

**By the end of this phase, you can:** correct a draft once and not have to make the same correction in the next
change.

**Size.** Medium.

### Phase 11. The `strict` tier

**Goal.** The third level of ceremony, for a change of many capabilities, high regression risk or an owed audit
trail. Today `strict` is read as `standard`.

**Features it adds.** As the report describes the tier: the standard tier, plus a design that is always owed, a
checklist a reviewer owns, no critical finding allowed, and a second approver recorded.

**By the end of this phase, you can:** mark a risky change `strict` and have adk-spec refuse to approve or archive
it until two people have approved it and nothing critical stands.

**Depends on.** A real change that needs it, in the report's words. **Size.** Medium.

## The owner's, outside any phase

- A smoke run on the Gemini arm. It needs a `GOOGLE_API_KEY`.
- The gate on a Windows machine. The CI workflow has a Windows job, and the repository has no remote.
- Plan 4's Task 4: one live `propose` and a 25-call measurement, on a go-ahead.
- Every live model call: each needs a go-ahead in so many words.
