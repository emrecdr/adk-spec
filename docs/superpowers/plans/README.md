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

### Phase 5. Brownfield, part 1: context for one feature

**Goal.** A design and a task list for a new feature rest on what the repository's code is, not on file names.

**What a person will see.**

- A new command, `adk-spec explore <id>`, run between `propose` and `plan`.
- A new file in the change's folder, `context.md`, in four sections: what exists, where the change plugs in,
  conventions to follow, risks. Each statement names a file and a line and quotes the code. The file is the
  person's to edit.
- `plan` drafting from it. Without it, `plan` works as today and says the plan rests on file names alone.
- `status` naming `explore` as the next step for a draft with a brief and no context.
- A setting, `[explore] exclude`, for paths that must never be read.

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
6. `status`, the README, and a labelled case for the measurement script: a small repository with one planted
   integration point and one decoy.
7. Live, on the owner's go-ahead: that case several times, and one real repository read by hand.

**Depends on.** Nothing unbuilt.

**Cost to a person.** The most expensive command: three or four model calls and up to some 20,000 tokens for one
exploration, where a `propose` and a `plan` together spend 3,000 to 10,000. `[limits] max_tokens` holds it.

**Risks.** A real model quoting loosely, so that true statements are left out. A scout that names the wrong files
in a large repository. Scrubbing that changes what other commands send. Each has a test or a live measurement.

**Open.** The owner's approval of the design.

### Phase 6. Brownfield, part 2: a baseline of the repository

Expected shape; its own design confirms it.

**Goal.** adk-spec knows a repository before the first change: its stack, its structure, its conventions, and which
folders belong to which capability.

**What a person will see.**

- A one-time command, run after `init` on an existing repository.
- A repository profile under `.spec/`: languages and frameworks with their versions, the layout, how the project
  is built and tested, each statement with a quote from a manifest, a README or the code.
- A proposed map from capability to folders, written to the config only when the person accepts it.
- A constitution drafted from rules that are already true of the code, each with its evidence, for the person to
  accept, change or drop. Spec Kit's own advice for an existing project is to write only such rules.

**How it works.** The reading, grounding and scrubbing of phase 5, pointed at the repository as a whole and at its
manifests first. `explore` then starts from the folders of the capabilities a change touches, which is the "code
picks" approach where a map exists.

**Depends on.** Phase 5.

**Size.** Medium to large.

**Risks.** A wrong map misleads every later run, so nothing is written to the config without the person.

**To decide then.**

- Whether `propose` explores before it writes the brief. Phase 5's measurement shows whether a request alone finds
  the right files.
- Whether living specs are drafted from existing code. It is the most requested feature of Spec Kit and the part
  most likely to be wrong; it stays out until the owner asks for it.
- A drift check between living specs and code, the report's sixth migration step, which needs the map.

### Phase 7. Tests as evidence for `verify`

Expected shape; its own design confirms it.

**Goal.** A verdict rests on the project's own tests as well as on the diff.

**What a person will see.** A test command set in `.spec/config.toml`. `verify` runs it, shows which requirements
its results speak for, and judges with that evidence in hand.

**How it works.** Code runs the configured command, as an argument list and never through a shell, with a timeout
and with no provider token in its environment. It maps results to requirement IDs. The model judges what the
evidence leaves open; a `met` still needs evidence code can check.

**Depends on.** Nothing unbuilt.

**Size.** Large.

**Risks.** It is the first phase in which adk-spec runs a command of the project's: a process left running, most of
all on Windows, and a command that should not have been run at all. Only a command the person wrote is ever run;
a model never chooses one.

### Phase 8. Triage by rules

**Goal.** Most requests are sized (lean, standard, none) with no model call.

**How it works.** Rules on measurable inputs, drawn from the recordings of real runs, with the model asked only
where the rules do not decide. It is proven by replaying recorded triage answers against the rules.

**Size.** Small.

### Phase 9. The contradiction pass of `check` in code

**Goal.** What code can decide about two files that disagree is decided by code.

**Depends on.** More measurement, and it may not happen. The two measurements so far show this pass is the least
steady of all: caught in 2 runs of 3, then in 1 of 3. The spec's own rule is that a step moves to code only where
its output is a function of its input with no judgement, and this one may not be.

**Size.** Medium.

### Phase 10. A lessons file

**Goal.** A workspace learns from its own runs.

**What a person will see.** A file under `.spec/` that keeps what a gate sent back and what a person corrected in
a draft. Later drafts read it, within a cap, and the person can edit it.

**Size.** Medium.

### Phase 11. The `strict` tier

**Goal.** The third level of ceremony. The report describes it for a change of many capabilities, high regression
risk or an owed audit trail: the standard tier, plus a mandatory design, a checklist a reviewer owns, no critical
finding, and a second approver. Today `strict` is read as `standard`.

**Depends on.** A real change that needs it, in the report's words.

**Size.** Medium.

## The owner's, outside any phase

- A smoke run on the Gemini arm. It needs a `GOOGLE_API_KEY`.
- The gate on a Windows machine. The CI workflow has a Windows job, and the repository has no remote.
- Plan 4's Task 4: one live `propose` and a 25-call measurement, on a go-ahead.
- Every live model call: each needs a go-ahead in so many words.
