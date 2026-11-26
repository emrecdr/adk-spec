# adk-spec audit: hardening, architecture, UX and market

Read-only audit of `main` at `5f1d022`, 25 November 2026. Local `main` is the latest code: `origin/main` is 89 commits
behind it (`299f639`), as nothing has been pushed since phase 15.

## Summary

- **Overall:** the design is sound. Layers are enforced, gates are in code, writes are atomic, and model words count
  only where code finds them. No crash or data-loss bug appeared in normal use.
- **P0 (3 items):** the secret scrub misses common credential lines and string-embedded private keys. Files under
  `.spec/` are also read, and `.spec/runs/` pruned, through symbolic links. The first two break the project's own rule
  "secrets never reach a model or a recording". All three are low effort.
- **P1 (15 items):**
  - a cancelled or killed command leaves the project's tests running;
  - the MCP `verify` tool turns a config edit into a command run;
  - the CLI-to-engine seam is typed `Any`;
  - tests copy stage openings and can pass silently;
  - minutes-long commands show internal stage names and no clock, and `verify` never states its outcome;
  - README transcripts drifted from the real output;
  - the Agent Skill misses the paths and upgrade path that competitors' skills now use.
- **Market:** four differentiators hold, none documented by any competitor checked:
  - quotes checked in code;
  - approvals as fingerprints;
  - a merge gate with no model;
  - suspect requirements after archive.

  Reading the code before drafting and living specs with deltas are no longer unique. The largest market risk is
  evidence: a peer-reviewed study of 88,052 pull requests found that spec documents did not reduce defects.
- **Golden rule:** no recommendation adds a subcommand. Each one makes an existing command, file or text do more.

**Legend:**
- **Confirmed:** reproduced by an offline probe, or read in the code with its failure path traced.
- **Potential:** the mechanism is in the code, and the harm depends on the environment or the inputs.

## Method and limits

- **Phase 1, read-only:**
  - Five parallel researchers covered hardening and performance, security, architecture, UX, and the market.
  - Every key claim was then checked again in this session against the code. Offline probes called `secrets.scrub`,
    `holds_a_key` and `--help`.
- **Journeys traced:**
  - `init` in an existing repository;
  - a standard change: `propose`, `approve`, implement, `verify`, `archive`;
  - a strict change with two approvers;
  - a change across repositories;
  - work through MCP and the Agent Skill;
  - CI through `validate`.
- **Not done:**
  - No live model call: model-quality claims are not measured.
  - No Windows run.
  - No file of the codebase changed. This report is the only file written, and it is not committed.
- **Market claims** come from web sources current on 25 November 2026, each cited. Two key claims were spot-checked
  again:
  - The ESEM 2026 study is confirmed.
  - OpenSpec 1.12 "reads the code before drafting" came from its release page. A second search could not confirm it
    from other sources, so treat it as reported, not verified.
- **Roadmap-aware:** items the roadmap (`docs/superpowers/plans/README.md`) already records are marked. One is
  reported again with new evidence (S1).

---

## 1. Hardening, security, performance and stability

### S1. A private key embedded in a string literal reaches the model

- **Status:** Confirmed by probe. This reopens a recorded decision: "the inline key header" at roadmap line 480.
- **Issue:**
  - `_KEY_BEGINS_A_LINE` withholds a file only when a key header begins a line. Only a diff mark, a quote mark or a
    comment mark may stand before it. This is decided on purpose, so that code which only names the header (as
    `secrets.py` does) is not withheld.
  - But a real key held in a string, a common test fixture, is not withheld either:
    - Key built from concatenated literals (`"-----BEGIN…\n"` then `"MIIE…\n"`): the body is left after `scrub`, even
      when the file is read whole.
    - Key in a triple-quoted string: the whole-file scrub hides the body, but `holds_a_key` is False. A `verify` diff
      hunk that shows only body lines is then sent.
- **Evidence:**
  - `adk_spec/domain/secrets.py:440` (`_KEY_BEGINS_A_LINE`) and `:448-455` (`holds_a_key`).
  - It gates `adk_spec/workspace/source.py:206`, the reading, and `:212-236` and `:484-497`, the verify diff.
  - Probe in this session:
    - concatenated key: `holds_a_key=False`, body present after `scrub`;
    - triple-quoted key: `holds_a_key=False`;
    - names-only code: `holds_a_key=False`, as decided.
- **Where it leaks:** the provider request, the recording in `.spec/runs/`, and possibly the committed `evidence.md`
  through a `met` quote.
- **Proposed solution:**
  - Withhold a file where a key header appears anywhere on a line and lines of long base64 follow it. Commit `922bb11`
    already applies this "long base64 follows" test to a comment's mark, so code that only names the header stays
    unaffected.
  - Let `_KEY_LINE` accept a line that opens with a quote or a `+` concatenation.
  - Add one test for each form.
  - Measure against the reference corpus first, as `secrets.py` requires.
- **Impact / Effort:** High / Low–Medium. **Priority: P0**. The owner decides whether to reopen the decision.

### S2. Common credential lines pass the scrub

- **Status:** Confirmed by probe.
- **Issue:** the unquoted assignment rule needs the value to end the line (`\s*$`). It allows only `export`, `env` or
  `arg` before the name.
  - Probed in this session, unchanged by `scrub`:
    - `DB_PASSWORD=hunter2pass # prod`
    - `  - POSTGRES_PASSWORD=hunter2pass` (docker-compose)
    - `password: hunter2pass  # rotate`
  - The same line without the comment is redacted.
  - The researcher also found these pass: Dockerfile `ENV API_KEY x`, `set PASSWORD=x`, `--password x`, `mysql -px`,
    `.netrc` `password x`, Docker's `"auth": "<b64>"`, and `Password=x;` in a connection string with no digit.
