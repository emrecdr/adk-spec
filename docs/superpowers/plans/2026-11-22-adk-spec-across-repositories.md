# Context Across Repositories, Checked by a Model: Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A change names the other repositories it spans; every reading for it covers them under phase 6's rules; a
model reviews each reading; `verify` judges the work in all of them.

**Architecture:** `Source` becomes the set of a change's repositories behind the interface `explore.py` already uses:
the workspace's paths as they are, another repository's as `name/path`, one round's caps shared. A new `review`
stage runs at the end of the explore graph, on statements alone. `verify` builds one diff over the repositories,
each from its own recorded commit, in one function that `_drifted` uses too.

**Tech Stack:** Python 3.14, uv, google-adk 2.14.1, litellm 1.106.2, pytest (asyncio strict), ruff 0.17.5, pyrefly 1.4.1.

**Spec:** `docs/superpowers/specs/2026-11-22-brownfield-across-repositories-design.md`

## Global Constraints

- No subcommand. One flag, `--with`, on `propose` and `plan`.
- Layers import one way, `domain → workspace → orchestration → interfaces`; only `workspace/git.py` runs a subprocess.
- macOS and Windows. Paths are compared, recorded and shown with forward slashes.
- No live model call in Tasks 1 to 6. Offline: `SPEC_PROVIDER=gemini`, `SPEC_MODEL=fake`, `GOOGLE_API_KEY=offline`.
- Every rule of phase 6 holds in every repository: git's own list, no link on the path, nothing ignored, the
  repository's own exclusions, secrets scrubbed whole before anything is cut, no file that holds a private key.
- A round's caps are shared by the repositories. A reading is at most seven model calls: one scout, four surveys,
  two reviews.
- Gate after each task: `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyrefly check`,
  `uv run pytest -q`. `scripts/dump_instructions.py` shows which instructions changed.
- C901 ≤ 10, line length 120.

## Review Focus

1. `--with .`, `--with ./`, an absolute path to the workspace, or a link to it: refused as "this repository itself",
   never read twice. Test in Task 1.
2. `--with ..\api` typed on Windows: recorded as `../api`, named `api`. Test in Task 2.
3. Another repository whose own `.spec/config.toml` does not load: that repository is said and left out, nothing is
   raised. Test in Task 1.
4. A review that disputes every statement: no `context.md` is written, and `propose` says why. Test in Task 4.
5. A verified change whose other repository's folder is later removed: `status` reads it as drifted and does not
   fail. Test in Task 5.

---

### Task 1: The reader across repositories

**Files:**
- Modify: `adk_spec/workspace/source.py`, `adk_spec/workspace/git.py`, `adk_spec/interfaces/cli.py` (REFUSALS only)
- Test: `tests/test_source.py`

**Interfaces:**
- Produces:
  - `class SourceError(Exception)` in `source.py`, added to `cli.REFUSALS`.
  - `Source.of(root: Path, *, exclude: Sequence[str], others: Sequence[tuple[str, str]] = ()) -> Source`, where each
    of `others` is a name and a path as recorded (relative to `root`, or absolute).
  - `Source.paths: list[str]`: the workspace's paths, then each present repository's as `name/path`.
  - `Source.names: tuple[str, ...]`: the other repositories that were read. `Source.missing: tuple[str, ...]`: one
    line each for one that was not, `"web: no git repository at ../web"`.
  - `Source.tree() -> str`: with no other repository, exactly `tree_text(paths)` as today; otherwise the workspace's
    tree, then for each `=== name (N files)` and `tree_text` of its prefixed paths, each folded on its own.
  - `Source.commits() -> dict[str, str | None]`: each present repository's HEAD.
  - `Source.gathered` and `Source.without_keys` keep their signatures and accept prefixed paths.
  - `git.top(root: Path) -> Path`: the repository's top folder (today's `_top`, made public).

- [ ] **Step 1: Write the failing tests** in `tests/test_source.py`, with a workspace repository and a sibling
  repository made by `conftest.repository`:
  - `test_another_repository_is_read_under_its_name`: `api/src/routes.py` is read whole; `got.texts` and `got.read`
    key it as `api/src/routes.py`; `held.paths` holds the workspace's paths first.
  - `test_a_search_finds_lines_in_every_repository`: one `=== search:` block whose rows name `src/…` and `api/src/…`.
  - `test_a_rounds_caps_are_shared_by_the_repositories`: with `ROUND_MAX_CHARS` patched small, a file of each
    repository is asked for and one is deferred.
  - `test_every_rule_of_phase_6_holds_in_another_repository`: in the other repository a link on the path, an ignored
    file, a key file, and a path its own `.spec/config.toml` excludes are each left out and named.
  - `test_a_missing_repository_or_one_whose_config_does_not_load_is_named_and_left_out` (Review Focus 3).
  - `test_this_repository_by_another_spelling_or_a_name_that_is_a_folder_here_is_refused` (Review Focus 1):
    `pytest.raises(SourceError)` for `.`, `./`, the absolute path, a link to it, and the name `src`.
  - `test_each_repository_folds_its_own_files_and_one_repository_reads_as_before`: `tree()` with no other repository
    equals `tree_text(paths)`.
