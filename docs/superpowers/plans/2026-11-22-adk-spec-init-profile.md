# `init` Describes the Repository: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `adk-spec init` in an existing repository reads its code, writes `.spec/profile.md` and drafts rules already
true of the code into the template constitution; every later change's reading starts from the profile.

**Architecture:** The explore app of phase 7, unchanged, seeded with a fixed brief that asks what a person changing
the repository first needs to know. `cli._read_code`'s run and write split into a shared `_reading` and two writers:
`context.md` for a change, `profile.md` for `init`. A drafted-rules section is rendered by the domain from the kept
`convention` statements. The profile reaches the scout, design and tasks stages through one optional section.

**Tech Stack:** Python 3.14, uv, google-adk 2.14.1, litellm 1.106.2, pytest (asyncio strict), ruff 0.17.5, pyrefly 1.4.1.

**Spec:** `docs/superpowers/specs/2026-11-22-brownfield-init-profile-design.md`

## Global Constraints

- No subcommand. Two flags on `init`: `--no-explore` and `--refresh`.
- `init` never fails for want of a model: the tree is made first, and every way the reading cannot run is one line.
- `constitution.md` is written to only while it is exactly `layout.CONSTITUTION_TEXT`, and never on `--refresh`.
- Layers import one way; only `workspace/git.py` runs a subprocess; `cli.py` imports no engine module at its top.
- No live model call in Tasks 1 to 4. Offline: `SPEC_PROVIDER=gemini`, `SPEC_MODEL=fake`, `GOOGLE_API_KEY=offline`.
- Gate after each task: `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyrefly check`,
  `uv run pytest -q`; `scripts/dump_instructions.py` shows which instructions changed.

## Review Focus

1. `init` outside a git repository, or in one with no file beside `.spec/`: the tree is made, nothing is read,
   exit 0. Test in Task 3.
2. No model ready (no key, no token): the tree is made, one line says why and names `init --refresh`, exit 0. Test in
   Task 3.
3. A constitution a person edited, then `init --refresh`: untouched. Test in Task 3.
4. `init --refresh` where there is no `.spec/`: refused by name, nothing made. Test in Task 3.
5. A secret shape in a tracked file: in neither `profile.md` nor a drafted rule. Test in Task 3.

---

### Task 1: The profile and the drafted rules, as text

**Files:**
- Modify: `adk_spec/domain/context_md.py`, `adk_spec/workspace/layout.py`, `adk_spec/workspace/context.py`
- Test: `tests/test_context_md.py`, `tests/test_context.py`

**Interfaces:**
- Produces:
  - `render_context(..., heading: str | None = None)`: the first line is `# {heading}` where given, `# Context:
    {change_id}` otherwise.
  - `PROFILE_HEADING = "This repository"` in `context_md.py`.
  - `drafted_rules(statements: Sequence[Statement]) -> str` in `context_md.py`: `""` where no statement is a
    `convention`; otherwise `## Drafted from the code`, one line saying `adk-spec init` drafted them from the code
    and each is the person's to keep, edit or delete, and one bullet a convention: `- {note} (`{path}:{line}`:
    {quote})`.
  - `layout.PROFILE = "profile.md"`; `context.profile_text(workspace) -> str`: the profile as a stage reads it,
    `""` where there is none, cut at `PROFILE_MAX_CHARS = 10_000` and saying so.

- [ ] **Step 1: Write the failing tests:** `test_a_profile_has_its_own_heading`,
  `test_drafted_rules_are_the_conventions_each_with_its_evidence`, `test_no_convention_drafts_no_rule`,
  `test_the_profile_is_read_as_it_stands_and_cut_past_its_cap`.
- [ ] **Step 2: Run them.** Expected: fail (`ImportError: cannot import name 'drafted_rules'`).
- [ ] **Step 3: Implement** as the Interfaces say.
- [ ] **Step 4: Run the gate.** Expected: all pass; instructions unchanged.
- [ ] **Step 5: Commit** `feat: the profile and the drafted rules, as text`.

### Task 2: Every change's reading starts from the profile

**Files:**
- Modify: `adk_spec/orchestration/stages/__init__.py`, `stages/scout.py`, `stages/design.py`, `stages/tasks.py`,
  `adk_spec/interfaces/cli.py` (`_plan_made`, `_read_code`)
- Test: `tests/test_plan.py`

**Interfaces:**
- Consumes: `context.profile_text` (Task 1).
- Produces: `stages.PROFILE_TEXT = "profile"`, `stages.THE_PROFILE = section("## What is known of this repository",
  "profile", PROFILE_TEXT, optional=True)`, in the scout's, the design's and the tasks' instructions; `_plan_made`
  seeds it, and `_read_code` passes it to the reading.

- [ ] **Step 1: Write the failing tests:** `test_the_scout_and_the_plan_are_shown_the_profile` (a `.spec/profile.md`
  written by hand reaches the scout's, the design's and the tasks' instructions between the `profile` markers) and
  `test_with_no_profile_no_stage_is_shown_one`.
- [ ] **Step 2: Run them.** Expected: fail.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the gate.** Expected: all pass; `dump_instructions` shows the one new section in three stages.
- [ ] **Step 5: Commit** `feat: every change's reading starts from the profile`.

