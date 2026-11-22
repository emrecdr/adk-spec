# adk-spec Brownfield Context Implementation Plan (plan 6)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Before `propose` or `plan` drafts a design and tasks, adk-spec reads the code that matters for the change and writes `context.md`, every statement with a quote code checked; and no known secret shape or excluded path is sent by any command.

**Architecture:** The model points and Python reads. Two stages of the usual shape, `scout` and `survey`, with code between them in one small graph: code checks every path a model names against git's own list, reads within fixed caps, and keeps a statement only where its quote is in the file. The reading is one more model pass of the plan part, sequenced in the command as the plan itself is, under the command's one ledger. A reading that fails never stops the plan.

**Tech Stack:** As plans 1 to 5. No new dependency.

**Spec:** `docs/superpowers/specs/2026-11-22-brownfield-feature-context-design.md`. Reference for Task 1: `adk_review/adk_review/core/secrets.py` and `judge/plugins.py` (`RedactSecretsPlugin`), read-only.

## Global Constraints

Plans 1 to 5's Global Constraints hold unchanged. In addition:

- No subcommand is added.
- Only `adk_spec/workspace/git.py` runs a subprocess. A search is `git grep` with a fixed string, as an argument list.
- A path a model names is used only after it is found, to the letter, in the list git gives. No path is joined to the repository's root before that.
- `adk_spec/domain/` imports nothing of ADK. The graph is handed a reader and touches no path itself.
- Nothing in `adk_review` is run or changed. No `.env` is read.
- No task makes a live model call. Task 8 holds the live steps, marked **owner**.

## Review Focus

1. A path a model names that git does not list: `../../etc/passwd`, an absolute path, a path under `.spec/`, a file git ignores, an excluded one. None is read; each is named as left out. Test in Task 3.
2. A tracked symbolic link, to a file inside or outside the repository. It is never read. Test in Task 3.
3. A tracked file that holds a secret of a known shape. What is sent and what is recorded hold `[REDACTED`, and a statement quoting the secret is left out. Tests in Tasks 1 and 6.
4. A reading that fails, or a ceiling spent in the middle of one. The plan is drafted without the context or with what was kept, the command says so, and a change that was written stands. Test in Task 6.
5. A file whose text tells the model what to do. It cannot make code read a path outside git's list, and a statement it dictates is kept only if it quotes a real line. Tests in Tasks 3 and 4.

---

### Task 1: No known secret shape is sent or recorded, by any command

**Files:**
- Create: `adk_spec/domain/secrets.py`
- Modify: `adk_spec/orchestration/plugins.py`
- Test: `tests/test_secrets.py`, `tests/test_plugins.py`

**Interfaces:**
- Produces:
  - `secrets.scrub(text: str, *, cut: bool = False) -> tuple[str, int]`: `text` with every known secret shape replaced, and how many were. Ported as it stands from `adk_review`'s `core/secrets.py`: its tables and `scrub`, and nothing of the rules built on them.
  - `plugins.Scrub(BasePlugin)`: before each model call it scrubs the instruction and every text part of the request. If scrubbing raises, the call is not sent: `LlmResponse(error_code=REDACTION, ...)`. `REDACTION = "REDACTION_FAILED"` joins `FINAL`.
  - `roster(ledger, recorder=None)`: `Scrub()` first, so the recorder and the provider both see scrubbed text.

- [ ] **Step 1: Write the failing tests**

```python
@pytest.mark.parametrize("secret", [AWS_KEY, GITHUB_TOKEN, PRIVATE_KEY_BLOCK, 'password = "hunter2-hunter2"', "postgres://app:s3cretpass@db/x", "Authorization: Bearer abcdef1234567890"])
def test_a_known_secret_shape_is_replaced(secret) -> None: ...
def test_code_that_names_a_secret_and_holds_none_is_left_alone() -> None:     # token = get_token(request)
def test_scrubbing_twice_changes_nothing_more() -> None:
async def test_what_a_model_is_sent_and_what_is_recorded_hold_no_secret(fake_provider) -> None:   # Review Focus 3
async def test_a_scrub_that_fails_sends_nothing(fake_provider, monkeypatch) -> None:
```

- [ ] **Step 2: Run them.** Expected: FAIL, `No module named 'adk_spec.domain.secrets'`.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the suite.** Expected: all pass.
- [ ] **Step 5: Commit.** `feat: known secret shapes are scrubbed from every model request`

---

### Task 2: Paths a person keeps out of every command

**Files:**
- Modify: `adk_spec/workspace/config.py`, `adk_spec/workspace/git.py`, `adk_spec/interfaces/cli.py`
- Test: `tests/test_workspace.py`, `tests/test_git.py`, `tests/test_plan.py`, `tests/test_verify.py`

