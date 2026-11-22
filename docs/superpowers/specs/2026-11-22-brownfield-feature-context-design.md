# Brownfield, part 1: context for one feature, read from the repository's code

Design for the brownfield phase of adk-spec, now phase 6. Written on 22 November 2026.

**Status: to be revised before its plan is written.** After it was written the owner set a golden rule (few
subcommands, simple flows) and the simple flow became phase 5. What changes here, and nothing else:

1. There is no `explore` command. The reading happens inside `propose`, before the brief, and `--no-explore` skips
   it. Everything below about what is read, how it is checked and what `context.md` holds stands.
2. In a repository past 300 files the scout is shown folders and not files, so it may also name folders to list.
   That makes four model calls at most, not three.
3. The exclusion setting holds for every command that sends anything of the repository, not for the reading alone.
4. A later stage takes `context.md` as its file stands. The check of quotes is made when the file is written.
5. An exploration that ends early writes what it kept so far and says that it is partial.

Points 2 to 5 answer the questions a reviewer raised when reading this design as its builder.

## Intent, and why

A person starts a feature in a repository that already holds code. Today adk-spec shows a model the **paths** of
that repository's files, in `plan`, and nothing of their contents. So a design and a task list can name real
files, and cannot know what is in them: what already exists, where the feature plugs in, how this repository does
things.

The owner's words (22 November 2026): "if i am working on a new feature on existing repo, a brownfield project,
can i provide the repo as context to analyze for about planning preparing new feature implemenattion plan?" and
"brownfield repo analyze is important big part of the project, make sure it is handled properly".

This phase makes the answer yes: adk-spec reads the code that matters for one change, writes down what it found
with a quoted line for every statement, and the design and the tasks are drafted from that.

It was always meant to be there. The research report's version 1 has a stage "Explore existing code", whose notes
feed the drafting stages; plans 1 to 3 did not build it.

## What the research says

- **Neither parent framework does this.** Spec Kit "does not rewrite your application or infer specifications for
  existing behavior", and a reverse-engineering command is its most requested missing feature. OpenSpec is
  brownfield-first through deltas, and has an `explore` step that is a stance for a coding agent, not a product.
- **The known weakness is invented context.** A published comparison notes that delta specs assume the model
  understands the unchanged code, so a poorly documented project risks hallucinated context. A field report on Spec
  Kit found that the agent "defaults to common conventions unless the project's architecture is spelled out".
- **The reference project has solved the dangerous parts.** `adk_review` scrubs known secret shapes from every
  request a model is sent, by a plugin that fails closed, and treats every argument a model chooses as untrusted.

Sources: `reports/Spec driven framework on Google ADK.md`, and in the research notes `speckit_internals.md`,
`openspec_internals.md` and `sdd_comparison_and_critique.md`.

## Goals

1. `adk-spec explore <id>` reads the repository for one draft change and writes `context.md` in the change's folder.
2. Every statement in `context.md` names a file and quotes text that code found in that file. A statement whose
   quote is not there is left out and counted.
3. `plan` shows `context.md` to the design and tasks stages, so both rest on what the code is.
4. Nothing leaves the machine that should not: only files git tracks or would track are read, a person can keep
   folders out, and known secret shapes are scrubbed from every model request of every command.
5. The cost is bounded and said: a fixed number of model calls, a fixed number of characters read, counted by the
   ledger and held by `[limits] max_tokens` as every other command is.

## Non-goals

- A baseline of the whole repository: its stack, its structure, which folders belong to which capability, a
  constitution drafted from what is already true. That is phase 6, and it makes this phase cheaper and better.
- Living specs written from existing code (reverse engineering).
- `propose` reading the code before it writes the brief. See "Left for after the first measurement".
- Editing application code, running the project's tests, or running any command of the project's.
- Understanding a language: no parser, no import graph. Files are text.

## Anti-goals: it has failed if any of these can happen

- A statement about the code reaches a drafting stage with nothing in the code behind it.
- A file git ignores, a file outside the repository, or the target of a symbolic link is read.
- A known secret shape in a tracked file is sent to a provider or kept in a recording.
- The cost of one exploration is open-ended.
- A failed exploration stops a person from planning. `plan` works without `context.md`, as it does today.

