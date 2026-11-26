# Stopping and the verify tool: phase 20

Designed on 26 November 2026 from the audit of 25 November (`docs/reports/2026-11-25-codebase-audit.md`, items H1
and S4). The owner said "proceed as recommended": phase 19 (S1-S3), then these two. Each was checked again in the
code before the design.

## Intent

A command stopped from outside, by a cancelled tool call, a closed terminal or a `kill`, leaves the project's tests
running: they run in a session of their own, and the stop reaches only the command, outright. And the MCP `verify`
tool runs whatever `[verify] test` names, so an assistant that edits `.spec/config.toml`, which an editor may let it
do with no prompt, then calls the tool, runs a command no person approved; its `bases` lets the work being judged
choose where its diff starts. This phase stops what a stopped command started, and holds the tool to a committed
test command and the approval's base. No model call, command, flag or `change.json` field.

## Goals

1. **H1: a stopped command stops its tests.** `adk-spec` hears SIGTERM and SIGHUP as Ctrl-C, so the interrupt path
   it already has stops the test tree, lets the lock go and records the run. The MCP server, and a command stopped at
   its time, ask first with SIGTERM, give the command `DRAIN_S` to stop what it started, and only then stop it whole.
2. **S4: the verify tool runs only a committed test command.** Run by the MCP server, `verify` refuses before any
   test runs where a repository's `.spec/config.toml` is not in its checked-out commit as it stands, naming it.
3. **S4: no `bases` on the tool.** The tool's `verify` diffs from the approval's base; a person passes `--base` in a
   terminal.

## Non-goals

- Windows: a process there is ended with no signal it could hear, and `taskkill /T` already stops the tree by its
  root; a job object (roadmap) holds what it leaves.
- The same rule for a terminal's `verify`: a person who edited the test command runs it, as before.
- The project files a committed test command runs (`package.json`'s script, `conftest.py`, a Makefile), which an
  assistant may have edited: running the work's tests is what `verify` is for; the rule closes only a changed command.

## Calls made in the design (the builder's)

- **How the command knows it runs for a tool.** The server sets `SPEC_TOOL_CALL=1` in the command's environment, as
  it already shapes that environment for `validate`. An assistant edits files, not the server's environment.
- **"Committed"** is the command as read held to the one the checked-out commit's `.spec/config.toml` names, read by
  the same reader (`git show HEAD:...`): asked of `git status` first, a config untracked where status lists none, or
  one the index marks unchanged, read as committed (the code review). An edit that leaves the command alone is no
  refusal, and the refusal asks the person, not the assistant, to commit.
- **A signal ignored before the command started stays ignored**, as `nohup` sets SIGHUP (the code review).
- **SIGTERM before SIGKILL, for the command only.** The project's tests are still stopped outright, as before: a test
  tree that hears a signal may not end.

## Tests

- A cancelled tool call, and a command hung up on, each leave no test process running (POSIX).
- Under a tool call, an uncommitted test command refused, nothing run; committed, run.
- The tool takes no `bases`; the command's environment says it runs for a tool.
