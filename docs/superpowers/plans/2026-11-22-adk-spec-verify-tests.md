# Tests as Evidence Inside `verify`: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `verify` runs the test command a person wrote in `.spec/config.toml`, in every repository of the change
that has one, shows the model and the report the results, and does not record a change as verified while a run
fails.

**Architecture:** A process module holds the one way a process is started and stopped, which git and the test run
share. A test-run module finds the program, runs it with a timeout and keeps the scrubbed end of its output. `verify`
runs each command before the model, passes the results to its stage and to the record.

**Tech Stack:** Python 3.14, uv, pytest, ruff 0.17.5, pyrefly 1.4.1.

**Spec:** `docs/superpowers/specs/2026-11-22-verify-tests-design.md`

## Global Constraints

- No subcommand, no flag. Only `workspace/process.py` starts a process.
- A command is run only from a `[verify] test` list a person wrote; never through a shell.
- No live model call in the build. Offline: `SPEC_PROVIDER=gemini`, `SPEC_MODEL=fake`, `GOOGLE_API_KEY=offline`.
- Gate after each task: `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyrefly check`,
  `uv run pytest -q`.

## Review Focus

1. A test command whose output is huge or never ends: bounded, stopped, the process tree gone. Test in Task 1.
2. A secret the tests print: in no request, recording or report. Test in Task 3.
3. A program name that is a relative path, or found only in the current folder: not run. Test in Task 1.
4. Another repository's test command: said before it runs, run in that repository's folder. Test in Task 3.
5. `verify --override` over a failing run: verified, the reason recorded. Test in Task 3.

---

### Task 1: One way to start a process, and a test run

**Files:** Create `adk_spec/workspace/process.py`, `adk_spec/workspace/tests.py`; modify `adk_spec/workspace/git.py`,
`adk_spec/workspace/config.py`. Test: `tests/test_tests.py` (new), `tests/test_workspace.py`.

**Interfaces:**
- `process.run(argv: list[str], *, cwd: Path, env: Mapping[str, str], timeout: float) -> CompletedProcess[bytes]`:
  git's `_run` moved, its Windows tree kill kept; raises `subprocess.TimeoutExpired` past `timeout`.
- `process.on_path(name: str) -> str | None`: git's, moved; git imports it.
- `Config.test: tuple[str, ...] = ()`, `Config.test_timeout: int = 900`; `[verify]` with `test` (a non-empty list
  of non-empty strings, a string refused naming the list form) and `timeout` (a whole number of seconds, 1 or more).
- `tests.TestRun(name: str, argv: tuple[str, ...], outcome: str, tail: str, seconds: float)` with `passed: bool`;
  `tests.run_tests(root: Path, argv: Sequence[str], *, timeout: int, name: str = "") -> TestRun`. `outcome` is
  `passed`, `failed (exit N)`, `timed out after N s`, or `not run: <why>`. `tail` is the last 6,000 characters of
  standard out and standard error, scrubbed.

- [ ] **Step 1: Write the failing tests:** a passing and a failing small Python program; one that sleeps past a
  1-second timeout; one not found; one named by a relative path; one printing 50,000 characters (the tail holds the
  end); one printing an AWS key shape (scrubbed); the config's list, a string refused, a bad timeout refused.
- [ ] **Step 2: Run them.** Expected: fail.
- [ ] **Step 3: Implement.** git keeps its behaviour through `process.run`.
- [ ] **Step 4: Run the gate.** Expected: all pass.
- [ ] **Step 5: Commit** `feat: one way to start a process, and a test run`.

### Task 2: The verify stage reads the test runs

**Files:** modify `adk_spec/orchestration/stages/verify.py`. Test: `tests/test_verify.py`.

- Produces: `TESTS = "tests"` state key and an optional section `## The tests` in the verify instruction; its guide
  gains one sentence: a requirement the tests show failing is not met.
- [ ] Steps: failing test that the section reaches the instruction; implement; gate; commit `feat: the verify stage
  reads the test runs`.

### Task 3: `verify` runs the tests and a failing run blocks

**Files:** modify `adk_spec/interfaces/cli.py` (`_verified`), `adk_spec/domain/model.py` (`Verification.tests`),
`adk_spec/domain/lifecycle.py` (`verified(..., tests_passed)`), `adk_spec/domain/report_md.py`, `README.md`. Test:
`tests/test_verify.py`.

- Produces: `Verification.tests: dict[str, str] = {}`; `verified(..., tests_passed: bool = True)`: verified only where
  every verdict is met and `tests_passed`, or overridden; `render_verify(..., tests=...)` with a `## Tests` section.
- [ ] **Step 1: Write the failing tests:** passing run, verified; failing run, not verified whatever the verdicts, the
  next line saying so; `--override` verified with the reason; no command, as today with the report saying so;
  another repository's own command run in its folder and said; a secret printed by the tests in no request,
  recording or report; the `testing` line printed before the run.
- [ ] **Step 2: Run them.** Expected: fail.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the gate.** Expected: all pass.
- [ ] **Step 5: Commit** `feat: verify runs the tests, and a failing run blocks`.
