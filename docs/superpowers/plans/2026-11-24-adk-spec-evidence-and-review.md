# Evidence and Review Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep what `verify` and the deltas already prove and put it where each reader looks: an approver's view, the
next work, evidence beside the living specs with suspect requirements, a CI gate, and a pull request's summary and a
changelog.

**Architecture:** Pure renderers and checks in `adk_spec/domain/` (one new `*_md.py` per file adk-spec writes, each
rendered and read back), file reading and writing in `adk_spec/workspace/`, printing in `adk_spec/interfaces/cli.py`.
No model call, no network, no new command, flag or `change.json` field.

**Tech Stack:** Python 3.14, pydantic, `difflib`, git through `workspace/git.py`, pytest with the `fake_provider`.

**Spec:** `docs/superpowers/specs/2026-11-24-evidence-and-review-design.md`

## Global Constraints

- No new subcommand, flag or `change.json` field; each command prints at most one more line.
- Layers: `domain` does no I/O; `workspace` imports no network module; `cli` imports no engine module at its top.
- No new file enters an approval's fingerprints (`Workspace.approval_texts`: brief, design, tasks, delta specs).
- Every kept quote passes through the scrubbed diff; a quote holding `[REDACTED` is dropped.
- Suspect requirements are INFO; `change.approval-void` and `change.work-drifted` are WARNING; `change.drift-unknown`,
  `spec.evidence-gone`, `spec.evidence-unreadable` are INFO.
- Evidence: at most 240 characters a quote, at most 3 quotes a requirement; at most 20 files confirmed when a quote is
  looked for elsewhere; the CI summary at most 50 rows; the next step names at most 3 unmet IDs.
- C901 at most 10, lines at most 120, test names are sentences; macOS and Windows.
- The gate before each commit: `uv run ruff check . && uv run ruff format --check . && uv run pyrefly check &&
  uv run pytest -q -p no:cacheprovider`, run in `bash -eo pipefail`.

## Review Focus

- A file with CRLF line endings holding a kept quote: the quote is found, never suspect (`quoted_at` reads `\r` as
  space). Test in Task 4.
- `GITHUB_ACTIONS=true` with `GITHUB_STEP_SUMMARY` unset or a folder that is not there: annotations are printed and
  `validate` exits as without them. Test in Task 5.
- A `.spec/changelog.md` that is not UTF-8: `archive` still archives, leaves the file as it is and says so in one
  line. Test in Task 6.
- `verify` run twice: the second's evidence replaces the first's, and `archive` folds only the recorded
  verification's. Test in Task 4.
- A lean change archived without a verification: no evidence folded, the changelog still written. Test in Task 6.

---

### Task 1: The approver's view, `reports/review.md`

**Files:**
- Create: `adk_spec/domain/review_md.py`, `tests/test_review.py`
- Modify: `adk_spec/workspace/layout.py` (a `touching` method beside `taken`), `adk_spec/interfaces/cli.py`
  (`_say_next`, `_approve`, `_archive`), `README.md` (approve section)

**Interfaces:**
- Produces: `render_review(change_id: str, deltas: Mapping[str, Delta], living: Mapping[str, Spec],
  overlaps: Mapping[str, Sequence[str]]) -> str`; `review_said(deltas: Mapping[str, Delta],
  overlaps: Mapping[str, Sequence[str]]) -> str` (the text after `review    <path>: `);
  `Workspace.touching(change_id: str) -> dict[str, list[str]]` (requirement ID to the other open changes, sorted,
  that modify or remove it); `REVIEW = "review.md"` in `layout.py`.

