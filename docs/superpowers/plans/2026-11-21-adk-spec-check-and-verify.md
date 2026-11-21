# adk-spec Check and Verify Implementation Plan (plan 3 of 3)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `adk-spec check <id>` judges a change's files against each other before approval, `adk-spec verify <id>` judges the repository's diff against the change's requirements after implementation, and every model call is recorded so a stage can be measured and, later, replaced by code.

**Architecture:** As plans 1 and 2: one short `Workflow` run a command, schema-bound stages with no tools, a gate after each, files as the record. Two rules are new. A model's finding counts only where the text it quotes is really in the file or the diff it names, and code decides that. What can be decided without judgement (which requirement has no task, which task names an ID nothing holds) is decided in the domain layer from the start and never sent to a model.

**Tech Stack:** As plans 1 and 2: Python 3.14, uv, google-adk 2.14.1, LiteLLM 1.106.2, Pydantic 2, pytest. No new dependency. Git is run as a program, through this package's own layer.

**Spec:** `reports/Spec driven framework on Google ADK.md` (the sections "Lifecycle, gates and keeping specs alive", "Version 1", "Migration" and "Testing and evaluation"); plans 1 and 2, whose sections "What changed while this plan was executed" are binding here; and `docs/confirmation/2026-11-propose.md`, whose seven findings and five decisions this plan answers.

Written on 21 November 2026. Plan 2's file name runs a day ahead of the day it was written.

## Where this plan starts from

- `main` holds plans 1 and 2. `gpt-4.1` on GitHub Copilot answers every schema of plan 2 on the owner's seat, on macOS. The Gemini arm and Windows are not run.
- The lifecycle already names what this plan builds: `archive_blockers` refuses a standard change that is not `verified`, and `next_action` says "implement tasks.md, then run `adk-spec verify <id>`". No command sets `verified` yet.
- No run pauses for a person, and none may: a paused run resumed runs again, unseen, any stage that had answered off its schema (`q18_resume_reruns_an_errored_stage_probe.py`).

## Validated before building

Checked on 21 November 2026 against the code and the pinned libraries, offline:

- A plugin standing first in the roster is handed each call's instruction already filled from state, sees each answer before the mismatch plugin replaces it, and knows the stage by `callback_context.agent_name`. For a call the ledger refuses it sees the request and no answer (`q19_plan3_recorder_plugin_probe.py`).
- Every name this plan consumes exists as spelled after the cleanup pass of plan 2: `roster(ledger)`, `build_plan_app(*, design, ledger)`, `build_propose_app(known, *, ask, entry, ledger)`, `first_run`, `next_run`, `gate.checked`, `stages.instruction`, `stages.section`, `Workspace.write_into`, `Workspace.taken(specs)`, `living_text(specs, capabilities)`, `approve_blockers`, `archive_blockers`, `next_action`, `findings_of`.
- `Status` already holds `verified`. `ChangeState` and `Approval` forbid unknown fields, so every field this plan adds has a default and an older state file still reads.
- The reference project's git layer (`adk_review/collect/git.py`, read and not run) starts git by its full path from PATH's absolute entries, as an argv list, under an environment with every `GIT_*` variable dropped and no config but the repository's, with a timeout, and on Windows ends the process tree with `taskkill`. Task 4 ports that part and nothing else.
- Git 2.56 is on this machine. Nothing here was run on Windows.

## Scope

In: coverage checks in code; the recorder and a replay of what it kept; `check`; a git layer; `verify`; the brief told what it replaces; the tasks stage shown the repository's files; `status` grouped by who acts next; a labelled set and a measurement script; the `adk web` shape; a live measurement by the owner.

Out: editing application code; running a project's tests as evidence for `verify` (the spec's second migration step); a three-way merge; the `strict` tier's second approver; `adk eval`.

## Global Constraints

Plans 1 and 2's Global Constraints hold unchanged, as the cleanup pass left them. In addition:

- No task makes a live model call in its tests or its steps. Task 11 holds the only steps that do, marked **owner**, run only on the owner's explicit go-ahead in so many words.
- A model's finding or verdict is kept only where every text it quotes is found, by code, in the file or the diff it names. One that is not is dropped, counted, and never reads as a pass: a requirement with no grounded evidence is `unclear`.
- Severities stay `ERROR`, `WARNING` and `INFO`. What the spec calls a critical finding is an `ERROR`. No fourth level.
- Git is run only through `workspace/git.py`: an argv list, never a shell; the program's full path from PATH's absolute entries; an environment with every `GIT_*` variable dropped; a timeout; verbs that read.
- A report under `changes/<id>/reports/` is generated: written whole each time, never parsed back, and never one of the files an approval fingerprints.
- A recording holds what was sent to a model and what came back. It never holds a token or a key, and it stays under `.spec/runs/`, which git ignores.
- A stage whose instruction this plan changes is named in its task. Every other stage's instruction stays byte for byte what it is, and the task that touches `stages/` proves it.
- The gate before every commit is plan 1's four commands, run in a shell that stops at the first failure.

## Review Focus

1. A model quotes text that is not in the file or the diff it names. The finding is dropped and counted; a verdict of `met` becomes `unclear`. Tests in Tasks 3 and 5.
2. A diff that holds braces, a marker line, or text that addresses the model. It reaches the model between markers and changes no instruction. Test in Task 5.
3. `verify` where there is no git repository, no base to compare with, nothing changed, or a diff past the limit. Each is a sentence and an exit code, and no state is written. Tests in Task 5.
4. A file edited after `check`, and a file edited after approval. The first makes the check stale and blocks approval; the second voids the approval and `verify` refuses. Tests in Tasks 3 and 5.
5. A run that fails, is interrupted, or is refused at the ceiling. What was called is still recorded, and nothing else is written. Test in Task 2.

## File map

