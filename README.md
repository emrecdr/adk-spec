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
```

- `init` makes `.spec/` with a config, a constitution to fill in, and the folders for specs and changes.
- `new` starts a change: its folder and its state file. The tier is `lean`, `standard` or `strict`.
- `validate` checks the structure of the living specs and of every open change. `--strict` fails on a warning too.
- `status` lists each open change and what to do next with it.

Two commands reach a model provider:

```
uv run adk-spec login
uv run adk-spec smoke
```

- `login` logs in to GitHub Copilot once, with GitHub's device flow.
- `smoke` runs the triage stage alone, to prove the chosen arm answers in a schema.

## Notes for each system

- Windows: set `PYTHONUTF8=1` in the user environment. LiteLLM may otherwise read its own files as cp1252.
- Windows on ARM64: set `UV_PYTHON_ARCH=x86_64`. LiteLLM ships no wheel for native ARM64.
- macOS: install the Xcode Command Line Tools while `google-adk` is 2.14.1. `watchdog` 6.0.0 builds from source on
  Python 3.14.

## Where things are

- `reports/Spec driven framework on Google ADK.md`: the research this project rests on.
- `docs/superpowers/plans/`: the implementation plans.