- **Evidence:**
  - `adk_spec/domain/secrets.py:341-349`.
  - Failing test output goes into `reports/verify.md` (`adk_spec/domain/report_md.py:99-104`), which is committed with
    the change.
- **Proposed solution:**
  - Allow a trailing `\s+#.*` and a YAML list item (`-\s+`) before the name.
  - Add `ENV` and `set` as leads.
  - Add rules for `--password[= ]`, the `.netrc` `password` field and Docker's `auth`.
  - One test per form.
- **Impact / Effort:** High / Low. **Priority: P0**.

### S3. `.spec/` is read, and `.spec/runs/` pruned, through symbolic links

- **Status:** Confirmed in the code. Exploiting it needs a hostile repository or pull request with committed links.
- **Issue:**
  - `inside()` guards the writes in `layout.py` only.
  - Reads follow links:
    - `files.read_text` calls `path.read_bytes()`;
    - `Workspace.find` uses `is_dir()`;
    - `context.py` reads the constitution, profile, lessons and context.
  - `runs.write` writes through `write_all` with no `inside()`. It then `unlink`s every `*.json` that `listed()` globs
    past the newest 20.
- **Scenarios:**
  - A committed `.spec/profile.md` that links to `../../.netrc` is sent with every `propose`, scrubbed by shape only
    (see S2).
  - A committed `.spec/runs` link to another folder gets recordings written there, and that folder's older `*.json`
    files deleted.
- **Evidence:**
  - `adk_spec/workspace/files.py:31-39`, `layout.py:142-147`, `context.py:77-125`, `runs.py:70-84`.
  - The code reading already refuses links on every path part (`source.py:194-268`): this is the same guard, missing
    on `.spec/`.
- **Proposed solution:**
  - Add one reader for `.spec/` that refuses a link on every path part, `.spec` included.
  - Use `inside()` for the runs folder.
  - Have `Workspace.find` refuse a linked `.spec`.
  - Test with a linked profile and a linked runs folder.
- **Impact / Effort:** Medium–High / Low. **Priority: P0**. An existing guard is inconsistent, and the fix is small.

### H1. Cancelling or killing a command leaves the project's tests running

- **Status:** Confirmed: the researcher's probe showed the grandchild alive after `stop()`, and this session read the
  code.
- **Issue:**
  - The MCP server promises that a cancelled call stops "its command, and what it started" (`mcp_server.py:13-14`,
    `:95`).
  - `stop()` sends SIGKILL to the command's own process group (`workspace/process.py:183`).
  - But `run_kept` starts the tests in a new session of their own (`process.py:125`). The kill never reaches them.
  - SIGKILL leaves the command no time to clean up. `cli.run()` handles only `KeyboardInterrupt`, so SIGTERM and
    SIGHUP (a closed terminal) are not handled either.
- **Failure scenario:**
  - An assistant cancels `verify` mid-test, the 3,600 s tool timeout fires, or the editor reloads.
  - The test suite, and any server it started, keeps running with no timeout enforced.
  - The next run takes over the lock, because its owner is dead. A second `verify` then runs tests beside the orphan.
- **Evidence:**
  - `adk_spec/workspace/process.py:64-75`, `:97`, `:114-126`, `:175-184`.
  - `adk_spec/interfaces/cli.py`, `run()`.
  - `tests/test_mcp_server.py:116-127` checks only the direct child.
- **Proposed solution:**
  - In `cli.run()`, turn SIGTERM and SIGHUP into `KeyboardInterrupt` (POSIX). The existing interrupt paths then stop
    the test tree, release the lock and record "interrupted".
  - In `stop()`, send SIGTERM to the group, wait `DRAIN_S`, then SIGKILL.
  - Add a test that the grandchild is gone.
  - Windows is covered by the roadmap's job-object item.
- **Impact / Effort:** Medium–High / Low. **Priority: P1**.

### S4. The MCP `verify` tool turns a file edit into a command run

- **Status:** Potential. The mechanism is confirmed; the harm depends on the editor's approval settings.
- **Issue:**
  - `verify` runs `[verify] test` from `.spec/config.toml`, which can be any argv. It also runs each other
    repository's own test command.
  - The server relies on "the editor's own approval of each step". But accept-edits modes apply file edits with no
    prompt and still ask before terminal commands.
  - So an assistant misled by injected text can edit the config, then call `verify`, often set to always allowed. The
    command runs with no shell prompt.
  - The `bases` parameter also lets the agent whose work is judged pick the diff's base commit.
- **Evidence:**
  - `adk_spec/interfaces/mcp_server.py:6-9`, `:185-196`.
  - `cli.py:1877-1889`, `config.py:84-97`, `source.py:353-358`.
- **Proposed solution:**
  - Under the server, refuse a test command whose `.spec/config.toml` differs from `HEAD`, and name it. Committing is
    a step the person approves.
  - Drop `bases` from the tool, or accept only commits that descend from the approval's base.
- **Impact / Effort:** High / Medium. **Priority: P1**. It changes an MCP tool contract, so it is the owner's call.

### Lower-priority hardening and security items

