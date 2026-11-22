# adk-spec Questions in Code Implementation Plan (plan 4)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A brief's open points are put to the person without a second model call: the brief stage names each open point with the answer it would suggest, and code words the questions. The `questions` stage goes.

**Architecture:** The second step of the spec's migration, done by its recipe: a stage whose output is a function of its input moves from a model to Python, its contract kept. The brief's schema gains `open_points`; conversion writes each as a `[NEEDS CLARIFICATION: ...]` marker in the brief's file, as before; the questions a run ends on are read from those markers, each with the suggestion its open point gave. Everything after the questions (`ASKING`, `next_run`, the terminal) is unchanged.

**Tech Stack:** As plans 1 to 3. No new dependency.

**Spec:** `docs/reports/Spec driven framework on Google ADK.md`, the section "Migration: one stage per release, chosen by the ledger, proven by replay"; plan 3 (`docs/superpowers/plans/2026-11-21-adk-spec-check-and-verify.md`) with what changed in it; `docs/confirmation/2026-11-propose.md`; and `docs/measurements/2026-11-copilot-gpt-4.1-second.md`, whose decisions Task 3 carries out.

Written on 21 November 2026, on the owner's choice of this piece over tests as evidence for `verify`.

## Why this stage, by the spec's five tests

| Test | The `questions` stage |
|---|---|
| Its output is a function of its input, with no judgement | The question is the text of the marker the brief wrote. Only the suggested answer takes judgement, and the brief stage can give it in the same call |
| A deterministic oracle exists | The marker: one question a marker, in the brief's order |
| Tokens times frequency | One call a round of every standard `propose` with an open point: 638 tokens and 24 seconds in the live run, a quarter of that run's calls |
| Its failures | It has its own gate, its own three tries, and a path of its own for when no question can be worded (`UNWORDED`) |
| The Python is small | A few lines of conversion |

## Validated before building

Checked on 21 November 2026, offline, on the recording kept from the second live run
(`docs/confirmation/2026-11-propose-run-2/runs/`):

- The brief wrote `[NEEDS CLARIFICATION: Should the user have means to manage a known device list?]`. The questions stage, one call later, asked "Should users be able to view and manage a list of their known devices associated with their account?". The marker's own text is the same question. What the call added was the suggested answer, which the person took with `=` in both live runs.
- So the suggestion must come from the brief stage, or `=` has nothing to take. That is the one change to a schema and to an instruction.
- `markers(text)` in `domain/brief_md.py` returns each marker in order, and `validate_brief` already holds a brief to three of them. Nothing outside `tests/test_clarify.py` and `tests/conftest.py` uses the canned questions.
- The code never declines an input: a marker always gives a question. So the model is not kept as a second route, where the spec keeps it "for inputs the code declines". This is a ruling, written here: no stage mode in the config for a route nothing would take.

## Global Constraints

Plans 1 to 3's Global Constraints hold unchanged. In addition:

- The brief's file is what it was: open points stand in it as `[NEEDS CLARIFICATION: ...]` markers, the validator counts them, and an unresolved one blocks approval.
- The instruction of the brief changes, and in Task 3 the check's. No other stage's instruction changes; `scripts/dump_instructions.py` proves it.
- No task makes a live model call. Task 4 holds the steps that do, marked **owner**.

## Review Focus

1. A question with a `]`, a line break or a control character in it. The marker in the file stays one well-formed marker, and what the person is shown is plain text. Test in Task 1.
2. A marker the model writes in a section by itself, against the instruction. It is asked too, with no suggestion. Test in Task 1.
3. An open point with no suggested answer, answered with `=`. Nothing is taken for an answer, and the point stays open. Test in Task 2.
4. A brief off its schema, then a good one, then questions. Each answer is kept beside the question that was shown. Test in Task 2.
5. The lean tier and `--no-input` with open points given. Nothing is asked; the markers stand in the file. Test in Task 2.

---

### Task 1: Open points as data, and the questions read from them

**Files:**
- Modify: `adk_spec/domain/drafts.py`, `adk_spec/domain/convert.py`, `adk_spec/domain/brief_md.py`, `tests/conftest.py`
- Test: `tests/test_convert.py`

**Interfaces:**
- Produces:
  - `OpenPointDraft`: `question: str`, `suggested: str`. `BriefDraft.open_points: list[OpenPointDraft]`.
  - `brief_md.marker_of(question: str) -> str`: the marker for a question, on one line, with no `]` inside it. `brief_md.asked_by(marker: str) -> str`: the question a marker holds, empty where it holds none.
  - `to_brief(draft)`: each open point's marker is added to the assumptions, a paragraph of its own.
  - `convert.questions_of(draft: BriefDraft, brief: Brief) -> list[dict[str, str]]`: one `{"question", "recommended"}` for each marker of the brief as rendered, in order. The suggestion is the open point's whose question the marker holds, and empty where none is: a marker the model wrote in a section itself. A marker with no question is asked as `The brief leaves a point open and names no question.`
  - `tests/conftest.py`: `CANNED_BRIEF` gains `open_points: []`; `BRIEF_WITH_A_MARKER` is the canned brief with one open point, `Which browsers are in scope?`, suggested `Evergreen browsers only`. `CANNED_QUESTIONS` goes.

