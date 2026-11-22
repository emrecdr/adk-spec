# adk_spec: the user-facing command flow as it stands on `main`

Read from the source only, at commit `3631c98` on branch `main` (clean working tree). Nothing was run: no
`adk-spec` command, no measurement script, and not the test suite. "A test pins X" means the assertion was read,
not that the suite was run. Every path below is relative to `/Users/emrec/Projects/playground/adk_spec/`.
All seven key questions were reached; what each could not settle is under its own Gaps heading.
Short names used in citations: `cli.py` = `adk_spec/interfaces/cli.py`; `lifecycle.py` =
`adk_spec/domain/lifecycle.py`; `graph.py` = `adk_spec/orchestration/graph.py`; `layout.py` =
`adk_spec/workspace/layout.py`; `plans/README.md` = `docs/superpowers/plans/README.md`; `confirm.md` =
`docs/confirmation/2026-11-propose.md`; `measure-1.md` = `docs/measurements/2026-11-copilot-gpt-4.1.md`;
`measure-2.md` = `docs/measurements/2026-11-copilot-gpt-4.1-second.md`.

## 1. The 14 subcommands, their purpose and class, and how the help presents them

### Takeaway

There are 14 subcommands, registered as one flat argparse list in the order the phases were built, not the order
of use: the first everyday step, `propose`, is the 8th entry. By use, six are the everyday path (`propose`, `plan`,
`check`, `approve`, `verify`, `archive`) plus `status`; three are occasional (`new`, `validate`, `rebase`); two are
setup (`init`, `login`); two are diagnostic (`smoke`, `models`).

### Cited Findings

The classification column is this note's own reading (see Inferences); the rest is cited.

| # | Command | Help line, word for word | Flags | Calls a model | Lock | Class | Source |
|---|---|---|---|---|---|---|---|
| 1 | `init` | "make the .spec tree in this repository" | none | no | no | setup | `cli.py:118-119`, `cli.py:234-237` |
| 2 | `new <id>` | "start a change: its folder and its state file" | `--tier` | no | no | occasional | `cli.py:121-124`, `cli.py:240-245` |
| 3 | `validate [id]` | "check the structure of the living specs and of open changes" | `--strict`, `--json` | no | no | occasional / diagnostic | `cli.py:126-130`, `cli.py:328-351` |
| 4 | `status` | "list each open change and what to do next with it" | `--all`, `--json` | no | no | everyday (orientation) | `cli.py:132-135`, `cli.py:358-380` |
| 5 | `rebase <id>` | "record what a change's deltas are written against" | none | no | yes | occasional | `cli.py:137-139`, `cli.py:383-410` |
| 6 | `approve <id>` | "record an approval of a change's files as they stand" | `--by`, `--strict`, `--override REASON` | no | yes | everyday | `cli.py:141-148`, `cli.py:413-435` |
| 7 | `archive <id>` | "fold an approved change's deltas into the living specs" | none | no | yes | everyday | `cli.py:150-152`, `cli.py:447-478` |
| 8 | `propose "<request>"` | "draft a change from a request: its brief and its deltas" | `--id`, `--tier lean\|standard`, `--no-input` | yes | yes | everyday | `cli.py:154-159`, `cli.py:591-602`, `cli.py:903-948` |
| 9 | `plan <id>` | "draft a change's tasks, and its design where one is owed" | `--replace` | yes | yes | everyday | `cli.py:161-164`, `cli.py:695-738` |
| 10 | `check <id>` | "check a change's files against each other, before it is approved" | `--no-model` | yes (not with `--no-model`) | yes | everyday on the standard tier | `cli.py:166-169`, `cli.py:741-781` |
| 11 | `verify <id>` | "judge what changed in the repository against a change's requirements" | `--base REF`, `--override REASON` | yes | yes | everyday on the standard tier | `cli.py:171-177`, `cli.py:838-871` |
| 12 | `smoke` | "run the triage stage alone, to prove an arm answers in a schema" | `--model`, `--request`, `--check`, `--json` | yes (not with `--check`) | no | diagnostic | `cli.py:179-184`, `cli.py:1014-1091` |
| 13 | `models` | "list the models the chosen arm serves: one request, no model call" | `--json` | no (one request to the provider) | no | diagnostic | `cli.py:186-188`, `cli.py:998-1011` |
| 14 | `login` | "log in to GitHub Copilot once, with GitHub's device flow" | `--force` | no | no | setup | `cli.py:190-192`, `cli.py:990-995` |

- The top-level parser is `_Parser(prog="adk-spec", description="Spec-driven development on Google ADK.")` with
  two global options, `--version` and `--root`, and one subparser group made by
  `add_subparsers(metavar="command", parser_class=_Parser)`: no `title`, no `description`, no epilog, no examples,
  no grouping — `cli.py:112-116`.
- The 14 `add_parser` calls stand in this order: `init`, `new`, `validate`, `status`, `rebase`, `approve`,
  `archive`, `propose`, `plan`, `check`, `verify`, `smoke`, `models`, `login` — `cli.py:118-192`.
- That order is the build order of the phases: phase 1 delivered `init`, `new`, `validate`, `status`, `rebase`,
  `approve`, `archive`; phase 2 `propose`, `plan`, `smoke`, `models`, `login`; phase 3 `check` and `verify` —
  `plans/README.md:22-24`.
- Run with no command, `main` prints the help and returns exit code 2 — `cli.py:199-202`.
- Every argparse error ends with "adk-spec: --help lists every command and flag" — `cli.py:105-109`; pinned by
  `tests/test_cli.py:23-26`.
- No test asserts on the text of the top-level help: the only mentions of `--help` in the tests are
  `tests/test_cli.py:26` (the sentence above) and `tests/test_login.py:75` (`login --help`).
- The README groups the commands by another axis, whether they call a model: seven under "None of these calls a
  model" (`README.md:25-35`), "Four commands call a model" (`README.md:79-86`), "Three more reach a model provider
  without drafting" (`README.md:150-156`).
- What the README says of frequency: `init` is run "once for a repository" (`README.md:52`); `login` "logs in to
  GitHub Copilot once" (`README.md:158`); "`adk-spec status` names the next step at any point" (`README.md:63`);
  the standard walk-through names `propose`, `plan`, `check`, `approve`, `verify`, `archive` in that order
  (`README.md:65-75`); `new` appears only in the hand-written lean walk-through (`README.md:49-61`).
- A third tier, `strict`, is accepted by `new --tier` (`cli.py:123`; `adk_spec/domain/model.py:14`) and is read as
  `standard` today: `graph.py:268-272`; `plans/README.md:237-238`. `propose --tier` offers `lean` and `standard`
  only — `cli.py:157`.

### Inferences

- Inferred from argparse's standard behaviour, not read in this repository and not run: `adk-spec --help` shows a
  usage line, the description, then one list of the 14 commands in registration order under a single heading, each
  with its one-line help, then the options. Nothing tells a new person that `propose` is where a change starts, or
  that `smoke`, `models` and `login` are not part of a change's flow.
- The class of each command is this note's reading of `README.md:47-75` and of `lifecycle.py:213-256` (which
  commands `next_step` ever names): `plan`, `rebase`, `check`, `approve`, `verify`, `archive` and `validate` are
  the only commands a `next` phrase names; `propose`, `new`, `init`, `status`, `smoke`, `models`, `login` are never
  named by one.
- `validate` and `status` are both read-only reports of the same assessment (`cli.py:341`, `cli.py:363`), so each
  is diagnostic as much as everyday.

### Gaps

- The exact rendering of `--help` was not observed, because running `adk-spec` in any form was out of bounds.
- No source says how often a person in fact runs `status` or `validate`; the class given is a reading of the docs.

## 2. The exact sequence from a request to `archive`, for a lean and for a standard change

### Takeaway

A standard change takes six commands today (`propose`, `plan`, `check`, `approve`, `verify`, `archive`), four of
which call a model, at five model calls at the least; a lean change drafted by a model takes four (`propose`,
`plan`, `approve`, `archive`) at three calls at the least; a lean change written by hand takes three to five
commands (`new`, optionally `validate`, `rebase` where the delta modifies or removes, `approve`, `archive`) and no
model call. The person's own work falls at three points: answering questions inside `propose`, reading and editing
after `plan`, and implementing between `approve` and `verify`/`archive`.

