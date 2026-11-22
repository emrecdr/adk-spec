# Brownfield, part 2: context across repositories, checked by a model

Design for phase 7 of adk-spec. Written on 22 November 2026.

**What the owner said, and when.**

- 22 November 2026, after phase 6 was built: "my only concern is, can we get alkl the context by using current
  python codes? because we will work mostly on brownfields, and in many cases more than 1 repo is involved in
  building new features, so gathering context is very imprortant part of the process, so llm model should be
  checking results".
- The same day, to my recommendation that this be the next phase, ahead of the `init` baseline: "proceed as
  recommended".
- Standing: the model points and Python reads (phase 6); reading the code happens inside `propose`, with no command
  of its own; the golden rule of few commands and simple flows.

Three decisions are the owner's and are marked **Owner** below, each with a recommendation. Everything else is the
builder's call, listed at the end.

## Intent, and why

Phase 6 reads one repository: the one that holds `.spec/`. A feature that changes an API and the web app calling it
is planned from half of its code. And a reading ends when its rounds run out, with nothing to say whether what was
read is enough, or what is still not known.

This phase makes the reading cover every repository a feature spans, and has a model check the reading: whether
each statement says what its code shows, and what is still unknown. Both go into `context.md`, where the person and
the planning stages read them.

## What the research says

- **OpenSpec** spans repositories with "stores" (beta): its specs and changes move to a repository of their own
  that several code repositories share. Reading the other repositories' code is left to the editor ("so your agent
  can read both, see Worksets"). Nothing records which repositories a change touches, or checks what was read.
  Source: https://openspec.dev/docs/stores.
- **Spec Kit** has no such feature. One user ran it in an editor workspace of five sibling repositories, and the
  assistant "discovered the radius repository autonomously" and named real paths. Nothing checked them. Source:
  https://github.com/github/spec-kit/discussions/1119.
- **Neither checks what was read.** That remains what adk-spec adds: a statement counts only where code found its
  quote, and now a second model reads the statements as a reviewer.

## Goals

1. Other repositories are named once, in `.spec/config.toml`, and every reading covers them with the same rules as
   the first repository.
2. A statement names its repository, file and line. Its quote is checked in that repository's file.
3. A model reviews each reading: it marks statements whose note the quoted code does not support, which are then
   left out and counted, and it names what is still unknown. It may send the reading one round further.
4. `context.md` says, for each repository, the commit it was read at, and lists what is still unknown.
5. **Owner, recommended yes:** `verify` judges the work in every named repository, from where each one stood when
   the change was first approved.
6. The cost stays bounded and said.

## Non-goals

- Cloning, pulling or fetching a repository. adk-spec reads what is on disk, as OpenSpec does.
- A registry of repositories per machine. See "Left for later".
- Room as a setting. I had said this phase would add one. I recommend against it now: the review's extra round
  gives room where a reading needs it, and the golden rule asks for few knobs. A live measurement decides later.
- Writing to another repository, or any spec kept there.
- The repository baseline inside `init`: phase 8.

## Anti-goals: it has failed if any of these can happen

- A file in another repository is read that phase 6 would not read in the first: ignored, excluded, a link on its
  path, holding a private key, or outside that repository.
- A statement is kept whose quote is not in the file of the repository it names.
- A repository that is missing on this machine stops a plan. It is said, and the plan goes on without it.
- A disputed statement reaches a drafting stage.
- The cost of one reading is open-ended.

## Approaches

| | How | For | Against |
|---|---|---|---|
| **A. adk-spec reads every named repository, and a model reviews the reading** (recommended) | Phase 6's reader, given several repositories; one review stage at the end | One flow, in `propose`; every rule of phase 6 holds in every repository; what the owner asked | More code to read means more tokens |
| B. The person's coding assistant gathers, adk-spec checks | The person has their assistant write `context.md`; adk-spec grounds each statement and has a model review it | Little to build; the assistant may already see every repository | A step outside adk-spec before every plan; a file in a free form to parse; nothing keeps the assistant from reading what `exclude` names |
| C. One reading per repository | Phase 6 run once per repository, one `context.md` each | Simple to build | A feature's seam is where two repositories meet, and no one reading sees both sides |

**Owner, recommended A.** B stays possible in A: a `context.md` a person writes is kept and used, as today.

## How it works

### Naming the other repositories

```toml
[[repositories]]
name = "api"
path = "../api"
exclude = ["fixtures/**"]

[[repositories]]
name = "web"
path = "../web"
```

- `name` is a short word (`a` to `z`, digits, `-`), unique, and not the name of a top-level folder of the
  workspace's own repository, so that `api/src/routes.py` can only mean one file.
- `path` is relative to the folder that holds `.spec/`, or absolute. It must be a git repository's folder, and not
  inside the workspace's own repository nor the workspace itself.
- `exclude` holds patterns read as `[repository] exclude` reads them, from that repository's root.
- A repository whose path is missing on this machine, or is no git repository, is said in one line and left out.

### The reading

The same loop as phase 6, with one reader per repository behind one lookup.

- **The scout** is shown each repository's files under its name. The workspace's own come first, as they are.
- **Paths** of another repository are written `api/src/routes.py`. A path is looked up in the list git gives for
  that repository, and only a path found there is read: the rule of phase 6, per repository.
- **Every rule of phase 6 holds per repository:** git's own list, no link on the path, nothing ignored, its own
  exclusions, secrets scrubbed before anything is cut, no file that holds a private key.