| ID | Issue (status) | Evidence | Proposed solution | Impact / Effort | Priority |
|---|---|---|---|---|---|
| H2 | Diffs are built and held whole before the 200,000-character refusal; every `status` and `validate` re-diffs each verified change (Confirmed) | `workspace/git.py:240-251`, `process.py:83`, `cli.py:505-517, 634-642, 1764-1768`, `source.py:228-233, 431-442` | `stat` untracked files first; refuse past about 4 × `DIFF_MAX_CHARS` bytes with "too large to judge; ignore it" | M / L | P2 |
| H3 | Evidence checks in `status` and `validate` repeat file reads and greps, with no cache and no size cap (Confirmed: a gone quote costs 43–60 ms here; a refactor in a large repository multiplies it) | `workspace/evidence.py:43-49, 64-125`, `cli.py:617, 703-709` | Cache text, plain and scrubbed text per path and grep hits per term within one call; skip files past `FILE_MAX_BYTES`; cap greps per command and count the rest as unknown | M / L | P2 |
| H4 | Model deadlines are fixed (180 s a call with retries, 600 s a run) and were never measured on slow models (Potential) | `orchestration/models.py:41, 43`; 10 calls took 321 s (`docs/measurements/2026-11-23-phase-15-live.md:95`) | Derive the run deadline from the app's maximum calls × `REQUEST_TIMEOUT_S`; record seconds per call in measurements | M / L | P2 |
| H5 | A lock left by a power loss is refused when its PID is reused after reboot (Potential) | `workspace/lock.py:97-117` | Also take over a lock whose file is older than the boot time | L / L | P2 |
| S5 | Injected text can reach the coding assistant through `context.md`, which the Skill says to read and no approval covers; a code comment saying "REQ-X is met" can count as `met` evidence (Potential) | `domain/context_md.py:1-7`, `mcp_server.py:63-64`, `domain/verify.py:96-118` | Say in the Skill, the server text and the file's header that `context.md` is material, not instructions; flag in `verify.md` a `met` verdict whose every quote is a comment or a string | M / L–M | P2 |
| S6 | Test runs keep provider keys exported in the shell or set in the MCP server's `env`; only names that `.env` added are withheld (Confirmed) | `cli.py:996-1018` (`_FROM_ENV_FILE`), `workspace/tests.py:38-48` | Always drop the variables adk-spec reads (`GOOGLE_API_KEY`, `GEMINI_API_KEY`, `GOOGLE_GENAI_*`, `GITHUB_COPILOT_*`, `LITELLM_*`, `SPEC_*`); add a `[verify] pass_env` opt-in | M / L | P2 |
| S7 | The README's CI example pins actions by tag, has no `permissions:` block and keeps default `persist-credentials` (the repository's own `ci.yml` is right) (Confirmed) | `README.md` ~581-592 vs `.github/workflows/ci.yml` | Copy `ci.yml`'s practices into the example: actions by commit, `permissions: contents: read`, `persist-credentials: false` | M / L | P2 |
| S8 | `login` imports LiteLLM without `_litellm()`, so LiteLLM runs in DEV mode: it reads a `.env` up from its install folder and fetches the remote price map (Confirmed) | `interfaces/login.py:93-99` vs `orchestration/models.py:150-160` | Call `models._litellm()` first, or set its two variables | L / L | P2 |
| S9 | Job-summary cells escape only `\|`; a folder name or heading from a PR renders as links or images (Confirmed) | `domain/ci_md.py:61` | Escape `[`, `]`, `!`, `<`, `` ` `` in cells | L / L | P2 |

---

## 2. Architecture and codebase modernization

The architecture is right for the product:
- four layers, enforced twice in `tests/test_layering.py`;
- one quote test (`quoted_at`);
- one tier table (`DEMANDS`);
- a pure domain with round-trip grammars.

No new layer, pattern or framework is recommended. The findings are seams and duplication that cost real time.

### A1. The CLI-to-engine seam is typed `Any`

- **Status:** Confirmed.
- **Issue:**
  - `cli.py` has 50 `Any`. It imports engine types lazily to keep offline commands fast, and loses their types doing
    so.
  - Examples:
    - `change: Any` appears at `cli.py:488, 1203, 1665, 1897`, although `Change` is imported at `:73`;
    - `ledger: Any` appears 12 times;
    - `found: Any` (an `Explored`) and `known: Any` (a `Known`).
  - No module uses `TYPE_CHECKING`.
  - So pyrefly cannot see a rename such as `Explored.unknown_over` or `UsageLedger.spent`. The error then appears only
    at runtime, in whichever test reaches that line.
- **Evidence:** `adk_spec/interfaces/cli.py`; `grep -c '\bAny\b'` gives 50; no `TYPE_CHECKING` in `adk_spec/`.
- **Proposed solution:**
  - Import `UsageLedger`, `Explored`, `Known`, `Recorder` and the run result under `if TYPE_CHECKING:`, and use
    `Change` where it is already imported.
  - Runtime behaviour is unchanged, and `test_layering`'s runtime probes still pass.
- **Impact / Effort:** Medium / Low. **Priority: P1**.

### A2. Tests copy stage openings, and an unmatched rule passes silently

- **Status:** The duplication is confirmed; the silent pass is potential.
- **Issue:**
  - Each stage exports `OPENING` (`stages/brief.py:29`, `check.py:20`, `review.py:20`, `survey.py:19`).
  - Tests redefine these instead: 23 module-level copies in 13 files, plus 25 inline openings. "You size a change
    request" alone appears 15 times inline.
  - When no rule matches, `FakeProvider.answer` returns None (`tests/conftest.py:276`), and the fake serves its canned
    answer (`:311`).
  - So if a stage's opening is reworded, a test meant to exercise one answer runs on the canned one, and passes or
    fails for the wrong reason.
- **Proposed solution:**
  - Import `OPENING` from the stage modules.
  - Make `fake_provider` fail on a rule that never matched, with an opt-out for tests that check a stage is never
    called.
- **Impact / Effort:** Medium / Low. **Priority: P1**.

### A3. `cli.py` is the change hotspot and holds use-case logic

- **Status:** Confirmed. The roadmap (line 480) lists "splitting `cli.py`" as decided. The only reason recorded is at
  line 402, that MCP tools run the CLI as a process, which answers an in-process split, not this one.
- **Issue:**
  - `cli.py` has 2,426 lines, 20% of the package.
  - It is touched by 141 of 286 commits; the next file by 50.
  - 8 of the 13 functions at complexity 9–10 are in it.
  - It has 63 inline `from ..orchestration` imports.
  - It holds use-case logic, not just argparse and printing:
    - change assessment and drift (`:444-517`);
    - the inputs each stage is given (`_plan_made`, `_judged`, `_verdicts`);
    - the multi-run propose loop (`_rounds`).
- **Proposed solution:** only if the owner reopens it.
  - One move, not a file per command: lines ~989-2426 go into one `interfaces` module that the commands import lazily.
    Its engine imports can then stand at its top.
  - Nine `monkeypatch.setattr(cli, …)` calls would need retargeting.
  - Do A1 first: it delivers most of the type benefit for a fraction of the cost.
- **Impact / Effort:** Medium / Medium. **Priority: P2**.

### Lower-priority architecture items

| ID | Issue (status) | Evidence | Proposed solution | Impact / Effort | Priority |
|---|---|---|---|---|---|
| A4 | Plurals and "first N, and M more" are hand-written about 20 times, with five spellings (commas and number formats drift) (Confirmed) | `context.py:142`, `source.py:150, 290`, `review_md.py:61`, `lifecycle.py:501`, `ci_md.py:45`, 14 in `cli.py` | `counted(n, noun)` and `first_of(names, n)` in `domain/text.py`; switch to them when a line is touched | L / L | P2 |
| A5 | Constant names clash and force 14 aliases; `RULES` means both a stage key alias and a section's text (Confirmed) | `cli.py:100-123`; `stages/__init__.py:76` | Give `layout`'s file-name constants a `_FILE` suffix at the source | L / L | P2 |
| A6 | Exit codes are written twice: `_ENDINGS` keys on the literals 1, 2, 3 (Confirmed) | `mcp_server.py:71` vs `cli.py:132-139` | Key `_ENDINGS` by `cli.EXIT_*` (no engine import is pulled in) | L / L | P2 |
| A7 | 148 source comments name the review that found a line ("found by the fourth audit"); docstrings and comments are 21% of non-blank lines (Confirmed) | `cli.py` 33, `secrets.py` 17, `lifecycle.py` 16; 312 in tests | Keep the clause that names the failure prevented; drop the provenance in new code; no sweep | L / L | P2 |
| A8 | Slow tests: the 15 slowest take 22.7 s of 90.8 s; the slowest waits out `DRAIN_S = 5.0` (Confirmed) | `tests/test_tests.py:65`, `workspace/process.py:25` | Monkeypatch `DRAIN_S` in timeout tests (saves 5–7 s); try `pytest-xdist` only after measuring | L / L | P2 |

**Checked and right as it is:**
- State keys: 60 named constants, and no raw-string access to session state.
- Pydantic is used for persisted and schema records, frozen dataclasses for in-process results.
- The error types are flat, with one `REFUSALS` tuple mapping them to exit codes 1, 2 and 3.
- Config validation is strict and hand-written, and names the key at fault.
- No dead top-level names were found.
- `source.py` (622 lines) has two clear caller groups; split it only when it grows.
- `from __future__ import annotations` in 116 files is redundant on 3.14 but harmless.

---

## 3. UI/UX: terminal output, reports and assistant text

adk-spec's "pages" are its terminal output, the Markdown files it writes, `--help`, and the text it gives coding
assistants. The base is good:
- plain ASCII with no colour;
- progress on stderr only on a terminal;
- a `next` line on every command that moves a change;
- refusals in one sentence, before anything is spent.

The findings below remove effort without adding commands. Several change printed lines that tests pin: printed labels
are an external contract, so each is the owner's call.

### U1. Progress lines name internal stages and show no time

- **Status:** Confirmed.
- **What the person sees:** minutes of `working   scout`, `survey`, `review`, with no clock. A live `propose` made 9
  calls and spent 42,523 tokens (`docs/measurements/2026-11-22-live-reading.md:25`). "review" here is the reading's
  check, but a later `review` line means `reports/review.md`.
- **Evidence:** `cli.py:1080-1082`; `tests/test_progress.py:38` pins
  `["working   brief", "working   deltas", "working   deltas, again", "working   tasks"]`.
- **Proposed solution:** plain verbs plus elapsed time, still one line per call, with no `\r`.
  - Example: `working   reading the code  0:47`.
  - Stage names map to verbs:

    | Stage | Verb |
    |---|---|
    | triage | sizing the request |
    | scout | choosing what to read |
    | survey | reading the code |
    | review | checking the reading |
    | check | checking the files |
    | verify | judging the work |

- **Impact / Effort:** High / Low. **Priority: P1**.

### U2. The `tokens` line is the longest line on screen

- **Status:** Confirmed.
- **What the person sees:** a `propose` that reads the code lists 7 stages in about 190 characters, which wraps across
  the label column. The README already cuts it with "…" (`README.md:254`).
- **Evidence:** `cli.py:1119-1124` (`_spent`); `tests/test_propose.py:260`.
- **Proposed solution:** print `tokens    23,149 in 9 calls`, plus `of 80,000` when a ceiling is set. The per-stage
  split stays in `.spec/runs/`.
- **Impact / Effort:** Medium / Low. **Priority: P1**.

### U3. `verify` never states its outcome, and names requirements by ID only

- **Status:** Confirmed.
- **What the person sees:** "verified" must be inferred from the `next` line. REQ IDs must be looked up in the spec
  files. A single `wrote` line runs past 150 characters.
- **Evidence:** `cli.py:1834-1836`; `tests/test_summary.py:52-53`; `verify.md` headings are `## {id}: {verdict}`.
- **Proposed solution:**

  ```
  met       REQ-AUTH-004  Sign in with a passkey
  unmet     REQ-AUTH-005  Backup codes: no handler reads them
  verified  no: 1 of 2 met, tests passed
  wrote     .spec/changes/x/reports/verify.md
            .spec/changes/x/reports/summary.md
  ```

  Also put requirement names in the headings of `verify.md`, `remaining.md` and `summary.md`. An assistant sent to
  `remaining.md` then needs no spec lookup.
