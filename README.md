# adk-spec

Spec-driven development on Google ADK. Models draft the specs and judge them; Python owns the files, the IDs, the
gates and the merge into one living spec per capability.

## Install

```
uv sync --locked
```

## The gate

Run before every commit, one command a line:

```
uv run ruff check .
uv run ruff format --check .
uv run pyrefly check
uv run pytest -q
```

## The flow

One change takes four commands, one for each decision you make. What the tool can do by itself happens inside them.

```
adk-spec propose "Let users sign in with a passkey."
adk-spec approve <id>
adk-spec verify <id>
adk-spec archive <id>
```

| Command | The question it answers | What happens inside |
|---|---|---|
| `propose` | What do we want to build? | Sizes the request, asks its questions, writes the brief and the specs, reads the code that matters for them, and writes the design where one is owed, and the tasks |
| `approve` | Do I agree with this plan? | Records what the change is written against, checks the files against each other, stops on anything blocking, then records your approval |
| `verify` | Is it built? | Judges what changed in the repository against each requirement. Run it as often as you like while implementing |
| `archive` | Make it the record? | Folds the change into the living specs, all of it or none |

Once for a repository: `adk-spec init`. At any time: `adk-spec status`, which says what to do next. `propose`,
`approve` and `verify` end on a `next` line that says the same.

Between `propose` and `approve` you read what was drafted and edit it: the files are yours. `propose` names what
to read first. Between `approve` and `verify` you implement the tasks, with the coding agent you use, ticking each
box. `adk-spec` writes specs and plans and judges the result. It does not edit your code.

A small change is `lean`: it owes no check and no verification, so it takes three commands, `propose`, `approve`,
`archive`. `propose` sizes a request itself; `--tier lean` or `--tier standard` says it by hand.

### What each command does

- **`propose`** drafts a change from a request. A model writes each part; a gate after each stage checks it and
  asks again at most twice. On the standard tier it puts each point the brief leaves open to you as a question, at
  most three a round and three rounds, each with a suggested answer: a line answers, `=` takes the suggestion, and
  an empty line leaves the point open, in which case approval waits until you settle it in the brief.
  `--no-input` asks nothing, and `--id` names the change. Where you leave a question unanswered, `propose` writes
  the brief and the specs and drafts no plan on a guess: settle the point in the brief, then `adk-spec plan <id>`.
  The same command finishes a plan that did not end well.

  In a git repository `propose` reads the code before it drafts the design and the tasks, and writes what it found
  to `context.md` in the change's folder. See "Working in an existing repository" below. `--no-explore` skips it.

- **`approve`** records who approved, when, and the fingerprint of each file. A later edit voids it; ticking a
  task does not. The name is a recorded claim, not an authentication. On a standard change it first makes the
  check, where none is current: code checks structure and that every requirement has a task, and a model looks for
  what takes a reading, such as two files that contradict each other. Each finding must quote the text it is about,
  and one whose quote is not in the file it names is left out. A blocking finding stops the approval: fix it and
  approve again, or approve with `--override "<your reason>"`, which is recorded. An override answers only a finding
  you were already shown, never one of the same run. Where no model is set up, `adk-spec check <id> --no-model`
  checks by code alone.

- **`verify`** reads what changed in the repository since the change was approved, as one diff: tracked files, and
  files git does not track yet and does not ignore. A model gives each requirement a verdict, `met`, `unmet` or
  `unclear`, and quotes the lines that show it. Code keeps a `met` only where a quoted line is really in the diff.
  Anything else is `unclear`, so a missing or an invented piece of evidence never reads as a pass. A change is
  verified where every requirement is shown met, or where you say so with `--override "<your reason>"`. `verify`
  needs a git repository and reads it only; `--base <ref>` names another commit to start from.

- **`archive`** folds the change's deltas into the living specs. A standard change is archived only once verified.
  If the living spec changed under a requirement the delta touches, the archive stops and writes nothing: read the
  current requirement, update the delta, then run `adk-spec rebase <id>` and approve again.

- **`status`** lists each open change and what to do next with it, in groups: `Waiting on you`, `Ready to run`,
  and with `--all` `Done`.

- **`init`** makes `.spec/` with a config, a constitution to fill in, and the folders for specs and changes.

### Working in an existing repository

Before `propose` or `plan` drafts a design and tasks, it reads the code that matters for the change, so that both
rest on what is there and not on file names.

- **How it reads.** A model names what it wants to see: files, folders to list, words to search for. Code reads
  them, and only where git lists the path: nothing git ignores, nothing outside the repository, never a symbolic
  link. A second model call states what the text shows. It may ask to see more, three rounds at most.
- **What you get.** `context.md` in the change's folder, in four sections: what exists, where the change plugs
  in, conventions to follow, risks. Every statement names a file and a line and quotes the code, and a statement
  whose quote is not in that file is left out and counted. The design and the tasks are drafted from it.
- **It is yours.** Edit `context.md` as you would any file of the change. One that is there is kept and read as it
  stands; delete it and the next `adk-spec plan <id>` reads the code again. It is no part of an approval.
