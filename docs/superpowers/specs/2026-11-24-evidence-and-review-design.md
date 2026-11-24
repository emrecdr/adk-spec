# Evidence and review: the phase after the fourth audit

Designed on 24 November 2026, from `docs/reports/Spec tool feature opportunities.md` (options 2, 3, 1, 4 and 5) and
a second outside report checked against it. The owner chose these five, in this order, as one phase, and answered
four questions (below).

## Intent

adk-spec already proves a model's words with code: every verdict `verify` keeps quotes lines it found in the diff.
Today that proof is printed once into `reports/verify.md` and then lost, and the people around a change read it the
hard way: an approver reconstructs each changed requirement from two files, an assistant gets "implement tasks.md"
after a verification that named exactly what is missing, and CI checks a spec's grammar but not whether the
approval or the verification still covers what is merged. This phase keeps what adk-spec already knows and puts it
where each reader looks, with no model call and no new command.

## Goals

1. **The approver's view.** One file shows, for each requirement a change touches, what it adds, removes, and a
   diff of what it modifies, and which other open change touches the same requirement.
2. **The next work.** A verification that finds requirements unmet writes what is left, and the next step names it.
3. **Evidence that outlives the change.** The lines `verify` proved are kept beside each living spec at archive;
   a requirement whose lines are gone from the code is flagged as suspect, by code alone.
4. **A merge gate.** `validate` reports a voided approval and drifted work, and speaks GitHub's annotations when it
   runs in GitHub Actions.
5. **What a reviewer of the pull request reads.** `verify` writes a summary to paste into the pull request, and
   `archive` keeps a changelog of the requirements each change added, modified and removed.

## Non-goals

- No new subcommand, flag, or `change.json` field. An older adk-spec refuses a field it does not know, and every
  new file sits where it reads nothing (an older adk-spec finds capabilities by `spec.md` and changes by
  `change.json` alone).
- No model call anywhere in this phase; nothing a model says is run.
- No network: the CI output is lines on standard output and one appended file.
- SARIF, GitLab's format, tests mapped to requirements, `verify` judging the constitution, a tier raised after the
  reading: later, the last three measured first.
- A count of requirements with no evidence on record: not now (little on screen).

## Anti-goals

- Noise that teaches people to ignore adk-spec: a suspect requirement is a note until real use measures how often a
  refactor sets it off.
- Anything that voids an approval by itself: no new file enters an approval's fingerprints, and `tasks.md` is never
  written after the plan.
- A secret kept in a tracked file: every kept quote passes `secrets.scrub` first.

## Constraints

- Layers: pure renderers and checks in `domain`, files in `workspace`, printing in `interfaces`
  (`tests/test_layering.py`). `domain` does no I/O.
- The golden rule: each command prints at most one more line; the detail is in the files.
- Every Markdown file adk-spec writes and reads again has a grammar that renders and parses back (the project's
  rule: a text that does not read back as written is refused).
- C901 at most 10, lines at most 120; macOS and Windows; Python 3.14.
- Tests first, the fake model only inside pytest.

## Approaches considered

- **A. By value, smallest first (chosen).** The approver's view and the next work first, being small and standing
  alone; then the evidence store; then the gate and the summaries, which read it. Each step ships something a
  person uses.
- **B. The evidence store first.** Everything as renderers over one store from the start. Cleaner on paper, but the
  two most useful features would wait on the largest.
- **C. Two phases.** The first two features alone, then the rest. The owner chose one phase.

## The owner's decisions, 24 November 2026

| Question | Decision |
|---|---|
| Where the remaining work goes | `reports/remaining.md`, beside `verify.md`; `tasks.md` untouched |
| How loud a suspect requirement is | A note (INFO) first; never fails CI |
| CI output | GitHub annotations and a job summary, automatically when `GITHUB_ACTIONS` is set; SARIF later |
| A changelog | Yes: `.spec/changelog.md`, written at archive |

## The design

### 1. The approver's view: `reports/review.md`

- **What it holds**, per capability of the change: each ADDED requirement whole, in its canonical render
  (`spec_md`); each REMOVED one with its reason; each MODIFIED one as a unified diff (`difflib`) of the living
  requirement's canonical render against the delta's. Then, for each MODIFIED or REMOVED requirement another open
  change also modifies or removes, the other change's ID.