- [ ] **Step 1: Write the failing tests** in `tests/test_review.py`:
  - `test_a_modified_requirement_is_shown_as_a_diff_of_the_living_one`: `render_review("passkeys", DELTAS, LIVING,
    {})` holds a `-` line and a `+` line of REQ-AUTH-002's statement from `samples`, the added REQ-AUTH-004 whole, and
    REQ-AUTH-001 under removed with its reason.
  - `test_another_open_change_modifying_a_requirement_is_named`: a second change `other` whose delta has
    `### REQ-AUTH-002:` under `## MODIFIED Requirements` gives `ws.touching("passkeys") == {"REQ-AUTH-002": ["other"]}`.
  - `test_a_requirement_only_mentioned_in_another_change_is_no_overlap`: `other` names REQ-AUTH-002 in an ADDED
    statement only, `touching` is `{}`.
  - `test_an_archived_change_is_no_overlap`.
  - `test_each_command_that_leaves_a_change_to_be_read_writes_the_view`: after `propose`, `plan`, `check --no-model`
    and `rebase` the file `.spec/changes/passkeys/reports/review.md` exists and the output holds `review    ` with
    `modified`; an approved change's `verify` writes none afresh (its mtime is unchanged).
  - `test_approve_notes_another_open_change_on_the_same_requirement`: output holds `note` and `other`; exit 0.
  - `test_archive_stopped_by_a_moved_base_names_the_view`: the living REQ-AUTH-002 edited after approval; `archive`
    exits 1, stderr names `reports/review.md`, the file holds the living spec's new statement on a `-` line.

- [ ] **Step 2: Run them**: `uv run pytest tests/test_review.py -q -p no:cacheprovider`. Expected: FAIL, no module
  `adk_spec.domain.review_md`.

- [ ] **Step 3: Implement.**
  - `review_md.render_review`: `# Review: <id>`; per capability (sorted) a `## <capability>` with `### Added`,
    `### Modified`, `### Removed` subsections, each present only where it holds something. Modified: a fenced `diff`
    block of `difflib.unified_diff(render_requirement(living_req), render_requirement(delta_req), lineterm="")`
    with `n=3`, its two `---`/`+++` header lines named `living` and `<id>`; a requirement the living spec lacks is
    shown whole. Then `### Also changed by open changes`, one line per overlapped ID.
  - `review_said`: counts as `1 added, 2 modified, 1 removed` (zeros left out), then
    `; REQ-AUTH-002 also changed by other` for at most 3 overlaps, then `and N more`.
  - `Workspace.touching`: the loop of `taken` over open changes but `change_id`; each delta read as text with
    `errors="replace"`; an ID counts where a line `### REQ-…:` (REQ_ID) follows a `## MODIFIED Requirements` or
    `## REMOVED Requirements` heading and no other `## ` heading since. Only IDs this change modifies or removes are
    kept by the caller.
  - `cli._say_next`: take the `Assessed` it already makes; where its state is `draft` and its change has a delta,
    write `review.md` with `workspace.write_report` and print `review    <shown path>: <review_said>` before `next`.
  - `cli._approve`: before its `next`, where `touching` meets this change's modified or removed IDs, print
    `note      <ID> is also changed by open change <other>: the second to archive is stopped until rebased`.
  - `cli._archive`: where a refusal holds `delta.base-stale`, write `review.md` and replace "read the current
    requirement" with "read <shown path of review.md>".
  - README: one paragraph under approving: the view, the overlap note.

- [ ] **Step 4: Run** `uv run pytest tests/test_review.py -q -p no:cacheprovider` then the whole gate. Expected:
  PASS; tests that counted output lines of these commands are updated for the one `review` line.

- [ ] **Step 5: Commit** `feat: the approver's view of each requirement a change touches, and who else touches it`.

### Task 2: The next work, `reports/remaining.md`

**Files:**
- Create: `adk_spec/domain/remaining.py`, `tests/test_remaining.py`
- Modify: `adk_spec/domain/lifecycle.py` (`_after_approval`), `adk_spec/workspace/layout.py` (`drop_report`),
  `adk_spec/interfaces/cli.py` (`_verified`), `README.md` (verify section)

**Interfaces:**
- Consumes: `Verdict` (`domain/verify.py`), `parts_of_diff(diff) -> list[tuple[str | None, str]]`, `TaskGroup`.
- Produces: `@dataclass(frozen=True) class Left: id: str; verdict: str; reason: str; ticked: tuple[str, ...];
  open: tuple[str, ...]; untouched: tuple[str, ...]` (task IDs ticked, task IDs not ticked, files those tasks named
  that the diff never touched); `remaining(verdicts: Sequence[Verdict], groups: Sequence[TaskGroup],
  touched: frozenset[str]) -> list[Left]`; `render_remaining(change_id: str, left: Sequence[Left]) -> str`;
  `Workspace.drop_report(change_id: str, name: str) -> None`; `REMAINING = "remaining.md"`.