**Interfaces:**
- Produces:
  - `Config.exclude: tuple[str, ...] = ()`, read from `[repository] exclude`, a list of non-empty strings. A pattern is a path from the repository's top as git reads a glob: `vendor/**`, `**/*.pem`.
  - `git.files(root, *, exclude=())` and `git.diff(root, base, *, exclude=())`: each pattern is passed to git as `:(exclude,glob)<pattern>`.
  - The repository's files shown to the plan and the diff `verify` reads both leave out what is excluded.

- [ ] **Step 1: Write the failing tests**

```python
def test_an_excluded_path_is_never_listed(tmp_path) -> None:
def test_an_excluded_path_is_no_part_of_the_diff_tracked_or_not(tmp_path) -> None:
def test_exclude_must_be_a_list_of_patterns(tmp_path) -> None:        # a string, an empty one, a number: ConfigError
def test_the_plan_is_shown_no_excluded_file(tmp_path, fake_provider) -> None:
```

- [ ] **Step 2: Run them.** Expected: FAIL on the unknown key `repository`.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the suite.**
- [ ] **Step 5: Commit.** `feat: paths a person excludes are never listed or sent`

---

### Task 3: Reading source safely

**Files:**
- Create: `adk_spec/workspace/source.py`
- Modify: `adk_spec/workspace/git.py`
- Test: `tests/test_source.py`

