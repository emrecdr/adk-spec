# Tests as evidence, inside `verify`

Design for phase 9 of adk-spec. Written on 22 November 2026.

**What the owner decided, and when.** 22 November 2026, in a dialog, both as recommended:

- **The test command is one a person writes in the project's `.spec/config.toml`**, run by every `verify` before the
  model judges; never a command a model drafted. Another repository of a change uses the command in its own
  `.spec/config.toml`, where it has one.
- **A failing test run blocks "verified"**, whatever the model says; `--override` with a reason is the way through.

Everything else is the builder's call, listed at the end.

## Intent, and why

`verify` today judges the work from its diff alone: a model reads what changed and says whether each requirement is
met. A requirement can read as met in a diff whose tests fail. The project's own tests are the stronger evidence,
and the person already has the command that runs them.

## Goals

1. `[verify] test` in `.spec/config.toml` names the command, and `verify` runs it in the workspace's folder before
   the model is asked, saying first what it runs.
2. Each other repository of the change whose own config names a test command has it run in its folder, said first.
3. A run that fails, cannot start or runs past its time makes the change not verified, whatever the verdicts;
   `--override` with a reason verifies it anyway, as today.
4. The model is shown each run's result and the end of its output, scrubbed, as evidence; `reports/verify.md` shows
   them too.
5. No command a model wrote is ever run, and no shell reads the command.

## Non-goals

- Mapping each test to a requirement ID.
- Running tests anywhere but `verify`: not in `check`, not in `approve`.
- A command for each change: the command is the project's.

## Anti-goals: it has failed if any of these can happen

- A command from a change's files, a model's answer or a task's `verify:` line is run.
- A shell reads the command: a quote or a `;` in it does anything but reach the program as written.
- A run that never ends stops `verify` for ever, or leaves a process behind.
- A secret the tests print reaches a model, a recording or the report.
- A change is recorded as verified with a failing run and no `--override`.

## How it works

```toml
[verify]
test = ["uv", "run", "pytest", "-q"]
timeout = 900
```

- `test` is a list: the program and its arguments, as given. A string is refused, with the list to write instead:
  no shell, and no splitting a string by guesswork on Windows.
- The program is found on `PATH`'s absolute entries only, as git is: never in the current folder.
- `timeout` is in seconds, 900 where it is not set. Past it the run is stopped, its whole process tree, and counts
  as failed.
- The run gets the person's own environment and the folder of the repository's workspace. Its output, standard out
  and standard error together, is kept to its last 6,000 characters and scrubbed of secret shapes before anything
  shows it.

```
adk-spec verify passkeys
testing   uv run pytest -q
tests     passed in 12.4 s
testing   api: npm test
tests     api failed (exit 1) in 3.1 s
met       REQ-AUTH-004  ...
wrote     .spec/changes/passkeys/reports/verify.md
next      ... the tests failed: fix them, or `verify --override "<why>"`
```

- The verify stage gains one section, the tests: each run's line and the end of its output.
- The verification record keeps each run's result by repository: `passed`, `failed (exit 1)`, `timed out`, or
  `not run: <why>`. The change is verified only where every requirement is met and every run passed, or a person
  overrides with a reason.
- Without a test command, `verify` runs as today, and the report says no command is set.
- The model is still asked when a run fails: its verdicts say which requirements the work does not show, and that
  is what a person fixes next.

## Constraints

- No subcommand and no flag.
- One module starts processes: `workspace/process.py`, which git and the test run both call. Its stopping of a
  process tree on Windows is git's today, moved.
- No live model call in the build.

## Decided by the builder, for the owner to check

1. `test` is a list, never a string.
2. `timeout` 900 seconds by default; past it, failed.
3. The last 6,000 characters of output, scrubbed, are what the model and the report see.
4. A command that cannot start counts as a failed run.
5. The model is asked even when a run fails.
6. Another repository's command is said before it runs, with the repository's name.

## How it is proven

Offline: a test command that passes, one that fails, one that runs past a short timeout, one that is not found, one
that prints a secret shape; a string refused; another repository's command run in its folder; the record, the
report and the next line; `--override` over a failing run. The tests run small Python programs, not a test runner.