## Approaches

Three ways to read the code were put to the owner on 22 November 2026.

| Approach | What it is | Why it was or was not chosen |
|---|---|---|
| **The model points, Python reads** (chosen) | One stage names files and search words. Code reads them. A second stage writes statements that each quote a line, and code keeps only those whose quote is in the file. It may ask to look again, a fixed number of times. | Bounded cost. Every statement is checked. It uses the stage shape, the gates, the recorder, the ledger and the fake model that every other command uses. A model's choice of path is checked against a list before anything is read. |
| An explorer agent with read-only tools | A model with list, read and search tools wanders freely and writes notes. The report's first sketch. | Open-ended cost. Free-form notes cannot be held to the code the same way. A schema combined with tools is unproven on Copilot, where it runs through two different mechanisms depending on the model. |
| Code picks, no model | Python selects files by a folder map and by words of the request. | Cheapest, and blind in a repository with no map yet. It becomes a first step of the chosen approach in phase 6, when the map exists. |

The owner also chose the order: this per-feature context first, the repository baseline second.

## How it works

```
adk-spec explore <id>
   scout    (model)   reads: the brief, the deltas, the rules, the repository's paths
                      names: files to read, words to search for
   gather   (code)    checks each path against git's list, reads within the caps, runs the searches
   survey   (model)   reads: what was gathered, and the statements kept so far
                      writes: statements, each with a file and a quote; and what to look at next
   ground   (code)    keeps a statement only where its quote is in the file it names
   ... gather and survey once more, where the survey asked and a round is left
   write    (code)    context.md
```

### The command

`adk-spec explore <id>` works on a draft change that has a brief. It needs a git repository, as `verify` does. It
writes `context.md`, and replaces one that is there only with `--replace`. It prints what it wrote, how many
statements it kept and left out, which files it read, and the `tokens` line.

`status` names it as the step to run for a draft change with a brief, no tasks and no `context.md`, in a git
repository that holds files. It is never required: `plan` runs without it, and says in one line that the plan
rests on file names alone.

### The two stages

Both are the shape every stage has: an `LlmAgent` with an instruction built from state, a Pydantic `output_schema`,
no tools, behind a gate that asks again at most twice.

- **`scout`** answers with `files` (paths, each optionally with a line range, `src/app.py:120-260`), `searches`
  (words or phrases) and one sentence of `reason`.
- **`survey`** answers with `statements`, and with `more_files` and `more_searches`. A statement holds a `kind`, a
  `file`, a `quote` copied word for word, and a `note` of one or two sentences.

The four kinds, which are also the sections of `context.md`:

| Kind | What it says |
|---|---|
| `exists` | Behaviour or code already there that the change builds on, or must not write a second time. |
| `touches` | Where the change plugs in: code that would be called, extended or changed. |
| `convention` | How this repository does a thing that new code should follow: where tests live, how errors are raised, what a module is named. |
| `risk` | What the code leaves unclear, or what the change could break. |

### What code does between them

- **A path is checked before anything is read.** The model's path must be, to the letter, one of the paths git
  lists for the repository (tracked, or untracked and not ignored, never under `.spec/`). Anything else is dropped
  and named in the output. This one rule is what keeps a file's text, or a request's, from steering the tool to
  another file.
- **A symbolic link is never read.** It is named as left out.
- **Only text.** A file that is not UTF-8 is left out and named.
- **A person's own exclusions.** `[explore] exclude` in `.spec/config.toml` holds globs, read as `.gitignore` reads
  one, of paths that are never read and never listed, tracked or not.
- **A search is a fixed string.** Code runs it with `git grep`, never as a pattern and never through a shell.
- **Grounding.** A statement is kept only where its quote, at least 8 characters, is found in the text of the file
  it names as that text was shown, with runs of white space read as one space. This is the rule `check` and
  `verify` already hold a model to, and the same code.

### The caps

Provisional, as the context limits are, until a live run measures them. All are constants in one place.

| Cap | Value |
|---|---|
| Files a round | 12 |
| Searches a round | 6 |
| Lines a search returns | 20, each cut at 200 characters |
| Characters of one file | 12,000, then the cut is said, with the file's number of lines |
| Characters gathered a round | 40,000 |
| Rounds | 2: the scout's, and one more the survey may ask for |
| Statements kept | 40 |