- **Impact / Effort:** Medium–High / Low. **Priority: P1**.

### U4. A cross-repository `propose` prints `with` and `left out` inside the file list

- **Status:** Confirmed from the code path; no test covers propose's order. `tests/test_plan.py:508` covers `plan`
  only.
- **What the person sees:**

  ```
            .spec/changes/x/context.md
  left out  ../shop-mobile: not on this machine
            .spec/changes/x/tasks.md
  ```

  This reads as if `tasks.md` were left out. The other repositories are named only after their code was sent.
- **Evidence:** `_said_sources` (`cli.py:1361`) runs between the `context.md` line (`:1477`) and the `tasks.md` line
  (`:2115-2116`).
- **Proposed solution:** print `with` and `left out` right after `sized`, before the reading. Silence them in
  propose's plan step.
- **Impact / Effort:** Medium / Low. **Priority: P1**.

### U5. Subcommand help does not say what a command does

- **Status:** Confirmed.
- **Issue:**
  - Only the top-level parser has a `description=`. `adk-spec approve --help` prints usage and options only.
  - The help for `--id` omits "or revise the open change", which the README states (`README.md:643`).
  - Help and messages use jargon: "arm", "triage stage", "in a schema", "ceremony", "deltas", and "a living spec
    does not read" meaning "cannot be parsed" (`cli.py:526, 1304, 1954`).