```
adk_spec/domain/check.py               new: coverage of requirements by tasks
adk_spec/domain/verify.py              new: a diff's lines, and verdicts grounded in them
adk_spec/domain/report_md.py           new: check.md and verify.md, rendered
adk_spec/domain/drafts.py              + FindingsDraft, VerdictsDraft
adk_spec/domain/convert.py             + to_findings; drops a modified requirement that did not change
adk_spec/domain/model.py               + Checked, Verification; Approval.commit, Approval.override
adk_spec/domain/lifecycle.py           check and verify in the blockers; next_step
adk_spec/domain/validate.py            + coverage findings, delta.modified-unchanged
adk_spec/workspace/git.py              new: read-only git
adk_spec/workspace/runs.py             new: recordings under .spec/runs
adk_spec/workspace/context.py          + tree_text
adk_spec/workspace/config.py           [limits] keep_runs
adk_spec/workspace/layout.py           init writes .spec/.gitignore; write_report
adk_spec/orchestration/recorder.py     new: Recorder
adk_spec/orchestration/stages/         check.py, verify.py; brief.py and tasks.py changed
adk_spec/orchestration/graph.py        build_check_app, build_verify_app
adk_spec/agent.py                      new: the shape `adk web` loads
adk_spec/interfaces/cli.py             check, verify; status in groups
scripts/cases.py, scripts/measure.py   new: the labelled set and its measurement
tests/                                 test_check.py test_recorder.py test_git.py test_verify.py test_measure.py
```

---

### Task 1: Coverage, decided in code

The first judgement a model never gets: which requirement has no task, and which task names an ID nothing holds. The spec lists it first among the steps to move to Python; there is no model version to move, so it is code from the start.

**Files:**
- Create: `adk_spec/domain/check.py`
- Modify: `adk_spec/domain/validate.py`, `adk_spec/domain/convert.py`, `adk_spec/orchestration/graph.py`, `adk_spec/interfaces/cli.py`
- Test: `tests/test_check.py`, `tests/test_plan.py`, `tests/test_convert.py`

**Interfaces:**
- Consumes: `Change`, `Delta`, `Spec`, `TaskGroup`, `finding`, `SEVERITY`, `fingerprint`, `build_plan_app(*, design, ledger)`.
- Produces:
  - `check.owed(deltas: Mapping[str, Delta]) -> frozenset[str]`: every ID a delta adds or modifies.
  - `check.nameable(deltas, living: Mapping[str, Spec]) -> frozenset[str]`: `owed`, each ID a delta removes, and every requirement ID of each touched capability's living spec.
  - `check.coverage(groups: Sequence[TaskGroup], *, owed: frozenset[str], nameable: frozenset[str]) -> list[Finding]`.
  - Codes: `check.requirement-no-task` (`ERROR`), `check.task-unknown-requirement` (`ERROR`), `delta.modified-unchanged` (`WARNING`).
  - `build_plan_app(*, design: bool, ledger: UsageLedger, owed: frozenset[str], nameable: frozenset[str]) -> App`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_check.py
def test_a_requirement_no_task_names_is_found() -> None:
    groups = parse_tasks(TASKS)                      # names REQ-AUTH-004 and REQ-AUTH-002
    found = coverage(groups, owed=frozenset({"REQ-AUTH-004", "REQ-AUTH-002", "REQ-AUTH-009"}), nameable=ALL)
    assert [(f.code, f.severity) for f in found] == [("check.requirement-no-task", "ERROR")]
    assert "REQ-AUTH-009" in found[0].message

def test_a_task_naming_an_id_nothing_holds_is_found() -> None:
    found = coverage(parse_tasks(TASKS), owed=frozenset(), nameable=frozenset({"REQ-AUTH-004"}))
    assert [f.code for f in found] == ["check.task-unknown-requirement"] and "REQ-AUTH-002" in found[0].message

def test_a_change_with_no_task_yet_owes_no_coverage(tmp_path) -> None:
    # validate_change reports change.missing-tasks alone, never one finding a requirement

def test_validate_change_carries_coverage_with_the_task_lists_path(tmp_path) -> None:
    # a delta that adds a second requirement no task names: check.requirement-no-task, path "tasks.md"

def test_a_modified_requirement_that_did_not_change_is_a_warning() -> None:
    # validate_delta: MODIFIED REQ-AUTH-002 equal to the living one -> ("delta.modified-unchanged", "WARNING")

# tests/test_convert.py
def test_a_modified_requirement_the_model_copied_unchanged_is_dropped() -> None:
    # the first live run did this (docs/confirmation/2026-11-propose.md, finding 3)
    # to_deltas: modified = [REQ-AUTH-001 changed, REQ-AUTH-002 word for word] -> modified ids == ("REQ-AUTH-001",)

# tests/test_plan.py
def test_a_plan_that_covers_only_one_requirement_is_sent_back(tmp_path, capsys, fake_provider) -> None:
    # tasks naming REQ-AUTH-004 alone, for a change that also modifies REQ-AUTH-002:
    # exit 3 after three tries, "check.requirement-no-task" and "REQ-AUTH-002" in stderr, tasks.md unchanged