- **What it costs.** Up to four model calls and, at its caps, some 30,000 tokens; far less in a small repository.
  It is the largest part of `propose`. `[limits] max_tokens` holds it, and the `tokens` line shows it.
- **It never stops a plan.** A reading that fails or finds nothing says so in one line, and the plan is drafted
  without it.

To keep paths out of every command, name them in `.spec/config.toml`. A pattern with no slash, such as `*.pem` or
`secrets`, names a file or a folder at any depth. One with a slash, such as `vendor/**`, is a path from the folder
that holds `.spec/`. Letters match in either case. An excluded path is never read, never listed among the repository's files, and
never part of the diff `verify` sends, so work done only there is no evidence for `verify`. A `context.md` written
before a path was excluded still holds what it quoted from it: delete the file to read again.

A file that holds a private key is treated as an excluded path is, with nothing to set up: it is never read, and
`verify` leaves its changes out and says so.

```toml
[repository]
exclude = ["vendor/**", "**/*.pem", "config/production.yaml"]
```

### To redo one step

You never need these in a normal change. Each does one step of the flow again, by itself.

```
adk-spec plan <id>
adk-spec check <id>
adk-spec rebase <id>
adk-spec validate
adk-spec new <id> --tier lean
```

- `plan` drafts a change's tasks again, and its design where one is owed, after you edited the brief or the specs.
  Where a task is already ticked it replaces nothing unless you add `--replace`. It reads the code first where the
  change has no `context.md`; `--no-explore` skips that.
- `check` makes the check `approve` makes, and writes `reports/check.md`, without approving.
- `rebase` records anew what a change's deltas are written against, after a living spec moved under them.
- `validate` checks the structure of the living specs and of every open change. `--strict` fails on a warning too.
- `new` starts a change you write by hand: `brief.md`, `tasks.md`, and one `specs/<capability>/spec.md` for each
  capability it touches, with whole requirement blocks under `## ADDED Requirements`, `## MODIFIED Requirements`
  and `## REMOVED Requirements`. Then `approve` and `archive` as above.

### Setup

```
adk-spec login
adk-spec models
adk-spec smoke
```

- `login` logs in to GitHub Copilot once, with GitHub's device flow.
- `models` lists the models the chosen arm serves. It only reads the provider's list and calls no model.
- `smoke` runs one stage alone, to prove the chosen arm answers in a schema. `smoke --check` says whether the arm
  is ready and sends nothing.

### What a command costs, and what it sends

`propose`, `verify`, `plan` and `check` call a model, and `approve` does where a standard change's check is not
current. `[limits] max_tokens` in `.spec/config.toml` caps what one command may spend: once that much is spent no
further call is sent, so a command overshoots by its last call at most, and `propose` asks no question whose answer
it could not use.

```toml
[limits]
max_tokens = 30000
```

On a terminal a command says which stage it is on while it works. Every command that calls a model keeps what it
sent and what came back under `.spec/runs/`, which ignores itself for git: one file a model pass, so a `propose`
leaves up to three, its own, its reading of the code and its plan's. The newest 20 are kept, and
`[limits] keep_runs` changes that.

What a model is sent is what the command reads: your request, your specs and the change's files, the names of the
repository's files, the parts of your code the reading asked for, and for `verify` the diff of your working tree.
No key or token of the provider is ever part of it.

Every request is scrubbed of known secret shapes before it is sent or recorded: vendors' keys and tokens, private
key blocks, passwords in URLs, and values a name says are secret. If the scrub fails, nothing is sent. It knows
shapes, not secrets, so it is a net and no guarantee: keep secrets in files git ignores, and name anything else
that must not leave under `[repository] exclude`.

## Watching a run in ADK's own interface

`adk_spec/agent.py` is the shape ADK's interface loads. From inside a repository that holds `.spec/`, run
`uv run --project <this checkout> adk web --no_use_local_storage <this checkout>` and choose `adk_spec`. One message
you type is one request: it is drafted as `propose --no-input` drafts it, stage by stage in the event view, and the
chat ends on the drafts. Nothing is written to `.spec/` and no question is asked. Without `--no_use_local_storage`,
ADK keeps each session, the code a reading showed included, in a `.adk` folder of the checkout. The commands are
the product; this is for watching.

## Measuring the model's stages

`uv run python -m scripts.measure` builds seven small changes, runs `check`, `verify` or `plan` on each a few
times on the arm your environment names, and reports how often each planted fault was caught, and whether the
reading of the code named the place a change plugs in. It calls a model: about eight calls a run of the set, and
it says the number before the first. `docs/measurements/README.md` says what each case plants.

`uv run python scripts/dump_instructions.py` prints every stage's instruction, to compare before and after a change
to one.

## Notes for each system

- Windows: set `PYTHONUTF8=1` in the user environment. LiteLLM may otherwise read its own files as cp1252.
- Windows on ARM64: set `UV_PYTHON_ARCH=x86_64`. LiteLLM ships no wheel for native ARM64.
- macOS: install the Xcode Command Line Tools while `google-adk` is 2.14.1. `watchdog` 6.0.0 builds from source on
  Python 3.14.

## Where things are

- `reports/Spec driven framework on Google ADK.md`: the research this project rests on.
- `docs/superpowers/plans/`: the implementation plans.