### Cited Findings

#### Lean, by hand (the README's own walk-through)

- The sequence: `init` once; `new passkeys --tier lean`; write `brief.md`, `tasks.md` and one
  `specs/<capability>/spec.md`; `validate passkeys` "until it lists no error"; `rebase passkeys`, then
  `approve passkeys`; implement, ticking each box; `archive passkeys` — `README.md:52-61`.
- It "needs one approval and calls no model" — `README.md:49-50`; the whole of it is run by a test with no model:
  `tests/test_cli.py:98-117`.
- `rebase` is needed here because `new` writes a state with no bases (`layout.py:216-218`;
  `adk_spec/domain/model.py:154`) and the sample delta modifies and removes a requirement: `approve` before
  `rebase` exits 1 with `delta.base-missing` — `tests/test_cli.py:101-104`.
- A delta that only adds needs no base: bases are captured for modified and removed requirements alone —
  `lifecycle.py:25-34`; `delta.base-missing` is raised only for a modified or removed ID the living spec holds —
  `adk_spec/domain/validate.py:215-234`.

#### Lean, drafted by a model

- `propose` writes the brief and the deltas and leaves one finding, `change.missing-tasks` —
  `tests/test_propose.py:36-47` (line 43).
- `propose` records the bases itself (`cli.py:977-979`), so no `rebase` follows: "no rebase needed after propose"
  — `tests/test_propose.py:58-69`.
- A lean change owes no check (`lifecycle.py:112-113`) and is archived once approved (`lifecycle.py:182-183`,
  `lifecycle.py:188`); after approval its next step is "implement tasks.md, then run `adk-spec archive <id>`" —
  `lifecycle.py:248-249`; `tests/test_lifecycle.py:102`.
- So the sequence is `propose` → `plan` → `approve` → implement → `archive`. `verify` is allowed on a lean change
  and not required — `tests/test_verify.py:255-259`.

#### Standard

- The sequence, as the README gives it: `propose "..."`; `plan <id>`; "Read what was drafted, and edit it: the
  files are yours"; `check <id>`, "Fix what it marks as blocking"; `approve <id>`; implement with a coding agent,
  ticking each box; `verify <id>`; `archive <id>` — `README.md:67-75`. The roadmap states the same list:
  `plans/README.md:38-41`.

#### Step by step (standard; lean differs where said)

| Step | Model stages, and calls at the least | What the person does before the next step | What blocks the next step if this one is skipped |
|---|---|---|---|
| `propose` | `triage` (skipped with `--tier`), `brief`, `deltas`. 2 calls with `--tier`, 3 without. On the standard tier one more `brief` call for each answered round of questions, three rounds at most. | Answers up to three questions a round on the terminal (standard tier, unless `--no-input`). | There is no change to work on; by hand the substitute is `new` plus three files. |
| `plan` | `design` only where the brief owes one, then `tasks`. 1 call, or 2. | "Read what was drafted, and edit it" (`README.md:70`). | `approve` refuses: `change.missing-tasks` is in `BLOCKS_APPROVAL`. |
| `check` (standard only) | `check`. 1 call; 0 with `--no-model` or where a structural ERROR stands. | Fixes what is blocking; any edit makes the check stale and it is run again. | `approve` refuses with `check.missing` (or `check.stale`, `check.blocking`). |
| `approve` | none | Decides; then implements the tasks with a coding agent, ticking boxes. | `verify` and `archive` refuse: "is not approved: run `adk-spec approve <id>`". |
| `verify` (standard only) | `verify`. 1 call; 0 where the change has no requirement to judge. | Reads the verdicts; fixes the work and verifies again, or overrides with a reason. | `archive` refuses a non-lean change that is not `verified`. |
| `archive` | none | nothing | — |

Sources for the table, row by row:

