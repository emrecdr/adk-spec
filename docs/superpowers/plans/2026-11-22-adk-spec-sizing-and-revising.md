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

---

## What changed in the build

- **Task 1.** The fix verbs are fix, correct, rename, reword and bump, and the word typo anywhere; "remove" and
  "adjust" from the design are left out, since removing a feature can be large and "adjust" says nothing of size.
- **Task 2.** The brief stage's existing "brief you are replacing" section carries the brief as it stands; no new
  key. The deltas stage gains `## The deltas as they stand`.
- **Task 3.**
  - `propose` no longer refuses an ID that names a change: it revises it. A folder under `changes/` that is no
    change is still refused.
  - A revised approved change goes back to a draft with its approval cleared, as `rebase` does, and says "the
    approval is void"; the design had the approval left recorded and stale.
  - A person's `--tier` beside an `--id` that names an open change is ignored: the change keeps its tier.
  - A kept ID is given once: a second requirement of the same name gets an ID of its own.
  - A delta of a capability the revision no longer touches is removed, through `Workspace.remove_from`.
  - Hand edits are kept as far as the model restates them. What code guarantees is the list of requirements
    changed, compared before and after; an edit lost from the brief is not listed.
- **After the cleanup review.**
  - A ticked box is counted as `plan` counts it, in a list off its grammar too: three reviewers found the first
    count missed that, and a revision could have lost a ticked task.
  - The tier is decided once, before the readiness check: the change's own for a revision, then a person's, then a
    rule's. A request a rule sizes no longer needs the sizing model to be set up.
  - A revision that changes no requirement keeps `tasks.md` and drafts none, and a revision never reads the code
    again: up to one tasks call and up to seven reading calls saved each time.
  - `lifecycle.reopened` is the one place a change goes back to a draft, for `rebase` and a revision alike. A
    revision writes its files and state as one set, through `Workspace.rewrite_change`.
  - The deltas as they stand are shown each under its path, within the limit every stage input has.
  - A test run keeps a virtual environment inside the project: adk-spec installed in the project's own `.venv`.
  - Not done: moving the retry section after the long inputs in every stage (older than this phase), a revision
    schema that returns only what changed (large), and the sizing rule in ADK's web chat (outside this phase).
- **After the code review.**
  - The lean rule took a typo fix, which the sizing stage's own guide calls `none`, and short feature requests that
    opened with "fix" or named a typo. Now a request with a typo-, wording-, docs- or prototype-shaped word is never
    sized by a rule, and lean by rule needs a fix verb first, a word of a fault (bug, crash, error, fails, wrong...)
    and no feature word.
  - A requirement the change adds, given back by the model as modified or removed, stays added with its ID or is
    dropped; the deltas guide says so too.
  - A delta off its grammar of a capability no longer touched is taken out: what is gone is read from the disk.
  - Two requirements of one name keep their IDs in order.
  - A revision that writes every file as it stood keeps the approval.
  - A person's `--tier` beside an `--id` of an open change is said to be unused.
  - The kept-tasks line is said beside a point left open.
  - A virtual environment whose folder holds the project, a monorepo's top `.venv` too, stays on a test run's PATH.
- **Removed, on the owner's decision.** After an outside review and two reviews of the follow-up each found risk words
  the sizing rule missed, the owner chose to delete it: `propose` asks the model for the tier unless `--tier` names one.
