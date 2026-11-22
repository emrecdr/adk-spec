# The first live reading of a repository's code

Measured on 22 November 2026, on the owner's go-ahead, on gpt-4.1 on Copilot, at commit `ad434cc` (phase 6 with
the fixes of an outside review). Two runs: the labelled `integration` case five times, and one `propose` on a copy
of adk-spec's own repository.

## The labelled case

| Case | Command | Caught | Blocking on nothing planted | Left out, no such quote | Tokens a run | Seconds a run | Failed |
|---|---|---|---|---|---|---|---|
| `integration` | plan | 5/5 | 0 | 0 | 6,333 | 20.2 | 0 |

In every run a kept statement named the file where sign-in starts a session. No statement quoted text that is not in
its file. 15 model calls, as estimated.

## One `propose` on a real repository

A copy of adk-spec at commit `16784d5` (268 tracked files, `cli.py` 1,424 lines), with a short constitution of rules
already true of it. The request:

> Add a --quiet flag to the propose command. With --quiet, propose prints no progress lines while it works and no
> tokens line at the end; it still prints each file it wrote, any refusal, and the next line. Without --quiet
> nothing changes.

9 model calls (triage 1, brief 1, deltas 2 with one retry, scout 1, survey 3, tasks 1), 42,523 tokens, of which the
reading took 30,463. A lean change: brief, one delta, `context.md` with 7 statements, three tasks.

**What was right.** The brief and the delta say what was asked, with the right non-goals and two scenarios. The tasks
put the test first and name real files. Every statement's quote is in its file. The statements found the parser's
definition of `propose`, `_propose`, and how options are added.

**What was wrong, checked against the code by hand.**

1. **A true quote under a wrong note.** "`cli.py:527` The propose command currently outputs progress and token count
   lines", quoting `print(f"tokens    {_spent(made.ledger)}")`. The line is real, and it is in `_approve`. A quote
   found in the file cannot catch this, and neither can a reviewer that reads the statement alone: nothing in it
   says which function the line is in.
2. **The searches never ran.** The scout asked for eleven files and four searches. A round takes files first, and
   five of the files were stage prompts the change does not touch: the searches for `progress`, `token`, `quiet` and
   `propose` were all "past what a round reads". So the reading never reached where `propose` prints its progress
   (`_working`, line 670, which was shown but not stated) and its tokens line (lines 1209 to 1252, never shown).
3. **The test file was missed.** `tests/test_propose.py`, 39 tests, was left out for room; the tasks name
   `tests/test_cli.py`.

## What this changes in phase 7

- **A round makes its searches first**, then lists its folders, then reads its files. A search is small and aimed; a
  whole file is large and often a guess.
- **A statement carries the line that opens the block it stands in**, found by code in the file as it stands:
  `in: def _approve(args: argparse.Namespace) -> int:`. The review is shown it, and can then dispute a note that
  names the wrong function. The design and tasks stages read it in `context.md`.
- The review's extra round is the room the reading needs where it ran short, as here.

## Phase 7's `across` case

Measured the same day, on the owner's go-ahead, at commit `a81dc0c` (phase 7 merged): a web app in the workspace
signs in through an API in a repository beside it, named with the change; the place sign-in starts a session is in
the API, and the web app holds an old file of a similar name that nothing uses.

| Case | Command | Caught | Blocking on nothing planted | Left out, no such quote | Tokens a run | Seconds a run | Failed |
|---|---|---|---|---|---|---|---|
| `across` | plan | 5/5 | 0 | 0 | 11,335 | 55.6 | 0 |

In every run a kept statement named the planted file in the other repository, under its name. No statement quoted
text that is not in its file. About 20 model calls, as estimated; a run costs some twice the `integration` case's,
which reads one repository and has no review.

## Phase 8: `init` on a copy of adk-spec, and the `profile` case

Measured the same day, on the owner's go-ahead, at commit `cd7ce74` (phase 8 merged).

**`init` on a copy of adk-spec.** Up to 7 calls: 11 files read, 14 statements kept, 2 left out, 3 unknown, 6 rules
drafted. Every quote is in its file, and the facts are right: Python 3.14, the pinned versions, the entry point, and
a rule that matters, that no module loads the engine at import time. Two faults, read by hand:

1. **It leaned on the newest feature.** Most statements, and all three unknowns, are about `init` itself rather
   than the repository as a whole.
2. **Most drafted rules were descriptions.** "The command `adk-spec init` creates the `.spec/` folder ..." is what
   is there, not a rule new code follows; some two of the six read as rules, and the notes ran to a paragraph.

| Case | Command | Caught | Blocking on nothing planted | Left out, no such quote | Tokens a run | Seconds a run | Failed |
|---|---|---|---|---|---|---|---|
| `profile` | init | 3/5, 5/5 | 0 | 0 | 7,443 | 41.6 | 0 |

Tests beside the code were found as a convention every time; errors raised as one class three times in five, the
model filing `AppError` under what exists in the other two. The same fault as the second above.

**What it changed.** `init`'s brief asks for the whole repository, not one feature of it, and for each convention
as a rule new code must follow, in one sentence; a drafted rule is its note's first sentence.
