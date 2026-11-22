# adk-spec Simple Flow Implementation Plan (plan 5)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** One standard change takes four commands (`propose`, `approve`, `verify`, `archive`) and one lean change three, with every existing command still working alone.

**Architecture:** No rule of the lifecycle changes and no state field is added. Two commands take over work a person had to start by hand: `propose` goes on to the plan, and `approve` records missing bases and makes the check where none is current. Each is done by calling the body of the existing command from inside the other, under the lock the outer command already holds, so a failure half-way leaves what the first part wrote.

**Tech Stack:** As plans 1 to 4. No new dependency.

**Spec:** `docs/superpowers/specs/2026-11-22-simple-flow-design.md` (approved 22 November 2026). Evidence for every merge, with file and line: `research_notes/Simple command flows in spec tools/adk_spec_current_flow.md`, section 5.

## Global Constraints

Plans 1 to 4's Global Constraints hold unchanged. In addition:

- No subcommand is added and none is removed. Every flag that exists keeps its meaning.
- `adk_spec/interfaces/cli.py` imports no engine module at its top: a handler that calls a model imports it inside itself.
- The lock is not re-entrant. A command that runs another command's work calls its body, never its registered handler.
- No stage's instruction changes. `scripts/dump_instructions.py` proves it.
- No task makes a live model call. Task 6 holds the live steps, marked **owner**.
- After this plan `adk-spec approve` on a standard change may call a model. It is added to the commands that need the owner's go-ahead.

## Review Focus

1. `approve` on a standard change with no provider set up. It says so in one sentence, names `adk-spec check <id> --no-model`, exits 2, and records neither a check nor an approval. Test in Task 2.
2. `--override` typed on the run that made the check. It is not applied: a person cannot set aside a finding they have not been shown. Test in Task 2.
3. A base that moved since it was recorded. `approve` records only a base that is missing and never re-records one, so `delta.base-stale` still stops it. Test in Task 1.
4. The plan part of `propose` fails after the change is written: the ceiling is spent, or a gate gives up. The draft stands, the command names `adk-spec plan <id>`, shows what was spent, exits 3, and lets the lock go. Test in Task 3.
5. `approve` where a file has an error of structure. It refuses as today and calls no model. Test in Task 2.

---

### Task 1: `approve` records the bases that are missing

**Files:**
- Modify: `adk_spec/domain/lifecycle.py`, `adk_spec/interfaces/cli.py`
- Test: `tests/test_lifecycle.py`, `tests/test_cli.py`

**Interfaces:**
- Produces:
  - `lifecycle.missing_bases(state: ChangeState, deltas: Mapping[str, Delta], living: Mapping[str, Spec]) -> dict[str, str]`: the base of each modified or removed requirement that has none recorded, as `capture_bases` reads it now. A recorded base is never among them.
  - `BLOCKS_APPROVAL` loses `delta.base-missing`, and `_HOLDS` loses its row.
  - `_approve` saves `state.bases | missing_bases(...)` before it assesses, where there is one to add.

- [ ] **Step 1: Write the failing tests**

```python
def test_approve_records_a_base_that_is_missing_and_needs_no_rebase(tmp_path) -> None:
    # a hand-written lean change that modifies REQ-AUTH-002, no `rebase` run: `approve` exits 0,
    # and the state's bases hold REQ-AUTH-002 with the living spec's fingerprint

def test_approve_never_records_anew_a_base_that_moved(tmp_path, capsys) -> None:      # Review Focus 3
    # rebase, then the living requirement changes: `approve` exits 1 with `delta.base-stale`,
    # and the recorded base is what it was

def test_a_missing_base_holds_no_draft(…) -> None:
    # next_step for a draft whose only finding is delta.base-missing: Step("you", "run `adk-spec approve passkeys`")
```

- [ ] **Step 2: Run them.** Expected: FAIL: `approve` exits 1 with `delta.base-missing`.
- [ ] **Step 3: Implement.** Rewrite the assertions that pin `rebase` as a step before `approve`.
- [ ] **Step 4: Run the suite.** Expected: all pass.
- [ ] **Step 5: Commit.** `feat: approve records a missing base itself`

---

### Task 2: `approve` checks a standard change first

**Files:**
- Modify: `adk_spec/domain/lifecycle.py`, `adk_spec/interfaces/cli.py`, `README.md`
- Test: `tests/test_check.py`, `tests/test_lifecycle.py`, `tests/test_cli.py`

