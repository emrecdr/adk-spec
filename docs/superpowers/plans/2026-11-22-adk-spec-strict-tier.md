# The Strict Tier: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `strict` is a tier: a design always owed, `propose` stopping after the brief and specs, two different
approvers, and warnings that block with no override.

**Architecture:** The tier joins `BUILT_TIERS`; the domain owns the rules (`validate_change` for a design owed,
`lifecycle.approve` for the two approvals, `next_step` and `_unready` for what they say); the command line stops
`propose` and refuses an override on strict.

**Spec:** `docs/superpowers/specs/2026-11-22-strict-tier-design.md`

## Global Constraints

- No subcommand. No live model call in the build. Gate after each task: ruff, ruff format, pyrefly, pytest.

## Review Focus

1. A strict change approved once, then revised: the first approval is gone, and the change is a draft. Task 3.
2. A second approver while the first approval is stale: it counts as the first. Task 3.
3. `verify` on a change approved once: refused, saying one more approval is owed. Task 3.
4. A strict revision through `propose --id`: it stops before the plan as a new one does. Task 2.
5. A standard change whose brief owed a design and that has none: blocked, with `plan` next. Task 1.

---

### Task 1: `strict` is a tier, and a design is always owed

**Files:** `domain/model.py` (`BUILT_TIERS`), `workspace/config.py`, `orchestration/graph.py` (triage),
`domain/validate.py` (`change.missing-design`), `domain/lifecycle.py` (`_HOLDS`), `cli.py` (`_written`, `new`),
`workspace/layout.py` (`new_change`). Test: `tests/test_strict.py`.

- [ ] Failing tests; implement; gate; commit.

### Task 2: A strict `propose` stops after the brief and the specs

**Files:** `cli.py` (`_proposed`, `_then_planned`). Test: `tests/test_strict.py`.

- [ ] Failing tests; implement; gate; commit.

### Task 3: Two approvers, and warnings that block

**Files:** `domain/model.py` (`Approval.second`), `domain/lifecycle.py` (`approve`, `_unready`, `next_step`),
`cli.py` (`_approve`), `README.md`. Test: `tests/test_strict.py`.

- [ ] Failing tests; implement; gate; commit.