```

- [ ] **Step 2: Run them.** `uv run pytest tests/test_check.py tests/test_convert.py tests/test_plan.py -q`. Expected: FAIL, `No module named 'adk_spec.domain.check'` and the two older files' new tests failing on their assertions.

- [ ] **Step 3: Implement.**
  - `check.py` as the Interfaces say. A setup task that names no requirement draws no finding.
  - `validate_change`: where the change has a task, `coverage(...)` under the path `tasks.md`.
  - `validate_delta`: `delta.modified-unchanged` where `fingerprint(modified) == fingerprint(living requirement of that ID)`.
  - `to_deltas`: a modified requirement equal to the living one is left out. A delta left with nothing then fails `delta.empty`, as it should.
  - `_check_tasks` in `graph.py` becomes `_tasks_check(owed, nameable)` and runs `coverage` after `validate_tasks` and before the read-back. `_planned` computes both sets from the change.

- [ ] **Step 4: Run the suite.** `uv run pytest -q`. Expected: all pass. The live-run evidence under `docs/confirmation/2026-11-propose-run/` is not a workspace and is not read.

- [ ] **Step 5: Commit.** `feat: coverage of requirements by tasks is checked in code, at the gate and by validate`

---

### Task 2: The recorder, and what it keeps

**Files:**
- Create: `adk_spec/orchestration/recorder.py`, `adk_spec/workspace/runs.py`
- Modify: `adk_spec/orchestration/plugins.py` (`roster`), `adk_spec/workspace/config.py`, `adk_spec/workspace/layout.py` (`init`), `adk_spec/interfaces/cli.py`, `tests/conftest.py`, `README.md`
- Test: `tests/test_recorder.py`

**Interfaces:**
- Consumes: `UsageLedger`, `SchemaMismatch`, `FINDINGS`, `Usage`, `write_all`, `Config`.
- Produces:
  - `runs.Call` (frozen Pydantic model): `stage: str`, `instruction: str`, `findings: str | None` (what the gate had told the stage), `answer: str | None`, `error: str | None`, `tokens: int`, `seconds: float`.
  - `runs.Recording`: `command: str`, `change: str | None`, `at: str`, `model: str`, `outcome: str`, `calls: tuple[Call, ...]`.
  - `runs.write(workspace, recording, *, keep: int) -> Path | None`: one file, `.spec/runs/<UTC stamp>-<command>.json`, then the oldest files past `keep` removed. `keep == 0` writes nothing and returns `None`. It makes `.spec/runs/.gitignore` holding `*` where there is none.
  - `runs.read(path: Path) -> Recording`, `runs.listed(workspace) -> list[Path]`, newest first.
  - `Recorder(BasePlugin)`, name `recorder`, with `calls: list[Call]`.
  - `roster(ledger: UsageLedger, recorder: Recorder | None = None) -> list[BasePlugin]`: the recorder first where given. `build_propose_app` and `build_plan_app` each gain `recorder: Recorder | None = None` and hand it on.
  - `Config.keep_runs: int = 20`, read from `[limits] keep_runs`; a negative number or a non-integer is a `ConfigError`.
  - `Workspace.init` also writes `.spec/.gitignore` holding `.lock`.
  - `tests/conftest.py`: `FakeProvider.answers_from(recording)`, each stage's answers in the order recorded.

- [ ] **Step 1: Write the failing tests**

```python
def test_each_call_is_recorded_with_what_was_sent_and_what_came_back(tmp_path, fake_provider) -> None:
    seeded(tmp_path)
    fake_provider.answers_each_time(DELTAS, iter(["not json", None]))
    assert run(tmp_path, "propose", REQUEST, "--id", "kept") == 0
    (path,) = listed(Workspace.find(tmp_path))
    held = read(path)
    assert (held.command, held.change, held.outcome) == ("propose", "kept", "written")
    assert [call.stage for call in held.calls] == ["triage", "brief", "deltas", "deltas"]
    assert held.calls[2].answer == "not json" and "did not fit its schema" in held.calls[3].findings
    assert REQUEST in held.calls[0].instruction and held.calls[0].tokens == 120

def test_a_run_that_fails_is_recorded_and_writes_nothing_else(tmp_path, fake_provider) -> None:   # Review Focus 5
    # the ceiling refuses the third call: one recording, outcome starting "failed", its last call with no answer;
    # no change folder

def test_a_recording_is_ignored_by_git_and_holds_no_secret(tmp_path, monkeypatch, fake_provider) -> None:
    # .spec/runs/.gitignore == "*\n"; GOOGLE_API_KEY's value appears nowhere in the file

def test_only_the_newest_runs_are_kept(tmp_path, fake_provider) -> None:
    # [limits] keep_runs = 2, three commands: two files, the oldest gone; keep_runs = 0: none, and no runs folder

def test_a_recording_replays_to_the_same_files(tmp_path, fake_provider) -> None:
    # propose in one workspace; answers_from(its recording) in a second, same seed: brief.md and the delta are equal

def test_init_ignores_the_lock(tmp_path) -> None:
    assert read_text(Workspace.init(tmp_path).home / ".gitignore") == ".lock\n"