**Interfaces:**
- Produces:
  - `git.grep(root, term, *, exclude=()) -> list[str]`: each `path:line:text` git finds for the fixed string `term` in tracked and untracked-not-ignored text files, none of `.spec/`.
  - The caps, as constants of `source.py`: `FILES_A_ROUND = 12`, `FOLDERS_A_ROUND = 4`, `FOLDER_MAX_PATHS = 200`, `SEARCHES_A_ROUND = 6`, `SEARCH_MAX_LINES = 20`, `LINE_MAX_CHARS = 200`, `FILE_MAX_CHARS = 12_000`, `ROUND_MAX_CHARS = 40_000`.
  - `source.Gathered`: `texts: dict[str, str]` (each file's text as it was shown, by path), `shown: str` (what a stage reads: each file under `=== path (lines a to b of n)`, each listing under `=== folder/ (n files)`, each search under `=== search: term`), `read: tuple[str, ...]`, `left_out: tuple[str, ...]`.
  - `source.Source(root, paths, *, exclude=())`, with `Source.of(root, *, exclude=())` asking git. `gathered(files, folders, searches) -> Gathered`.
  - A file is asked for as `path` or `path:120-260`.

- [ ] **Step 1: Write the failing tests**

```python
def test_a_file_git_lists_is_read_whole_and_one_past_the_cap_is_cut_and_says_so(tmp_path) -> None:
def test_a_line_range_reads_those_lines(tmp_path) -> None:
@pytest.mark.parametrize("asked", ["../outside.txt", "/etc/passwd", ".spec/config.toml", "ignored/secret.txt", "src/../../x", "SRC/app.py"])
def test_a_path_git_does_not_list_is_not_read(tmp_path, asked) -> None:      # Review Focus 1
def test_a_symbolic_link_is_never_read(tmp_path) -> None:                     # Review Focus 2
def test_a_file_that_is_no_text_is_left_out(tmp_path) -> None:
def test_a_folder_lists_what_git_lists_under_it_within_the_cap(tmp_path) -> None:
def test_a_search_is_a_fixed_string(tmp_path) -> None:                        # ".*" and "$(rm x)" find themselves or nothing
def test_a_round_holds_no_more_than_its_caps(tmp_path) -> None:
```

- [ ] **Step 2: Run them.** Expected: FAIL, no module `source`.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the suite.**
- [ ] **Step 5: Commit.** `feat: source read through git's own list, within fixed caps`

---

### Task 4: Statements a model must ground

**Files:**
- Create: `adk_spec/domain/context_md.py`
- Modify: `adk_spec/domain/drafts.py`, `adk_spec/domain/model.py`, `adk_spec/domain/convert.py`
- Test: `tests/test_context_md.py`, `tests/test_convert.py`

**Interfaces:**
- Produces:
  - `drafts.ScoutDraft`: `files`, `folders`, `searches` (lists of str), `reason: str`. `drafts.StatementDraft`: `kind: Literal["exists", "touches", "convention", "risk"]`, `file`, `quote`, `note`. `drafts.SurveyDraft`: `statements`, `more_files`, `more_folders`, `more_searches`.
  - `model.Statement`: `kind`, `path`, `line`, `quote`, `note`.
  - `convert.to_statements(draft: SurveyDraft, texts: Mapping[str, str]) -> tuple[list[Statement], int]`: each statement whose quote `pointed_at` finds, with its line, as plain text; and how many were left out.
  - `context_md.SECTIONS`: the four kinds with their headings. `context_md.render_context(change_id, *, at, commit, statements, read, left_out, dropped, partial=None) -> str`.

- [ ] **Step 1: Write the failing tests**

```python
def test_a_statement_is_kept_where_its_quote_is_in_the_file_it_names() -> None:
def test_a_statement_with_a_quote_that_is_nowhere_or_in_another_file_is_left_out() -> None:   # Review Focus 5
def test_a_statements_words_are_plain_text() -> None:
def test_context_md_has_a_section_a_kind_and_says_what_was_read_and_left_out() -> None:
def test_a_partial_reading_says_so_at_its_top() -> None:
```

- [ ] **Step 2: Run them.** Expected: FAIL on the imports.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the suite.**
- [ ] **Step 5: Commit.** `feat: statements about the code, each held to a quote`

---

### Task 5: The scout, the survey and the loop between them

**Files:**
- Create: `adk_spec/orchestration/stages/scout.py`, `adk_spec/orchestration/stages/survey.py`, `adk_spec/orchestration/explore.py`
- Modify: `adk_spec/orchestration/stages/__init__.py`, `scripts/dump_instructions.py`
- Test: `tests/test_explore.py`

**Interfaces:**
- Produces:
  - `explore.LOOK_BUDGET = 3`, `explore.STATEMENT_BUDGET = 40`.
  - `explore.build_explore_app(*, source: Source, ledger: UsageLedger, recorder: BasePlugin | None = None) -> App`.
  - `explore.Explored`: `statements: list[Statement]`, `read: tuple[str, ...]`, `left_out: tuple[str, ...]`, `dropped: int`. `explore.explored(state) -> Explored`: what a run kept, also where it ended early.
  - Seeds the run reads: `BRIEF_TEXT`, `DELTAS_TEXT`, `CONSTITUTION`, `TREE`.
  - No existing stage's instruction changes in this task.

- [ ] **Step 1: Write the failing tests**

```python
async def test_the_scout_names_and_the_survey_states_and_code_keeps_what_is_quoted(tmp_path, fake_provider) -> None:
async def test_the_survey_may_look_again_and_no_more_than_the_budget(tmp_path, fake_provider) -> None:
async def test_a_file_already_read_is_not_read_twice(tmp_path, fake_provider) -> None:
async def test_a_scout_that_names_nothing_readable_ends_with_nothing_kept(tmp_path, fake_provider) -> None:
async def test_a_survey_given_up_keeps_what_the_rounds_before_it_kept(tmp_path, fake_provider) -> None:
async def test_no_more_statements_are_kept_than_the_budget(tmp_path, fake_provider) -> None:
```

- [ ] **Step 2: Run them.** Expected: FAIL, no module `explore`.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the suite.**
- [ ] **Step 5: Commit.** `feat: the scout, the survey and the loop that reads between them`

---

### Task 6: The plan reads the code first

**Files:**
- Modify: `adk_spec/interfaces/cli.py`, `adk_spec/workspace/layout.py`, `adk_spec/orchestration/stages/__init__.py`, `adk_spec/orchestration/stages/design.py`, `adk_spec/orchestration/stages/tasks.py`
- Test: `tests/test_plan.py`, `tests/test_propose.py`

**Interfaces:**
- Produces:
  - `layout.CONTEXT = "context.md"`: a file of a change that no approval covers.
  - `stages.CONTEXT_TEXT` and the section `THE_CONTEXT`, "What the repository already holds", read by the design and tasks stages, and by no other.
  - `_plan_made` reads the code before it drafts, where the workspace is in a git repository that holds files, the change has no `context.md`, and `--no-explore` was not given. It writes `context.md` and prints `explored  <n> files: <k> statements kept, <d> left out`. A `context.md` that is there is read as it stands.
  - A reading that does not end well is said in one line, `explored  nothing: <why>`, and the plan is drafted.
  - `--no-explore` on `propose` and on `plan`.

- [ ] **Step 1: Write the failing tests**

```python
def test_plan_reads_the_code_and_the_design_and_tasks_are_shown_what_it_found(tmp_path, capsys, fake_provider) -> None:
def test_propose_reads_the_code_once_the_change_is_written(tmp_path, capsys, fake_provider) -> None:
def test_a_context_that_is_there_is_kept_and_read(tmp_path, fake_provider) -> None:
def test_no_explore_reads_nothing(tmp_path, fake_provider) -> None:
def test_outside_a_repository_nothing_is_read_and_the_plan_is_drafted(tmp_path, fake_provider) -> None:
def test_a_reading_that_fails_does_not_stop_the_plan(tmp_path, capsys, fake_provider) -> None:      # Review Focus 4
def test_a_secret_in_a_tracked_file_reaches_no_request_no_recording_and_no_context(tmp_path, fake_provider) -> None:   # Review Focus 3
def test_context_md_is_no_part_of_an_approval(tmp_path, fake_provider) -> None:
```

- [ ] **Step 2: Run them.** Expected: FAIL: no `context.md` is written.
- [ ] **Step 3: Implement.** `scripts/dump_instructions.py` shows the design's and the tasks' instructions changed, the scout's and the survey's new, and no other changed.
- [ ] **Step 4: Run the suite.**
- [ ] **Step 5: Commit.** `feat: the plan of a change rests on the code it read`

---

### Task 7: A labelled case, and the README

**Files:**
- Modify: `scripts/cases.py`, `scripts/measure.py`, `docs/measurements/README.md`, `README.md`, `docs/superpowers/plans/README.md`
- Test: `tests/test_measure.py`

**Interfaces:**
- Produces: a case `integration`: a small repository with one planted integration point and one decoy file of a similar name, run through `plan`, scored on whether a kept statement of kind `touches` or `exists` names the planted file and none blocks on the decoy.

- [ ] **Step 1: Write the failing test.** `test_the_integration_case_is_caught_where_a_statement_names_the_planted_file`.
- [ ] **Step 2: Run it.** Expected: FAIL, no such case.
- [ ] **Step 3: Implement,** and write the README's section on reading the code: what is read, what is sent, the caps, the cost, `[repository] exclude`, `--no-explore`.
- [ ] **Step 4: Run the suite.**
- [ ] **Step 5: Commit.** `feat: a labelled case for reading the code; the README says what is read and sent`

---

### Task 8: Proven live (owner)

Each step calls a model with the owner's account, on the owner's go-ahead in so many words.

- [ ] **Step 1 (owner, live).** `uv run python -m scripts.measure --case integration --runs 5`.
- [ ] **Step 2 (owner, live).** One `propose` in a real repository of the owner's choice. Read `context.md` by hand: is each statement true, and which files that mattered were not read.
- [ ] **Step 3.** Record both in `docs/confirmation/2026-11-brownfield.md`, with tokens and seconds, and decide: the caps, and whether the brief should read the code too.

---

## What this plan leaves

The brief and the specs reading the code. `check` reading `context.md`. The repository baseline inside `init` (the next phase).

## What changed while this plan was executed

Tasks 1 to 7 were built as written, with the rulings in the ledger. Task 8, the live steps, waits for the owner's
go-ahead. The cleanup review and the code review found real faults, each fixed test first; the ones that change what
the plan says are these.

- **A file is scrubbed whole, once, before anything is cut from it.** Task 6 scrubbed each line alone, after a range
  or a search line was cut out. A private key's first line was then hidden on its own, its block was no longer
  known, and its body was shown. `secrets.scrub_lines` keeps every line at its number, and the reader takes every
  range, search line and capped file from that one text.
- **A model is held to the text it was shown.** With every request scrubbed, `check` and `verify` looked for a
  model's quote in the unscrubbed text, so a quote of a scrubbed line was "not there". Both now scrub once and use
  that text for the request and for the grounding. The fingerprint of the work stays that of the diff as it stands.
- **A file that holds a private key is shown in no piece.** A diff shows a file in pieces, and a piece near or inside
  a key holds neither of the lines the scrub knows a key by. Measured: one line changed in a key's middle showed all
  eight lines around it. Such a file is left out of a reading and of `verify`'s diff, and that is said. The same
  gap is in the reference project's table; the note `docs/notes/2026-11-22-private-key-lines-in-a-diff-hunk.md` is
  for the owner to take there.
- **Exclusions mean what a person means.** A pattern with no slash names a file or a folder at any depth, and letters
  match in either case. Handed to git as written, `*.pem` kept only the top folder's keys out. `exclude` is a
  required argument of every reader of the repository, and a table written as a value is refused.
- **The reader refuses a link anywhere on the path**, not only at its end: git lists a tracked file still after its
  folder became a link.
- **A search counts only lines that still hold the word once scrubbed**, so it cannot tell whether a hidden value
  holds a word.
- **What was left out for room may be asked for again**, and the stage is told what that is. A request is remembered
  as answered only once it was shown or refused for good; before, a file left out for room was never read.
- `smoke` is scrubbed as every command is.