**Interfaces:**
- Produces:
  - `cli._check_made(workspace, change_id, specs, assessed, *, no_model: bool) -> _Checked | str`: the work of `check` with nothing printed: the report written and the check recorded, or the failure's sentence where the model's pass did not end well. `_Checked` holds `findings` (every finding, pathed from the root), `report` (its path), `dropped`, `ledger`.
  - `_reviewed` is `_check_made` plus what it prints today, unchanged.
  - `_approve`, in this order: records missing bases; refuses on what blocks beside the check, calling no model; where the check is missing or stale, makes it; refuses on a blocking finding; approves. It prints `checked   <report>: <n> findings, <m> blocking` where it made the check, the blocking findings where it refuses, the `tokens` line where a model was called, and a `next` line where it approves.
  - `--override` sets aside a blocking finding only of a check recorded before this run.
  - `next_step`: a missing or stale check holds no draft, so the step is `run adk-spec approve <id>`. A blocking check: `fix what reports/check.md lists, then run adk-spec approve <id>`. A stale approval: `approve again: <files> changed since the approval`.
  - `check_blockers` words `check.missing` as "`<id>` has not been checked: `adk-spec approve <id>` checks it first." and `check.stale` as "A file of `<id>` changed since its check: `adk-spec approve <id>` checks it again."

- [ ] **Step 1: Write the failing tests**

```python
def test_approve_makes_the_check_a_standard_change_owes(tmp_path, capsys, fake_provider) -> None:
    # standard change, planned, never checked: `approve` exits 0, one request (the check's),
    # out has "checked   .spec/changes/passkeys/reports/check.md: 1 findings, 0 blocking", "approved", "next"

def test_approve_checks_again_after_an_edit(…) -> None:              # check.stale: a second request is made
def test_a_current_check_is_not_made_again(…) -> None:               # check, then approve: one request in all
def test_a_blocking_finding_of_its_own_check_stops_the_approval(…) -> None:   # exit 1, the finding printed, no approval
def test_an_override_does_not_reach_a_check_made_in_the_same_run(…) -> None:  # Review Focus 2
def test_an_override_reaches_a_check_a_person_was_shown(…) -> None:  # second run with --override: approved, reason recorded
def test_approve_with_no_provider_says_so_and_names_the_way_without_one(…) -> None:   # Review Focus 1: exit 2
def test_approve_calls_no_model_where_a_file_does_not_read(…) -> None:        # Review Focus 5: exit 1, no request
def test_a_lean_change_is_approved_with_no_check_and_no_model(…) -> None:
def test_a_check_that_does_not_finish_approves_nothing(…) -> None:   # exit 3, no check and no approval recorded
```

- [ ] **Step 2: Run them.** Expected: FAIL: `approve` exits 1 with `check.missing`.
- [ ] **Step 3: Implement.** Rewrite the assertions that pin `check` as a step before `approve`.
- [ ] **Step 4: Run the suite.** Expected: all pass.
- [ ] **Step 5: Commit.** `feat: approve makes the check a standard change owes`

---

### Task 3: `propose` goes on to the plan

**Files:**
- Modify: `adk_spec/interfaces/cli.py`, `README.md`
- Test: `tests/test_propose.py`, `tests/test_clarify.py`, `tests/test_recorder.py`, `tests/test_plan.py`