- [ ] **Step 1: Write the failing tests**

```python
def test_an_open_point_is_a_marker_in_the_briefs_file_and_a_question_with_its_suggestion() -> None:
    draft = BriefDraft.model_validate(BRIEF_WITH_A_MARKER)
    brief = to_brief(draft)
    assert brief.assumptions.endswith("\n\n[NEEDS CLARIFICATION: Which browsers are in scope?]")
    assert parse_brief(render_brief(brief)) == brief and len(markers(render_brief(brief))) == 1
    assert questions_of(draft, brief) == [{"question": "Which browsers are in scope?", "recommended": "Evergreen browsers only"}]

def test_a_question_that_would_break_its_marker_is_kept_whole_on_one_line() -> None:       # Review Focus 1
    # question "Which [evergreen] browsers,\nand since when?" + ESC: one marker, no `]` or control character in it,
    # and the question asked is the marker's own text

def test_a_marker_written_in_a_section_is_asked_too_with_nothing_suggested() -> None:      # Review Focus 2
    # assumptions "... [NEEDS CLARIFICATION: which regions?]" and one open point: two questions, in the file's order

def test_a_marker_with_no_question_is_still_put_to_the_person() -> None:
def test_no_open_point_and_no_marker_is_no_question() -> None:
```

- [ ] **Step 2: Run them.** Expected: FAIL, `cannot import name 'questions_of'`.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the suite.** The clarify tests fail until Task 2: they still call a questions stage. That is the next task; this one is committed with it.

---

### Task 2: The run ends on questions code made, and the stage goes

**Files:**
- Delete: `adk_spec/orchestration/stages/questions.py`
- Modify: `adk_spec/domain/drafts.py` (`Question`, `QuestionsDraft` go), `adk_spec/orchestration/stages/brief.py`, `adk_spec/orchestration/graph.py`, `adk_spec/interfaces/cli.py`, `scripts/dump_instructions.py`, `README.md`
- Test: `tests/test_clarify.py` (rewritten for one stage fewer), `tests/test_recorder.py`, `tests/test_propose.py`

**Interfaces:**
- Consumes: Task 1's `questions_of`.
- Produces:
  - In `graph.py`: `open_points` routes `SOME` to the run's end with `ASKING` set from `questions_of`, and `NONE` on to the deltas. `_pending`, `_unasked`, `_check_questions`, `UNWORDED` and `QUESTION_BUDGET` go: a brief holds three markers at most, so five questions cannot be reached.
  - `propose` no longer needs the `questions` role to be ready, and prints no `note` line.
  - The brief's guide says where an open point goes:

```
A point you cannot settle from the request goes in open_points: the question, worded so a person can answer it in
a sentence, and the answer you would suggest. Three at most. Write no [NEEDS CLARIFICATION] marker yourself.
```

    and its lean line becomes `On the lean tier no question is asked: leave open_points empty there, and state what you assume.`

- [ ] **Step 1: Rewrite `tests/test_clarify.py`** so that every behaviour it holds is asserted with no questions stage: the question shown is the open point's, `=` takes its suggestion, an empty line and an ended input leave the point open and end the asking with the brief kept, three rounds at most, `--no-input` and the lean tier ask nothing, four open points send the brief back, a brief off its schema first does not unpair an answer (Review Focus 4), an open point with nothing suggested answered with `=` stays open (Review Focus 3), Ctrl-C, bytes that are no text, control characters, and a new draft given the brief it replaces. In each, no request's instruction starts with the old stage's opening, and the `tokens` line names no `questions`.
- [ ] **Step 2: Run them.** Expected: FAIL: the graph still calls the questions stage.
- [ ] **Step 3: Implement.**
- [ ] **Step 4: Run the suite.** Expected: all pass. `scripts/dump_instructions.py` shows the brief's instruction changed, the questions' gone, and no other changed.
- [ ] **Step 5: Commit.** `feat: a brief's open points are asked without a second model call`

---

### Task 3: What the second measurement decided

**Files:**
- Modify: `adk_spec/orchestration/stages/check.py`, `docs/measurements/README.md`
- Test: `tests/test_check.py`

**Interfaces:**
- Produces: the check's guide gains `Report every fault you find. One finding does not excuse the next.` Nothing else of it changes.

- [ ] **Step 1: Write the failing test**

```python
def test_the_check_is_told_to_report_every_fault_it_finds(tmp_path, fake_provider) -> None:
    # the second measurement: where the model named one fault it left the next unsaid
    # the instruction sent holds "Report every fault you find. One finding does not excuse the next."
```