- [ ] **Step 2: Run them.** `uv run pytest tests/test_source.py -q`. Expected: the new tests fail
  (`TypeError: ... unexpected keyword argument 'others'`).
- [ ] **Step 3: Implement.** Move the per-repository state and methods of `Source` (`_listed`, `_exclude`,
  `_opened`, `_read`, `_lines`, `_linked`, the search's hits) into a private `_Repository(name, root, paths,
  exclude)`; `Source` holds the workspace's first and routes a path by its first segment to the repository of that
  name, the workspace's otherwise. `_file`, `_folder` and `_search` write prefixed paths into one shared `_Round`. A
  search runs in every repository and makes one block. Another repository's exclusions come from its own
  `.spec/config.toml` through `load_config`, where the file exists.
- [ ] **Step 4: Run the gate.** Expected: all pass; `dump_instructions` unchanged.
- [ ] **Step 5: Commit** `feat: a reader across a change's repositories`.

### Task 2: Repositories named with the change

**Files:**
- Modify: `adk_spec/domain/model.py`, `adk_spec/interfaces/cli.py`
- Test: `tests/test_propose.py`, `tests/test_plan.py`

**Interfaces:**
- Consumes: `Source.of(..., others=...)`, `Source.tree()`, `Source.missing` (Task 1).
- Produces:
  - `ChangeState.repositories: dict[str, str] = {}`: name to path, forward slashes.
  - `cli._named(given: Sequence[str], held: Mapping[str, str]) -> dict[str, str]`: `held` with each `--with` added;
    `UsageError` for a name that cannot be made or a name given twice in one command.
  - `cli._source(workspace: Workspace, repositories: Mapping[str, str]) -> Source | None`.
  - `--with` (`action="append"`, metavar `PATH or NAME=PATH`) on `propose` and `plan`.

- [ ] **Step 1: Write the failing tests:**
  - `test_propose_records_the_repositories_named_with_the_change`: `propose "..." --with ../api --with web=../web-app`
    leaves `state.repositories == {"api": "../api", "web": "../web-app"}`.
  - `test_plan_with_adds_a_repository_and_a_name_given_again_takes_its_new_path`.
  - `test_the_scout_is_shown_each_repository_and_a_statement_may_name_one`: the scout's tree holds `=== api (`; a
    canned survey quoting `api/src/routes.py` is kept as `api/src/routes.py:N` in `context.md`.
  - `test_a_missing_repository_is_said_and_the_plan_goes_on`: output holds `left out  web: no git repository at
    ../web`, exit 0, tasks written.
  - `test_a_with_whose_name_cannot_be_made_is_refused`, parametrised over `..`, `9x=../a`, `api=../a api=../b`.
  - `test_a_path_typed_with_backslashes_is_recorded_with_slashes` (Review Focus 2): `_named(["..\\api"], {}) ==
    {"api": "../api"}`.
  - `test_plan_with_on_a_change_that_has_a_context_keeps_it_and_says_how_to_read_again`: output holds `delete it to
    read again`, and the scout is not asked.
- [ ] **Step 2: Run them.** Expected: fail (`unrecognized arguments: --with`).
- [ ] **Step 3: Implement.** A name is the folder's last part, lowercased, every other character `-`, and must match
  `[a-z][a-z0-9-]{0,30}`. `_written` records the repositories in the new `ChangeState`; `_planned` saves the merged
  ones before `_plan_made`. `_plan_made` builds the `Source` from the change's repositories, seeds `TREE` with
  `source.tree()`, and prints each of `source.missing` as `left out  …`.
- [ ] **Step 4: Run the gate.** Expected: all pass.
- [ ] **Step 5: Commit** `feat: a change names the other repositories it spans`.

### Task 3: The review

**Files:**
- Create: `adk_spec/orchestration/stages/review.py`
- Modify: `adk_spec/domain/drafts.py`, `adk_spec/orchestration/explore.py`, `adk_spec/interfaces/cli.py`
  (`require_ready` roles), `scripts/dump_instructions.py`, `tests/conftest.py`
- Test: `tests/test_explore.py`, and the counts of model calls in `tests/test_measure.py`, `tests/test_verify.py`,
  `tests/test_plan.py`, `tests/test_propose.py`