- **Evidence:** `cli.py:200-292`; `uv run adk-spec approve --help`.
- **Proposed solution:**
  - Give each parser a `description=`: its help line plus `Calls a model: yes / no / only when its check is stale`.
  - `--id`: "the new change's name; an open change's name revises it".
  - Add a top epilog: `One change: propose → approve → implement → verify → archive. adk-spec status says what is
    next.`
  - Say "provider" for "arm".
- **Impact / Effort:** Medium / Low. **Priority: P1**.

### U6. The question round is cryptic, and Ctrl-C there loses the reading silently

- **Status:** Confirmed. Line editing is potential.
- **Issue:**
  - The header reads "A line answers. `=` takes the suggestion, and `yes` one that says yes.", with no prompt marker.
  - Ctrl-C at a question writes nothing (`tests/test_clarify.py:190-204`).
  - The exit message then says "`adk-spec status` says where things stand", and `status` shows nothing for it.
- **Evidence:** `cli.py:1024`, `:1034-1041`, `:2425`.
- **Proposed solution:**
  - Header: `1 point is open. Type an answer and press Enter; = takes the suggestion; an empty line leaves it open in
    brief.md.`, then an `answer> ` prompt.
  - On an interrupted `propose`, print `interrupted: no change was written` and the `tokens` line.
  - Use `input()` with `readline` where available, for arrow keys.
- **Impact / Effort:** Medium / Low. **Priority: P1**.

### U7. README transcripts no longer match the real output

- **Status:** Confirmed.
- **Issue:** `README.md:228` calls them "what adk-spec prints", but:
  - The propose sample (`:241-257`) lacks the `review` line that `tests/test_review.py:123` pins. Checked in this
    session: no `review` line.
  - The strict sample (`:455-456`) contradicts `tests/test_strict.py:93-95`.
  - The verify sample (`:369`) shows one path where `tests/test_summary.py:52` pins two.
- **Proposed solution:** regenerate the three blocks from the tests' pinned output, or point one test at them.
- **Impact / Effort:** Medium / Low. **Priority: P1**.

### U8. `init` never says the test command is unset

- **Status:** Confirmed.
- **Issue:**
  - The config template leaves `[verify]` commented out, and init's `next` line (`cli.py:354`) does not mention it.
  - `verify` says so only after the work is done (`cli.py:1885`). `verify.md` then says the verdicts "rest on the diff
    alone".
- **Proposed solution:** `init` prints `tests     none named: set [verify] test in .spec/config.toml`, and `status`
  repeats it while it is unset.
- **Impact / Effort:** Medium / Low. **Priority: P1**.