- [ ] **Step 2: Run it.** Expected: FAIL on the assertion.
- [ ] **Step 3: Implement.** `scripts/dump_instructions.py` shows the check's instruction changed and no other.
- [ ] **Step 4: Commit.** `feat: the check is told to report every fault, as the second measurement asks`

---

### Task 4: Measured live (owner)

Each step calls a model with the owner's account, on the owner's go-ahead in so many words.

- [ ] **Step 1 (owner, live).** The standard `propose` of the two earlier live runs, word for word, each question answered with `=`. Expected by the design: three calls (brief, brief, deltas) where the last run made four. Record beside the two in `docs/confirmation/2026-11-propose.md`: the calls, the tokens, whether a suggestion came with each open point, and whether the answer was kept.
- [ ] **Step 2 (owner, live).** `uv run python -m scripts.measure --runs 5 --out docs/measurements/2026-11-copilot-gpt-4.1-third.md`: 25 calls on the corrected set. Read the three lists under its table before the table.
- [ ] **Step 3.** Decide from the two, in the measurement file: whether the check now names the planted fault where it also names another, and whether any open point came without a suggestion.

---

## What changed while this plan was executed

Tasks 1 to 3 were built on 21 and 22 November 2026, test first, with no model called.

**Proved by `scripts/dump_instructions.py`, before and after:** the brief's instruction changed, the questions' is
gone, the check's changed by its one sentence, and triage, deltas, design, tasks and verify are byte for byte what
they were.

**Where the code departs from the Interfaces above, each a ruling in the ledger:**

- `questions_of(draft)` takes the draft alone. Every caller passed `to_brief(draft)` beside it, two arguments that
  had to agree with nothing enforcing it.
- A question's suggestion is keyed `suggested`, as the schema names it, not `recommended` as the removed stage did.
- `brief_md.asked_by(marker)` became `asked_in(text)` and `worded(question)`. The question is read by the marker
  pattern's own group: a second parse disagreed with it where a hand-written question ends in a bracket.
- A point named twice, or named and also written as a marker by hand in any section, is one marker and one
  question. The brief a new draft replaces is shown with its markers, and the guide says "keep what it says".
- The brief's guide gained one sentence the plan did not list: "A [NEEDS CLARIFICATION: ...] line in it is a point
  that draft left open: do not copy it. Settle it from an answer, or name it again in open_points." Its "Leave
  every point" became "Name every point".
- A run that asks ends at the graph's own end node, not at the one a caller passes: a chat's renders "nothing
  drafted", and a chat never asks.

**Beside the plan:** `scripts/measure.py` words every list under its table in one place and as plain text, so a
quote that runs over lines no longer breaks the page; the count of findings left out is the length of their list.

**Not proved:** the brief's new instruction has met the suite's fake model alone. Whether a real model fills
`open_points`, with a suggestion each, and writes no marker by hand, is Task 4.

### After the code review

`/code-review` at high effort read the whole range on 22 November 2026: three findings it called important, five
nits. Each fix below was written test first.

**Fixed.**

- **A spent ceiling asked the person anyway.** Asking costs no model call now, so `[limits] max_tokens` no longer
  refused it: the person was asked, answered, and the next brief's refusal threw the answer away. `propose` now
  ends before the question, saying the open points were not put
  (`test_a_spent_ceiling_asks_the_person_nothing`).
- **A marker that is no marker.** `[NEEDS CLARIFICATION: which provider` with no `]`, one with no colon, or one
  misspelt was counted as no open point at all, so it held no approval, or it ran on to the next `]` in the file
  and took what stood between into its question, the appended marker included. The validator has a new error,
  `brief.marker-malformed`, which the brief's gate sends back and `adk-spec validate` reports for a brief edited by
  hand.
- **A brief past its budget was told what only a person can do.** The gate passed on "settle some with its author
  first". It now says how many points are open, how many of them were written as a marker in a section, and to
  name the three that matter most.
- **`=` where nothing is suggested** now says that the point stays open.
- **A left-out finding's file name** reaches the measurement page as plain text.

**Left as they are, each a ruling.**

- A marker the model keeps from the brief it replaces, beside the same point reworded in `open_points`, is two
  markers and two questions, the first with nothing suggested. No rule of text tells a point reworded from a second
  point, and dropping a kept marker could drop a point still open. The hard case, a brief pushed past its budget,
  now gets a sentence the stage can act on. Whether a real model copies markers at all is for Task 4 to show.
- Two markers written by hand with no question are asked as one question that names nothing. Both stay in the brief
  and hold its approval.
- A marker written by hand whose question holds a `]` is cut there, as the marker's grammar always cut it.

## What this plan leaves

Tests as evidence for `verify`; the Gemini arm and Windows, which are the owner's; a measurement that reports a range and not a count.