- [ ] **Step 1: Write the failing tests**:
  - `test_a_ticked_task_whose_requirement_is_unmet_comes_first` (pure): one unmet verdict, its task ticked: the
    rendered text names the task under a "ticked, yet unmet" line before the model's reason.
  - `test_a_file_a_task_named_that_the_diff_never_touched_is_listed` (pure).
  - `test_the_models_reason_is_labelled_as_its_own_words` (pure): the text holds `The model's reason (not grounded):`.
  - `test_verify_writes_the_remaining_work_and_names_it`: in `test_verify`'s repository setup, REQ-AUTH-002 unmet:
    `reports/remaining.md` exists, `verify`'s `wrote` line names it.
  - `test_the_remaining_work_is_removed_once_everything_is_met`: a second `verify` with all met removes the file.
  - `test_the_next_step_names_the_unmet_requirements`: after the unmet `verify`, `status --json`'s `next` for
    `passkeys` is `REQ-AUTH-002 unmet: work from reports/remaining.md, then run \`adk-spec verify passkeys\``.
  - `test_the_next_step_names_three_unmet_requirements_and_counts_the_rest` (lifecycle, pure state with 5 unmet).
  - `test_failed_tests_come_before_unmet_requirements` (lifecycle).

- [ ] **Step 2: Run** `uv run pytest tests/test_remaining.py -q -p no:cacheprovider`. Expected: FAIL, no module.

- [ ] **Step 3: Implement.** `remaining` keeps every verdict whose `verdict != "met"`, in ID order. `_verified`: the
  diff's paths from `parts_of_diff(work.text)` (skip `None`); write or drop `remaining.md` after `verify.md`; print
  `wrote     <verify.md>, <remaining.md>` on the one line. `_after_approval`: after the failed-tests branch, where
  `state.verification` has any verdict not `met`, `Step("you", "<IDs> unmet: work from reports/remaining.md, then
  run `adk-spec verify <id>`")`, at most 3 IDs, then `and N more`. README: one paragraph.

- [ ] **Step 4: Run** the new tests and the gate. Expected: PASS; earlier tests expecting "implement tasks.md" after
  an unmet verification now expect the new step.

- [ ] **Step 5: Commit** `feat: unmet verdicts written as the next work, and the next step names them`.

### Task 3: Evidence kept by `verify`

**Files:**
- Create: `adk_spec/domain/evidence_md.py`, `tests/test_evidence.py`
- Modify: `adk_spec/interfaces/cli.py` (`_verified`), `adk_spec/workspace/layout.py` (`EVIDENCE = "evidence.md"`)

**Interfaces:**
- Produces: `@dataclass(frozen=True) class Proof: req: str; repository: str; path: str; quote: str; change: str;
  at: str`; `render_evidence(title: str, proofs: Sequence[Proof]) -> str`;
  `parse_evidence(text: str) -> tuple[list[tuple[int, Proof]], list[int]]` (each proof with its line, counted from
  1, and the lines that do not read); `kept(verdicts: Sequence[Verdict], *, added: frozenset[str], change: str,
  at: str, repositories: Mapping[str, str]) -> list[Proof]`.

- [ ] **Step 1: Write the failing tests**:
  - `test_evidence_reads_back_as_it_was_written`: proofs with a backtick, a `|` in the quote, and repository `../api`
    round-trip through `render_evidence` and `parse_evidence` with no unread line.
  - `test_evidence_with_a_line_deleted_still_reads`.
  - `test_a_line_off_the_grammar_is_named_not_fatal`: one line edited, `parse_evidence` returns it in the second list.
  - `test_only_met_verdicts_of_what_a_change_adds_or_modifies_are_kept`: a met removed requirement and an unmet one
    keep nothing.
  - `test_a_quote_over_a_secret_is_not_kept`: a quote holding `[REDACTED]` is dropped.
  - `test_another_repositorys_path_is_kept_with_its_folder`: path `api/x.py` with `repositories={"api": "../api"}`
    gives `Proof(repository="../api", path="x.py", ...)`.
  - `test_quotes_are_capped_in_length_and_number` (240 characters, 3 a requirement).
  - `test_verify_keeps_the_changes_evidence`: after the all-met `verify` of `test_verify`'s setup,
    `.spec/changes/passkeys/evidence.md` holds `return passkey(user)` and the verification's `at`; approval is not
    voided (`status` does not ask to approve again).

