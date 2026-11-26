# A typed seam and a loud fake: phase 21

Designed on 26 November 2026 from the audit of 25 November (`docs/reports/2026-11-25-codebase-audit.md`, A1 and A2,
step 3 of its order: no change of behaviour, so the phases after it are safer). The owner said "proceed as
recommended". Both findings were measured again before the design.

## Intent

The checker cannot see the seam the CLI changes most: `cli.py` names the engine's objects `Any` (50 times), as it
imports the engine lazily so that offline commands start without it. A renamed field there fails only at run time, in
whichever test reaches it. And the tests aim the fake model by a stage's opening line, copied into the test: a rule
whose text no longer matches is passed over in silence, and the test runs on the canned answer instead.

## Goals

1. **A1: the seam typed.** The engine's types are imported under `if TYPE_CHECKING:` and named where `Any` stood:
   `UsageLedger`, `Recorder`, `Known`, `Explored`, `Run`, `App`, and `Change`, already imported. Nothing changes at
   run time: the command still starts with no engine module loaded (`test_layering`'s probes).
2. **A2: a rule that never matched is an error.** The `fake_provider` fixture fails a test whose rules include one no
   request matched; `answers_if_asked` sets a default for a stage that may not be asked.

## Non-goals

- The 61 inline and 10 module-level copies of stage openings in the tests: with A2 a reworded opening fails loudly
  where it was copied, which was the risk; importing each from its stage is convenience, left out.
- `_Top.commands`, argparse's private subparsers object: stays `Any`.

## Calls made in the design (the builder's)

- **Measured first:** 3 of 1,274 tests set a rule no request matched. One set a triage rule only to show triage is
  not asked, which `asked()` shows alone: the rule goes. Two strict tests share `planned`'s check rule, a default for
  an `approve` that may not run the check: it becomes `answers_if_asked`.
- **What typing found:** a check made with no model has no ledger. `check` and `verify` already print no tokens line
  then; `approve`'s check and a pass that did not finish now follow them, and a plan always has its ledger. The seam's
  central `_asked` is typed end to end: `(UsageLedger, Recorder) -> App` in, `Run` and `UsageLedger` out (the
  cleanup reviews).
- **The code review's three holes closed:** a `clear()` part-way through a test checks the rules it forgets;
  `planned` excuses its check rule only for the two tests that stop before the check; and a test whose body failed is
  not given a second, misleading teardown error. Left: a rule matched anywhere in an instruction rather than at its
  start, queued answers left unused, and a default that would shadow a later rule of the same text (no test does).