- **Domain**: a new `adk_spec/domain/review_md.py`, `render_review(change_id, deltas, living, overlaps) -> str`,
  with `overlaps: Mapping[str, Sequence[str]]` (requirement ID to the other open changes' IDs).
- **Workspace**: the overlaps are read from every open change but this one and the archived ones, as text, so a
  delta mid-edit still counts, but by its headings: an ID counts only as a `### REQ-…:` heading under the MODIFIED
  or REMOVED section, never where a statement mentions it. (Builder check: read as `taken` reads, a mention would
  count as a modification.)
- **When it is written**: whenever a command leaves the change waiting on its approval, so the file the approver
  reads is current. That is the end of `propose` (whether it stopped before the plan or drafted it), `plan`,
  `check` and `rebase`: each prints `review    <path>: N modified, M also by open change X` (one line; the second
  half only where there is an overlap).
- **`approve`** prints one `note` line where another open change modifies or removes a requirement this one does;
  it never refuses for it.
- **`archive`'s stale base**: where a merge is refused with `delta.base-stale`, `archive` writes `review.md` again
  (its diff is against the living spec as it now stands, which is what moved) and its stderr paragraph names it, in
  place of "read the current requirement".

### 2. The next work: `reports/remaining.md`

- **What it holds**, for each requirement whose verdict is not `met` (`unmet`, `unclear`, or none), code-derived
  items first:
  - each task that names the requirement, and whether it is ticked (a ticked task whose requirement is unmet first:
    the clearest sign the work and the list disagree);
  - the files those tasks named (`Task.files`) that the diff never touched (`parts_of_diff`);
  - then the model's reason, labelled as the model's words, which code has not grounded.
- **Domain**: a new `adk_spec/domain/remaining.py`: a pure function over the verdicts (`Verdict`), the task groups
  and the diff's paths, and its renderer.
- **When**: `verify` writes it where any requirement is not met, and removes it where every one is. `verify`'s
  `wrote` line names it beside `verify.md`.
- **The next step**: `lifecycle._after_approval` reads `state.verification.verdicts` (already in `change.json`):
  after the failed-tests step, a change with a requirement not met gets
  `REQ-A, REQ-B unmet: work from reports/remaining.md, then run `adk-spec verify <id>``, at most three IDs named,
  then "and N more". `status`, the Skill and the MCP tools follow this step already, so an assistant loops back with
  no prompt written.

### 3. Evidence, and suspect requirements

- **What is kept**: for each `met` verdict of an ADDED or MODIFIED requirement, its grounded evidence, the
  (path, quote) pairs `grounded()` returned. A removed requirement's quotes are of lines taken out and are not
  kept. The diff is scrubbed before a model sees it, so a quote over a secret holds `[REDACTED`: such a quote is
  dropped, as it could never be found in the file again. A quote is one line already (`grounded` keeps it `plain`,
  its whitespace runs one space, as `quoted_at` compares); at most 240 characters, at most three a requirement.
- **Grammar**: a new `adk_spec/domain/evidence_md.py` renders and parses back an evidence file, one entry a line,
  grouped under each requirement's ID: the repository (`.` for this one; for another, its path from the folder that
  holds `.spec/`, as the proving change recorded it in `repositories`), the path within it, the quote, the change
  that proved it and the verification's time. One entry a line, so deleting a line by hand, the way a suspect is
  cleared, always leaves a file that reads. A quote holding a backtick, or any text, round-trips.
- **An evidence file that does not read** (a line edited by hand off its grammar): `validate` notes it, INFO
  `spec.evidence-unreadable`, with the line; `archive` leaves such a living file as it is, folds nothing into it,
  and says so in one line. Evidence is read by `verify`, `archive`, `status` and `validate` alone, never by
  `Workspace.specs()`, so no other command can be stopped by it.
- **The change's file**: `verify` writes `changes/<id>/evidence.md`, outside every approval
  (`Workspace.approval_texts` covers the brief, the design, the tasks and the delta specs only), headed with the
  verification's time.
- **The living file**: `archive` folds the change's evidence into `.spec/specs/<capability>/evidence.md` in the
  same all-or-none write as the merged specs and the state (`Workspace.write_specs`): the lines of each requirement
  the change added or modified are replaced by the change's, a requirement it removed loses its lines, the rest are
  kept. Only evidence whose time is the recorded verification's is folded; anything else is left out, as from a
  verification since superseded.
- **The check**: a pure `suspects(evidence, read, found_elsewhere) -> list[Finding]` in `domain`. An entry stands
  where `quoted_at` finds its quote in its file, read as it is on disk. One that does not is looked for elsewhere in
  its repository, so a moved function reads as moved: the quote's longest run with no space is searched with
  `workspace/git.py`'s `grep` (a fixed string), and each of at most 20 files it names is read whole and confirmed
  with `quoted_at`. A requirement none of whose quotes is found anywhere is suspect: one INFO finding,
  `spec.evidence-gone`, with the evidence file's path and the line, naming the requirement and its file. A
  repository whose folder is not there, or is no git repository, as in CI, is not checked.