- [ ] **Step 2: Run** `uv run pytest tests/test_evidence.py -q -p no:cacheprovider`. Expected: FAIL, no module.

- [ ] **Step 3: Implement.** One entry a line: `- <req> | <repository> | <path> | <change> | <at> | <quote>`, the
  quote last and split with `maxsplit=5`; a proof whose path or repository holds ` | ` is not kept. Lines that are
  blank, the `# Evidence: ` title or a `> ` note are skipped; any other line that is not an entry is unread. Sorted
  by requirement, then path, then quote. `kept` cuts a quote at its last space before 240 characters.
  `_verified` writes `changes/<id>/evidence.md` (`write_into`) where any proof is kept, else removes it.

- [ ] **Step 4: Run** the tests and the gate. Expected: PASS.

- [ ] **Step 5: Commit** `feat: verify keeps the lines it proved each requirement with`.

### Task 4: Evidence beside the living specs, and suspect requirements

**Files:**
- Create: `adk_spec/workspace/evidence.py`
- Modify: `adk_spec/domain/evidence_md.py` (`folded`, `suspects`), `adk_spec/domain/validate.py` (two codes),
  `adk_spec/workspace/layout.py` (`write_specs(..., files=)`), `adk_spec/interfaces/cli.py` (`_archive`,
  `_validate`, `_status`), `tests/test_evidence.py`, `README.md` (archive and status sections)

**Interfaces:**
- Consumes: Task 3's `Proof`, `parse_evidence`, `render_evidence`; `quoted_at`; `git.grep(root, term, exclude=)`.
- Produces: `folded(living: Sequence[Proof], change: Sequence[Proof], *, replaced: frozenset[str],
  removed: frozenset[str]) -> list[Proof]`; `suspects(proofs: Sequence[tuple[int, Proof]], holds: Callable[[Proof],
  bool | None], *, path: str) -> list[Finding]`; `workspace/evidence.py`: `holds(root: Path, proof: Proof,
  exclude: Sequence[str]) -> bool | None`, `evidence_findings(workspace: Workspace) -> list[Finding]`;
  `Workspace.write_specs(specs, *, state=None, files: Mapping[str, str] = {})` (paths from `.spec/`).

- [ ] **Step 1: Write the failing tests**:
  - `test_archive_folds_the_verified_evidence_beside_the_living_spec`: all-met verify, archive:
    `.spec/specs/auth/evidence.md` holds REQ-AUTH-002 and REQ-AUTH-004, not REQ-AUTH-001 (removed).
  - `test_a_later_change_replaces_a_requirements_evidence` (pure `folded`).
  - `test_evidence_of_a_superseded_verification_is_not_folded`: `change`'s proofs with another `at` than the recorded
    verification are left out.
  - `test_a_living_evidence_file_that_does_not_read_is_left_as_it_is`: archive exits 0, the file is byte-identical,
    one line says so.
  - `test_a_quote_gone_from_the_code_makes_its_requirement_suspect`: delete `return passkey(user)` from `src/auth.py`:
    `validate` lists `INFO spec.evidence-gone` naming REQ-AUTH-004 and exits 0, `--strict` exits 0 too; `status`
    prints `auth: 1 requirement suspect (adk-spec validate lists them)`.
  - `test_a_quote_moved_to_another_file_is_not_suspect`.
  - `test_a_file_with_crlf_endings_still_holds_its_quote`.
  - `test_another_repository_that_is_not_there_is_not_checked`.
  - `test_an_evidence_line_off_the_grammar_is_a_note`: `spec.evidence-unreadable` with its line.

