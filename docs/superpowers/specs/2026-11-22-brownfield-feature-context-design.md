# Brownfield, part 1: the plan of a change rests on the repository's code

Design for phase 6 of adk-spec. Written on 22 November 2026 and revised the same day, after the owner's golden
rule (few subcommands, simple flows) and after phase 5 made `propose` write the whole change.

**What the owner decided, and when.**

- 22 November 2026: brownfield analysis is "important big part of the project, make sure it is handled properly".
- The same day, of three ways to read the code: **the model points, Python reads**. And of the order: **context for
  one feature first**, the repository baseline second.
- The same day, the golden rule, and "proceed as recommeded" on a flow in which reading the code happens inside
  `propose`, with no command of its own.

Everything else below is the builder's call and is listed at the end for the owner to check.

## Intent, and why

A person starts a feature in a repository that already holds code. Today adk-spec shows a model the **paths** of
that repository's files, when it drafts the plan, and nothing of their contents. So a design and a task list can
name real files, and cannot know what is in them: what already exists, where the feature plugs in, how this
repository does things.

The owner's words: "if i am working on a new feature on existing repo, a brownfield project, can i provide the
repo as context to analyze for about planning preparing new feature implemenattion plan?"

This phase makes the answer yes, with no new command: before `propose` drafts the design and the tasks, adk-spec
reads the code that matters for the change, writes down what it found with a quoted line for every statement, and
the design and the tasks are drafted from that.

## What the research says

- **Neither parent framework checks what it read.** OpenSpec's `propose` has inspected "relevant implementation,
  nearby tests, configuration, and documentation" before drafting since its version 1.12.0, and keeps no record of
  it. Spec Kit "does not rewrite your application or infer specifications for existing behavior".
- **The known weakness is invented context.** A published comparison notes that delta specs assume the model
  understands the unchanged code, so a poorly documented project risks hallucinated context.
- **The reference project has solved the dangerous parts.** `adk_review` scrubs known secret shapes from every
  request a model is sent, by a plugin that fails closed, and treats every argument a model chooses as untrusted.

Sources: `research_notes/Simple command flows in spec tools/openspec_command_flow.md`, and in
`research_notes/Spec driven framework on Google ADK/`: `speckit_internals.md`, `sdd_comparison_and_critique.md`.

## Goals

1. Where `propose` writes a plan, it first reads the code that matters for the change, and writes `context.md` in
   the change's folder. `plan` does the same for a change that has none.
2. Every statement in `context.md` names a file and quotes text that code found in that file. A statement whose
   quote is not there is left out and counted.
3. The design and the tasks stages are shown `context.md`, so both rest on what the code is.
4. Nothing leaves the machine that should not: only files git tracks or would track are read, a person can keep
   paths out of every command, and known secret shapes are scrubbed from every model request of every command.
5. The cost is bounded and said: a fixed number of model calls and of characters read, counted by the ledger and
   held by `[limits] max_tokens` as everything else is.

## Non-goals

- A baseline of the whole repository. That is phase 7, inside `init`.
- Living specs written from existing code.
- The brief and the specs reading the code. See "Left for after the first measurement".
- Editing application code, or running any command of the project's.
- Understanding a language: no parser, no import graph. Files are text.

## Anti-goals: it has failed if any of these can happen

- A statement about the code reaches a drafting stage with nothing in the code behind it.
- A file git ignores, a file outside the repository, or the target of a symbolic link is read.
- A known secret shape in a tracked file is sent to a provider or kept in a recording.
- The cost of one reading is open-ended.
- A reading that fails stops the plan. The plan is drafted without it, as today, and the command says so.

## Where it happens

```
adk-spec propose "..."
   triage, brief, questions, specs          as today
   -- the change is written --
   explore                                  new: reads the code for this change, writes context.md
   design, tasks                            as today, with context.md in front of them
```

It sits in the part of `propose` that phase 5 added, the plan, and so in `adk-spec plan <id>` too. That place has
three properties the place before the brief does not:

- The scout knows the brief and the specs, with the person's answers in them, so it names files for the change
  that was agreed and not for a first reading of the request.
- A request that owes no spec, and a change with a question left open, read nothing: `propose` stops before the
  plan in both.
- A reading that fails leaves a written change, and the plan is drafted without it.

