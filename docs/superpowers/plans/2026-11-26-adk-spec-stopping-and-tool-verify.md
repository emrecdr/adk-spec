# Stopping and the verify tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** a stopped command stops its tests (H1); the MCP `verify` tool runs only a committed test command and takes
no `bases` (S4).

**Architecture:** `cli.interrupt_on_signals()` called by `cli.run()`; `process._asked_to_stop` (SIGTERM, `DRAIN_S`,
then the whole tree) used by `stop` and `waited`; `git.committed(root, path)`; `_tested` refuses under
`SPEC_TOOL_CALL`, which `mcp_server.child_environment` sets; `bases` removed from the tool.

**Tech Stack:** Python 3.14, `signal`, `subprocess`, git, pytest, the MCP SDK.

**Spec:** `docs/superpowers/specs/2026-11-26-stopping-and-tool-verify-design.md`

## Global Constraints

- No model call, command, flag or `change.json` field; the gates and `pyrefly --python-platform windows` green.
- Signal tests skip on Windows.

## Review Focus

1. A command that ignores SIGTERM: stopped whole after `DRAIN_S`, the call still cancelled.
2. A repository named by the change whose config is uncommitted: refused, named, before any repository's tests run.
3. A workspace with no commit yet: refused under a tool call, not an error from git.
4. A cancel while the command already ended: no signal sent to a reused pid.
5. The terminal's `verify` with an edited test command: runs as before.

---

### Task 1: a stopped command stops its tests (H1)

- [ ] Tests in `tests/test_mcp_server.py`: `test_a_cancelled_call_stops_the_tests_its_command_started` and
  `test_a_command_hung_up_on_stops_its_tests` (a child that calls `interrupt_on_signals()` then `run_kept` on a
  sleeper; the sleeper's pid gone after the cancel, or after SIGHUP). Run: FAIL.
- [ ] `interrupt_on_signals()` in `cli.py`, called by `run()`; `_asked_to_stop` in `process.py`, used by `stop` and
  `waited`. Run: PASS; suite green. Commit.

### Task 2: the verify tool (S4)

- [ ] Tests: `test_a_tool_calls_verify_refuses_a_test_command_not_committed` (nothing run, the config named),
  `test_a_tool_calls_verify_runs_a_committed_test_command`, the tool taking no `bases`, the environment's
  `SPEC_TOOL_CALL`. Run: FAIL.
- [ ] `git.committed`; `_tested` refuses under `SPEC_TOOL_CALL`; `child_environment` sets it; `bases` removed. Run:
  PASS; suite green. Commit.

### Task 3: docs

- [ ] README (the tool's `verify`, a stopped command), the roadmap's row 20, CLAUDE.md and Copilot's guide where the
  MCP server is described. Gate; commit.