- [ ] **Step 2: Run** them. Expected: FAIL (`folded` missing; archive writes no living evidence).

- [ ] **Step 3: Implement.**
  - `folded`: the living proofs less those of `replaced | removed` requirements, plus the change's proofs, sorted.
  - `_archive`: read the change's `evidence.md` and keep the proofs whose `at` is `state.verification.at` (none
    without a verification); per merged capability, read its living `evidence.md` (missing is empty; one with an
    unread line, or not UTF-8, is left as it is with one `kept      <path>: it does not read, nothing was added`
    line); `replaced` is the IDs the delta adds or modifies, `removed` the ones it removes; write through
    `write_specs(..., files=...)`, none where nothing is kept.
  - `holds`: the repository's folder is `root` for `.`, else `root / repository`; not a folder or no `.git` there:
    `None`. Read the file (a missing file is not found); `quoted_at(quote, text)` is not None: True. Else the
    quote's longest run without whitespace, through `git.grep` (exclude the person's patterns for `.`), each of at
    most 20 named files read and confirmed with `quoted_at`: True on the first, else False.
  - `suspects`: per requirement, suspect where every proof's `holds` is False (one None and it is not checked):
    `finding("spec.evidence-gone", "<REQ> has none of its evidence left in the code: <path>, by <change>. Verify a
    change that keeps it, or delete its lines once it is reviewed", path=path, line=<its first line>)`.
  - `evidence_findings`: every capability with an `evidence.md`; unread lines as `spec.evidence-unreadable`.
  - `_validate`: `found += evidence_findings(workspace)`. `_status` (text only): after the groups, one line per
    capability with `spec.evidence-gone`, `<capability>: N requirement(s) suspect (adk-spec validate lists them)`.
  - SEVERITY: `spec.evidence-gone` and `spec.evidence-unreadable` as INFO.

- [ ] **Step 4: Run** the tests and the gate. Expected: PASS.

- [ ] **Step 5: Commit** `feat: evidence kept beside each living spec, and a requirement whose code is gone flagged`.

### Task 5: The merge gate

**Files:**
- Create: `adk_spec/domain/ci_md.py`, `tests/test_gate.py`
- Modify: `adk_spec/domain/validate.py` (three codes), `adk_spec/interfaces/cli.py` (`_drifted`, `_validate`),
  `adk_spec/workspace/files.py` (`append_text`), `README.md` (CI section, sample workflow)

**Interfaces:**
- Produces: `annotations(findings: Sequence[Finding]) -> list[str]`; `step_summary(findings: Sequence[Finding], *,
  failed: bool) -> str`; `files.append_text(path: Path, text: str) -> None`; `cli._drift(workspace, state) ->
  bool | None` (None: could not compare), `_drifted` as `_drift(...) is not False`.

- [ ] **Step 1: Write the failing tests**:
  - `test_a_voided_approval_is_a_warning_that_fails_strict`: approve, edit `brief.md`: `validate` lists `WARNING
    change.approval-void`, exit 0; `validate --strict` exits 1.
  - `test_a_voided_strict_approval_can_still_be_approved_again`: the strict tier, the same edit: `approve` by two names
    succeeds; `status`'s step unchanged from before this phase (approve again).
  - `test_drifted_work_is_a_warning`: verified, then `src/auth.py` edited: `change.work-drifted`.
  - `test_work_that_cannot_be_compared_is_a_note_and_archive_still_refuses`: the base commit made unknown: INFO
    `change.drift-unknown`; `archive` exits 1.
  - `test_github_actions_gets_annotations_and_a_summary`: `GITHUB_ACTIONS=true`, `GITHUB_STEP_SUMMARY` a file:
    stdout holds `::warning file=.spec/changes/passkeys/brief.md,title=change.approval-void::`, the file holds
    `| WARNING |`.
  - `test_annotations_escape_what_github_reads_as_syntax` (pure): a message with `%`, `\n` and a path with `,`.
  - `test_the_summary_is_capped`: 60 findings give 50 rows and `and 10 more`.
  - `test_no_summary_file_still_annotates`: `GITHUB_STEP_SUMMARY` unset, and set to a missing folder's file.
  - `test_nothing_github_is_said_outside_github_actions`.
  - `test_json_output_is_unchanged_by_github_actions`.