**Interfaces:**
- Produces:
  - `cli._asked(..., ledger: Any | None = None)`: uses the ledger it is given, so one command has one ceiling.
  - `cli._plan_made(workspace, change_id, *, replace: bool, ledger: Any | None = None) -> _Planned`: the work of `plan` with nothing printed. `_Planned` holds `written` (each file's name, path, and whether it replaced one), `ledger`, and `failure`.
  - `_planned` is `_plan_made` plus what it prints today, unchanged.
  - `_proposed`, once the change is written, calls `_plan_made` with its own ledger, then prints one `wrote` line a file of the whole change, one `tokens` line for every stage, and `next`. The line `design owed` goes: the design is written.
  - `_propose` asks the readiness of `design` and `tasks` with the roles it asks today.
  - Where the plan part fails: `adk-spec: the brief and the specs are written, and the plan is not: <failure>. Run \`adk-spec plan <id>\` to finish it`, the `tokens` line, exit 3.
  - A `propose` leaves two recordings, `propose` and `plan`, as the two commands did.

- [ ] **Step 1: Write the failing tests**

```python
def test_propose_writes_the_whole_change_tasks_included(tmp_path, capsys, fake_provider) -> None:
    # lean: brief.md, specs/auth/spec.md and tasks.md stand; `validate` lists no change.missing-tasks;
    # out names tasks.md, has one tokens line that names "tasks", and next is "run `adk-spec approve …`"

def test_propose_writes_the_design_where_the_brief_owes_one(…) -> None:
def test_one_ceiling_holds_the_drafting_and_the_plan_together(…) -> None:      # max_tokens spent by the deltas: no tasks call
def test_a_plan_that_fails_leaves_the_draft_and_says_how_to_finish(…) -> None: # Review Focus 4: exit 3, names plan <id>, lock free
def test_propose_refuses_before_spending_where_the_tasks_role_has_no_model(…) -> None:
def test_plan_alone_still_redrafts_a_change(…) -> None:                         # `plan <id> --replace` after a propose
```

- [ ] **Step 2: Run them.** Expected: FAIL: no `tasks.md` after `propose`.
- [ ] **Step 3: Implement.** Rewrite the assertions that pin a `propose`'s request count, its `tokens` line and `change.missing-tasks` after it.
- [ ] **Step 4: Run the suite.** Expected: all pass. `scripts/dump_instructions.py` shows no instruction changed.
- [ ] **Step 5: Commit.** `feat: propose writes the whole change, its plan included`

---

### Task 4: What a command says while it works and when it ends

**Files:**
- Create: `adk_spec/orchestration/progress.py`
- Modify: `adk_spec/orchestration/plugins.py` (`roster`), `adk_spec/orchestration/graph.py` (`_app`), `adk_spec/interfaces/cli.py`
- Test: `tests/test_progress.py`, `tests/test_propose.py`

**Interfaces:**
- Produces:
  - `progress.Progress(BasePlugin)`, built with `say: Callable[[str], None]`: before each model call it says `working   <stage>`, and `working   <stage>, again` for a call a gate asked for.
  - `roster(ledger, recorder=None, progress=None)`: the progress plugin first where there is one.
  - The commands pass one only where the error stream is a terminal, and it writes there. A pipe and a test see nothing new.
  - `propose` ends with `read      brief.md (<n> lines), design.md (<n> lines) first`, the design only where there is one, before `next`.

- [ ] **Step 1: Write the failing tests**

```python
async def test_each_model_call_is_said_once_and_a_second_try_is_marked(fake_provider) -> None:
def test_nothing_is_said_where_the_error_stream_is_no_terminal(tmp_path, capsys, fake_provider) -> None:
def test_a_terminal_is_told_each_stage_as_it_starts(tmp_path, monkeypatch, capsys, fake_provider) -> None:
def test_propose_names_what_to_read_first_with_its_length(tmp_path, capsys, fake_provider) -> None:
```

- [ ] **Step 2: Run them.** Expected: FAIL, `No module named 'adk_spec.orchestration.progress'`.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the suite.** Expected: all pass.
- [ ] **Step 5: Commit.** `feat: a command says which stage it is on, and propose what to read first`

---

### Task 5: The help in three groups, and the README around four commands

**Files:**
- Modify: `adk_spec/interfaces/cli.py`, `README.md`, `docs/superpowers/plans/README.md`
- Test: `tests/test_cli.py`

**Interfaces:**
- Produces: `cli.COMMAND_GROUPS`, three pairs of a heading and command names: `Everyday` (`propose`, `approve`, `verify`, `archive`, `status`, `init`), `To redo one step` (`plan`, `check`, `rebase`, `validate`, `new`), `Setup` (`login`, `models`, `smoke`). `adk-spec --help` lists the commands under those headings in that order, each with its one-line help. The one-line helps of `propose` and `approve` say what they now do.

- [ ] **Step 1: Write the failing tests**

```python
def test_the_help_lists_the_everyday_commands_first_under_three_headings(capsys) -> None:
def test_every_command_stands_in_exactly_one_group() -> None:      # no command can be registered and left out
def test_a_standard_change_takes_four_commands_from_request_to_record(tmp_path, capsys, fake_provider) -> None:
    # in a git repository: propose --tier standard, approve, the work committed, verify, archive: each exits 0
def test_a_lean_change_takes_three(tmp_path, fake_provider) -> None:
```

- [ ] **Step 2: Run them.** Expected: the two help tests FAIL; the two flow tests pass, which is what Tasks 1 to 3 built.
- [ ] **Step 3: Implement,** and rewrite the README's command sections around the four commands.
- [ ] **Step 4: Run the suite.** Expected: all pass.
- [ ] **Step 5: Commit.** `feat: the help shows the everyday commands first; the README follows the flow`

---

### Task 6: Proven live (owner)

Each step calls a model with the owner's account, on the owner's go-ahead in so many words.

- [ ] **Step 1 (owner, live).** One standard change through the four commands in a small git repository. Record in `docs/confirmation/2026-11-simple-flow.md`: each command's tokens and seconds, the lines a person has to read (each file's length), and whether `approve`'s own check blocked.
- [ ] **Step 2.** Decide from it, in that file: whether a length limit on the brief and the design is worth an instruction change.

---

## What this plan leaves

Brownfield reading inside `propose` (the next phase). A length limit on what a stage writes. `archive` saying anything more than its one line.
