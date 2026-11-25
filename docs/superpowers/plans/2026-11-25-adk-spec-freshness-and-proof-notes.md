# Freshness and Proof Notes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Check three statements about the code with code: the profile's quotes, the evidence a verification's work
removed, and a drafted task's `[P]`.

**Architecture:** A quote's test is split out of `workspace/evidence.holds` and reused for the profile; the profile
is read by a lenient parser in `domain/context_md.py`; `verify` filters the existing `spec.evidence-gone` notes by
the files its diff touched; `domain/convert.py` drops a `[P]` that breaks its rule.

**Tech Stack:** Python 3.14, uv, pytest, ruff, pyrefly.

**Spec:** `docs/superpowers/specs/2026-11-25-freshness-and-proof-notes-design.md`

## Global Constraints

- No model call, no new command, flag, `change.json` field or file; no change to `validate` or to `--json` output.
- Layers: `domain` does no I/O; `workspace` imports no network module. C901 at most 10, lines at most 120.
- Never write over an existing test file: add tests to the file of the behaviour, or a new free name.

## Review Focus

- A profile edited by a person (entries reordered, a quote line removed, prose added): nothing raised, nothing said.
- A profile statement on an installed library's file (`python:httpx/_client.py`): never counted as gone.
- Another repository's evidence file touched by a multi-repository change: matched by the change's name for it.
- A requirement whose evidence was already gone before the work, in a file the work did not touch: not named.
- `[P]` on the first or last task of a group: one neighbour only.

---

### Task 1: The profile checked against the code

**Files:** Modify `adk_spec/domain/context_md.py`, `adk_spec/workspace/evidence.py`, `adk_spec/interfaces/cli.py`
(`_status`, `_propose`'s start). Test: `tests/test_freshness.py` (new; check the name is free).

**Interfaces:**
- Produces: `context_md.quoted_statements(text: str) -> list[tuple[str, str]]` (path, quote) of each entry;
  `evidence.quote_holds(folder: Path, path: str, quote: str, exclude: Sequence[str], *, own: bool) -> bool | None`
  (the body of `holds`, which now calls it); `evidence.profile_gone(workspace) -> tuple[int, int] | None` (gone,
  checked; None where there is no profile that reads, or nothing to check).

- [ ] Tests first: all hold → no line; one gone → `profile: 1 of 3 quotes no longer in the code: ...init --refresh`
  in `status`; a moved quote holds; `python:` paths not counted; an unreadable profile says nothing; `propose` prints
  the line before triage's call (fake provider).
- [ ] Implement; run the tests; commit.

### Task 2: The proofs the work removed (built, then taken out: see the design's Goal 2)

**Files:** Modify `adk_spec/interfaces/cli.py` (`_verified`), `adk_spec/workspace/evidence.py`. Test:
`tests/test_evidence.py` (append).

**Interfaces:**
- Produces: `evidence.removed_by(workspace, living, touched: frozenset[str], names: Mapping[str, str], own:
  frozenset[str]) -> list[str]` (requirement IDs, with their capability, whose evidence is all gone and has a file
  among `touched`; `names` maps a repository's location to the name the change gives it; `own` are the change's
  requirement IDs, left out). It runs `holds` only for requirements with a file among `touched`, then on all of
  their lines; never `evidence_findings`' whole scan.

- [ ] Tests first: one named; one the change modifies not named; one still holding not named; one untouched file not
  named; four named as three and "and 1 more".
- [ ] Implement; run; commit.

### Task 3: `[P]` held to its rule

**Files:** Modify `adk_spec/domain/convert.py`, `adk_spec/domain/tasks_md.py` (`task_path`, moved from
`remaining._path`), `adk_spec/domain/remaining.py`. Test: `tests/test_convert.py` if it exists, else the tasks tests.

- [ ] Tests first: shared file loses `[P]`; folder over file loses it; no files loses it; apart keeps it; first and
  last task of a group.
- [ ] Implement; run; commit.

### Task 4: Docs

README (status, propose, verify lines), `docs/full-usage-guide.md`, CLAUDE.md and `.github/copilot-instructions.md`
if a rule they state changes, the roadmap row for phase 17.
