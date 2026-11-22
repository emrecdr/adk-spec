# Sizing by Rules and Revising by Instruction: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `propose` sizes short fixes and long features by rule, with no model call, and revises an open change in
place when `--id` names one, keeping what the instruction does not reach.

**Architecture:** A domain module of sizing rules returns a tier or nothing. The brief and deltas stages gain optional
sections for the files as they stand; `propose` seeds them for a revision, starts at the brief, keeps IDs by name,
writes into the existing folder and says what changed.

**Spec:** `docs/superpowers/specs/2026-11-22-sizing-and-revising-design.md`

## Global Constraints

- No subcommand. No live model call in the build. Gate after each task: ruff, ruff format, pyrefly, pytest.

## Review Focus

1. A revision whose model returns the brief unchanged: the file is as it was, hand edits and all. Task 3.
2. A requirement renamed by the revision: a new ID, the old one listed as dropped. Task 3.
3. A request just over the rules' lengths, or with a fix verb inside a long feature request: the model sizes it.
   Task 1.
4. `--id` naming a change of another tier: the change's tier is kept. Task 3.
5. A revision of a change whose task is ticked: `tasks.md` untouched. Task 3.

---

### Task 0: A test run is given the person's environment, not adk-spec's own

Measured live in phase 9: the run inherited adk-spec's virtual environment first on `PATH` and in `VIRTUAL_ENV`.

- [ ] Failing test: `run_tests` with a fake `sys.prefix` venv: `VIRTUAL_ENV` absent and its `bin` off `PATH` in the
  child's environment. Implement `tests._environment()`; gate; commit.

### Task 1: Sizing by rules

**Files:** create `adk_spec/domain/sizing.py`; modify `adk_spec/interfaces/cli.py` (`_proposed`). Test:
`tests/test_sizing.py`, `tests/test_propose.py`.

- `sized(request: str) -> tuple[Tier, str] | None`: a tier and its reason, or nothing.
- [ ] Failing tests: the lean and standard cases, the edges, a fix verb in a long request; `propose` skips triage
  where a rule sizes and prints `sized     …, by rule: …`; `--tier` wins. Implement; gate; commit.

### Task 2: The brief and deltas stages read what stands

**Files:** `stages/brief.py`, `stages/deltas.py`, `stages/__init__.py`. Test: `tests/test_propose.py`.

- `CURRENT_BRIEF`, `CURRENT_DELTAS` state keys; optional sections `## The brief as it stands`, `## The deltas as they
  stand`; one guide sentence each.
- [ ] Failing test on the instructions; implement; gate; commit.

### Task 3: `propose --id` revises an open change

**Files:** `adk_spec/interfaces/cli.py`, `adk_spec/domain/convert.py` (IDs kept by name), `README.md`. Test:
`tests/test_revise.py` (new).

- [ ] Failing tests from the design's "How it is proven"; implement; gate; commit.
