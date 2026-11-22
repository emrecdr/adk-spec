# A Lessons File: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `.spec/lessons.md`, read by every drafting stage, gains a line in code for each fault a gate sent back that
the next try fixed; `approve` names a drafted file a person edited.

**Architecture:** `domain/lessons_md.py` holds the template and the pure merge of sent-back problems into the file.
The gate notes what it sends back and hands it on when a try passes. The command writes the lessons after each run,
seeds the file into the drafting stages, and records drafted fingerprints in the change's state for `approve`.

**Spec:** `docs/superpowers/specs/2026-11-22-lessons-design.md`

## Global Constraints

- No subcommand, no model call for a lesson, no live model call in the build. Gate after each task: ruff, ruff
  format, pyrefly, pytest.

## Review Focus

1. A gate sentence with a backtick or a secret shape in it: the line is one line, scrubbed. Task 1.
2. A person who renamed the gate heading or wrote their own line in that shape: theirs is never rewritten. Task 1.
3. A stage sent back twice for two faults, then passing: both lines. Task 2.
4. `propose` with rounds of questions: each run's lessons written once. Task 3.
5. A revision, a `plan --replace`: drafted fingerprints follow what was written. Task 4.

---

### Task 1: The lessons file, in the domain and the workspace

**Files:** create `adk_spec/domain/lessons_md.py`; modify `adk_spec/workspace/layout.py` (`LESSONS`, `init`,
`learn`), `adk_spec/workspace/context.py` (`lessons_text`). Test: `tests/test_lessons.py`.

- `TEMPLATE`, `learned(text, sent_back: Iterable[tuple[str, str]]) -> str`.
- [ ] Failing tests; implement; gate; commit.

### Task 2: Gates note what they sent back, and every gate sentence has a code

**Files:** `adk_spec/orchestration/gate.py` (`SENT_BACK`, `learns`), `adk_spec/orchestration/graph.py`. Test:
`tests/test_gate.py` or `tests/test_lessons.py`.

- [ ] Failing tests; implement; gate; commit.

### Task 3: The drafting stages read the lessons, and runs write them

**Files:** `stages/__init__.py` (`LESSONS_TEXT`, `THE_LESSONS`), the four drafting stages, `cli.py` (`_asked`,
`_rounds`, the seeds). Test: `tests/test_lessons.py`.

- [ ] Failing tests; implement; gate; commit.

### Task 4: `approve` names a drafted file a person edited

**Files:** `domain/model.py` (`ChangeState.drafted`), `cli.py` (`_written`, `_rewritten`, `_plan_made`,
`_approve`), `README.md`. Test: `tests/test_lessons.py`.

- [ ] Failing tests; implement; gate; commit.
