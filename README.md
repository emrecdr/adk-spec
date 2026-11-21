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
- `status` lists each open change and what to do next with it.
- `rebase` records the fingerprint each modified or removed requirement has in the living spec now.
- `approve` records who approved, when, and the fingerprint of each file. A later edit voids it; ticking a task does
  not. The name is a recorded claim, not an authentication.
- `archive` folds an approved change's deltas into the living specs, all of them or none.

### A change from start to finish

This is the `lean` tier, which needs one approval. A `standard` change also waits for `verify`, which comes later.

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

Two commands draft with a model:

```
uv run adk-spec propose "Let users sign in with a passkey."
uv run adk-spec plan <id>
```

- `propose` drafts a change from a request: its brief and one delta for each capability it touches. A model writes
  each draft; a gate after each stage checks it and asks again at most twice; nothing is written until the whole
  run has ended well. `--tier lean` or `--tier standard` sets the ceremony by hand, `--id` names the change, and
  `--no-input` asks no question. `[limits] max_tokens` in `.spec/config.toml` caps what one command may spend:
  once that much is spent no further call is sent, so a command overshoots by its last call at most.

- `plan` drafts a draft change's tasks, and first its design where the brief says one is owed. It refuses a change
  whose brief or deltas have an error, and one that is approved already.

On the standard tier `propose` puts each point the brief leaves open to you as a question, at most five a round and
three rounds, each with a suggested answer. A line answers, `=` takes the suggestion, and an empty line leaves the
point open, in which case approval waits until you settle it in the brief. A round you answer nothing in ends the
asking, and the brief is kept as it stood. The `tokens` line counts each stage's calls, the asked-again ones too.

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

## Notes for each system

- Windows: set `PYTHONUTF8=1` in the user environment. LiteLLM may otherwise read its own files as cp1252.
- Windows on ARM64: set `UV_PYTHON_ARCH=x86_64`. LiteLLM ships no wheel for native ARM64.
- macOS: install the Xcode Command Line Tools while `google-adk` is 2.14.1. `watchdog` 6.0.0 builds from source on
  Python 3.14.

## Where things are

- `reports/Spec driven framework on Google ADK.md`: the research this project rests on.
- `docs/superpowers/plans/`: the implementation plans.
