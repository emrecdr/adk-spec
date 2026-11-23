# Research during planning — implementation plan

> Executed inline (superpowers:executing-plans), test first; then `/simplify` and `/code-review high`, a fresh-clone
> gate, and a local merge. No live model call in the build: Task 6 waits for the owner's go-ahead.

**Goal:** `propose` reads the repository, its installed libraries included, before it drafts the brief; the brief asks
only what the person can decide, in order of what depends on what, and "yes" takes a suggestion.

**Spec:** `docs/superpowers/specs/2026-11-23-research-during-planning-design.md`.

## Global constraints

- Layers hold: `workspace` imports no network module; only `workspace/process.py` starts a program.
- No new subcommand and no new flag; `--no-explore` and `--no-input` keep their meaning.
- A stage's opening line is unchanged: the fake model and recordings match on it.
- Ruff: complexity 10, lines 120. Test names are sentences. No test calls a model or the network.

## Review focus

1. A library path that leaves its root (`../`, a link, a `RECORD` line outside `site-packages`) is never read.
2. A request triage sizes `none` spends no reading; a revision and `--no-explore` read nothing.
3. A reading that keeps nothing, or fails, writes no `context.md`, and `plan` does not read again for that `propose`.
4. Dependencies among open points that loop, or name a point that is not there, ask every point rather than none.
5. "yes" typed to a question with no suggestion is the answer "yes", not acceptance.

---

### Task 1: Installed libraries as read-only sources

**Files:** create `adk_spec/workspace/installed.py`; modify `adk_spec/workspace/source.py`; test
`tests/test_installed.py`.

**Interfaces — produces:**
- `installed.Environment(scheme: str, where: str, root: Path, packages: tuple[tuple[str, str, tuple[str, ...]], ...],
  paths: tuple[str, ...])`: one environment, `python` (root `site-packages`) or `node` (root `node_modules`); each
  package's name, version and top-level names; every readable path, from the root, with forward slashes.
- `installed.environments(root: Path) -> list[Environment]`: `.venv` then `venv` (the first found, POSIX
  `lib/python3.*/site-packages` or Windows `Lib/site-packages`), and `node_modules`.
- `Source.of(root, *, exclude, others=None, installed=False)`; library paths shown as `python:<path>`,
  `node:<path>`; `Source.tree()` ends with a block naming each library and version and how to read one.

Python packages from each `*.dist-info`: `METADATA` `Name:` and `Version:`, files from `RECORD` (the CSV's first
field), keeping text suffixes (`.py .pyi .md .rst .txt .json .toml .cfg`) and dropping lines that leave the root
(`..`), `__pycache__` and the `dist-info` folder itself. Node packages: each `node_modules/<name>` and
`node_modules/@scope/<name>` holding `package.json`, files walked without following links, nested `node_modules`
skipped, suffixes `.js .mjs .cjs .ts .mts .cts .json .md`. At most `LIBRARY_MAX_PATHS = 50_000` paths an environment,
`LIBRARIES_SHOWN = 120` names in the tree.

- [ ] Tests, red first:
  - `test_a_python_environments_library_is_read_by_its_import_path`: a `site-packages` with `httpx/_client.py` and its
    `dist-info` → `gathered(["python:httpx/_client.py"], [], [])` shows the text; `tree()` names `httpx 0.28.1`.
  - `test_a_windows_environment_is_found_as_well` (`.venv/Lib/site-packages`).
  - `test_a_node_package_is_listed_and_read` (`node:react` folder lists `node:react/index.js`).
  - `test_a_record_line_outside_site_packages_is_never_listed` (`../../bin/tool`).
  - `test_a_linked_package_is_not_read` (a symlinked `node_modules/linked`).
  - `test_a_library_holding_a_key_is_withheld`.
  - `test_libraries_are_not_searched_and_name_no_repository`: a search finds the repository's line only; `names`,
    `commits()` hold no library.
  - `test_no_library_is_read_unless_asked_for` (`installed=False`, the default).