### Lower-priority UX items

| ID | Issue (status) | Evidence | Proposed solution | Impact / Effort | Priority |
|---|---|---|---|---|---|
| U9 | Two "read first" lines; the strict `next` line adds `--no-explore` where `plan` already skips the reading (Confirmed) | `cli.py:2118, 545, 2045, 1413` | One line: `read      brief.md (25 lines, 1 assumption), then reports/review.md (1 added)`; drop the redundant flag | L–M / L | P2 |
| U10 | Inconsistent line shapes: `approved \`x\` …` and `archived \`x\`` break the 10-column label; `archive` and `new` end with no `next` line; `validate`'s count leaves out the notes it prints (Confirmed) | `cli.py:425, 586, 627, 709, 717, 738, 901, 966, 2358` | One label column everywhere: `approved  x by ana`, `archived  x into auth; changelog entry added`, `0 errors, 0 warnings, 2 notes`, `next      commit .spec/ with the code` | L–M / L | P2 |
| U11 | Commands on the terminal are wrapped in backticks; pasted with them, zsh and bash run a command substitution, and PowerShell reads the backtick as a line continuation (Potential) | 16 `` run `adk-spec `` phrases in `domain/lifecycle.py:441-540` | Print bare commands on the terminal; keep backticks in Markdown | L / L | P2 |
| U12 | The Skill and the MCP text never mention `reports/remaining.md` or `summary.md`; the MCP text says only `propose` and `plan` take minutes (Confirmed) | `workspace/skill.py:63-64`, `mcp_server.py:56` | Add "Where verify leaves requirements unmet, work from reports/remaining.md; put reports/summary.md in the pull request"; name the four slow commands | M / L | P2 |
| U13 | `status` shows no task progress; `new` writes only `change.json` (Confirmed) | `cli.py:696`, `layout.py:250-252` | A `3/7` tasks column for approved changes; `new` writes `brief.md` and `tasks.md` skeletons that `validate` reports as unfilled | L–M / L | P2 |

**Kept as is:**
- No colour. The labels carry the meaning, and the tool already conforms to NO_COLOR, since it adds none.
- No spinner, and no TUI layer.
- `status` grouped by who acts next ("Waiting on you" / "Ready to run").
- Cost and scope stated before spending.
- Reports that keep code's findings apart from the model's words.

---

## 4. Competitive gap analysis and feature expansion

### Market snapshot (25 November 2026)

| Tool | Form | Verification | Standout | Weakness |
|---|---|---|---|---|
| [GitHub Spec Kit 1.4.5](https://github.com/github/spec-kit/releases) | Python CLI + assistant commands | `converge` adds remaining work as tasks; a prompt judges | Extensions, presets, workflows | No living spec ([doc](https://github.com/github/spec-kit/blob/main/docs/how-to/evolving-specs.md)); read-only, experimental MCP server ([doc](https://github.com/github/spec-kit/blob/main/docs/overview/mcp.md)) |
| [OpenSpec 2.2.0](https://github.com/Fission-AI/OpenSpec/releases) | Node CLI + skills in `.agents/skills` | `validate --strict`; verify is a skill | Brownfield deltas into living specs; a plain-language `/openspec` router; Thoughtworks Radar "Trial" ([radar](https://www.thoughtworks.com/radar/tools/openspec)) | Radar warns of "documentation sprawl" |
| [Kiro](https://kiro.dev/docs/specs/) (AWS) | IDE, CLI, VS Code extension ([changelog](https://kiro.dev/changelog/)) | Property-based tests from EARS requirements, IDE only ([doc](https://kiro.dev/docs/specs/correctness/)) | Quick Spec; bugfix specs; tasks in dependency waves | Per-feature specs, not living; commercial |
| [Conductor](https://github.com/gemini-cli-extensions/conductor) (Google) | Plugin for Antigravity and Claude Code | Review runs tests and checks spec compliance and security ([blog](https://developers.googleblog.com/en/conductor-update-introducing-automated-reviews/)) | Google's own spec tool | A model judges; per-track specs |
| [Tessl 0.124](https://docs.tessl.io/changelog-cli) | Hosted CLI, registry, GitHub App | `change verify`: an LLM judge with `--max-calls` and GitHub annotations ([doc](https://docs.tessl.io/codifying-and-enforcing/verify-agent-changes-in-ci)) | Built for CI | Sends code to a hosted judge; no longer "spec-as-source" |
| [BMAD 6.12.4](https://github.com/bmad-code-org/BMAD-METHOD/releases) | Persona skills | Review triage logs verdict and evidence per finding | Adversarial review; sizes ceremony after investigating | Heavy ceremony |
| [GSD core](https://github.com/open-gsd/gsd-core/blob/main/docs/how-to/verify-and-ship.md) | Skills for many assistants | A digest marks verification `stale` when inputs change | Ship hand-off with requirement IDs in the PR body | Interactive acceptance testing |
| [Traycer](https://docs.traycer.ai/concepts/artifact-workflow.md) | Desktop app, IDE extension | Each batch reviewed against the plan | Reviewer walkthrough | Proprietary; a model judges |
| [Qodo Spec Agent](https://docs.qodo.ai/code-review/view-requirement-gaps-in-findings) (new) | PR review bot | "Requirement gap" findings with a code reference | Spec gaps at review time | Research preview |

Planning modes in [Cursor](https://cursor.com/docs/agent/plan-mode), [VS Code](https://code.visualstudio.com/docs/agents/planning)
and [Windsurf](https://devin.ai/blog/windsurf-2-0) do not check the result against the plan.

### Differentiators to protect

These were checked against the competitors above. None documents the same.

1. **A model's quotes are checked in code.** BMAD, Qodo and Conductor cite evidence, but none documents a check that
   the quoted text exists.
2. **Approvals as file fingerprints,** voided by any edit, with two approvers on strict. GSD fingerprints verification,
   not approval.
3. **A merge gate with no model and no token** (`validate`). Tessl's gate calls an LLM.
4. **Suspect requirements after archive,** from kept evidence. A 2026 study asks tools to "detect code changes linked
   to specs" ([arXiv 2608.25202](https://arxiv.org/abs/2608.25202)). GSD's digest stops at ship.

No longer unique:
- reading the code before drafting (OpenSpec 1.12, reported; see Method);
- living specs with deltas (OpenSpec);
- ceremony sized to the change (Kiro, BMAD).

adk-spec's MCP server is still ahead of Spec Kit's read-only one.

### Feature opportunities

#### C1. A router section in the Agent Skill

- **Opportunity:** plain language in, `status` read, the next step run, a pause at each approval. OpenSpec 2.2.0 ships
  this as a `/openspec` router.
- **Who benefits:** a person in an assistant who does not know the command order.
- **Fit:** Skill text only. It needs no command and no code, and the CLI stays the single source of truth.
- **Location:** `adk_spec/workspace/skill.py`.
- **Impact / Effort:** Medium–High / Low. **Priority: P1**.

#### C2. Write the Skill to `.agents/skills` as well

- **Opportunity:** Antigravity reads only `.agents/skills` ([doc](https://antigravity.google/docs/skills.md)). Copilot
  reads both paths ([doc](https://docs.github.com/en/copilot/concepts/agents/about-agent-skills)). Claude Code reads
  only `.claude/skills` ([doc](https://code.claude.com/docs/en/skills);
  [#16345](https://github.com/anthropics/claude-code/issues/16345)). Gemini CLI, the baseline's target, now hands
  individual users to Antigravity CLI ([Google](https://developers.googleblog.com/en/an-important-update-transitioning-gemini-cli-to-antigravity-cli/)).
- **Who benefits:** Gemini-arm users, who are this tool's natural Google audience.
- **Proposed solution:** `init` writes both copies.
- **Impact / Effort:** Medium / Low. **Priority: P1**.

#### C3. `init --refresh` upgrades an unedited Skill

- **Opportunity:** the Skill is written once, so fixes to its text never reach existing installs. OpenSpec's `update`
  upgrades files nobody edited.
- **Proposed solution:** `init --refresh` rewrites the Skill when its fingerprint matches what adk-spec wrote, and
  names it when a person edited it. This needs no new command.
- **Impact / Effort:** Medium / Low–Medium. **Priority: P1**.

#### C4. Structured MCP results

- **Opportunity:** MCP 2026-07-28 allows any JSON in `structuredContent`
  ([changelog](https://modelcontextprotocol.io/specification/2026-07-28/changelog)), and the pinned `mcp==2.3.0`
  supports it. Assistants then read `status` and `verify` results without parsing text.
- **Proposed solution:** return the existing `--json` payloads of `status` and `validate` as `structuredContent`, and
  add one for `verify`'s verdicts.
- **Impact / Effort:** Medium / Medium. **Priority: P2**.

#### C5. Publish a verify-precision measurement

- **Opportunity:** a peer-reviewed study of 88,052 pull requests found spec'd and unspec'd PRs "indistinguishable in
  defect introduction" ([ESEM 2026](https://drops.dagstuhl.de/entities/document/10.4230/LIPIcs.ESEM.2026.84), confirmed
  in this session). No vendor publishes how often its verify catches real gaps.
- **Proposed solution:** seed known gaps in a demo repository and report how many `verify` marks unmet, through
  `scripts/measure`.
- **Who benefits:** adoption: this answers the strongest objection to the category.
- **Impact / Effort:** High / Medium. **Priority: P2**. It needs live model calls: the owner's explicit go-ahead.

#### C6. A suspect requirement's `next` line names `propose`

- **Opportunity:** the same study asks tools to "draft updates … for human confirmation".
- **Proposed solution:** a suspect requirement's `next` line says
  `adk-spec propose "keep REQ-X: its code moved"`. This adds no automation that edits specs.
- **Impact / Effort:** Medium / Low. **Priority: P2**.

#### C7. Ask open points through the assistant (MCP elicitation)

- **Opportunity:** Kiro supports this ([0.10](https://kiro.dev/changelog/ide/0-10/)).
- **Why wait:** under 2026-07-28 it needs multi-round-trip requests
  ([doc](https://modelcontextprotocol.io/specification/2026-07-28/basic/patterns/mrtr)), and a retry would need
  `propose`'s work kept. Which clients support it is unverified.
- **Priority: P2, hold.**

**Not recommended:**

| Item | Reason |
|---|---|
| Parallel task waves | adk-spec never edits application code. |
| OpenTelemetry GenAI traces | Still "Development" status; fields were renamed on 21 Nov ([changelog](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/CHANGELOG.md)). |
| SARIF upload | Private repositories need GitHub Code Security ([doc](https://docs.github.com/en/code-security/how-tos/find-and-fix-code-vulnerabilities/integrate-with-existing-tools/upload-sarif-file)); annotations were the right first step. |
| Reviewer personas, self-updating specs | Hype; they add no gate in code. |
| Model code review for style and security | It is the deferred "rules judged in verify" option: measure first. |

**Baseline reports now out of date:**
- `docs/reports/01-…` versions: OpenSpec is now 2.2.0 and Spec Kit 1.4.5.
- "Tessl = spec-as-source" no longer holds.
- Gemini CLI as a Skill target is replaced by Antigravity CLI.
- The MCP SDK and SARIF questions are settled, as above.

---

## Prioritized roadmap matrix

### P0: Critical

| ID | Item | Area | Impact / Effort | Owner decision |
|---|---|---|---|---|
| S2 | Scrub common credential lines (trailing comment, YAML list item, `ENV`, `--password`, `.netrc`, Docker `auth`) | Security | High / Low | No |
| S1 | Withhold a file with a string-embedded private key (header anywhere, long base64 after) | Security | High / Low–Medium | Yes: reopens roadmap line 480 |
| S3 | Refuse links under `.spec/` for reads; `inside()` for the runs folder; refuse a linked `.spec` | Security, data integrity | Medium–High / Low | No |

### P1: Core enhancements

| ID | Item | Area | Impact / Effort | Owner decision |
|---|---|---|---|---|
| H1 | Stop the test tree on cancel, SIGTERM and SIGHUP; SIGTERM before SIGKILL | Reliability | Medium–High / Low | No |
| S4 | MCP `verify`: refuse an uncommitted test command; drop or bound `bases` | Security | High / Medium | Yes: tool contract |
| A1 | Type the CLI-to-engine seam with `TYPE_CHECKING` imports | Architecture | Medium / Low | No |
| A2 | Import `OPENING` in tests; fail on an unmatched fake rule | Test reliability | Medium / Low | No |
| U1 | Plain progress verbs plus elapsed time | UX | High / Low | Yes: printed labels |
| U2 | One-figure `tokens` line | UX | Medium / Low | Yes: printed labels |
| U3 | `verify` prints each verdict with its requirement name and the outcome | UX | Medium–High / Low | Yes: printed labels |
| U4 | Name the other repositories before the reading | UX | Medium / Low | No |
| U5 | Subcommand descriptions, model-call note, plainer help | UX | Medium / Low | No |
| U6 | A clear question prompt; say what an interrupted `propose` lost | UX | Medium / Low | No |
| U7 | Regenerate the README transcripts | Docs | Medium / Low | No |
| U8 | `init` and `status` say the test command is unset | UX | Medium / Low | No |
| C1 | Router section in the Agent Skill | Product | Medium–High / Low | No |
| C2 | Skill also written to `.agents/skills` | Product | Medium / Low | No |
| C3 | `init --refresh` upgrades an unedited Skill | Product | Medium / Low–Medium | No |

### P2: Future growth

| ID | Item | Area |
|---|---|---|
| H2 | Size check before building diffs | Performance |
| H3 | Per-call cache and caps for evidence checks | Performance |
| H4 | Run deadline derived from the call budget | Reliability |
| H5 | Stale lock after reboot | Reliability |
| S5 | `context.md` marked as material; flag comment-only `met` quotes | Security |
| S6 | Drop adk-spec's own keys from test runs | Security |
| S7 | Harden the README's CI example | Supply chain |
| S8 | `login` loads LiteLLM in production mode | Security |
| S9 | Escape Markdown in job-summary cells | Security |
| A3 | Move use-case logic out of `cli.py` (if reopened) | Architecture |
| A4–A8 | Shared count helpers, `_FILE` suffix, one exit-code map, provenance comments, `DRAIN_S` in tests | Maintainability |
| U9–U13 | One read-first line, one label column, bare commands, report paths in the Skill, task progress in `status` | UX |
| C4 | Structured MCP results | Product |
| C5 | Published verify-precision measurement (live calls) | Product, market |
| C6 | Suspect requirement's `next` line names `propose` | Product |
| C7 | MCP elicitation for open points (hold) | Product |

### Suggested order

1. **One small security phase:** S2, S1 and S3, test first. Measure the scrub changes against the corpus before
   merging.
2. **Process and MCP hardening:** H1, then S4 once the owner rules on the tool contract.
3. **No-behaviour-change cleanup:** A1 and A2. This makes every later phase safer.
4. **One UX phase:** U1–U8. Most edits are in `cli.py`'s printing and the README, so one review covers them.
5. **Skill phase:** C1–C3, all text and `init`.
6. **Measurement (C5),** only on the owner's explicit go-ahead for live calls.

## Strengths to preserve

- **The layer rule, enforced twice** in `tests/test_layering.py`: by import direction read from the syntax tree, and
  by runtime probes that prove offline commands start without ADK.
- **A model's words count only where code finds them.** There is one quote test, `quoted_at`, used by convert, verify
  and evidence.
- **Secrets fail closed.** The `Scrub` plugin stands first in every app, agents have no tools, and untrusted text is
  fenced by a random boundary for each process.
- **Programs are started safely.** No shell, a PATH of absolute entries only, `GIT_*` variables dropped, fsmonitor and
  textconv off, a timeout on every call, and test output held as a bounded tail.
- **Writes are atomic and fsynced,** rolled back as a set. The lock is created exclusively, and only one run takes over
  a stale one.
- **What each tier demands is one table,** `DEMANDS`.
- **The fake model sits at the model registry,** so tests run the real ADK graphs, gates and plugins end to end.
- **The output is calm.** Plain stdout with no colour, a `next` line on every step, and refusals before anything is
  spent.