- `propose`: triage is skipped where a tier is given — `graph.py:113-116`, `cli.py:598-599`,
  `tests/test_propose.py:79-85`. Three calls with no tier — `tests/test_propose.py:44`. Two with `--tier lean` —
  `tests/test_recorder.py:69-75`. Questions cost no model call: they are read by code from the brief —
  `graph.py:275-286`, `tests/test_clarify.py:42-57` ("triage, two briefs and the deltas: no call words a
  question"). Each answered round is one more run starting at the brief — `graph.py:119-139`, `cli.py:951-968`.
  Three rounds at most — `graph.py:57`, `graph.py:281`; four brief calls then — `tests/test_clarify.py:93-99`. At
  most three questions a round — `README.md:131-132`. A round nobody answers keeps the brief and goes on to the
  deltas — `graph.py:129-130`, `tests/test_clarify.py:82-90`. Asking happens only with `ask`, on the standard tier
  — `graph.py:281`; `--no-input` and the lean tier ask nothing — `tests/test_clarify.py:102-109`. A request sized
  `none` ends after one call with nothing written, exit 0 — `cli.py:932-937`, `tests/test_propose.py:72-76`.
- Every stage stands behind a gate that asks again at most twice, three tries in all — `adk_spec/orchestration/gate.py:24-25`,
  `adk_spec/orchestration/gate.py:56`; so "at the least" is one call a stage and the worst case is three.
- `propose` writes the change whole at the end: state, `brief.md`, one delta a capability — `cli.py:971-987`,
  `layout.py:243-254`. After a standard `propose` the `next` line is "run `adk-spec plan <id>`", or "settle the
  open point in brief.md" where a point was left open — `lifecycle.py:213-221`.
- `plan`: the design stage runs only where `state.needs_design` — `cli.py:702`, `cli.py:723`, `graph.py:417-424`;
  one call without (`tests/test_plan.py:35`), two with (`tests/test_plan.py:50-57`). It refuses a change that is
  no draft, one with a ticked task unless `--replace`, one whose living specs do not read, and one whose brief or
  deltas have an ERROR — `cli.py:670-692`. Skipped: `change.missing-tasks` blocks approval — `lifecycle.py:20-21`,
  `adk_spec/domain/validate.py:325-328`. A person may write `tasks.md` by hand in its place (the lean walk-through
  does: `README.md:54`).
- `check`: one stage behind its gate — `graph.py:430-435`. No model call with `--no-model` (`cli.py:762`) or
  where the change has an ERROR of structure (`cli.py:760-761`, `tests/test_check.py:200-207`). It writes
  `reports/check.md` and records the check with the fingerprints of the files read — `cli.py:769-773`. Skipped on
  a standard change: `approve` exits 1 with `check.missing` — `lifecycle.py:114-115`, `tests/test_check.py:168-172`.
  An edit after it makes it stale — `lifecycle.py:116-117`, `tests/test_check.py:156-165`.
- `approve`: records who, when, each file's fingerprint, the bases, an override reason where one set a blocking
  finding aside, and at the first approval the commit checked out — `cli.py:425-434`, `lifecycle.py:52-66`. Any
  later edit of `brief.md`, `design.md`, `tasks.md` or a delta voids it, except ticking a task —
  `lifecycle.py:37-44`, `lifecycle.py:129-136`, `layout.py:309-314`. Skipped: `lifecycle.py:161-173`,
  `tests/test_verify.py:213-216`.
- Implementing is outside the tool: "`adk-spec` writes specs and plans and judges the result. It does not edit
  your code" — `README.md:77`.
- `verify`: one stage behind its gate — `graph.py:438-451`; no call where the change has no delta requirement —
  `cli.py:851`. It needs a git repository, a base commit (recorded at the first approval, or `--base`), a diff
  that is not empty and holds at most 200,000 characters — `cli.py:813-835`, `adk_spec/workspace/git.py:31`. The
  change becomes `verified` where every verdict is `met` or a reason is given with `--override`; otherwise it
  stays `approved` — `lifecycle.py:98-105`. Skipped on a non-lean change: `lifecycle.py:188-189`,
  `tests/test_cli.py:149-159`. Work changed after it: `archive` refuses until it is verified again —
  `lifecycle.py:190-191`, `cli.py:297-306`, `tests/test_verify.py:304-317`.
- `archive`: computes every capability's merge before writing, then writes the merged specs and the state as one
  set — `cli.py:447-478`, `layout.py:178-186`. Where a base moved it refuses, writes nothing and says to "update
  the delta, then run adk-spec rebase and approve again" — `cli.py:466-475`, `tests/test_cli.py:131-146`.
- Whether a design is owed is acted on by `plan` alone: `needs_design` is written by `propose` (`cli.py:978`) and
  read only at `cli.py:702`, `cli.py:718`, `cli.py:723`, `cli.py:729`; `lifecycle.py` and
  `adk_spec/domain/validate.py` never read it.

### Inferences

- Model calls at the least, summed from the rows above: standard with `--tier standard`, no design and no answered
  question: 2 + 1 + 1 + 1 = 5; without `--tier`: 6; with one answered round and a design: 1 + 2 + 1 + 2 + 1 + 1 =
  8. Lean by model: 3 with `--tier lean`, 4 without (one more where a design is owed).
- Command count per change, not counting `status` or `validate`: standard 6, lean by model 4, lean by hand 3 to 5.
- Between `propose` and `plan` the README places no reading step; the first reading step comes after `plan`
  (`README.md:67-70`). So in the documented flow `plan` follows `propose` with no decision of the person's in
  between, except where an open point is left in the brief.
- `check` before `plan` would be wasted: `plan` then writes `tasks.md`, the fingerprints change, and the check is
  stale (`lifecycle.py:116-117`).

### Gaps

- The sequences are read from the README, the lifecycle rules and the tests; no recording of a person's real
  session exists in the repository to show what people run in practice (retries, `status` calls, edits).

## 3. Commands run only to satisfy another command's precondition

### Takeaway

`rebase` and `validate` are pure preconditions or reports whose work the dependent command already has everything
to do itself; `check` and `verify` are preconditions that hold real work (a model call and a report), each already
recorded with a fingerprint so a dependent command can tell a current one from a missing or stale one; `plan` is
real drafting work that always follows `propose` in the documented flow.

### Cited Findings

- **`check` before `approve`.** The rule, `lifecycle.py:108-126`: "What a change's check still owes its approval,
  as one finding or none. A lean change owes no check. Any other owes one of its files as they stand now (`files`,
  their fingerprints), with nothing blocking in it." It yields `check.missing` ("has not been checked. Run
  `adk-spec check <id>`."), `check.stale` ("A file of `<id>` changed since its check. Run `adk-spec check <id>`
  again.") or `check.blocking`, each an ERROR. `approve_blockers` adds them: "With `override`, a blocking finding
  of a current check is set aside, and nothing else: a check never run, or run on other files, is still owed" —
  `lifecycle.py:139-158`. `_approve` passes them in — `cli.py:416-424`.
- The check's work is a function body that takes `(args, workspace)`, reads `args.id` and `args.no_model`, and
  takes no lock itself (the lock is the `_drafting` wrapper's) — `cli.py:741-781`, `cli.py:605-615`.
- **`rebase` before `approve`.** The rule, `lifecycle.py:20-21`: "Findings that block an approval whatever their
  severity: an open point, no plan, or a delta with no recorded base." with
  `BLOCKS_APPROVAL = frozenset({"brief.marker-unresolved", "change.missing-tasks", "delta.base-missing"})`. The
  finding itself: "No base is recorded for <ID>. Run `adk-spec rebase` to record what the delta was written
  against." — `adk_spec/domain/validate.py:227-234`, a WARNING (`adk_spec/domain/validate.py:42`). The step table
  sends the person to it: `("delta.base-missing", "run", "run `adk-spec rebase {cid}`")` — `lifecycle.py:217`. The
  merge refuses on it as well — `adk_spec/domain/merge.py:15-16`.
- What `rebase` computes is one pure function of the change's deltas and the living specs,
  `capture_bases(deltas, living)` — `lifecycle.py:25-34`; `_rebase` calls it at `cli.py:396`, and `propose` calls
  the same function when it writes a change — `cli.py:977-979`. `_approve` has both inputs loaded already —
  `cli.py:415-416`.
- `rebase` does two more things an approval would not want done in silence: where bases changed it sets the status
  back to `draft` and clears the approval (`cli.py:407-409`), and it refuses where a living spec does not read,
  since "every base on it would be dropped" (`cli.py:391-395`). It also reports a base that "was stale" —
  `cli.py:397-399`, `tests/test_cli.py:177-185`.
- **`plan` after `propose`.** The rule is the same `BLOCKS_APPROVAL` set (`change.missing-tasks`,
  `lifecycle.py:21`), raised at `adk_spec/domain/validate.py:325-328` ("The change has no task. Plan its tasks in
  tasks.md before approval."), and the step table: `("change.missing-tasks", "run", "run `adk-spec plan {cid}`")`
  — `lifecycle.py:216`. The table's own comment gives the order: "an open point before the plan, since its answer
  shapes the tasks; the plan before the base, and the base before the check, which reads what the two leave" —
  `lifecycle.py:209-212`.
- `plan`'s body takes `(args, workspace)`, reads `args.id` and `args.replace`, reads the change back from disk and
  takes no lock itself — `cli.py:695-738`.
- **`verify` before `archive`.** The rule, `lifecycle.py:181-192`: "A lean change is archived once approved; a
  standard or strict one once verified, and only while the work is what was verified: `drifted` says it has
  changed since." Its sentences: "`<id>` is a <tier> change and is not verified: run `adk-spec verify <id>` first"
  and "the work changed since `<id>` was verified: run `adk-spec verify <id>` again".
- `verify`'s body takes `(args, workspace)`, reads `args.id`, `args.base` and `args.override`, and takes no lock
  itself — `cli.py:838-871`, `cli.py:813-835`.
- A verification is recorded with the fingerprint of the diff it judged (`cli.py:860`,
  `adk_spec/domain/model.py:134-143`), and `_drifted` compares the present diff with it, for a `verified` change
  alone — `cli.py:297-306`.
- **`validate`.** No rule in `lifecycle.py` asks that `validate` was run, and `_validate` records nothing: it
  prints and returns — `cli.py:328-351`. Every gating command computes the same findings itself through
  `_assessed` — `cli.py:287-294`, called by `approve` (`cli.py:416`), `plan` (`cli.py:697`), `check`
  (`cli.py:746`), `verify` (`cli.py:843`), `archive` (`cli.py:452`) and `status` (`cli.py:363`).
- `validate` is named only as where to read findings: "fix what `adk-spec validate {cid}` lists" —
  `lifecycle.py:214`, `lifecycle.py:243`, `lifecycle.py:255`; and in the README's hand-written flow,
  "`adk-spec validate passkeys`, until it lists no error" — `README.md:57`.
- The gating commands print what blocks them themselves: `approve` prints each blocker (`cli.py:421-424`), `plan`
  prints the blocking findings (`cli.py:688-691`), `check` prints every finding (`cli.py:774`).

### Inferences

- `validate`: already merged in effect. It is a report, never a precondition; nothing would change by leaving it
  out of the everyday set.
- `rebase`: the same work can be done inside `approve` for a base that is missing (see 5c). After `propose` it is
  not needed at all today, so it is a step only for hand-written deltas, for a delta edited to modify or remove
  one more requirement, and for recovery after the living spec moved.
- `check` and `verify`: the same work can be run from inside the dependent command, because each body is callable
  with `(args, workspace)` under a lock the caller already holds, and because the state already says whether a
  current result exists. What is lost is the pause in which a person reads the result before the dependent step
  (see 5b and 5d).
- `plan`: the same work can follow `propose` in one invocation (see 5a); it is not a mere precondition, since it
  drafts files a person then reads.

### Gaps

- The repository holds no statement of why `check` and `approve`, or `verify` and `archive`, were made separate
  commands beyond the rules quoted; whether the pause between them is wanted is a product decision the code does
  not settle.

## 4. What each everyday command prints on a normal run

### Takeaway

Output is already short: a normal run prints 1 line (`approve`, `archive`), 3 to 4 lines (`plan`), 5 to 6 lines
(`propose`, plus 2 lines a question), or 3 lines plus one a finding or a requirement (`check`, `verify`). Three
labelled lines recur, `wrote`, `tokens`, `next`; only the change's name and the `next` line are needed to act, and
`approve` and `archive` print no `next` line at all.

### Cited Findings

- **`propose`**, in order: for each round of questions a two-line header ("The brief leaves N points open. A line
  answers. `=` takes the suggestion." / "An empty line leaves the point open."), then two lines a question
  ("N. <question>", "   suggested: <text or (none)>") — `cli.py:511-529`; `wrote     <folder>, a <tier> draft`,
  then one indented line for each file written (`brief.md` and one delta a capability) — `cli.py:982-984`;
  `design    owed: <reason>` only where a design is owed — `cli.py:985-986`; `tokens    <stage> N in K calls, ...:
  N total` — `cli.py:946`, format at `cli.py:583-588`, an example asserted at `tests/test_clarify.py:56`;
  `next      <phrase>` — `cli.py:947`, `cli.py:309-311`.
- **`plan`**: `wrote     <path>` or `replaced  <path>` for `tasks.md`, and one more for `design.md` where it was
  drafted — `cli.py:728-735`, `tests/test_plan.py:170-178`; `tokens` — `cli.py:736`; `next` — `cli.py:737`.
- **`check`**: one line for every finding, the validator's and the model's, as "<SEVERITY> <code> <place>
  <message>" — `cli.py:774`, format at `cli.py:323-325`; `wrote     .spec/changes/<id>/reports/check.md` —
  `cli.py:775`; `note      N findings of the model were left out: ...` only where some were — `cli.py:776-777`;
  `tokens` only where the model ran — `cli.py:778-779`; `next` — `cli.py:780`.
- **`approve`**: one line, "approved `<id>` by <who>: N files recorded" — `cli.py:434`. On a refusal: each blocker
  as a finding line on stdout and one sentence on stderr — `cli.py:421-424`.
- **`verify`**: one line a requirement, "<verdict>  <ID>  <reason>" — `cli.py:865-866`; `wrote
  .spec/changes/<id>/reports/verify.md` — `cli.py:867`; `tokens` — `cli.py:868-869`; `next` — `cli.py:870`.
- **`archive`**: one line, "archived `<id>`: folded into <capabilities>" — `cli.py:477`.
- **`status`**: a heading for each group that holds a change, and one row a change: id, tier, status, next phrase
  — `cli.py:374-379`.
- **`rebase`**: one line a base ("<ID>  recorded | unchanged | was stale"), one for each base dropped, then
  "nothing to record: every base stands" or, where an approval was voided, a sentence saying so —
  `cli.py:397-409`.
- `_say_next` is documented as "The line every command that changes a change ends on" (`cli.py:309-310`) and is
  called by four handlers only: `plan` (`cli.py:737`), `check` (`cli.py:780`), `verify` (`cli.py:870`) and
  `propose` (`cli.py:947`). `approve`, `rebase` and `archive` do not call it.
- No everyday command prints how long it took; only `smoke` prints a `seconds` line — `cli.py:1088`. Seconds are
  kept per call in the recording — `adk_spec/workspace/runs.py:36-37`.
- What also lives in a file: every finding `check` prints is in `reports/check.md`, as is the left-out count —
  `cli.py:770-772`, `adk_spec/domain/report_md.py:33-45`; every verdict and reason `verify` prints is in
  `reports/verify.md`, with the quoted evidence the terminal does not show —
  `adk_spec/domain/report_md.py:48-66`; the tokens of each call are in `.spec/runs/<stamp>-<command>.json` unless
  `keep_runs` is 0 — `adk_spec/workspace/runs.py:36`, `adk_spec/workspace/runs.py:65-79`; the files `propose` and
  `plan` list are the change's folder itself.
- What lives nowhere else: the reason a design is owed is "Shown to the person; nothing is decided by it"
  (`graph.py:84-85`) and is printed only (`cli.py:986`); the brief's file holds no such field
  (`adk_spec/domain/model.py:94-101`). The model's non-blocking findings are not in the state either: the state
  keeps the count of blocking ones alone — `lifecycle.py:84-85`, `adk_spec/domain/model.py:124-131`.
- Refusals are one sentence on stderr prefixed `adk-spec:` — `cli.py:203-214`; a model pass that gives no answer
  prints the sentence and a `tokens` line and exits 3 — `cli.py:640-645`.

### Inferences

- Rough line counts on a normal run: `propose` 5 for one capability with no question and no design (wrote, two
  files, tokens, next), 6 with a design, plus 2 + 2 a question for each round; `plan` 3 (4 with a design);
  `check` 3 plus one a finding (4 with a note); `approve` 1; `verify` 3 plus one a requirement; `archive` 1. A
  whole standard change with one capability, two requirements, one finding and no question prints about 5 + 3 + 4
  + 1 + 5 + 1 = 19 lines over six commands.
- Needed to act: the change's name in `propose`'s `wrote` line (it is made from the brief's title where `--id` is
  not given, `cli.py:976`), the questions, any blocking finding or unmet verdict, and `next`. Detail that also
  lives in a file: the list of files written, the non-blocking findings, the verdict reasons, the tokens.
- The volume of output is not the burden; the count of invocations is. The one gap in guidance is that `approve`
  and `archive` end without a `next` line, so after `approve` a person learns the next step only from `status`.

### Gaps

- No transcript of a real terminal session is kept in the repository; the line counts are derived from the print
  statements, not observed.

## 5. Feasibility of merging steps, judged from the code

### Takeaway

All five are feasible without new state fields, because every phase body is a function of `(args, workspace)` that
writes whole or not at all, and the state already records a check and a verification with fingerprints. In rising
order of cost and risk: (e) help grouping and (c) `approve` capturing missing bases are small and low-risk; (d)
`archive` verifying and (b) `approve` checking are medium, and each removes the pause in which a person reads a
model's judgement before an irreversible-feeling step; (a) `propose` running on into `plan` is medium and fits the
code, while its `check` part is largely wasted whenever the person edits a draft, and is redundant if (b) is done.

### Cited Findings

#### Facts every merge rests on

- The lock is one file for the whole workspace, made exclusively, and not re-entrant: a second attempt in the same
  process fails as "held by another adk-spec run" — `adk_spec/workspace/lock.py:19-35`. It is taken by the
  wrappers `_locked` (`cli.py:220-227`) and `_drafting` (`cli.py:605-615`) and by `_propose` (`cli.py:601-602`),
  never by the bodies `_planned`, `_reviewed`, `_verified`. While it is held every other writing command in the
  workspace is refused with exit 2, whatever change it is about — `tests/test_propose.py:130-137`. It is let go on
  any exit, Ctrl-C included — `adk_spec/workspace/lock.py:32-35`, `tests/test_propose.py:270-276`.
- The token ledger is made per model pass: `_asked` builds `UsageLedger(workspace.config().max_tokens or None)`
  itself — `cli.py:631`; `propose` builds one for all its runs: "One ledger for every run of this command: the
  count and the ceiling are the command's" — `cli.py:919-920`. The ceiling refuses the next call once spent —
  `adk_spec/orchestration/plugins.py:93-104`; the README promises it "caps what one command may spend" —
  `README.md:92-93`. The app builders take the ledger and the recorder as arguments — `graph.py:346-348`,
  `graph.py:405-412`, `graph.py:430`, `graph.py:438`.
- A recording is written when a `_recording` block ends, however it ends, where at least one call was made; it
  carries one `command` name and one `outcome`, and its file is `<stamp>-<command>.json`; the newest 20 are kept —
  `cli.py:559-580`, `adk_spec/workspace/runs.py:40-52`, `adk_spec/workspace/runs.py:65-79`,
  `adk_spec/workspace/config.py:33-34`. `_asked` opens one recording a pass under the command name it is given —
  `cli.py:632`.
- Writes are whole or nothing: `write_all` stages every file and puts each back if a move fails —
  `adk_spec/workspace/files.py:66-88`; a new change's folder is removed again if its write fails —
  `layout.py:243-254`.
- A failed model pass writes and records nothing: `plan` — `cli.py:725-727`, `tests/test_plan.py:76-82`; `check`
  — `cli.py:765-767`, `tests/test_check.py:192-197`; `verify` — `cli.py:854-856`; `propose` —
  `cli.py:926-931`, `tests/test_propose.py:116-121`.
- Readiness of the provider is asked per role, before anything is spent: `propose` for `triage`, `brief`, `deltas`
  (`cli.py:598-600`), `plan` for `design`, `tasks` (`cli.py:702-704`), `check` (`cli.py:789-792`), `verify`
  (`cli.py:879-882`); a role may have its own model through `SPEC_<ROLE>_MODEL` —
  `adk_spec/orchestration/settings.py:25-32`. A refusal is a `UsageError`, exit 2 — `cli.py:208-210`.
- Each run of the engine has its own deadline of 600 s — `adk_spec/orchestration/models.py:47`,
  `adk_spec/orchestration/run.py:74`.
- Exit codes: 0 ok, 1 "A gate refused, or findings at the bar", 2 usage or configuration, 3 engine or provider,
  130 interrupted — `cli.py:80-87`.

#### (a) `propose` continuing into the work of `plan`, then of `check`

- `propose` is already several engine runs in one command, with one ledger and one recorder passed to each app:
  "the first run, then one more for each round of questions" — `cli.py:951-968`, `cli.py:919-923`.
- The propose graph has a hook for what follows the deltas' gate: "goes to `done` once the deltas pass their gate"
  — `graph.py:308-313`; the chat app uses it — `graph.py:398-401`.
- The plan graph cannot simply be appended to the propose graph as built: its tasks gate is closed over `owed` and
  `nameable`, which are computed from the change's deltas before the app is built — `graph.py:242-258`,
  `graph.py:405-415`, `cli.py:720-723`; and its stages read seeds the command prepares (`DELTAS_TEXT`, `LIVING`,
  `TREE`, a hand-written design) — `cli.py:711-719`.
- `_planned(args, workspace)` re-reads the change from disk, so it can run directly after `_written` —
  `cli.py:696-699`. It needs `args.replace` — `cli.py:679`. It prints its own `wrote`, `tokens` and `next` lines
  — `cli.py:734-737`; `_proposed` has by then printed its own `tokens` and `next` — `cli.py:946-947`.
- `_reviewed(args, workspace)` reads the files from disk and records their fingerprints — `cli.py:749`,
  `cli.py:773`; it returns exit 1 where any finding is an ERROR — `cli.py:781`.
- The step table orders an open point before the plan — `lifecycle.py:209-216`; `_plannable` itself does not
  refuse a brief with an open point, which is a WARNING — `cli.py:688`, `adk_spec/domain/validate.py:53`.
- An open point can remain after `propose`: a round nobody answers, `--no-input`, the lean tier —
  `tests/test_clarify.py:82-90`, `tests/test_clarify.py:102-109`; the first live run left one on a lean change —
  `confirm.md:57-58`.
- A check is void after any edit of the files it read — `lifecycle.py:116-117`; the documented flow has the
  person read and edit between `plan` and `check` — `README.md:70-71`.
- A lean change owes no check — `lifecycle.py:112-113`.
- "nothing is written until the whole run has ended well" is a stated property of `propose` — `README.md:89-90`;
  and where calls were paid for and the write then fails, the command still says what was spent — `cli.py:938-944`.
- Tests that pin today's shape: one recording a `propose`, with exactly the stages `triage, brief, deltas,
  deltas` — `tests/test_recorder.py:28-37`; the exact `tokens` line of a `propose` — `tests/test_clarify.py:56`,
  `tests/test_propose.py:250-255`; the request counts of a `propose` — `tests/test_propose.py:44`,
  `tests/test_clarify.py:57`, `tests/test_recorder.py:75`, `tests/test_recorder.py:84`; a `propose` leaves
  exactly `change.missing-tasks` — `tests/test_propose.py:43`.
- The roadmap's next phase puts a new command between the two: "`adk-spec explore <id>`: a new command, run
  between `propose` and `plan`" — `plans/README.md:58-59`, `plans/README.md:76-79`; it is in design and waits for
  approval — `plans/README.md:26`.

#### (b) `approve` running the check itself where the recorded check is missing or stale

- `check_blockers` already tells the three cases apart, `check.missing`, `check.stale`, `check.blocking` —
  `lifecycle.py:114-126`; `_approve` holds them as `assessed.unchecked` — `cli.py:416-420`.
- `approve` is wrapped by `_locked`, which reads no `.env`; the model commands are wrapped by `_drafting`, which
  does — `cli.py:148`, `cli.py:605-615`, `cli.py:490-500`.
- `_reviewed` runs the model's pass only where no ERROR of structure stands — `cli.py:760-762`; saves the check
  to the state before it returns — `cli.py:773`; and records the fingerprints, so a second run on unchanged files
  finds a current check — `lifecycle.py:76-85`.
- An approval can be made today with no provider at all, after `check --no-model` — `tests/test_check.py:184-189`,
  `tests/test_cli.py:149-159`.
- `--override` records a reason only where a blocking finding of a current check was set aside — `cli.py:431-432`;
  it does not stand in for a check never run — `tests/test_check.py:177-181`.
- The model's non-blocking findings are printed and written to the report and nowhere else; `approve --strict`
  reads the validator's findings, not those — `cli.py:770-774`, `lifecycle.py:84-85`, `lifecycle.py:153-158`.
- The step table calls an approval the person's own act (`Step("you", ...)`, `lifecycle.py:256`); the test says
  why: "an approval is a person's decision" — `tests/test_lifecycle.py:161`.
- The README lists `approve` under "None of these calls a model" — `README.md:25-35`.
- The engine-absent test covers `init`, `new`, `validate`, `status` only, so `approve` importing the engine inside
  its handler breaks no layering test — `tests/test_layering.py:169-179`; the module's rule is that "a handler
  that calls a model imports it inside itself" — `cli.py:4-5`.
- Tests that pin today's refusals: `approve` exits 1 with `check.missing` — `tests/test_check.py:168-172`; with
  `check.stale` after an edit, and no second model request is made — `tests/test_check.py:156-165`; with
  `check.blocking` until overridden — `tests/test_check.py:143-153`; the phrases "run `adk-spec check passkeys`"
  and "run `adk-spec check passkeys`, then approve again: ..." — `tests/test_lifecycle.py:141-151`,
  `tests/test_lifecycle.py:233-242`.
- The measurement script runs `check` as a command and reads the recordings whose `command` is `check` —
  `scripts/measure.py:95`, `scripts/measure.py:141`.
- How steady the check is: a planted contradiction was caught in 2 runs of 3, then in 1 of 3; a planted broken
  rule in 3 of 3, then 0 of 3 — `measure-1.md:7-10`, `measure-2.md:7-10`; "Three runs do not make a rate" —
  `measure-2.md:57-58`; nothing that blocked in the second measurement was wrong — `measure-2.md:69`.

#### (c) `approve` capturing bases itself

- `capture_bases` is pure and already used by `propose` at write time — `lifecycle.py:25-34`, `cli.py:977-979`.
- An approval records the bases as they stand — `lifecycle.py:64`; `Approval.bases` is "the bases it was approved
  against" — `adk_spec/domain/model.py:112-119`; a base is "The fingerprint each modified or removed requirement
  had in the living spec when the delta was based on it" — `adk_spec/domain/model.py:153-154`.
- The findings `approve` blocks on are computed from the state's bases as read from disk — `cli.py:287-294`,
  `adk_spec/domain/validate.py:323-324`.
- A base that moved is a different finding, `delta.base-stale`, an ERROR that tells the person to read the current
  requirement and update the delta — `adk_spec/domain/validate.py:235-242`; it is what stops a second change to
  one requirement at `archive` — `tests/test_cli.py:131-146`.
- The README's hand-written flow runs the two back to back: "`adk-spec rebase passkeys`, then `adk-spec approve
  passkeys`" — `README.md:58`.
- The check's fingerprint covers the change's files and not the bases, so new bases do not make a check stale —
  `lifecycle.py:116`, `layout.py:309-314`.
- Tests that pin today's shape: `approve` exits 1 with `delta.base-missing` before a `rebase` —
  `tests/test_cli.py:101-104`; `status` says "run `adk-spec rebase passkeys`" with actor `run` —
  `tests/test_cli.py:67-79`; `plan`'s `next` line names `rebase` — `tests/test_plan.py:37`; the next-step cases —
  `tests/test_lifecycle.py:91-95`, `tests/test_lifecycle.py:160`; the grouping test uses the missing base to put
  a change under "Ready to run" — `tests/test_cli.py:336-347`; the helper `approved()` runs `rebase` then
  `approve` — `tests/conftest.py:367-369`; every code of `BLOCKS_APPROVAL` must have a row in `_HOLDS` —
  `tests/test_lifecycle.py:185-198`.

#### (d) `archive` running `verify` itself where no current verification is recorded

- `archive_blockers` knows two cases for a non-lean change: not `verified`, and `drifted` — `lifecycle.py:188-191`.
  Unlike the check, nothing tells "never verified" from "verified on this same diff and found unmet": `_drifted`
  answers for a `verified` change alone — `cli.py:300-302`.
- `_archive` reads the state once, before anything else, and writes that state back with `status` set to
  `archived` — `cli.py:452-453`, `cli.py:476`; `_verified` saves a new state holding the verification —
  `cli.py:860-864`.
- `_archive` computes every merge in memory before it writes — `cli.py:458-475`; a refused merge writes nothing.
- `verify` needs what a lean archive does not: a git repository, a base commit, a diff within 200,000 characters,
  a ready provider — `cli.py:813-835`, `cli.py:879-882`. A lean change is archived today outside any repository —
  `tests/test_cli.py:98-117`.
- A verdict of `met` stands only on a line the diff holds on the right side — `cli.py:900`,
  `tests/test_verify.py:84-102`; the half-done case was judged rightly in 3 runs of 3, twice —
  `measure-1.md:12`, `measure-2.md:12`.
- `--override` belongs to `verify` and records why a person verified over a verdict — `cli.py:174-176`,
  `lifecycle.py:101-105`.
- The roadmap makes `verify` heavier: phase 7 has it run the project's test command, with a timeout, before a
  model judges — `plans/README.md:165-190`.
- Tests that pin today's shape: a standard change's `archive` exits 1 and names `verify` —
  `tests/test_cli.py:149-159`, `tests/test_lifecycle.py:82`; work changed after verification: `archive` exits 1
  with "changed since" and "nothing is rewritten by a refusal" — `tests/test_verify.py:304-317`; the phrases
  "implement tasks.md, then run `adk-spec verify passkeys`" and "run `adk-spec archive passkeys`" —
  `tests/test_lifecycle.py:105-106`; `verify`'s `next` line names `archive` — `tests/test_verify.py:131`.

#### (e) The help showing a small everyday set first

- The commands are registered by straight-line code on one subparser group — `cli.py:116-192`; `_Parser` is
  already a subclass of `argparse.ArgumentParser` — `cli.py:105-109`.
- Nothing but the error suffix "--help lists every command and flag" depends on the help's content —
  `cli.py:109`, `tests/test_cli.py:23-26`.

### Inferences

#### (a) `propose` → `plan` → `check` in one pass

- **Least change:** sequence the phases in the command, not in the graph: after `_written`, call the plan phase
  and then the check phase inside `propose`'s own lock. The bodies `_planned(args, workspace)` and
  `_reviewed(args, workspace)` can be reused as they are with a namespace carrying `id`, `replace=False`,
  `no_model=False`; the registered handlers cannot, since their wrappers would take the lock a second time.
  Building plan into the propose graph would need the tasks gate to read `owed` and `nameable` from state, and
  would touch the chat app that shares `_propose_edges`.
- **What must change if reused as is:** the printing. Three `tokens` lines and three `next` lines would appear,
  the first two `next` lines naming steps already taken. Work and printing are interleaved in each handler, so a
  clean merge splits each body into "do" and "say".
- **Ledger:** reused as is, each phase gets its own ledger, so `max_tokens` would cap each phase and not the
  command, against `README.md:92-93`. One ledger for the command needs `_asked` to accept a ledger (and a
  recorder), a small signature change; `_spent` would then print one line with every stage.
- **Recording:** reused as is, one invocation writes three files (`-propose`, `-plan`, `-check`), which keeps the
  measurement script's filter by command name working and uses three of the 20 kept slots a change. One file under
  `propose` is possible, since a call carries its stage's name, and breaks `tests/test_recorder.py:28-37` either
  way.
- **Readiness:** the roles `design`, `tasks` and `check` should be asked up front with the others, or a missing
  model for a later role is found only after the first phase is paid for.
- **Failure half-way:** if the change is written before the plan phase starts (as today), a failed plan leaves a
  valid draft with no tasks, exit 3, and the person reruns `plan <id>`; a failed check leaves a planned change
  with no check recorded, and the person reruns `check <id>` or goes straight to `approve` under (b). Nothing
  needs rolling back, because each phase writes whole or nothing. The alternative, holding every draft until the
  last phase ends, would throw away up to some 9,600 tokens of drafting on a late failure (`confirm.md:16`), and
  runs against `cli.py:940` ("the calls are paid for by now").
- **Open points:** the pass should stop before the plan where the brief still holds an open point, to keep the
  order the step table states; so one invocation completes only where nothing is left open.
- **Exit code:** a blocking finding of the check would make a successful drafting exit 1 unless the merged command
  defines otherwise.
- **Lock:** held for the whole longer command, questions included; any other writing command in the workspace is
  refused meanwhile. A run killed without cleanup leaves the lock file to be removed by hand.
- **The check part is the weak one.** The documented flow has the person read and edit after `plan`; any edit
  voids the check, so a check at the end of `propose` is paid for (about 1,200 tokens and 3 to 19 s, see 6) and
  then run again. It pays only for a person who approves a draft untouched. If (b) is done, the check runs at the
  moment the files are final and the check inside `propose` adds nothing.
- **Risk:** medium for `propose` → `plan` (many tests pin counts, the `tokens` line and the recording; the roadmap
  wants `explore` between the two, which a merged pass must either include or leave room for). Low benefit and
  some waste for `→ check`.

#### (b) `approve` checking

- **What would change:** `_approve` runs the check phase where the only blockers are `check.missing` or
  `check.stale`, then assesses again and goes on; it must read `.env` as the model commands do. Where an ERROR or
  another blocker stands, it should refuse as today and spend nothing.
- **Reusable as is:** `check_blockers` (it already names the case), `_reviewed`'s body or `_judged`, `checked`,
  `render_check`. No new state field.
- **Failure half-way:** a failed model pass exits 3 with nothing recorded and nothing approved; rerun `approve`.
  A check that passes is saved before the approval is, so if the approval then fails for another reason (an
  account with no name, `cli.py:426-429`), the rerun finds a current check and makes no second call.
- **Ledger, recording, lock:** the pass can keep its own ledger and its own recording named `check`, so the
  measurement script and `tests/test_check.py:140` are untouched; `approve` already holds the lock.
- **Risks:** (1) a model call, a provider and a login become part of `approve` on the standard tier, which today
  needs none; a path with no model (`check --no-model`, or a flag on `approve`) must remain. (2) Where nothing
  blocks, the approval is recorded in the same breath as the check, so the model's warnings are printed after the
  fact and never weighed before the decision. (3) `--override` typed on the same invocation would set aside a
  blocking finding the person has not yet seen; the rule that an override answers only a check already read needs
  restating, for instance by not applying it to a check run in that invocation. (4) Three exit codes can now come
  from `approve`: 1 for blockers, 2 for no provider, 3 for a failed pass. (5) The check is the least steady pass
  measured, so the same files may block in one run and pass in the next. Medium risk, and the most visible change
  of meaning of the five.
- **Tests to rewrite:** `tests/test_check.py:156-181`, and the next-step phrases in `tests/test_lifecycle.py`
  that name `check`.

#### (c) `approve` capturing bases

- **What would change:** before it assesses, `_approve` records a base for each modified or removed requirement
  that has none, and leaves every recorded base alone; `delta.base-missing` leaves `BLOCKS_APPROVAL` and its row
  leaves `_HOLDS`. A stale base must not be re-captured: that would silence the one guard against two changes to
  one requirement.
- **Reusable as is:** `capture_bases`, `approve` (it already copies the state's bases into the approval).
- **Failure half-way:** if the new bases are saved and the approval is then refused, the state holds bases and no
  approval, which is what `rebase` leaves today; harmless and rerunnable.
- **Ledger, recording:** none; no model. Lock: already held.
- **Risk:** low. Nothing is lost against today's ritual, in which `rebase` is run immediately before `approve` and
  knows no more about when the delta was written. `rebase` stays for the recovery after a living spec moved, and
  `validate --strict` would still report the missing base as a warning until the approval.
- **Tests to rewrite:** about seven assertions, listed under (c) above.

#### (d) `archive` verifying

- **What would change:** `_archive` runs the verify phase where a non-lean change is approved, its approval
  current, and no verification of the present diff stands; then reloads the state before it writes. A new rule is
  needed, the twin of `check_blockers`, to tell "never verified", "verified on another diff" and "verified on this
  diff and found unmet", or a rerun of `archive` would pay for the same unmet verdict again.
- **Reusable as is:** `_verified`'s body, `_work`, `_verdicts`, `verified`, `render_verify`, `_drifted`.
- **A trap in the present code:** `_archive` writes back the state it read at its start; with a verification
  saved in between, that write would erase it unless the state is read again.
- **Order:** the merges should be computed before the model is called, so a stale base costs no tokens.
- **Failure half-way:** a failed pass exits 3, nothing recorded, nothing merged. A pass that is recorded, followed
  by a refused merge, leaves the change `verified` and the specs untouched, as today.
- **Ledger, recording, lock:** as (b): own ledger, a recording named `verify`, the lock already held.
- **Risks:** (1) the living specs are rewritten in the same invocation that first shows the verdicts, so nobody
  reads `reports/verify.md` before the fold; the grounding by quoted lines limits a false `met` and does not rule
  one out. (2) `archive` of a standard change would need git, a base commit and a provider, and `--base` and
  `--override` must be reachable from it or the person is sent back to `verify`. (3) With phase 7, `archive` would
  also run the project's tests. Medium risk; the gain is one command for a person who would have read nothing in
  between anyway, and none for a person who verifies first, since a current verification costs nothing more.

#### (e) Help grouping

- **What would change:** argparse has no second heading for one subparser group, so either the registrations are
  reordered with the everyday commands first (no new code), or the top-level `_Parser` prints a two-part list from
  a small table of name, help and group. The second keeps "--help lists every command and flag" true as long as
  both groups are printed.
- **Risk:** negligible; no test reads the help. It changes nothing a command does, and so removes no step: it
  makes six everyday commands easier to find, not fewer.

#### Across the five

- With (a) for `plan`, (b), (c) and (d), a standard change would be `propose`, `approve`, `archive`, three
  invocations where there are six, with the same model calls; `plan`, `check`, `verify` and `rebase` would remain
  as commands for rerunning one phase.
- The merges that save a command at no change of meaning are (c) and `propose` → `plan`. The two that change what
  a person sees before deciding are (b) and (d).

### Gaps

- No merge was prototyped; the judgement is from reading the code. How the terminal should read when two phases'
  output is joined is undecided by anything in the repository.
- Whether a person wants to read a check's warnings before approving, and a verification's verdicts before
  archiving, is not answered by any file read.
- How often a person edits a draft between `plan` and `check` is unknown, and it decides whether a check inside
  `propose` pays.

## 6. What the measured records say a change costs

### Takeaway

On `gpt-4.1` through GitHub Copilot, `propose` plus `plan` for a standard change cost 14,010 tokens and 169 s in
the first live run (three rounds of questions), and about 9,000 tokens by the newest figure of each (4,664 for a
one-round `propose`, 4,383 for a `plan` with a design); `check` cost about 1,160 to 1,390 tokens and 3 to 19 s a
run, and `verify` about 1,290 tokens and 10 to 14 s a run, both on very small changes.

### Cited Findings

- The first live runs, 21 November 2026, on `gpt-4.1` on GitHub Copilot, macOS, a scratch repository with two
  living specs — `confirm.md:1-9`:

  | Run | Command | Calls by stage | Tokens | Time |
  |---|---|---|---|---|
  | 1 | `propose --tier lean` | triage 1, brief 1, deltas 1 | 2,753 | 34 s |
  | 2 | `propose --tier standard`, three answered rounds | triage 1, brief 4, questions 3, deltas 2 | 9,627 | 126 s |
  | 3 | `plan` on run 1's change | tasks 1 | 1,299 | 15 s |
  | 4 | `plan` on run 2's change | design 1, tasks 1 | 4,383 | 43 s |

  — `confirm.md:13-18`. "All four ended well, in 16 model calls and 18,062 tokens" — `confirm.md:3-4`.
- One retry in 16 calls: the deltas of run 2 — `confirm.md:28-30`, `confirm.md:68`.
- The second live `propose`, same request, after plan 3: one round of questions, calls "brief 2, questions 1,
  deltas 1", 4,664 tokens, no retry — `confirm.md:92-103`. It did not call `plan` — `confirm.md:113-114`. No time
  is given for it.
- What changed between the two: the new brief draft is given the brief it replaces; "a tier given by hand is not
  asked of triage"; an unchanged requirement under MODIFIED is left out — `confirm.md:105-107`.
- Since then the questions are read by code: "one model call fewer a round" — `plans/README.md:25`; its live proof
  has not been run — `plans/README.md:25`, `plans/README.md:252`.
- The project's own summary figures: "about 2,800 tokens on a lean change and 9,600 on a standard one with three
  rounds of questions" — `README.md:94-95`; "a `propose` and a `plan` together spend 3,000 to 10,000" —
  `plans/README.md:114-115`; "a standard `propose` now spends about 4,700 tokens ... half of what it did" —
  `measure-1.md:46-47`; the suggested ceiling is `max_tokens = 30000` — `README.md:97-100`, `confirm.md:70-71`.
- `check`, first measurement (3 runs a case): tokens a run 1,394, 1,219, 1,164, 1,164 for the four cases a model
  reads, seconds a run 19.0, 15.8, 9.0, 3.4; the case code decides cost 0 tokens and 0.0 s — `measure-1.md:7-11`.
- `check`, second measurement: tokens a run 1,323, 1,245, 1,179, 1,199; seconds a run 5.6, 11.8, 10.8, 8.7 —
  `measure-2.md:7-11`.
- `verify`: 1,291 tokens and 10.0 s a run, then 1,285 tokens and 13.5 s a run — `measure-1.md:12`,
  `measure-2.md:12`.
- Each measurement was "15 model calls, about 18,700 tokens", the first in "three minutes" — `measure-1.md:25`,
  `measure-2.md:42-43`.
- The measured tokens and seconds are sums over the model calls of each run's recordings, not the time of the
  whole process — `scripts/measure.py:89-96`.
- The labelled set is "six small changes" — `docs/measurements/README.md:5`.
- Nothing was measured on the Gemini arm or on Windows — `confirm.md:84-88`, `measure-1.md:49-50`.

### Inferences

- `propose` plus `plan` for one standard change: 9,627 + 4,383 = 14,010 tokens and 126 + 43 = 169 s in the first
  run, where both were run on the same change. The newest figure of each gives 4,664 + 4,383 = 9,047 tokens; this
  joins two different runs, and the `plan` figure predates the file tree now sent to its stages
  (`cli.py:716`), so today's `plan` likely costs somewhat more.
- A whole standard change today, by these figures: about 9,000 for `propose` and `plan`, about 1,250 for `check`,
  about 1,290 for `verify`: some 11,500 tokens, on a small change. Real changes have longer files and diffs, so
  `check` and `verify` will cost more than on the labelled set.
- Seconds a call, derived: about 11 to 13 s in the first `propose` runs (34 s over 3 calls, 126 s over 10), 15 to
  21 s in `plan`, about 12 s averaged over a measurement (three minutes over 15 calls). So a merged
  `propose` → `plan` of 4 to 5 calls is on the order of a minute of model time, and a check inside `approve` or a
  verification inside `archive` adds some 3 to 20 s to commands that return at once today.
- Merging commands changes none of these totals: the same stages run. The only saving in tokens would come from
  not running a check that an edit then voids.

### Gaps

- No live measurement exists of `propose` or `plan` as they stand now (after the questions moved to code and the
  file tree was added); the newest `propose` figure still holds one questions call.
- No time was recorded for the second `propose` run.
- `confirm.md` does not say whether its Time column counts the seconds a person took to type an answer.
- No cost is recorded for `check` or `verify` on a change of real size, nor for any command on Gemini.
- Start-up time of the process (importing the engine) is nowhere measured.

## 7. What in the code assumes the present number of steps and would resist a merge

### Takeaway

The rules themselves are small and central (one table, `_HOLDS`, and a few branches of `next_step`), so the code
resists little; the tests resist most, since some 40 assertions pin a `next` phrase, a refusal code or an exit
code of today's step list. Three structural facts also matter: the lock is not re-entrant, a ledger and a
recording belong to one model pass, and two status groups and one status value exist for steps a merge would make
rare.

### Cited Findings

- **One table decides the next step.** `_HOLDS` holds seven rows, each a literal phrase naming a command —
  `lifecycle.py:213-221`; the branches for an approved or verified change name `check`, `verify` and `archive` —
  `lifecycle.py:238-249`; the last line names `approve` — `lifecycle.py:256`. `status`, and the `next` line of
  four commands, read it through `Assessed.step` — `cli.py:281-284`, `cli.py:309-311`, `cli.py:364-367`.
- **Tests that pin a `next` phrase.** The table of 18 states — `tests/test_lifecycle.py:87-111`; the check's
  phrases — `tests/test_lifecycle.py:141-151`, `tests/test_lifecycle.py:233-242`; who acts —
  `tests/test_lifecycle.py:154-182`; `status` saying "run `adk-spec rebase passkeys`" — `tests/test_cli.py:67-79`;
  "fix what `adk-spec validate passkeys` lists" — `tests/test_cli.py:284`; `status` naming `plan` and `plan`'s
  own `next` naming `rebase` — `tests/test_plan.py:29`, `tests/test_plan.py:37`; `check`'s `next` naming
  `approve` — `tests/test_check.py:137`; `status` naming `check` — `tests/test_check.py:164`; `verify`'s `next`
  naming `archive` and `status` saying to verify again — `tests/test_verify.py:131`, `tests/test_verify.py:312`.
- **An invariant between the two lists:** every code that blocks an approval must have a step of its own —
  `tests/test_lifecycle.py:185-198`.
- **Tests that pin a refusal between two steps.** `approve` before `rebase` — `tests/test_cli.py:101-104`;
  `approve` before, after an edit since, and over a blocking `check` — `tests/test_check.py:143-181`; `archive`
  before `verify` — `tests/test_cli.py:149-159`, `tests/test_lifecycle.py:78-84`; `archive` after the work changed
  — `tests/test_verify.py:304-317`; `verify` before `approve` — `tests/test_verify.py:213-216`,
  `tests/test_verify.py:238-244`.
- **The status groups.** `GROUPS = (("you", "Waiting on you"), ("run", "Ready to run"), ("done", "Done"))` —
  `cli.py:354-355`. The rows with actor `run` are: no tasks (`plan`), no base (`rebase`), check missing or stale
  (`check`), verified (`archive`), drifted (`verify` again) — `lifecycle.py:216-220`, `lifecycle.py:244-247`. The
  grouping test relies on a missing base to fill "Ready to run" — `tests/test_cli.py:336-354`. The README
  describes the groups — `README.md:40-41`.
- **State and transitions.** `Status = Literal["draft", "approved", "verified", "archived"]` —
  `adk_spec/domain/model.py:15`. `approve` sets `approved` (`lifecycle.py:66`); `verify` sets `verified`, or
  `approved` again where a later judgement falls short (`lifecycle.py:98-105`); `rebase` with new bases sets
  `draft` and clears the approval (`cli.py:407`); `archive` sets `archived` (`cli.py:476`); `plan` refuses
  anything but a draft (`cli.py:674-675`). The state file refuses a key it does not know and reads one written
  before a field was added — `adk_spec/domain/model.py:27-28`, `tests/test_workspace.py:107`,
  `tests/test_workspace.py:203`.
- **Exit codes.** Five codes with one meaning each — `cli.py:80-87`; `NotYetError` is exit 1, usage and
  workspace refusals exit 2, a file-system failure exit 3 — `cli.py:203-214`; a model pass with no answer is exit
  3 — `cli.py:640-645`. `check` exits 1 on any ERROR finding and `verify` exits 1 where not every requirement is
  met — `cli.py:781`, `cli.py:871`. The measurement script counts a run as failed where the code is neither 0 nor
  1 — `scripts/measure.py:142`.
- **The lock** is not re-entrant, and is taken by the wrappers, so a merged command must call the bodies —
  `adk_spec/workspace/lock.py:19-35`, `cli.py:220-227`, `cli.py:605-615`.
- **One ledger and one recording a model pass.** `_asked` makes both — `cli.py:631-632`; a recording has one
  `command` and one `outcome` — `adk_spec/workspace/runs.py:40-52`; tests pin one recording a command and its
  stages — `tests/test_recorder.py:28-37`, `tests/test_recorder.py:102-107`, and that a recording replays to the
  same files — `tests/test_recorder.py:110-123`. The measurement reads recordings by command name —
  `scripts/measure.py:95`.
- **Overrides are tied to the step they answer.** `approve --override` answers a check already recorded —
  `lifecycle.py:147-150`, `cli.py:431-432`; `verify --override` answers verdicts just given —
  `lifecycle.py:98-105`, `cli.py:860`.
- **Printing is inside each handler.** Each of `_proposed`, `_planned`, `_reviewed`, `_verified` prints its own
  `tokens` and `next` lines as it ends — `cli.py:946-947`, `cli.py:736-737`, `cli.py:778-780`, `cli.py:868-870`.
- **Written promises.** "None of these calls a model" over a list holding `approve` and `archive` —
  `README.md:25-35`; "nothing is written until the whole run has ended well" — `README.md:89-90`; `max_tokens`
  "caps what one command may spend" — `README.md:92-93`; "A standard change must be checked before it is
  approved" and "A standard change is archived only once verified" — `README.md:115`, `README.md:128`.
- **The roadmap assumes the step list and adds to it.** "Then: `check`, `approve`, implement, `verify`,
  `archive`", "the same" after phases 5 and 6 — `plans/README.md:41`; phase 5 adds `explore` between `propose`
  and `plan` and has `status` name it — `plans/README.md:58-59`, `plans/README.md:69`; phase 7 has `verify` run
  the project's tests — `plans/README.md:171-172`; phase 11's strict tier wants "a second approver recorded" —
  `plans/README.md:240-241`.
- **What does not resist.** The domain rules are functions of the state with no command in them besides the
  phrases — `lifecycle.py:1-7`; the check and the verification are already recorded with fingerprints —
  `adk_spec/domain/model.py:124-143`; the engine is imported inside handlers, and the engine-absent test covers
  `init`, `new`, `validate`, `status` only — `cli.py:4-5`, `tests/test_layering.py:169-179`.

### Inferences

- Counted by reading: about 30 assertions pin a `next` phrase or an actor (18 of them one parametrised table) and
  about 12 pin a refusal between two steps; the merges (b), (c) and (d) would each rewrite a handful, and (a)
  mostly the counts and recordings of `propose`.
- If `plan` followed `propose`, bases were captured at approval, and the check ran inside `approve`, no draft
  would ever be "Ready to run" except a hand-made one with no tasks; the group would hold verified changes alone,
  and with (d) hardly those. The grouping would want a second look.
- `verified` would remain a real status under (d) for a person who verifies first, and a state passed through
  within one command otherwise; no transition needs removing.
- The largest non-test resistance is the roadmap, not the code: phase 5 adds a step in the very place (a) removes
  one, and its design is waiting for approval now, so the two decisions should be taken together.
- Exit code 1 would mean three things in a merged `approve` (blocked by findings, blocked by the check it just
  ran) and a merged `propose` (drafted, and the check found something); scripts that read codes would see new
  cases, of which the measurement script is the one in this repository.

### Gaps

- The count of assertions is by reading six test files and `tests/test_lifecycle.py`, `tests/test_recorder.py`,
  `tests/test_layering.py`; the suite was not run, and other test files were not searched line by line for
  indirect dependence on the step order.
- `docs/superpowers/specs/2026-11-22-brownfield-feature-context-design.md` (the phase 5 design) was not read; what
  it says of `explore`'s place in the flow is taken from the roadmap alone.