So one exploration is three model calls at most beyond a gate's asking again: one scout, two surveys.

### `context.md`

Written by code from the kept statements, and a person's to edit afterwards, as every file of a change is.

```markdown
# Context: passkeys

Read from the repository at commit 1a2b3c4 on 2026-11-22, for the brief as it stood then.

## What exists

- `src/auth/session.py:41` Sessions are created by `start_session(user)`, which every sign-in path calls.
  > def start_session(user: User) -> Session:

## Where the change plugs in
...
## Conventions to follow
...
## Risks and what is unclear
...

## What was read

- src/auth/session.py (whole)
- src/auth/password.py (lines 1 to 240 of 612)

Left out: 2 statements whose quote was not in the file named. Not read: `config/secrets.yaml` (excluded).
```

It is supporting material, like a report: no part of an approval, and editing it voids none.

### What `plan` does with it

The design and tasks stages gain one section, "What the repository already holds", which is `context.md` as
text between the markers every untrusted text stands between. Their guides gain one sentence each: name the files
and follow the conventions the context gives, and add nothing to it. No other stage's instruction changes.

### Secrets

A port of `adk_review`'s `scrub` and of its plugin, first in every app's roster: each request's instruction and
content are scrubbed of known secret shapes before the recorder reads them and before anything is sent. If the
scrub fails, the call is refused. This covers every command, `verify`'s diff included, which is sent as it stands
today.

A statement that quotes a scrubbed line does not ground, since the file holds the secret and the model saw
`[REDACTED]`. It is left out, which is the safe side.

## Constraints

- The layers keep their one-way imports. Reading files and running git stay in `workspace/`; the graph is handed a
  reader and never touches a path itself.
- Only `workspace/git.py` runs a subprocess.
- macOS and Windows. Paths are compared and shown with forward slashes.
- No live model call in the build. The plan's last task holds the live steps, each on the owner's go-ahead.
- The fake model drives every test, the exploration loop included.

## Decided by the builder, for the owner to check

Each is my call, not something the owner said.

1. **Its own command, not folded into `plan`.** A person can read and correct `context.md` before a design is
   drafted from it, and `plan` keeps its cost. The other way, `plan` exploring by itself, saves a step and hides one.
2. **Scrubbing applies to every command**, not to `explore` alone. It changes what `propose`, `plan`, `check` and
   `verify` send where a known secret shape stands in their input.
3. **`context.md` is no part of an approval.**
4. **The four kinds and the caps above.**
5. **A file that is not UTF-8 is left out.** A Windows repository with cp1252 or UTF-16 sources loses those files
   from the context, and is told so.
6. **Lean and standard changes explore alike.** The tier changes ceremony, not what the code is.

## Cost, said plainly

Today a `propose` and a `plan` together spend some 3,000 to 10,000 tokens. One exploration reads up to 80,000
characters of code, about 20,000 tokens, over three calls. It is the most expensive command, by several times.
`[limits] max_tokens` holds it as it holds the others, and the caps are constants a later change can make settings.

## Left for after the first measurement

- **`propose` exploring before the brief**, so the brief's scope and its questions know the code. It doubles the
  places an exploration runs, and whether exploring from a request alone finds the right files is a question a
  measurement should answer first.
- **`check` reading `context.md`**, to find a task that names a file the repository does not hold.
- Whether two rounds are enough, and whether the design and tasks stages should also be shown the code itself
  and not only the statements about it.

## How it is proven

- Offline: the suite, on the fake model, with small git repositories made in a temporary folder. It covers a path
  outside git's list, a link, an ignored file, an excluded glob, a quote that is nowhere, a spent ceiling, and a
  secret in a tracked file.
- A new case in the labelled set: a small repository with one planted integration point and one decoy, scored on
  whether a kept statement names the right file.
- Live, on the owner's go-ahead: the case above several times, and one exploration of a real repository of the
  owner's choice, read by hand.

## What is left to the builder

Module and function names, the wording of the two instructions, the layout of the command's output, and how the
tests are split. The plan settles them.