```

- [ ] **Step 2: Run them.** Expected: FAIL, `No module named 'adk_spec.workspace.runs'`.

- [ ] **Step 3: Implement.** The recorder notes the instruction, `state[FINDINGS]` and the clock in `before_model_callback`, and completes the call in `after_model_callback` with the answer's text, its error code and its tokens. A call with no answer is completed when the next one starts or when the command reads `calls`. `propose` and `plan` each make one recorder beside their ledger and write the recording in a `finally`, so a failed or interrupted run is kept; the outcome is `written`, `nothing owed`, `failed: <sentence>` or `interrupted`.

- [ ] **Step 4: Run the suite.** Expected: all pass. Every stage's instruction is byte for byte what it was: `uv run python scripts/dump_instructions.py` before and after, compared (the script is added by this task, from the one used in plan 2's cleanup).

- [ ] **Step 5: Commit.** `feat: every model call is recorded under .spec/runs, and a recording replays`

---

### Task 3: `check`

**Files:**
- Create: `adk_spec/orchestration/stages/check.py`, `adk_spec/domain/report_md.py`
- Modify: `adk_spec/domain/drafts.py`, `adk_spec/domain/convert.py`, `adk_spec/domain/model.py`, `adk_spec/domain/lifecycle.py`, `adk_spec/workspace/layout.py`, `adk_spec/orchestration/graph.py`, `adk_spec/interfaces/cli.py`, `tests/conftest.py` (`CANNED_FINDINGS`), `README.md`
- Test: `tests/test_check.py`, `tests/test_lifecycle.py`

**Interfaces:**
- Consumes: Task 1's `coverage`; Task 2's `Recorder`; `approval_files`, `Workspace.approval_texts`, `Workspace.write_into`.
- Produces:
  - `FindingDraft`: `kind: Literal["contradiction", "ambiguity", "gap", "duplication", "constitution"]`, `severity: Literal["critical", "warning", "note"]`, `file: str`, `quote: str`, `message: str`. `FindingsDraft`: `findings: list[FindingDraft]`.
  - `convert.to_findings(draft: FindingsDraft, texts: Mapping[str, str]) -> tuple[list[Finding], int]`: the findings whose quote is in the text of the file they name, and how many were dropped. Code `check.<kind>`; `critical` is `ERROR`, `warning` `WARNING`, `note` `INFO`; `path` the file; `line` where the quote starts. A quote is compared with runs of whitespace read as one space, and must hold eight characters at least.
  - `model.Checked`: `at: str`, `files: dict[str, str]`, `blocking: int`. `ChangeState.check: Checked | None = None`. `Approval.override: str | None = None`.
  - `lifecycle.check_blockers(state, files: Mapping[str, str]) -> list[Finding]`: nothing for a lean change; else `check.missing`, `check.stale` or `check.blocking`, each an `ERROR`. `approve_blockers` gains `files` and `override: bool`, and adds them unless overridden.
  - `report_md.render_check(change_id, at, findings, dropped) -> str`.
  - `Workspace.write_report(change_id, name, text) -> Path`, under `reports/`.
  - `build_check_app(*, ledger, recorder) -> App`: `START -> check -> check_gate -> (end)`.
  - Commands: `adk-spec check <id> [--no-model]`; `adk-spec approve <id> --override "<reason>"`.

`check` runs the code's passes always and the model's pass unless `--no-model`. It writes `reports/check.md` and records `Checked` with the fingerprints `approval_files` gives. Exit 0 where nothing blocks, 1 where a finding does, 3 where the model's pass failed (nothing is then recorded, and the report says the pass did not run). The stage's instruction opens `You review the files of a change against each other. You change none of them.` and reads the rules, the living specs, and each of the change's files under a line naming its path.

- [ ] **Step 1: Write the failing tests**

```python
def test_a_finding_is_kept_only_where_its_quote_is_in_the_file() -> None:                          # Review Focus 1
    texts = {"brief.md": BRIEF, "specs/auth/spec.md": DELTA}
    real = {"kind": "contradiction", "severity": "critical", "file": "brief.md",
            "quote": "Passwords are phished", "message": "The delta keeps password sign-in."}
    invented = {**real, "quote": "Passwords are never used"}
    elsewhere = {**real, "file": "tasks.md"}
    kept, dropped = to_findings(FindingsDraft.model_validate({"findings": [real, invented, elsewhere]}), texts)
    assert [(f.code, f.severity, f.path) for f in kept] == [("check.contradiction", "ERROR", "brief.md")]
    assert dropped == 2 and kept[0].line == 5

def test_check_writes_a_report_and_records_what_it_read(tmp_path, capsys, fake_provider) -> None:
    # CANNED_FINDINGS holds one warning that quotes the sample brief: exit 0; reports/check.md names it;
    # state.check.blocking == 0 and state.check.files == approval_files(...)

def test_a_critical_finding_blocks_approval_until_it_is_fixed_or_overridden(tmp_path, capsys, fake_provider) -> None:
    # a standard change, a grounded critical finding: check exits 1; approve exits 1 with check.blocking;
    # approve --override "the delta is right" exits 0 and the state's approval.override holds the reason

def test_an_edit_after_the_check_makes_it_stale(tmp_path, capsys, fake_provider) -> None:          # Review Focus 4
    # check, then one word added to brief.md: approve exits 1 with check.stale; status says to run check

def test_a_standard_change_never_checked_cannot_be_approved_and_a_lean_one_can(tmp_path, capsys) -> None:
def test_no_model_runs_the_codes_passes_alone(tmp_path, fake_provider) -> None:                    # no request sent
def test_a_failed_pass_records_no_check(tmp_path, capsys, fake_provider) -> None:                  # exit 3
def test_a_report_is_no_part_of_an_approval(tmp_path) -> None:                                     # approve, check again: not stale
```

- [ ] **Step 2: Run them.** Expected: FAIL on the missing names.
- [ ] **Step 3: Implement** as the Interfaces say. The gate's check is the schema alone: a finding off its file is dropped by `to_findings`, not sent back.
- [ ] **Step 4: Run the suite.** Expected: all pass, and the older stages' instructions byte for byte what they were.
- [ ] **Step 5: Commit.** `feat: check judges a change's files against each other, and a blocking finding holds approval`

---

### Task 4: Read-only git

**Files:**
- Create: `adk_spec/workspace/git.py`
- Test: `tests/test_git.py`, `tests/conftest.py` (`repository(root)`, which makes a repository with one commit, by `subprocess` and an argv list)