**Interfaces:**
- Produces:
  - `DisputeDraft(statement: int, reason: str)`, `UnknownDraft(question: str, where: str)`,
    `ReviewDraft(disputed: list[DisputeDraft], unknown: list[UnknownDraft], more_files, more_folders, more_searches)`.
  - `stages/review.py`: `KEY = "review"`, `NUMBERED = "numbered"`, `NOT_READ = "not_read"`, `build_review()`; role
    `review`. Sections: the statements, numbered, each with its kind, path, line, note and quote; every file read;
    what was not read; the brief; the deltas.
  - `explore.REVIEW_BUDGET = 2`, `explore.UNKNOWN_BUDGET = 8`; `Explored.unknown: tuple[tuple[str, str], ...]`,
    `Explored.disputed: int`.
  - `conftest.CANNED_REVIEW = {"disputed": [], "unknown": [], "more_files": [], "more_folders": [], "more_searches": []}`.

- [ ] **Step 1: Write the failing tests** in `tests/test_explore.py`:
  - `test_the_review_reads_the_statements_and_no_file`: its instruction holds `1. touches src/app.py:2` and the quote,
    and no `=== src/app.py`.
  - `test_a_disputed_statement_is_left_out_and_counted_and_a_number_naming_nothing_is_ignored`.
  - `test_unknowns_are_kept_plain_and_at_most_eight`.
  - `test_the_review_may_send_the_reading_one_round_further_and_runs_twice_at_most`: a review asking for
    `docs/auth.md` gives one more round, its survey, and a second review; the second's unknowns are the ones kept.
  - `test_a_reading_is_at_most_seven_model_calls`: every survey and review asks for more; `len(fake_provider.requests)
    <= 7`.
  - `test_a_review_that_fails_keeps_what_was_kept_and_ends_the_run`.
  - `test_a_reading_that_kept_nothing_is_not_reviewed`.
- [ ] **Step 2: Run them.** Expected: fail (`ImportError: cannot import name 'ReviewDraft'`).
- [ ] **Step 3: Implement.** Edges: `_grounded` NONE and `next_look` NONE go to `_to_review`, which numbers the kept
  statements, starts the review anew (its key cleared, its tries set back, `reviews` counted) and routes NONE where
  nothing was kept or two reviews ran; the review's gate OK goes to `_weighed`, which drops disputed numbers, keeps
  the unknowns, and routes to `review_look` where more was asked, one review has run and room for a statement is
  left; `review_look` reads past `LOOK_BUDGET` once and goes to the survey. Guide, in substance: dispute a statement
  only where its quote does not show what its note says; name what the change needs to know that no statement
  establishes, with where it might be found; ask to read only what would answer an unknown.
- [ ] **Step 4: Run the gate.** Expected: all pass, the four count tests updated by one review call a reading;
  `dump_instructions` shows the new `review` stage only.
- [ ] **Step 5: Commit** `feat: a model reviews each reading of the code`.

### Task 4: What a reading writes and says

**Files:**
- Modify: `adk_spec/domain/context_md.py`, `adk_spec/interfaces/cli.py` (`_read_code`, `_first_reads`),
  `adk_spec/orchestration/stages/design.py`, `adk_spec/orchestration/stages/tasks.py`
- Test: `tests/test_context_md.py`, `tests/test_plan.py`

**Interfaces:**
- Consumes: `Explored.unknown`, `Explored.disputed` (Task 3); `Source.names`, `Source.commits()` (Task 1).
- Produces:
  - `render_context(..., others: Mapping[str, str | None] = {}, unknown: Sequence[tuple[str, str]] = (), disputed: int = 0)`.
    With others, the second line reads `Read on 2026-11-22: this repository at commit 1a2b3c4d5e6f, api at commit
    9f8e7d6c5b4a.`; without, as today. A section `## What is still unknown` after the four kinds, each `- {question}
    Look in: {where}.`; the `Left out:` line adds `; 1 the review disputed`.
  - `unknown_count(text: str) -> int` in `context_md.py`: the lines under that heading.

- [ ] **Step 1: Write the failing tests:**
  - `test_a_reading_across_repositories_names_each_commit`, `test_what_is_still_unknown_has_its_section_and_the_disputed_are_counted`.
  - `test_propose_says_how_many_repositories_and_unknowns`: `explored  2 files in 2 repositories: 2 statements kept,
    1 left out, 1 unknown`.
  - `test_read_first_names_context_md_where_something_is_unknown`.
  - `test_a_review_that_disputes_every_statement_writes_no_context_and_says_so` (Review Focus 4): `explored  nothing:
    the review disputed every statement`.
  - `test_design_and_tasks_are_told_not_to_plan_on_an_unknown`.