- [ ] **Step 2: Run** `uv run pytest tests/test_gate.py -q -p no:cacheprovider`. Expected: FAIL.

- [ ] **Step 3: Implement.** SEVERITY: `change.approval-void` WARNING, `change.work-drifted` WARNING,
  `change.drift-unknown` INFO. `_validate` makes them from `assessed.stale` (status approved or verified) and
  `_drift` (status verified), never inside `findings_of` or `Assessed.findings`; paths `.spec/changes/<id>/<file>`
  for the first stale file, `.spec/changes/<id>/change.json` otherwise. `annotations`: ERROR `error`, WARNING
  `warning`, INFO `notice`; only findings with a path; data escaped `%`→`%25`, `\r`→`%0D`, `\n`→`%0A`, properties
  also `:`→`%3A`, `,`→`%2C`; messages through `secrets.scrub`. `step_summary`: `## adk-spec validate`, a counts line
  with `failed`/`passed`, a table `| Severity | Code | Where | Message |`, `|` in cells as `\|`, 50 rows then
  `and N more`. `_validate`: after its usual output, where `os.environ.get("GITHUB_ACTIONS") == "true"` and not
  `--json`: print the annotations; append the summary where `GITHUB_STEP_SUMMARY` names a file whose folder is
  there (`OSError` ignored). README: the workflow with `actions/checkout` `ref:
  ${{ github.event.pull_request.head.sha }}`, `fetch-depth: 0`, `uv run adk-spec validate --strict`.

- [ ] **Step 4: Run** the tests and the gate. Expected: PASS.

- [ ] **Step 5: Commit** `feat: validate gates a merge on the approval and the verification, with GitHub annotations`.

### Task 6: The pull request's summary, the changelog, and the roadmap

**Files:**
- Create: `adk_spec/domain/summary_md.py`, `adk_spec/domain/changelog_md.py`, `tests/test_summary.py`
- Modify: `adk_spec/interfaces/cli.py` (`_verified`, `_archive`), `README.md`, `docs/superpowers/plans/README.md`

**Interfaces:**
- Produces: `render_summary(change: Change, verdicts: Mapping[str, str], tests: Mapping[str, str],
  approval: Approval | None) -> str`; `changelog_entry(change_id: str, day: str, deltas: Mapping[str, Delta]) ->
  str`; `with_entry(text: str | None, entry: str) -> str`; `CHANGELOG = "changelog.md"` in `layout.py`.

- [ ] **Step 1: Write the failing tests**:
  - `test_the_summary_holds_the_why_the_requirements_and_the_verdicts` (pure).
  - `test_verify_writes_the_summary_and_names_it_on_its_one_line`.
  - `test_archive_writes_a_changelog_entry_newest_first`: two archives, the second's entry above the first's.
  - `test_a_persons_edits_below_the_heading_are_kept` (pure `with_entry`).
  - `test_a_changelog_that_does_not_read_is_left_and_the_change_archived`.
  - `test_a_lean_change_archived_without_verify_still_gets_its_entry`.

- [ ] **Step 2: Run** `uv run pytest tests/test_summary.py -q -p no:cacheprovider`. Expected: FAIL.

- [ ] **Step 3: Implement.** Summary: `# <brief title>`, the brief's why, `## Requirements` with `Added`, `Modified`,
  `Removed` lines (`- REQ-…: <name> (<capability>)`), `## Verification` with each verdict and each test run,
  `Approved by <by>` (and the second). Entry: `## <change_id>, <YYYY-MM-DD>` then the three groups' lines, the empty
  ones left out. `with_entry`: `# Changelog` heading where there is none, the entry after the heading and its blank
  line. `_verified` writes `reports/summary.md` and names it on the `wrote` line; `_archive` adds `changelog.md` to
  `write_specs(files=)`, and leaves one that does not read with one `kept` line. Roadmap: the phase's entry.

- [ ] **Step 4: Run** the tests and the gate. Expected: PASS.

- [ ] **Step 5: Commit** `feat: a pull request's summary at verify, and a changelog at archive`.