### Task 3: `init` reads the code

**Files:**
- Modify: `adk_spec/interfaces/cli.py` (`_init`, the `init` parser, `_read_code` split into `_reading` and its
  writer), `README.md`
- Test: `tests/test_init.py` (new)

**Interfaces:**
- Consumes: Tasks 1 and 2; `explore.ROLES`, `build_explore_app`, `explored`.
- Produces:
  - `cli.DESCRIBE`: the fixed brief `init` seeds the reading with, a short Markdown text asking for the stack and
    versions, the layout and where each part lives, how it is built and tested, how errors and configuration are
    handled, and what is risky to change.
  - `cli._reading(workspace, label: str, seed: dict[str, Any], ledger: Any, source: Source) -> tuple[Explored,
    str | None]`: one recorded reading and its failure; `_read_code` keeps its behaviour on top of it.
  - `init --no-explore`, `init --refresh`.

- [ ] **Step 1: Write the failing tests** in `tests/test_init.py`, on the fake model, each in a small repository:
  - `test_init_reads_the_code_writes_the_profile_and_drafts_the_rules`: output in order `made`, `reading`,
    `explored`, `wrote     .spec/profile.md`, `drafted   1 rule into .spec/constitution.md`, `next`; the profile
    starts `# This repository`; the constitution ends with the drafted section.
  - `test_init_says_what_it_will_spend_before_it_reads`: the `reading` line holds `up to 7 model calls` and
    `--no-explore skips it`.
  - `test_no_explore_and_no_repository_and_no_file_read_nothing` (Review Focus 1).
  - `test_no_model_ready_makes_the_tree_and_says_how_to_read_later` (Review Focus 2): exit 0, `.spec/` there,
    `init --refresh` in the output, no request.
  - `test_refresh_rewrites_the_profile_and_never_the_constitution` (Review Focus 3).
  - `test_refresh_where_there_is_no_workspace_is_refused` (Review Focus 4).
  - `test_a_reading_that_keeps_nothing_writes_no_profile` and `test_a_reading_that_ends_early_writes_a_partial_profile`.
  - `test_a_secret_reaches_neither_the_profile_nor_a_rule` (Review Focus 5).
- [ ] **Step 2: Run them.** Expected: fail.
- [ ] **Step 3: Implement.** `init` makes the tree first (or finds it, with `--refresh`), then loads the `.env`,
  holds the lock, and reads where it can. The recording is `init`'s, with no change.
- [ ] **Step 4: Run the gate.** Expected: all pass.
- [ ] **Step 5: Commit** `feat: init reads the code and describes the repository`.

### Task 4: The labelled case

**Files:**
- Modify: `scripts/cases.py`, `scripts/measure.py` (a case run with `init`), `docs/measurements/README.md`
- Test: `tests/test_measure.py`

- [ ] **Step 1: Write the failing test** `test_the_profile_case_is_caught_where_a_drafted_rule_names_the_convention`:
  a repository whose tests stand beside the code and whose errors are raised as one class; caught where
  `constitution.md`'s drafted section holds a rule on one of the two planted files.
- [ ] **Step 2: Run it.** Expected: fail.
- [ ] **Step 3: Implement** `Case("profile", _profile, "init", ...)`; `measure` runs `init --refresh` for an `init`
  case and reads the drafted rules as it reads `context.md`'s statements.
- [ ] **Step 4: Run the gate.** Expected: all pass.
- [ ] **Step 5: Commit** `feat: a labelled case for init's drafted rules`.

### Task 5: Live, on the owner's go-ahead

- [ ] `init` on a copy of adk-spec itself, the profile and the drafted rules read by hand.
- [ ] The `profile` case five times.

## What this plan leaves

Describing a change's other repositories at `init`, a capability-to-folder map with an accept step, living specs
drafted from code.