- **A round's caps are shared** by all the repositories: they bound what one model call is shown, and more
  repositories do not make a model's window larger. Each repository's list of files is folded to its folders on its
  own, past 300 paths, so a large repository does not crowd a small one out of the scout's view.
- **Grounding** looks for a statement's quote in the text of the file it names, in the repository it names.

### The review

A new stage, after the last round of reading. It reads the brief, the deltas, and the statements kept, each with its
number, its quote and its note. It reads no file, so it is cheap: statements, not code. It answers:

- `disputed`: each a statement's number and a reason, where the quoted code does not support the note. Code drops
  a disputed statement that names a kept number, and counts it. A number that names nothing is ignored.
- `unknown`: what the change needs to know and the reading did not establish, each a question and where it might
  be answered. At most eight, on one line each.
- `more_files`, `more_folders`, `more_searches`: what to read to answer an unknown.

Where the review asks for more, one more round is read and surveyed, beyond the three rounds of phase 6, and the
review runs a second and last time on the whole. That round is the room a reading gets where it needs it. So one
reading is at most seven model calls: one scout, four surveys, two reviews.

**Owner, recommended "say, do not stop":** an unknown is written to `context.md`, shown to the design and tasks
stages ("do not plan on it as if it were known; where a task depends on one, the task says so"), and counted in what
`propose` prints. `propose` does not stop on it. The other way, `propose` would stop before the plan, as it does on
an open point of the brief, and ask the person: safer, and one more stop in the flow.

### `context.md`

```markdown
# Context: passkeys

Read on 2026-11-22: this repository at commit 1a2b3c4, api at 9f8e7d6, web at 5a4b3c2.

## What exists
- `api/src/auth/session.py:41` Sessions are created by `start_session(user)`.
  > def start_session(user: User) -> Session:
...
## What is still unknown
- Does the mobile app call the sign-in endpoint too? Look in: a repository not named here.

## What was read
...
Left out: 2 statements whose quote was not in the file named; 1 the review disputed.
```

### What a person sees

```
explored  9 files in 3 repositories: 14 statements kept, 3 left out, 2 unknown
```

and, where something is unknown, `propose`'s "read first" line names `context.md` with that count.

### `verify` across repositories (Owner, recommended in this phase)

Without it, a requirement met in the API repository reads as unmet, and a feature that spans repositories cannot
pass `verify` without a person overriding it: the four-command flow breaks for the case the owner calls common.

- Each approval records where each named repository stands, where none is recorded yet, as it does today for the
  workspace's own commit: a recorded one is never moved past work already done. A repository missing on disk at an
  approval is said, and recorded at a later one.
- `verify` reads each repository's diff from its own recorded commit, with paths written `api/…`, the key rule and
  the exclusions applied per repository, and one fingerprint over all of them.
- `--base` names where the work began, as today, and also takes `api=REF` for another repository, as often as
  needed. It is the way to give a repository whose starting point was not recorded, or was recorded too late: one
  named after the work in it began. No new flag.
- A named repository that is missing at `verify`, or has no starting point, is refused by name, with the way out:
  work cannot be judged on part of it. `--override` records a person's verdict over that, as today.
- The size cap holds over the diffs together. `--base` with a later commit, for any repository, is how a change too
  large for one call is narrowed, as today.

## Constraints

- No subcommand, and no flag beyond what exists.
- The layers keep their one-way imports. Reading files and running git stay in `workspace/`.
- macOS and Windows. A `path` with backslashes is read as a path on Windows.
- No live model call in the build. The plan's last task holds the live steps, each on the owner's go-ahead.
- The fake model drives every test, with two or three small repositories made in a temporary folder.

## Cost, said plainly

A reading of one repository costs what it does today, plus one or two review calls on statements alone, a few
thousand tokens, and at most one more round where the review asks for it. A reading of three repositories shows the
scout three lists of files, and a round's caps are shared, not tripled. So more repositories means a wider choice in
the same room, not three times the cost. `max_tokens` holds it.

## Decided by the builder, for the owner to check

1. The other repositories are named in the workspace's committed config, with paths relative to it: teams that
   clone side by side share one config. A machine where a path differs is told so and reads without that repository.
2. A repository's name prefixes its paths, and may not be a top-level folder of the workspace's repository.
3. The review reads statements, not code, and runs at most twice.
4. A disputed statement is left out, as one whose quote is not found, and counted apart from those.
5. Unknowns are at most eight, plain text, and are not grounded: they name an absence.
6. No setting for room in this phase.
7. The review is a stage with its own role, so it can run on a stricter model than the survey, as every stage can.
8. A round's caps are shared by the repositories, each repository's file list folds on its own, and the review's
   round is one beyond the three.
9. Starting points are recorded at every approval where missing, and `--base api=REF` gives one by hand.

## Left for later

- Paths per machine, for a team whose checkouts differ: a local file beside the config that git ignores.
- An unknown asked of the person, where it is one only the person can answer.
- `check` reading `context.md`, to find a task that names a file no repository holds.
- Room as a setting, after a live measurement.

## How it is proven

- Offline, on the fake model: a workspace and two other repositories in a temporary folder. Covered: a path in each
  repository, a name that is also a folder, a missing repository, an excluded path per repository, a link on the
  path in another repository, a key file there, a disputed statement, a review that asks for more and its last
  round, the six-call bound, and `verify` over two repositories with one missing.
- A new labelled case, `across`: an API repository and a web repository, the integration point in the API and a
  decoy in the web app, scored on whether a kept statement names the right file in the right repository.
- Live, on the owner's go-ahead: that case several times, and one reading of the owner's own repositories.
