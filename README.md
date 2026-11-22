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

## Commands

Each runs from any folder of a repository that holds a `.spec` tree. None of these calls a model.

```
uv run adk-spec init
uv run adk-spec new <id> --tier lean
uv run adk-spec validate
uv run adk-spec status
uv run adk-spec rebase <id>
uv run adk-spec approve <id>
uv run adk-spec archive <id>
```

- `init` makes `.spec/` with a config, a constitution to fill in, and the folders for specs and changes.
- `new` starts a change: its folder and its state file. The tier is `lean`, `standard` or `strict`.
- `validate` checks the structure of the living specs and of every open change. `--strict` fails on a warning too.
- `status` lists each open change and what to do next with it, in groups: `Waiting on you` (your work or your
  decision), `Ready to run` (one command), and with `--all` `Done`.
- `rebase` records the fingerprint each modified or removed requirement has in the living spec now.
- `approve` records who approved, when, and the fingerprint of each file. A later edit voids it; ticking a task does
  not. The name is a recorded claim, not an authentication.
- `archive` folds an approved change's deltas into the living specs, all of them or none.

### A change from start to finish

This is the `lean` tier, written by hand: it needs one approval and calls no model. The `standard` tier, with a
model drafting and judging, follows the commands below.

1. `adk-spec init`, once for a repository.
2. `adk-spec new passkeys --tier lean`.
3. In `.spec/changes/passkeys/`, write `brief.md`, `tasks.md` and one `specs/<capability>/spec.md` for each
   capability the change touches. A delta lists whole requirement blocks under `## ADDED Requirements`,
   `## MODIFIED Requirements` and `## REMOVED Requirements`, each keyed by its ID.
4. `adk-spec validate passkeys`, until it lists no error.
5. `adk-spec rebase passkeys`, then `adk-spec approve passkeys`.
6. Implement the tasks, ticking each box.
7. `adk-spec archive passkeys`. If the living spec changed under a requirement the delta touches, the archive stops
   and writes nothing: read the current requirement, update the delta, then rebase and approve again.

`adk-spec status` names the next step at any point.

### A standard change, with a model

1. `adk-spec propose "Let users sign in with a passkey."` drafts the brief and the deltas, asking you about what
   the request leaves open.
2. `adk-spec plan <id>` drafts the tasks, and a design first where the brief owes one.
3. Read what was drafted, and edit it: the files are yours.
4. `adk-spec check <id>` reads the files against each other. Fix what it marks as blocking.
5. `adk-spec approve <id>`.
6. Implement the tasks, with the coding agent you use, ticking each box.
7. `adk-spec verify <id>` judges what changed in the repository against each requirement.
8. `adk-spec archive <id>` folds the change into the living specs.

`adk-spec` writes specs and plans and judges the result. It does not edit your code.

Four commands call a model:

```
uv run adk-spec propose "Let users sign in with a passkey."
uv run adk-spec plan <id>
uv run adk-spec check <id>
uv run adk-spec verify <id>
```

- `propose` drafts a change from a request: its brief and one delta for each capability it touches. A model writes
  each draft; a gate after each stage checks it and asks again at most twice; nothing is written until the whole
  run has ended well. `--tier lean` or `--tier standard` sets the ceremony by hand and saves the call that would
  have sized the request, `--id` names the change, and
  `--no-input` asks no question. `[limits] max_tokens` in `.spec/config.toml` caps what one command may spend:
  once that much is spent no further call is sent, so a command overshoots by its last call at most.
  The first live runs spent about 2,800 tokens on a lean change and 9,600 on a standard one with three rounds of
  questions (`docs/confirmation/2026-11-propose.md`), so this leaves room:

  ```toml
  [limits]
  max_tokens = 30000
  ```

- `plan` drafts a draft change's tasks, and first its design where the brief says one is owed. It refuses a change
  whose brief or deltas have an error, and one that is approved already. In a git repository its stages are shown
  the repository's files, so a task names real paths; a `design.md` you wrote yourself is read by the tasks stage.
  The tasks must serve every requirement the change adds or modifies. Where a task of the list is already ticked,
  `plan` replaces nothing unless you add `--replace`.

