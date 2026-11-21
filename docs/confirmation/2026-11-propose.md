# Task 9: the first live runs of `propose` and `plan`, 21 November 2026

Four commands were run with a real model, on the owner's go-ahead ("go ahead with the live calls"): two `propose`
and two `plan`. **All four ended well**, in 16 model calls and 18,062 tokens.

System: macOS on Apple silicon, Python 3.14, google-adk 2.14.1, LiteLLM 1.106.2, `gpt-4.1` on GitHub Copilot.
The repository was a scratch one: two living specs written by hand (`auth` with two requirements and one retired,
`notifications` with two) and the constitution `init` writes. What the runs wrote is kept beside this file, in
`2026-11-propose-run/`.

## The runs

| # | Command | Calls by stage | Tokens | Time | Sent back by a gate | `validate` |
|---|---|---|---|---|---|---|
| 1 | `propose --tier lean`, a bug fix in `auth` | triage 1, brief 1, deltas 1 | 2,753 | 34 s | nothing | 0 errors, 3 warnings |
| 2 | `propose --tier standard`, a feature across both | triage 1, brief 4, questions 3, deltas 2 | 9,627 | 126 s | the deltas, once | 0 errors, 2 warnings |
| 3 | `plan` on the change of run 1 | tasks 1 | 1,299 | 15 s | nothing | 0 errors, 2 warnings |
| 4 | `plan` on the change of run 2 | design 1, tasks 1 | 4,383 | 43 s | nothing | 0 errors, 1 warning |

The requests, word for word:

1. "Sign-in rejects an email address typed with capital letters. Treat the email address as case-insensitive when a
   user signs in."
2. "Tell a user when someone signs in to their account from a device they have not used before." It leaves unsaid
   how the user is told and what makes a device new. Each question was answered with `=`, which takes the model's
   own suggestion.

In run 2 the four brief calls are the first draft and one new draft after each of three answered rounds. None was
a gate's retry. The one retry of the four commands was the deltas of run 2. The finding that sent them back is
not shown and not kept.

## What the model wrote, as I read it

The owner has not read these yet. The plan asks that they do.

**What held.**

- All six schemas were accepted with a strict JSON schema, and 15 of 16 answers passed their gate at the first try.
- The IDs were right. Run 2 added `REQ-AUTH-004`, past the retired `003`, and `REQ-NOTIFICATIONS-003`.
- The brief of run 1 said what was asked and no more.
- Three rounds of questions ran through separate runs, each answer reaching the next brief. This is the path the
  review of this plan had rebuilt.
- The tasks put a test before the code it tests and name the right requirement IDs. The design has its four
  sections, and each decision names what was weighed against it.

**What did not.**

1. **The asking does not converge.** Each new draft of the brief raised one new open point and never the one
   before: whether users can remove devices, then how a device is identified, then which channels, then, after the
   last round, whether staff are told too. Three rounds were spent and a fourth point was left. A new draft is
   written from the request and the answers alone; it never sees the brief it replaces.
2. **An answer was not honoured.** Round 1's answer was that users can review and remove devices. The final brief
   lists "device removal UI" under Non-goals.
3. **A requirement that did not change was listed as modified.** Run 1's delta carries `REQ-AUTH-002` under
   MODIFIED, word for word as the living spec has it. No finding names this.
4. **A scenario was renamed inside a modified requirement.** The validator caught it, as `delta.drops-scenario`.
5. **The lean brief left a point open**, though the lean tier asks no question. Approval then waits on an edit by
   hand, for a one-line bug fix.
6. **File paths in the tasks are invented**, and differ between the two changes (`tests/auth/` and `auth/tests/`).
   No stage is shown the repository's files. Two tasks are checked by "check the file exists".
7. **The design reads a suggested answer as an existing mechanism**: device fingerprinting "using the existing
   approach", which exists nowhere. That came from taking the model's own suggestion with `=`.

## Decisions

From the three rules the plan gave:

- **A stage that needed a second try in most runs:** none did. One retry in 16 calls.
- **A schema an arm refused outright:** none. `domain/drafts.py` stands for `gpt-4.1`. Gemini is not shown.
- **Tokens for each change:** the largest command spent 9,627. The README's example is now `max_tokens = 30000`,
  about three times that.

`CONTEXT_MAX_CHARS` is unchanged: no call came near it.

For plan 3, in this order:

1. The new draft of a brief is given the brief it replaces, is told to settle the points that were answered, and
   raises every open point at once. This is the first thing to measure on the labelled set, not to tune on one run.
2. A finding for a modified requirement that equals its base, checked in code at the deltas' gate.
3. The recorder keeps each gate's finding, so a retry can be read afterwards.
4. The tasks stage is shown the repository's file tree.
5. Whether the lean tier may leave a point open at all.

## Not run

- The Gemini arm: no key was set.
- Anything on Windows.
- A run with a constitution that says anything of the repository's own.