It is skipped where there is nothing to read (no git repository, or no file beside `.spec/`), where the change
already has a `context.md` (a person's edits are kept; deleting the file reads again), and with `--no-explore` on
`propose` or `plan`.

## How it works

```
scout    (model)   reads: the brief, the specs, the rules, the repository's paths
                   names: files to read, folders to list, words to search for
gather   (code)    checks each path against git's list, reads within the caps, lists, searches
survey   (model)   reads: what was gathered, and the statements kept so far
                   writes: statements, each with a file and a quote; and what to look at next
ground   (code)    keeps a statement only where its quote is in the file it names
... gather and survey again, where the survey asked and a round is left
write    (code)    context.md
```

### The two stages

Both are the shape every stage has: an instruction built from state, a schema for the answer, no tools, behind a
gate that asks again at most twice.

- **`scout`** answers with `files` (paths, each optionally with a line range, `src/app.py:120-260`), `folders`,
  `searches` (words or phrases) and one sentence of `reason`.
- **`survey`** answers with `statements`, and with `more_files`, `more_folders` and `more_searches`. A statement
  holds a `kind`, a `file`, a `quote` copied word for word, and a `note` of one or two sentences.

The four kinds, which are also the sections of `context.md`:

| Kind | What it says |
|---|---|
| `exists` | Behaviour or code already there that the change builds on, or must not write a second time. |
| `touches` | Where the change plugs in: code that would be called, extended or changed. |
| `convention` | How this repository does a thing that new code should follow: where tests live, how errors are raised, what a module is named. |
| `risk` | What the code leaves unclear, or what the change could break. |

### What code does between them

- **A path is checked before anything is read.** The model's path must be, to the letter, one of the paths git
  lists for the repository: tracked, or untracked and not ignored, never under `.spec/`, never excluded. Anything
  else is dropped and named in the output. This one rule keeps a file's text from steering the tool to another.
- **A symbolic link is never read.** It is named as left out.
- **Only text.** A file that is not UTF-8 is left out and named.
- **A folder's listing** is the paths git lists under it, within a cap. In a repository past 300 files the scout is
  shown folders and not files, so a listing or a search is how it finds a file to name.
- **A search is a fixed string.** Code runs it with `git grep`, never as a pattern and never through a shell.
- **Grounding.** A statement is kept only where its quote, at least 8 characters, is found in the text of the file
  it names as that text was shown, with runs of white space read as one space. This is the rule, and the code,
  that `check` and `verify` already hold a model to.

### The caps

Provisional, as the context limits are, until a live run measures them. All are constants in one place.

| Cap | Value |
|---|---|
| Files a round | 12 |
| Folders listed a round | 4, each to 200 paths |
| Searches a round | 6, each to 20 lines of 200 characters |
| Characters of one file | 12,000, then the cut is said, with the file's number of lines |
| Characters gathered a round | 40,000 |
| Rounds of gathering | 3 |
| Statements kept | 40 |

So one reading is four model calls at most beyond a gate's asking again: one scout and three surveys. In a small
repository it is usually two.

### `context.md`

Written by code from the kept statements, and a person's to edit afterwards, as every file of a change is.

```markdown
# Context: passkeys

Read from the repository at commit 1a2b3c4 on 2026-11-22.

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

Left out: 2 statements whose quote was not in the file named.
```

It is supporting material, like a report: no part of an approval, and editing it voids none. The design and tasks
stages take it as the file stands; the check of quotes is made when it is written. A reading that ends early
writes what it kept and says that it is partial.

### What the plan does with it

The design and tasks stages gain one section, "What the repository already holds", which is `context.md` between
the markers every untrusted text stands between. Their guides gain one sentence each: name the files and follow
the conventions the context gives, and add nothing to it. No other stage's instruction changes.

### What a person sees

One more line from `propose`, and one more file in the list:

```
explored  7 files: 12 statements kept, 2 left out
```

### Keeping paths out

`[repository] exclude` in `.spec/config.toml` holds patterns, each read by git as a path from the repository's top
(`vendor/**`, `**/*.pem`, `config/production.yaml`). An excluded path is never read, never listed among the
repository's files, and never part of the diff `verify` sends. So it holds for every command, not for the reading
alone: work done only in an excluded path cannot be evidence for `verify`, and that is said where it happens.

### Secrets

A port of `adk_review`'s `scrub` and of its plugin, first in every app's roster: each request's instruction and
content are scrubbed of known secret shapes before the recorder reads them and before anything is sent. If the
scrub fails, the call is refused. This covers every command, `verify`'s diff included, which is sent as it stands
today.

A statement that quotes a scrubbed line does not ground, since the file holds the secret and the model saw
`[REDACTED]`. It is left out, which is the safe side.

## Constraints

- No subcommand is added.
- The layers keep their one-way imports. Reading files and running git stay in `workspace/`; the graph is handed a
  reader and never touches a path itself.
- Only `workspace/git.py` runs a subprocess.
- macOS and Windows. Paths are compared and shown with forward slashes.
- No live model call in the build. The plan's last task holds the live steps, each on the owner's go-ahead.
- The fake model drives every test, the loop included.

## Cost, said plainly

A `propose` spends some 3,000 to 6,000 tokens today. A reading adds up to 120,000 characters of code over at most
four calls, some 30,000 tokens at the cap and far less in a small repository or for a small change. It becomes the
largest part of `propose`. `[limits] max_tokens` holds it, `--no-explore` skips it, and the `tokens` line shows it.

## Decided by the builder, for the owner to check

1. **The reading sits before the design and the tasks, not before the brief.** The owner asked for the repository
   as context for the implementation plan, and that is what this serves. The reasons are under "Where it happens".
2. **It is on by default** in a git repository that holds files.
3. **A `context.md` that is there is kept.** To read again, delete it.
4. **Scrubbing and exclusions apply to every command**, and change what `plan` and `verify` send.
5. **`context.md` is no part of an approval.**
6. **The four kinds and the caps above.**
7. **A file that is not UTF-8 is left out.** A Windows repository with cp1252 or UTF-16 sources loses those files
   from the context, and is told so.
8. **Lean and standard changes read alike.** The tier changes ceremony, not what the code is.

## Left for after the first measurement

- **The brief and the specs reading the code**, so the scope and the questions know it. Whether a reading from a
  request alone finds the right files is a question a measurement should answer first.
- **`check` reading `context.md`**, to find a task that names a file the repository does not hold.
- Whether three rounds are right, and whether the design and tasks stages should also be shown the code itself.

## How it is proven

- Offline: the suite, on the fake model, with small git repositories made in a temporary folder. It covers a path
  outside git's list, a link, an ignored file, an excluded pattern, a quote that is nowhere, a spent ceiling, a
  reading that fails, and a secret in a tracked file.
- A new case in the labelled set: a small repository with one planted integration point and one decoy, scored on
  whether a kept statement names the right file.
- Live, on the owner's go-ahead: the case above several times, and one reading of a real repository of the owner's
  choice, read by hand.

## What is left to the builder

Module and function names, the wording of the two instructions, and how the tests are split. The plan settles them.