- [ ] **Step 2: Run them.** Expected: fail.
- [ ] **Step 3: Implement.** Design and tasks guides gain one sentence: "Where the context lists something as still
  unknown, do not plan on it as if it were known: a task that depends on it says so."
- [ ] **Step 4: Run the gate.** Expected: all pass; `dump_instructions` shows the design and tasks stages changed by
  that sentence alone.
- [ ] **Step 5: Commit** `feat: context.md names each repository and what is still unknown`.

### Task 5: `verify` across repositories

**Files:**
- Modify: `adk_spec/workspace/git.py`, `adk_spec/domain/model.py`, `adk_spec/domain/lifecycle.py`,
  `adk_spec/domain/report_md.py`, `adk_spec/interfaces/cli.py` (`_approve`, `_work`, `_drifted`, `_verified`)
- Test: `tests/test_git.py`, `tests/test_verify.py`

**Interfaces:**
- Consumes: `ChangeState.repositories` (Task 2), `Source.commits()`, `Source.without_keys` (Task 1).
- Produces:
  - `git.diff(root, base, *, exclude, prefix: str = "")`: paths as `a/{prefix}…` and `b/{prefix}…`, by
    `--src-prefix` and `--dst-prefix` on both of its git calls.
  - `ChangeState.base_commits: dict[str, str] = {}`; `Verification.bases: dict[str, str] = {}`.
  - `lifecycle.approve(..., commit, others: Mapping[str, str] = {})`: `base_commits` is `{**others, **state.base_commits}`.
  - `lifecycle.verified(..., bases: Mapping[str, str] = {})`; `render_verify(..., bases: Mapping[str, str] = {})`.
  - `cli._work_diff(workspace, state, base: str, bases: Mapping[str, str]) -> tuple[str, tuple[str, ...]]`: the
    diff over the repositories less key files, and those files; used by `_work` and by `_drifted`.
  - `--base` takes `REF` and `NAME=REF`, as often as needed (`action="append"`).

- [ ] **Step 1: Write the failing tests:**
  - `test_a_diff_names_its_paths_under_a_prefix` (`test_git.py`), tracked and untracked files alike.
  - `test_approve_records_where_each_repository_began_and_never_moves_it`.
  - `test_verify_judges_the_work_in_every_repository_of_the_change`: work in `api/` is in the request as `api/…`, a
    verdict quoting it is grounded.
  - `test_a_repository_missing_at_verify_or_with_no_starting_point_is_refused_by_name`, and
    `test_base_names_a_starting_point_for_another_repository` (`--base api=<commit>`).
  - `test_a_verified_change_whose_diff_holds_a_key_file_has_not_drifted`: a fault of phase 6, `_drifted` hashed the
    diff before key files were left out.
  - `test_work_changed_in_another_repository_makes_a_verified_change_drift`.
  - `test_a_verified_change_whose_other_repository_is_gone_reads_as_drifted` (Review Focus 5).
- [ ] **Step 2: Run them.** Expected: fail.
- [ ] **Step 3: Implement** as the design's "`verify` across repositories" section says. The size cap holds over the
  diffs together. `render_verify` names each repository's commit after the workspace's.
- [ ] **Step 4: Run the gate.** Expected: all pass.
- [ ] **Step 5: Commit** `feat: verify judges the work in every repository of a change`.

### Task 6: The labelled case, the README

**Files:**
- Modify: `scripts/cases.py`, `README.md`, `docs/measurements/README.md`
- Test: `tests/test_measure.py`

- [ ] **Step 1: Write the failing test** `test_the_across_case_runs_whole_on_the_fake`: the case builds a workspace
  repository with a decoy and an API repository with the integration point, its change naming the API with
  `repositories`, and the fake run scores it.
- [ ] **Step 2: Run it.** Expected: fail (`no case named across`).
- [ ] **Step 3: Implement** `Case("across", _across, "plan", (Expected(("context.touches", "context.exists"), ACROSS),))`
  with `ACROSS` paths under `api/`. README: one section, "A feature across repositories", with the `--with` line, what
  is read, what `context.md` then says, and that `verify` covers each repository.
- [ ] **Step 4: Run the gate.** Expected: all pass.
- [ ] **Step 5: Commit** `feat: a labelled case for a reading across repositories`.

### Task 7: Live, on the owner's go-ahead

Each step waits for a go-ahead in so many words; a general "proceed" does not count.

- [ ] The `across` case five times on Copilot: `uv run python -m scripts.measure --case across --runs 5`.
- [ ] One `propose ... --with` on two of the owner's own repositories, `context.md` read by hand.
- [ ] Record both under `docs/measurements/`.

## What this plan leaves

Paths per machine, an unknown asked of the person, `check` reading `context.md`, room as a setting.