- `check` reads a change's files against each other and writes `reports/check.md` in the change's folder. Code
  checks what it can decide: structure, that every requirement the change adds or modifies has a task, and that no
  task names a requirement nothing holds. A model then looks for what takes a reading: two files that contradict
  each other, wording that allows two readings, a promise no requirement keeps, a broken rule of the repository.
  Each of its findings must quote the text it is about, and one whose quote is not in the file it names is left
  out. `check --no-model` runs the code's checks alone.

  A standard change must be checked before it is approved, and a finding marked blocking holds the approval. Fix
  it and check again, or approve with `--override "<your reason>"`, which is recorded in the approval. An edit
  after the check makes it stale. A lean change owes no check.

- `verify` judges the work once it is done. It reads what changed in the repository since the change was approved
  (the commit is recorded at approval; `--base <ref>` names another), as one diff: tracked files, and files git
  does not track yet and does not ignore. A model gives each requirement of the change a verdict, `met`, `unmet` or
  `unclear`, and quotes the lines that show it. Code then keeps a `met` only where a quoted line is really in the
  diff: an added line for a requirement the change adds or modifies, a removed line for one it removes. Anything
  else is `unclear`, so a missing or an invented piece of evidence never reads as a pass. The verdicts are written
  to `reports/verify.md`.

  A change is `verified` where every requirement is shown met, or where you say so with
  `--override "<your reason>"`, which is recorded. A standard change is archived only once verified. `verify`
  needs a git repository and reads it only; it never cuts a diff, and refuses one past 200,000 characters.

On the standard tier `propose` puts each point the brief leaves open to you as a question, at most three a round and
three rounds, each with the answer the brief's own stage suggests. No further model call words them: the brief names
its open points, and code asks them. A line answers, `=` takes the suggestion, and an empty line leaves the point
open, in which case approval waits until you settle it in the brief, where it stands as a
`[NEEDS CLARIFICATION: ...]` line. A round you answer nothing in ends the asking, and the brief is kept as it stood.
Where `[limits] max_tokens` is spent by then, nothing is asked: no answer could be used.
The `tokens` line counts each stage's calls, the asked-again ones too.

Every command that calls a model keeps what it sent and what came back, one file a command, under `.spec/runs/`:
each stage's instruction, its answer as it came, and what a gate found wrong where it asked again. The folder
ignores itself for git. The newest 20 are kept; `[limits] keep_runs` in `.spec/config.toml` changes that, and `0`
keeps none.

What a model is sent, and so what a recording holds, is what the command reads: your request, your specs and the
change's files, for `plan` the paths of the repository's files, and for `verify` the diff of your working tree
against the commit the work began at. No key or token of the provider is ever part of it. A diff holds whatever
changed in files git tracks or would track, so keep secrets in files git ignores: what the repository's
`.gitignore` or your own global ignore file leaves out is never read.

Three more reach a model provider without drafting:

```
uv run adk-spec login
uv run adk-spec models
uv run adk-spec smoke
```

- `login` logs in to GitHub Copilot once, with GitHub's device flow.
- `models` lists the models the chosen arm serves. It only reads the provider's list and calls no model.
- `smoke` runs the triage stage alone, to prove the chosen arm answers in a schema.
  `smoke --check` says whether the arm is ready and sends nothing. `smoke --model <name>` tries one model.

## Watching a run in ADK's own interface

`adk_spec/agent.py` is the shape ADK's interface loads. From inside a repository that holds `.spec/`, run
`uv run --project <this checkout> adk web <this checkout>` and choose `adk_spec`. One message you type is one
request: it is drafted as `propose --no-input` drafts it, stage by stage in the event view, and the chat ends on the
drafts. Nothing is written and no question is asked. The commands are the product; this is for watching.

## Measuring the model's stages

`uv run python -m scripts.measure` builds six small changes, five with one fault planted, runs `check` or `verify`
on each a few times on the arm your environment names, and reports how often each fault was caught. It calls a
model: about five calls a run of the set, and it says the number before the first. `docs/measurements/README.md`
says what each case plants.

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