**Interfaces:**
- Produces:
  - `GitError(Exception)`; `GIT_TIMEOUT_S = 30`.
  - `on_path(name: str) -> str | None`: the program's full path from PATH's absolute entries, never from the current folder.
  - `git(root: Path, *args: str, ok: tuple[int, ...] = (0,)) -> str`: stdout decoded as UTF-8. `GitError` for a code outside `ok`, for a timeout, and where git is not found.
  - `is_repository(root) -> bool`, `head(root) -> str | None`, `resolves(root, ref) -> str | None` (the commit's full ID).
  - `diff(root: Path, base: str) -> str`: `base` against the working tree, paths from `root`, with `.spec/` left out, no colour, no external diff, no textconv. A file git does not track yet reads as added; past `UNTRACKED_MAX = 500` such files it is a `GitError`.
  - `files(root: Path) -> list[str]`: every file git tracks or would, nothing it ignores, forward slashes.

- [ ] **Step 1: Write the failing tests**

```python
def test_a_diff_is_the_base_against_the_working_tree_without_the_spec_tree(tmp_path) -> None:
    repository(tmp_path)                                    # commits src/app.py and .spec/config.toml
    base = head(tmp_path)
    (tmp_path / "src/app.py").write_text("def login():\n    return passkey()\n", encoding="utf-8")
    (tmp_path / ".spec/config.toml").write_text("# changed\n", encoding="utf-8")
    text = diff(tmp_path, base)
    assert "+    return passkey()" in text and ".spec/" not in text

def test_git_is_never_started_from_the_current_folder(tmp_path, monkeypatch) -> None:
    # PATH=".": on_path("git") is None, and git(...) raises GitError naming PATH

def test_a_persons_own_git_settings_change_nothing(tmp_path, monkeypatch) -> None:
    # GIT_DIR set to another repository, and GIT_EXTERNAL_DIFF set to a program: the diff is the same

def test_a_folder_that_is_no_repository_and_a_ref_that_is_none(tmp_path) -> None:
    # is_repository False; head None; resolves(repo, "no-such") None; diff(tmp_path, "HEAD") raises GitError

def test_a_command_past_its_time_is_stopped(tmp_path, monkeypatch) -> None:
    # GIT_TIMEOUT_S patched to 0.01 around a `git` stand-in that sleeps: GitError naming the limit
```

- [ ] **Step 2: Run them.** Expected: FAIL, `No module named 'adk_spec.workspace.git'`.
- [ ] **Step 3: Implement**, porting from `adk_review/collect/git.py` the PATH lookup, the environment (every `GIT_*` dropped; `GIT_CONFIG_GLOBAL` and the system config off; `LC_ALL=C`; `safe.directory` set to the repository), the run with its timeout, and on Windows `taskkill /F /T /PID` before the output is read to its end. `test_layering.py` gains `subprocess` among what only `workspace/git.py` may import.
- [ ] **Step 4: Run the suite.** Expected: all pass.
- [ ] **Step 5: Commit.** `feat: a read-only git layer, started by full path under a clean environment`

---

### Task 5: `verify`

**Files:**
- Create: `adk_spec/domain/verify.py`, `adk_spec/orchestration/stages/verify.py`
- Modify: `adk_spec/domain/drafts.py`, `adk_spec/domain/model.py`, `adk_spec/domain/lifecycle.py`, `adk_spec/domain/report_md.py`, `adk_spec/orchestration/graph.py`, `adk_spec/interfaces/cli.py`, `tests/conftest.py` (`CANNED_VERDICTS`), `README.md`
- Test: `tests/test_verify.py`, `tests/test_lifecycle.py`

**Interfaces:**
- Consumes: Task 4's `diff`, `head`, `resolves`; Task 1's `owed`; Task 2's `Recorder`; Task 3's `Workspace.write_report`.
- Produces:
  - `EvidenceDraft`: `path: str`, `quote: str`. `VerdictDraft`: `id: str`, `verdict: Literal["met", "unmet", "unclear"]`, `evidence: list[EvidenceDraft]`, `reason: str`. `VerdictsDraft`: `verdicts: list[VerdictDraft]`.
  - `verify.lines_of_diff(diff: str) -> dict[str, tuple[list[str], list[str]]]`: by path, the lines added and the lines removed, without their sign.
  - `verify.Verdict` (frozen): `id`, `verdict`, `evidence: tuple[tuple[str, str], ...]`, `reason`.
  - `verify.grounded(draft: VerdictsDraft, diff: str, *, added: frozenset[str], removed: frozenset[str]) -> list[Verdict]`: one verdict for each ID of `added | removed`, in order. `met` stands only where a quote of its evidence is a line of the diff for its path: an added line for an ID of `added`, a removed line for one of `removed`. Otherwise it becomes `unclear`, its reason `no quoted line is in the diff`. An ID the model gave no verdict is `unclear`. A verdict for any other ID is left out.
  - `model.Verification`: `at`, `base: str`, `diff: str` (its fingerprint), `verdicts: dict[str, str]`, `override: str | None = None`. `ChangeState.verification: Verification | None = None`. `Approval.commit: str | None = None`, recorded by `approve` where the root is a git repository.
  - `report_md.render_verify(change_id, at, base, verdicts) -> str`.
  - `DIFF_MAX_CHARS = 200_000`.
  - `build_verify_app(*, ledger, recorder) -> App`.
  - Command: `adk-spec verify <id> [--base <ref>] [--override "<reason>"]`.

`verify` refuses with exit 1 a change that is not approved or whose approval is void. It refuses with exit 2 a root that is no repository, a base that does not resolve (the approval's `commit` where `--base` is not given, and a sentence asking for `--base` where neither is there), and a diff past `DIFF_MAX_CHARS`, which is never cut. An empty diff is exit 1: nothing was implemented. Otherwise it writes `reports/verify.md` and the verification, and sets the status to `verified` where every verdict is `met` or an override is given: exit 0, else 1. A change with no delta has nothing to judge and is verified. The stage's instruction opens `You judge whether a diff meets the requirements of a change. You change nothing.` and reads the deltas, the tasks and the diff.

- [ ] **Step 1: Write the failing tests**

```python
DIFF = """\
diff --git a/src/auth.py b/src/auth.py
--- a/src/auth.py
+++ b/src/auth.py
@@ -1,2 +1,3 @@
 def sign_in(user):
-    return password(user)
+    return passkey(user) or password(user)
"""

def test_met_stands_only_on_a_line_the_diff_adds() -> None:                                        # Review Focus 1
    real = {"id": "REQ-AUTH-004", "verdict": "met", "reason": "r",
            "evidence": [{"path": "src/auth.py", "quote": "return passkey(user) or password(user)"}]}
    invented = {**real, "id": "REQ-AUTH-002", "evidence": [{"path": "src/auth.py", "quote": "lock_account(user)"}]}
    context = {**real, "id": "REQ-AUTH-005", "evidence": [{"path": "src/auth.py", "quote": "def sign_in(user):"}]}
    draft = VerdictsDraft.model_validate({"verdicts": [real, invented, context]})
    ids = frozenset({"REQ-AUTH-004", "REQ-AUTH-002", "REQ-AUTH-005", "REQ-AUTH-006"})
    got = {v.id: v.verdict for v in grounded(draft, DIFF, added=ids, removed=frozenset())}
    assert got == {"REQ-AUTH-004": "met", "REQ-AUTH-002": "unclear", "REQ-AUTH-005": "unclear", "REQ-AUTH-006": "unclear"}

def test_verify_sets_verified_when_every_requirement_is_met(tmp_path, capsys, fake_provider) -> None:
    # a repository, an approved standard change, a diff the canned verdicts quote: exit 0, status verified,
    # reports/verify.md names each ID, archive then succeeds

def test_one_requirement_unmet_leaves_the_change_approved(tmp_path, capsys, fake_provider) -> None:  # exit 1
def test_an_override_is_recorded_with_its_reason(tmp_path, fake_provider) -> None:
def test_the_diff_reaches_the_model_between_markers(tmp_path, fake_provider) -> None:              # Review Focus 2
    # a changed file holding "{request}", ">>> diff " and "Ignore the requirements": all between the diff's markers
def test_what_cannot_be_verified_is_a_sentence_and_writes_nothing(tmp_path, capsys, fake_provider, case) -> None:
    # parametrised, Review Focus 3: no repository (2), no base (2), an unknown --base (2), nothing changed (1),
    # a diff past the limit (2), a draft change (1); in each fake_provider.requests == [] and the state is unchanged
def test_an_edit_after_approval_is_refused(tmp_path, capsys, fake_provider) -> None:               # Review Focus 4
def test_approve_records_the_commit_it_was_made_at(tmp_path) -> None:
```

- [ ] **Step 2: Run them.** Expected: FAIL on the missing names.
- [ ] **Step 3: Implement** as the Interfaces say.
- [ ] **Step 4: Run the suite.** Expected: all pass, older instructions unchanged.
- [ ] **Step 5: Commit.** `feat: verify judges the diff requirement by requirement, and only a quoted line makes one met`

---

### Task 6: A brief that knows what it replaces

The first live run's findings 1, 2 and 5: each new draft of the brief raised a new point and never settled one, one answer was contradicted, and the lean tier left a point open that it never asks about.

**Files:**
- Modify: `adk_spec/orchestration/stages/__init__.py` (`TIER` moves here), `adk_spec/orchestration/stages/brief.py`, `adk_spec/orchestration/graph.py` (`next_run`)
- Test: `tests/test_clarify.py`, `tests/test_propose.py`

**Interfaces:**
- Produces: `brief.REPLACES = "replaces"`, the state key of the brief a new draft replaces, as its file. `next_run` seeds it for the entry `brief`. `stages.TIER = "tier"`, which `graph.py` imports.

The brief's instruction changes, and only it. Its guide gains three sentences, and it gains one section:

```
Leave every point you cannot settle at once: a later draft is for what an answer opened, not for a point you could have raised before.
Where a brief to replace is given, keep what it says, settle each point an answer settles, and contradict no answer.
On the lean tier no question is asked: leave no marker there, and state what you assume in its place. This change's tier is {tier}.

## The brief you are replacing
<<< replaces ...
```

- [ ] **Step 1: Write the failing tests**

```python
def test_a_new_draft_is_given_the_brief_it_replaces(tmp_path, monkeypatch, fake_provider) -> None:
    # two rounds: the second brief's instruction holds the first brief's "# Sign in with a passkey" between the
    # `replaces` markers, and the first brief's instruction holds nothing there
def test_the_brief_is_told_its_tier(tmp_path, fake_provider) -> None:
    # "--tier lean": "This change's tier is lean." in the brief's instruction; without --tier, the model's tier
```

- [ ] **Step 2: Run them.** Expected: FAIL on the assertions.
- [ ] **Step 3: Implement.** No gate enforces the lean rule: a lean brief with a marker is written as today, and approval waits on it.
- [ ] **Step 4: Run the suite.** Expected: all pass. `scripts/dump_instructions.py` shows the brief's instruction changed and no other.
- [ ] **Step 5: Commit.** `feat: a redrafted brief reads the brief it replaces, and every brief its tier`

Whether a real model now converges is not shown by this task. Task 11 measures it.

---

### Task 7: What `plan`'s stages are shown, and what `plan` replaces

Findings 6 and 7 of the first live run (file paths were invented, and a design took a suggested answer for a mechanism that exists), and two of the review's minors.

**Files:**
- Modify: `adk_spec/workspace/context.py`, `adk_spec/orchestration/stages/__init__.py`, `adk_spec/orchestration/stages/tasks.py`, `adk_spec/orchestration/stages/design.py`, `adk_spec/interfaces/cli.py`
- Test: `tests/test_plan.py`, `tests/test_context.py`

**Interfaces:**
- Consumes: Task 4's `files`, `is_repository`.
- Produces:
  - `context.TREE_MAX_PATHS = 300`; `context.tree_text(paths: Sequence[str]) -> str`: every path, one a line, where there are `TREE_MAX_PATHS` at most; past that, a first line saying so and each folder two levels deep with the number of files under it. Nothing where there is no path.
  - `stages.TREE = "tree"` and `stages.FILES`, a section `## The files of this repository`, read by the design's and the tasks' instructions. The tasks' guide gains `Name files by the paths the repository uses. Where a file is new, put it beside its kind.` The design's gains `Call existing only what the files or the living specs show.`
  - `adk-spec plan <id> --replace`.

- [ ] **Step 1: Write the failing tests**

```python
def test_plans_stages_are_shown_the_repositorys_files(tmp_path, fake_provider) -> None:
    # repository(tmp_path) with src/app.py and tests/test_app.py, a change that needs a design: both paths between
    # the `tree` markers of the design's and of the tasks' instruction; no .spec/ path in either
def test_a_tree_past_the_limit_is_folders_with_counts_and_says_so() -> None:
    paths = [f"src/pkg{n % 4}/mod{n}.py" for n in range(301)]
    text = tree_text(paths)
    assert text.splitlines()[0].startswith("301 files: too many to list") and "src/pkg0/ (76 files)" in text
def test_plan_reads_a_design_written_by_hand(tmp_path, fake_provider) -> None:
    # needs_design false, a design.md in the folder: its text between the `design` markers, and no design call
def test_plan_does_not_replace_a_task_list_someone_has_started(tmp_path, capsys, fake_provider) -> None:
    # one box ticked: exit 1, "--replace" in stderr, no request sent, the file as it was; with --replace: exit 0
def test_plan_says_when_it_replaced_a_file(tmp_path, capsys, fake_provider) -> None:
    # tasks.md there, no box ticked: "replaced  .spec/changes/passkeys/tasks.md"
```

- [ ] **Step 2: Run them.** Expected: FAIL on the missing names.
- [ ] **Step 3: Implement.** Outside a git repository the tree is empty and the section reads as nothing.
- [ ] **Step 4: Run the suite.** `scripts/dump_instructions.py` shows the design's and the tasks' instructions changed and no other.
- [ ] **Step 5: Commit.** `feat: plan's stages read the repository's files, and plan never replaces started work unasked`

---

### Task 8: Status by who acts next

**Files:**
- Modify: `adk_spec/domain/lifecycle.py`, `adk_spec/interfaces/cli.py`, `README.md`
- Test: `tests/test_lifecycle.py`, `tests/test_cli.py`

**Interfaces:**
- Produces:
  - `lifecycle.Step` (frozen dataclass): `actor: Literal["you", "run", "done"]`, `phrase: str`.
  - `lifecycle.next_step(state, findings, stale, *, files: Mapping[str, str] | None = None) -> Step`. `next_action` stays, returning the phrase.
  - What blocks a draft is read from one ordered table, first match first: an `ERROR` (you: fix what validate lists), an open marker (you: settle it in the brief), no task (run: plan), a base not recorded (run: rebase), no check or a stale one on a standard change (run: check), a blocking check (you: fix what `reports/check.md` lists), nothing (you: approve).
  - `status` prints three groups, each only where it has a change: `Waiting on you`, `Ready to run`, and with `--all` `Done`. `--json` rows gain `"actor"`.
  - `propose` prints `design    owed: <reason>` where the brief says a design is needed; `Drafted` gains `design_reason: str`.

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.parametrize(("blocking", "actor", "phrase"), [
    ([ERROR, MARKER, NO_TASKS], "you", "fix what `adk-spec validate passkeys` lists"),
    ([MARKER, NO_TASKS, NO_BASE], "you", "settle the open point in brief.md"),
    ([NO_TASKS, NO_BASE], "run", "run `adk-spec plan passkeys`"),
    ([NO_BASE], "run", "run `adk-spec rebase passkeys`"),
    ([], "you", "run `adk-spec approve passkeys`"),
])
def test_the_first_thing_that_blocks_a_draft_names_the_next_step(blocking, actor, phrase) -> None: ...
def test_a_standard_draft_with_nothing_else_owed_is_ready_for_check() -> None: ...
def test_status_groups_changes_by_who_acts_next(tmp_path, capsys) -> None:
    # "Waiting on you" above "Ready to run"; a group with no change is not printed
```

- [ ] **Step 2: Run them.** Expected: FAIL on the missing names. One older case changes with the table and is updated in the same step: a marker with a missing base now says to settle the marker, where it said to rebase.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the suite.**
- [ ] **Step 5: Commit.** `feat: status groups changes by who acts next, from one table of what blocks a change`

---

### Task 9: A labelled set, and its measurement

**Files:**
- Create: `scripts/cases.py`, `scripts/measure.py`, `scripts/dump_instructions.py` (if Task 2 has not), `docs/measurements/README.md`
- Test: `tests/test_measure.py`

**Interfaces:**
- Consumes: the commands, in process; Task 2's recordings.
- Produces:
  - `cases.Case` (frozen dataclass): `name`, `build: Callable[[Path], str]` (makes a workspace and returns the change's ID), `command: tuple[str, ...]`, `expect: tuple[Expected, ...]`, `clean: bool`. `Expected`: `code` (a prefix), `path`, `holds` (a phrase its message or quote must hold).
  - `cases.CASES`, six: a brief and a delta that contradict each other; a requirement whose statement cannot be tested ("quickly"); a requirement no task names (found by code, every run); a constitution rule the tasks break; a consistent change (`clean`); and for `verify` a diff that implements one of two requirements.
  - `measure.scored(case, findings) -> Score`: `caught: int`, `missed: int`, `false_blocking: int`.
  - `uv run python -m scripts.measure [--runs N] [--case NAME] [--out FILE]`: each case built in a temporary folder and run N times on the arm the environment names; a table a case of how often each planted fault was caught, the blocking findings on nothing planted, the findings dropped for a quote that is not there, the tokens and the time; written to `--out` with the model's name and this package's commit.

- [ ] **Step 1: Write the failing tests**

```python
def test_a_planted_fault_is_caught_by_a_finding_on_its_file_that_names_it() -> None: ...
def test_a_blocking_finding_on_a_clean_case_is_counted_as_false() -> None: ...
def test_every_case_builds_a_workspace_that_validates(tmp_path) -> None:
    # for each case: build, then `validate` exits 0 or 1 and never 2: the labelled set itself is well formed
def test_the_measurement_runs_whole_on_the_fake(tmp_path, fake_provider) -> None:
    # --runs 2 with canned findings: a table with six rows, and the code-found case caught 2 of 2
```

- [ ] **Step 2: Run them.** Expected: FAIL, `No module named 'cases'`.
- [ ] **Step 3: Implement.** The script refuses to start on an arm that is not ready, and prints how many model calls it is about to make before the first.
- [ ] **Step 4: Run the suite.**
- [ ] **Step 5: Commit.** `feat: a labelled set of six changes, and a script that measures how often each fault is caught`

---

### Task 10: The shape `adk web` loads

Small on purpose: a way to watch a run's events in ADK's own interface, and nothing a person depends on.

**Files:**
- Create: `adk_spec/agent.py`
- Modify: `tests/test_layering.py`
- Test: `tests/test_agent.py`

**Interfaces:**
- Produces: `adk_spec.agent.root_agent` and `adk_spec.agent.app`: `propose` from the request typed in the chat, with `ask=False`, in the workspace found from the current folder, ending on one message that holds the brief and the deltas as their files. It writes nothing.

- [ ] **Step 1: Validate first.** An offline probe, `q20_adk_web_loader_probe.py`: ADK's own loader (`google.adk.cli.utils.agent_loader.AgentLoader`) loads the package from its parent folder and finds `root_agent`, with no server started. If it does not, or loading needs the engine imported by `adk_spec/__init__.py`, this task stops there and the reason is written in this plan: the commands are the product.
- [ ] **Step 2: Write the failing test**

```python
def test_the_chat_shape_drafts_and_writes_nothing(tmp_path, monkeypatch, fake_provider) -> None:
    # cwd a seeded workspace; importlib.reload(adk_spec.agent); one run with the request as the user's message:
    # the last event's text holds "# Sign in with a passkey" and "## ADDED Requirements"; no new change folder
```

- [ ] **Step 3: Implement.** `agent.py` is the one module that builds at import, as ADK's loader requires, and the layering test names it as the one exception.
- [ ] **Step 4: Run the suite.**
- [ ] **Step 5: Commit.** `feat: an agent.py for adk web, which drafts in the chat and writes nothing`

---

### Task 11: The first measurement (owner)

Every step here calls a model with the owner's account, or needs a machine or a key this session does not have.

- [ ] **Step 1 (owner, live): Copilot, macOS.** `uv run python -m scripts.measure --runs 3 --out docs/measurements/2026-11-copilot-gpt-4.1.md`. It prints its call count first: 15 calls for the six cases at three runs each (one case is decided by code and costs none), near 40,000 tokens at the first live run's rates.
- [ ] **Step 2 (owner, live): the standard tier once more.** The request of the first live run's second command, each question answered with `=`. Record beside the first run whether the asking now ends before the third round, and whether any answer is contradicted.
- [ ] **Step 3: Decide from the two records**, and write the decisions in the measurement file: a planted fault caught in fewer than two runs of three names the instruction to change first; a clean case blocked in any run names the severity rule to loosen; the largest command sets the README's `max_tokens` example.
- [ ] **Step 4 (owner): the Gemini arm**, once a key is set: `adk-spec smoke`, then Step 1 with `SPEC_PROVIDER=gemini`.
- [ ] **Step 5 (owner): Windows.** `uv sync --locked`, the four gate commands, `adk-spec login`, `adk-spec smoke`. Record the result in `docs/confirmation/`.

---

## What changed while this plan was executed

Tasks 1 to 10 were built in the order 4, 1, 2, 3, 5, 6, 7, 8, 9, 10, each test first, with no model called. Task 11
is the owner's and was not run.

**Where the code differs from the tasks above** (each a ruling in the ledger).

- **Coverage is `domain/check.py`'s `coverage_of(change, living)`, added by `findings_of`,** not by
  `validate_change`: the validator reads each file by itself, and `check.py` reads the validator's `finding`, so
  the call the other way would be a cycle. Every command that reads a change goes through `findings_of`. A task may
  name any requirement a living spec holds, and coverage is skipped while one of the change's own deltas does not
  read.
- **What a check still owes an approval is `lifecycle.check_blockers(state, files)`,** kept apart from the
  validator's findings. `approve_blockers` is unchanged, and `next_step` and `next_action` take the check's blockers
  as `check=`. Mixed into the findings, a change never checked would fail `validate` and be refused by `plan`.
  `_assessed` in the command returns four values: the change, its findings, what its approval no longer covers, and
  what its check owes.
- **`check` writes no report and records nothing where the model's pass fails,** and does not run that pass while a
  file has an error of structure. `--override` sets aside a blocking finding of a current check only: a check never
  run, or stale, is still owed, and `check --no-model` costs nothing.
- **`diff` reads a file git does not track yet as added,** and refuses past 500 such files. The listing is
  `files(root)`.
- **The verify gate sends the stage back where a requirement has no verdict.** A verification that does not pass
  sets a `verified` change back to `approved`.
- **The measurement runs as `uv run python -m scripts.measure`.** A planted contradiction counts as caught by a
  finding of kind `contradiction` or `gap`.
- **A recording names the change asked for with `--id` even where nothing was written,** and one model a command.
- `Checked` and `Verification` also record the model that judged. An approval records the commit it was made at.

**What the tasks did not foresee.**

- Four older fixtures gave a change a task list written for another delta, which the new coverage rule rightly
  refused. `samples.tasks_for(*ids)` makes a list that serves what a test's change adds.
- The sample task list has a ticked box, so twelve older tests of `plan` now pass `--replace`.
- Three older cases of the next step changed with the table: a draft with an open point is told to settle it in
  `brief.md`, before a plan or a rebase.

**What the cleanup pass after the phase changed** (four reviewers: reuse, simplification, efficiency, depth).

- **Where the work began is the change's own, `ChangeState.base_commit`,** set at the first approval and kept
  through an approval made again and through a rebase. It had been the approval's, so a person who committed half
  the work, reworded a task and approved again, as `status` told them to, moved the base past the work already
  done, and `verify` then judged the rest alone. `Approval.commit` is gone.
- **One test of a model's quote,** `quoted_at` in `domain/text.py`, serves a finding's quote in a file, a verdict's
  in a diff, and the measurement, which had a copy of its own that had already drifted.
- **The lifecycle decides what a check and a verification record:** `checked`, `verified` and `verify_blockers`
  stand beside `approve`, and `approve_blockers` takes the check's blockers and the override. The command prints
  and writes.
- **What holds a draft is one table of codes.** Whatever blocks an approval and has no step of its own falls to
  "fix what validate lists", so `status` cannot say to approve what `approve` refuses. An approved standard change
  that was edited is told to check before it approves again.
- The command reads a change as one record, `Assessed`, asks a model through one helper, `_asked`, and ends on one
  line, `_say_next`. `plan`, `check` and `verify` share one handler shape, `_drafting`. A recording of one of
  them ends `answered`: it closes when the model's pass does.
- `files_of(made)` in `graph.py` is a draft's files, for the command to write and the chat to show.
  `required_text` is in the verify stage, where `scripts/dump_instructions.py` can see it. `approve` and `plan`
  each start one git process fewer.
- Every stage's instruction is byte for byte what it was.

**Validated by a probe before it was built:** what a recorder sees (`q19`), and what the shape `adk web` loads has
to be (`q20`). `adk web` itself was never started.

## What this plan leaves

Running a project's tests as evidence for `verify`; a route for `check`'s contradiction pass to move to code; triage by rules; a capability-to-path map; a lessons file a workspace keeps between runs; the `strict` tier. Each waits on a measurement this plan makes possible.