- [ ] Implement; run the tests and the layering test; commit.

### Task 2: The reading's stages know libraries

**Files:** `adk_spec/orchestration/stages/{scout,survey,review}.py` (guides only); test `tests/test_explore.py`.

- [ ] `test_a_statement_quoting_an_installed_library_is_kept`: a fake reading whose scout names
  `python:httpx/_client.py` and whose survey quotes a line of it keeps the statement under that path.
- [ ] Each guide: libraries are listed after the files; name one's file as `python:<path>` or `node:<path>`, its
  folder to list it; read one only where the change depends on how it behaves at this version. Commit.

### Task 3: The reading before the brief

**Files:** `adk_spec/orchestration/graph.py` (`build_triage_app`), `stages/brief.py`, `stages/deltas.py`,
`adk_spec/interfaces/cli.py`; tests `tests/test_propose.py`.

**Interfaces — produces:** `graph.build_triage_app(*, ledger, recorder=None) -> App`: triage behind its gate, `TIER`
in state; brief and deltas instructions hold `THE_PROFILE` and `THE_CONTEXT`.

`propose` with no `--tier` runs the triage app first; `none` ends as now. A new change with no `--no-explore` reads
then, through `Source.of(..., installed=True)`, seeded with the request as the brief; the brief and the deltas are
seeded with the context text and the profile; `context.md` is written once the change is, and the plan is drafted
with `explore=False`. A revision is seeded with its own `context.md`.

- [ ] Tests, red first:
  - `test_propose_reads_the_code_before_the_brief_and_once`: the stages run triage, scout, survey, review, brief,
    deltas, tasks, in that order; one scout call; `context.md` written.
  - `test_the_brief_is_given_the_profile_and_what_the_reading_kept`.
  - `test_a_request_that_owes_no_spec_spends_no_reading`.
  - `test_a_reading_that_keeps_nothing_writes_no_context_and_the_plan_reads_no_more`.
  - `test_no_explore_reads_nothing_and_the_brief_still_sees_the_profile`.
- [ ] Implement; full suite (existing propose tests may need their call order); commit.

### Task 4: Questions by dependency, and "yes"

**Files:** `adk_spec/domain/drafts.py` (`OpenPointDraft.depends_on`), `adk_spec/domain/convert.py` (`questions_of`,
`to_brief` order), `stages/brief.py` (guide), `adk_spec/interfaces/cli.py` (`_answered`); tests
`tests/test_propose.py`, `tests/test_convert.py`.

- [ ] Tests, red first:
  - `test_a_round_asks_only_the_points_whose_prerequisites_are_settled`.
  - `test_points_that_depend_on_each_other_in_a_loop_are_all_asked`.
  - `test_the_brief_lists_the_points_answerable_now_first`.
  - `test_yes_takes_the_suggestion_and_is_an_answer_where_none_is_suggested`.
- [ ] `depends_on: list[int]` (1-based numbers of other open points; default empty); the frontier is every point none
  of whose numbers names another present point; a loop or a frontier that would be empty asks all. The guide: word
  each question so "yes" accepts the suggestion; ask nothing the context or profile settles; ask of what is still
  unknown what the person can decide or knows. Commit.

### Task 4b: Rules from the skills the owner pointed to (added mid-phase)

**Files:** `stages/{brief,deltas,tasks,check}.py` (guides only); test `tests/test_stage_rules.py`, one test a rule:
the brief invents nothing and keeps an answer's exact words; a THEN a run could show false; tasks easy-first, sliced,
tested at the highest seam, a bug fix starting with a failing test; the check finding a softened brief. Commit.

### Task 5: Docs

README (how `propose` reads first, libraries), `docs/full-usage-guide.md`, the roadmap's phase 15 row and state,
`CLAUDE.md` and `.github/copilot-instructions.md` (libraries under `Source`, the new order). Commit.

### Task 6: Live proof — waits for the owner's go-ahead

One `propose` and its `plan` on a repository with a `.venv`, on Copilot; recorded in `docs/measurements/`.