- **Where it shows**: `validate` lists the findings; `status` adds one line per capability holding a suspect
  requirement, `auth: 2 requirements suspect (adk-spec validate lists them)`.
- **Clearing**: a later change that verifies the requirement replaces its lines at archive; or a person deletes the
  lines in a reviewed commit. No command.

### 4. The merge gate

- **New codes** in `SEVERITY`:
  - `change.approval-void` (WARNING): an approved or verified change whose files changed since the approval
    (`Assessed.stale`).
  - `change.work-drifted` (WARNING): a verified change whose work changed since it was verified. `validate` now
    asks git, where it can.
  - `change.drift-unknown` (INFO): the work could not be compared (a shallow clone, a repository absent). `archive`
    keeps refusing in that case, as now; only `validate` tells the two apart.
  - `spec.evidence-gone` and `spec.evidence-unreadable` (INFO), from part 3.
  WARNING fails `validate --strict`, the documented CI recipe. The three `change.` codes are made by `validate`
  alone, from `Assessed.stale` and the drift it asks of git, and never enter `findings_of` or
  `Assessed.findings`: there, `approve_blockers` would read a void approval's WARNING as blocking on the strict tier,
  and the approval that is its only remedy would be refused for good.
- **GitHub output**: where `GITHUB_ACTIONS` is `true` and `--json` is not given, `validate` prints, after its usual
  output, one workflow command per finding with a path (`::error`, `::warning` or `::notice`, with `file`, `line`
  and the code as `title`, escaped as GitHub's rules say), and appends a short Markdown summary (the counts and a
  table, at most 50 rows then "and N more") to the file `GITHUB_STEP_SUMMARY` names. GitHub shows ten annotations
  of each kind a step; the summary carries the rest. Every message passes `secrets.scrub`.
- **Domain**: a new `adk_spec/domain/ci_md.py`, pure: the annotation lines and the summary from `Finding`s. The
  append is a `workspace/files.py` helper.
- **README**: a sample workflow that checks out the pull request's own commit
  (`ref: ${{ github.event.pull_request.head.sha }}`) with `fetch-depth: 0`. The default, the merge with the target
  branch, holds what that branch gained since the verification's base, and a verified change would read as drifted
  whenever the target moved. The README's flow archives a change before its pull request merges, so the WARNING
  fires for a change verified and then left unarchived while its work moved on: `verify` it again.

### 5. The pull request's summary, and the changelog

- **`reports/summary.md`**, written by `verify` each time: the brief's title and why; the requirements added,
  modified and removed, with their names; each verdict; the tests' outcome; who approved. Markdown to paste into a
  pull request. Named on the same `wrote` line.
- **`.spec/changelog.md`**, written by `archive` in its same all-or-none write: an entry per archived change,
  newest first: the change's ID and date, then `Added`, `Modified`, `Removed` lines of requirement ID, name and
  capability. A missing file is made with a `# Changelog` heading; the new entry goes after the heading and before
  everything below it, which a person may have edited and is kept as it is.

## What is left to the builder

- Where the review view is written from: one helper called by the commands listed, or by the code that says the
  next step where that step is the approval. Either, with a test per command.
- How `_drifted` tells "could not compare" from "changed" (a third value, or a separate question) while `archive`
  keeps refusing both.
- The evidence grammar's exact Markdown, under its round-trip test.
- The exact wording of each new line, in the project's style.
- Docs: the README's sections on `verify`, `archive`, `status`, `validate` and CI; the roadmap; and CLAUDE.md with
  `.github/copilot-instructions.md`, should a rule that spans files change.

## How it is proven

Tests first, with the fake model (`fake_provider`) and `seeded()`:

- `review.md`'s diff for a MODIFIED requirement, the overlap with another open change (and no overlap where its
  statement only mentions the ID), and the line each listed command prints; `approve`'s note; `archive`'s stale-base stop naming the file.
- `remaining.md` written with unmet verdicts and removed once all are met; a ticked-but-unmet task listed first;
  the next step naming the IDs, capped at three.
- Evidence: the grammar round-trips (a backtick, another repository's path) and still reads with a line deleted; a
  quote holding `[REDACTED` is dropped; archive folds and replaces; a superseded verification's evidence is not
  folded; a living file that does not read is left as it is; a quote moved to another file is not suspect; a deleted
  one is, as INFO; another repository that is not there is not checked.
- The gate: each new code, `--strict` failing on the two WARNINGs, INFO where git cannot compare; a strict change
  whose approval is void still approved again, its next step unchanged; the annotation
  lines escaped; the summary capped; nothing GitHub-specific without `GITHUB_ACTIONS`.
- The summary and the changelog: their content, the changelog's entry placed after the heading with a person's edits
  kept, and the archive writing all or none.
- Every change made by an older adk-spec reads the same: no new `change.json` field.
