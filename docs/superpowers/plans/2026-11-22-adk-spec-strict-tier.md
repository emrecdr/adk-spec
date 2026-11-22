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

---

## What changed in the build

- **Task 1.** A strict brief's open points are asked as a standard one's are: the question gate knew only the
  standard tier. A change of any tier that owes a design and has none cannot be approved, with `plan` as its next
  step, and `plan` counts that finding as its own to settle.
- **Task 3.** The first of the two approvals is recorded in the change's approval and leaves it a draft; the second
  is kept beside the first, as `second`. Where the work began is recorded at the second.
- **After the cleanup review.**
  - One table in `lifecycle`, `DEMANDS`, says what each tier asks: questions, a check, a verification, a design, the
    stop, how many approvers, whether warnings block and whether an override is allowed. Every rule of a tier reads
    it, the lean ones from before this phase included.
  - It closed four gaps the reviewers found: a warning of the model's check did not block a strict approval; the
    next line told a strict change a warning blocks to run `approve`; one name re-approving a strict change after an
    edit left it approved; and the domain took one name for both approvals.
  - `first_of_two` is the one test of "approved once, still standing"; `second_blockers` refuses the same name in
    the domain; the first of two approvals asks no repository; the approval says one line, and who is next is the
    next line's.
  - The stop's `plan` keeps a `--no-explore` the person gave. `TIERS` replaces `BUILT_TIERS`, now every tier.
  - Not done: `plan` keeps redrafting an owed design that stands, as on standard today; the finding no longer
    invites writing one by hand.
